"""
Agent 提示词模板

定义 Agent 各阶段使用的提示词
"""

# 系统提示词
SYSTEM_PROMPT = """你是一位资深的软件架构师和需求分析师。你的任务是根据代码库的源代码，逆向推导出该项目的需求规格说明书。

## 输出要求

请生成一份结构清晰、内容完整的需求文档，包含以下部分：

### 1. 系统概述
- 系统名称和简介
- 系统的核心目标和价值
- 主要用户群体

### 2. 功能需求
- 核心功能模块
- 每个模块的详细功能点
- 功能之间的关系

### 3. 数据实体
- 核心数据实体定义
- 实体的属性和字段
- 实体之间的关系

### 4. 业务流程
- 主要业务流程描述
- 用户交互流程

### 5. 非功能需求（如果能从代码推断）
- 性能要求
- 安全要求
- 其他约束

## 注意事项
1. 基于代码实际内容进行推断，不要臆造功能
2. 使用清晰的中文描述
3. 保持文档结构的一致性
4. 如果某些信息无法从代码推断，可以标注"待确认"
"""

# 初始文档生成提示词
INITIAL_DOC_PROMPT = """请根据以下仓库的高层信息，生成需求规格说明书的初版。

## 仓库信息

{high_level_info}

## 任务

基于上述高层信息，生成需求文档的初版。请注意：

1. 从 README 中提取项目目标、核心功能描述
2. 从目录结构中推断模块划分
3. 从配置文件中了解项目依赖和技术栈
4. 对于无法确定的部分，标注"待深入分析"

请生成完整的需求文档。
"""

# 文档更新提示词
UPDATE_DOC_PROMPT = """请根据新获取的代码信息，更新需求文档。

## 当前文档

{current_document}

## 新获取的信息

{tool_results}

## 之前识别的缺失部分

{missing_parts}

## 任务

请基于新获取的信息，更新需求文档：

1. 补充之前缺失的部分
2. 修正任何不准确的描述
3. 添加新发现的功能和实体
4. 保持文档结构的完整性

请输出**完整的、更新后的**需求文档。
"""

# 完整性检查提示词
CHECK_COMPLETENESS_PROMPT = """请评估以下需求文档的完整性。

## 当前文档

{document}

## 仓库高层信息

{high_level_info}

## 当前状态

- 当前迭代次数: {iteration}
- 最大迭代次数: {max_iterations}

## 任务

请评估文档的完整性，并以 JSON 格式返回结果：

```json
{{
    "is_complete": true/false,
    "confidence_score": 0.0-1.0,
    "missing_parts": ["缺失部分1", "缺失部分2"],
    "suggested_tools": [
        {{
            "tool": "get_file_content",
            "args": {{"file_path": "path/to/file.py"}},
            "reason": "需要了解具体实现"
        }}
    ],
    "analysis": "简要分析说明"
}}
```

## 评估标准

1. **is_complete**: 如果文档已经涵盖了主要功能、数据实体和业务流程，则为 true
2. **confidence_score**: 对文档质量的信心（0.0-1.0）
3. **missing_parts**: 列出仍然缺失或不清晰的部分
4. **suggested_tools**: 如果需要继续探索，建议使用的工具和参数

## 可用工具

- `get_file_content`: 获取文件内容，参数: file_path
- `get_file_outline`: 获取文件大纲，参数: file_path  
- `get_function_info`: 获取函数详情，参数: file_path, function_name
- `get_class_info`: 获取类详情，参数: file_path, class_name
- `search_code`: 搜索代码，参数: query, file_pattern
- `list_files_by_extension`: 按扩展名列出文件，参数: extension

请返回 JSON 格式的评估结果。
"""

# 工具选择提示词
TOOL_SELECTION_PROMPT = """请根据当前文档状态和缺失信息，选择需要调用的工具。

## 当前文档

{document}

## 缺失部分

{missing_parts}

## 仓库目录结构

{directory_tree}

## 可用工具

1. **get_file_content(file_path)**: 获取文件完整内容
2. **get_file_outline(file_path)**: 获取文件大纲（类、函数列表）
3. **get_function_info(file_path, function_name)**: 获取函数详情
4. **get_class_info(file_path, class_name)**: 获取类详情
5. **search_code(query, file_pattern)**: 搜索代码
6. **list_files_by_extension(extension)**: 按扩展名列出文件

## 任务

请选择最多 {max_tools} 个工具调用，以获取补充文档所需的信息。

以 JSON 格式返回：

```json
{{
    "tool_calls": [
        {{
            "tool": "工具名",
            "args": {{"参数名": "参数值"}},
            "reason": "调用原因"
        }}
    ]
}}
```
"""
