# Repo2Doc Agent

基于 LangGraph 的 Agent 驱动代码库需求文档生成工具。

## 概述

Repo2Doc Agent 采用 **Agent 主动探索**方案，与传统增量式方案不同：

- Agent 自主调用工具探索代码库
- 自主判断文档完整性
- 迭代更新直到满意

## 安装

```bash
cd repo2docAgent
uv sync
```

## 配置

1. 复制环境变量示例文件：

```bash
cp .env.example .env
```

2. 编辑 `.env`，设置 API 密钥：

```bash
OPENAI_API_KEY="your-api-key-here"
```

3. 可选：编辑 `config.yaml` 自定义配置

## 使用

```bash
# 基本用法
uv run python main.py /path/to/repo

# 详细模式
uv run python main.py /path/to/repo -v

# 指定配置
uv run python main.py /path/to/repo -c config.yaml
```

## 输出

运行后会在仓库目录下生成：

```
repo2doc-output/
├── requirements.md           # 最终需求文档
└── intermediate/             # 中间结果（如果启用）
```

## 许可证

MIT License
