"""
工具执行节点

解析并执行 Agent 选择的工具调用
"""

import logging
import json
from typing import Any

from langchain_openai import ChatOpenAI
from langchain_core.messages import SystemMessage, HumanMessage

from state import AgentState, ToolCall, ExplorationRecord
from config_loader import Config
from tools.file_tools import get_file_content, list_files_by_extension
from tools.code_tools import get_file_outline, get_function_info, get_class_info
from tools.search_tools import search_code, search_imports
from prompts.agent_prompts import TOOL_SELECTION_PROMPT


logger = logging.getLogger(__name__)


# 工具注册表
TOOL_REGISTRY = {
    "get_file_content": get_file_content,
    "get_file_outline": get_file_outline,
    "get_function_info": get_function_info,
    "get_class_info": get_class_info,
    "search_code": search_code,
    "search_imports": search_imports,
    "list_files_by_extension": list_files_by_extension,
}


def tool_execution_node(state: AgentState, config: Config) -> AgentState:
    """
    工具执行节点
    
    1. 解析检查节点建议的工具调用或让 LLM 选择工具
    2. 执行工具调用
    3. 收集结果更新状态
    
    Args:
        state: 当前状态
        config: 配置对象
    
    Returns:
        更新后的状态
    """
    logger.info("开始执行工具调用...")
    
    repo_path = state["repo_path"]
    
    # 尝试从状态中获取建议的工具调用
    suggested_tools = []
    if state["current_tool_results"]:
        try:
            suggested_tools = json.loads(state["current_tool_results"])
            if isinstance(suggested_tools, list):
                pass  # 已经是列表
            elif isinstance(suggested_tools, dict) and "tool_calls" in suggested_tools:
                suggested_tools = suggested_tools["tool_calls"]
            else:
                suggested_tools = []
        except json.JSONDecodeError:
            suggested_tools = []
    
    # 如果没有建议的工具，使用 LLM 选择
    if not suggested_tools:
        suggested_tools = _select_tools_with_llm(state, config)
    
    # 限制工具调用数量
    max_tools = config.agent.max_tool_calls_per_iteration
    suggested_tools = suggested_tools[:max_tools]
    
    # 执行工具调用
    tool_calls = []
    results = []
    
    for tool_spec in suggested_tools:
        tool_name = tool_spec.get("tool", "")
        args = tool_spec.get("args", {})
        reason = tool_spec.get("reason", "")
        
        if tool_name not in TOOL_REGISTRY:
            logger.warning(f"未知工具: {tool_name}")
            continue
        
        logger.info(f"执行工具: {tool_name}({args})")
        
        try:
            # 注入 repo_path
            args["repo_path"] = repo_path
            
            tool_fn = TOOL_REGISTRY[tool_name]
            result = tool_fn.invoke(args)
            
            tool_calls.append(ToolCall(
                tool_name=tool_name,
                arguments=args,
                result=str(result)[:2000],  # 限制结果长度
                success=True
            ))
            
            results.append(f"### 工具: {tool_name}\n**参数**: {args}\n**原因**: {reason}\n**结果**:\n{result}\n")
            
        except Exception as e:
            logger.error(f"工具执行失败: {e}")
            tool_calls.append(ToolCall(
                tool_name=tool_name,
                arguments=args,
                result=str(e),
                success=False
            ))
            results.append(f"### 工具: {tool_name}\n**错误**: {e}\n")
    
    # 记录探索历史
    exploration = ExplorationRecord(
        iteration=state["iteration_count"],
        action=f"执行了 {len(tool_calls)} 个工具调用",
        findings=f"获取了 {len([t for t in tool_calls if t.success])} 个成功结果",
        tool_calls=tool_calls
    )
    state["exploration_history"].append(exploration)
    
    # 更新状态
    state["current_tool_results"] = "\n\n".join(results)
    state["status"] = "tools_executed"
    
    logger.info(f"工具执行完成，成功 {len([t for t in tool_calls if t.success])}/{len(tool_calls)}")
    
    return state


def _select_tools_with_llm(state: AgentState, config: Config) -> list[dict]:
    """使用 LLM 选择工具"""
    llm = _create_llm(config)
    
    missing_str = "\n".join(f"- {part}" for part in state["missing_parts"]) if state["missing_parts"] else "无具体缺失，需要进一步探索"
    
    messages = [
        SystemMessage(content="你是一个代码分析助手，请选择合适的工具来获取更多信息。请严格返回 JSON 格式。"),
        HumanMessage(content=TOOL_SELECTION_PROMPT.format(
            document=state["current_document"][:2000],  # 限制长度
            missing_parts=missing_str,
            directory_tree=state["directory_tree"],
            max_tools=config.agent.max_tool_calls_per_iteration
        ))
    ]
    
    try:
        response = llm.invoke(messages)
        
        import re
        json_match = re.search(r'\{[\s\S]*\}', response.content)
        
        if json_match:
            result = json.loads(json_match.group())
            return result.get("tool_calls", [])
    
    except Exception as e:
        logger.error(f"LLM 工具选择失败: {e}")
    
    # 默认返回一些基础探索
    return [
        {
            "tool": "list_files_by_extension",
            "args": {"extension": ".py"},
            "reason": "探索 Python 源代码"
        }
    ]


def _create_llm(config: Config) -> ChatOpenAI:
    """创建 LLM 客户端"""
    kwargs = {
        "model": config.llm.model,
        "temperature": config.llm.temperature,
    }
    
    if config.llm.api_key:
        kwargs["api_key"] = config.llm.api_key
    
    if config.llm.base_url:
        kwargs["base_url"] = config.llm.base_url
    
    return ChatOpenAI(**kwargs)
