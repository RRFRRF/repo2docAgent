"""
文档生成节点

使用 LLM 生成或更新需求文档
"""

import logging
from typing import Optional

from langchain_openai import ChatOpenAI
from langchain_core.messages import SystemMessage, HumanMessage, AIMessage

from state import AgentState
from config_loader import Config
from prompts.agent_prompts import (
    SYSTEM_PROMPT,
    INITIAL_DOC_PROMPT,
    UPDATE_DOC_PROMPT,
)


logger = logging.getLogger(__name__)


def generate_doc_node(state: AgentState, config: Config) -> AgentState:
    """
    文档生成节点
    
    根据当前信息生成或更新需求文档：
    - 首次调用：基于高层信息生成初版文档
    - 后续调用：基于新工具结果更新文档
    
    Args:
        state: 当前状态
        config: 配置对象
    
    Returns:
        更新后的状态
    """
    logger.info(f"开始生成/更新文档（迭代 {state['iteration_count'] + 1}）...")
    
    # 创建 LLM 客户端
    llm = _create_llm(config)
    
    # 根据是否是首次生成选择不同的策略
    if state["iteration_count"] == 0:
        # 首次生成
        new_document = _generate_initial_doc(
            llm, 
            state["high_level_info"],
            config
        )
    else:
        # 增量更新
        new_document = _update_document(
            llm,
            state["current_document"],
            state["current_tool_results"],
            state["missing_parts"],
            config
        )
    
    # 更新状态
    state["current_document"] = new_document
    state["document_versions"].append(new_document)
    state["iteration_count"] += 1
    state["current_tool_results"] = ""  # 清空工具结果
    state["status"] = "doc_generated"
    
    logger.info(f"文档生成完成，长度: {len(new_document)} 字符")
    
    return state


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


def _generate_initial_doc(
    llm: ChatOpenAI, 
    high_level_info: str,
    config: Config
) -> str:
    """生成初版文档"""
    messages = [
        SystemMessage(content=SYSTEM_PROMPT),
        HumanMessage(content=INITIAL_DOC_PROMPT.format(
            high_level_info=high_level_info
        ))
    ]
    
    response = llm.invoke(messages)
    return response.content


def _update_document(
    llm: ChatOpenAI,
    current_document: str,
    tool_results: str,
    missing_parts: list[str],
    config: Config
) -> str:
    """更新文档"""
    missing_str = "\n".join(f"- {part}" for part in missing_parts) if missing_parts else "无"
    
    messages = [
        SystemMessage(content=SYSTEM_PROMPT),
        HumanMessage(content=UPDATE_DOC_PROMPT.format(
            current_document=current_document,
            tool_results=tool_results,
            missing_parts=missing_str
        ))
    ]
    
    response = llm.invoke(messages)
    return response.content
