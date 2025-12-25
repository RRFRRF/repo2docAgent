"""
初始化节点

收集仓库的高层信息，包括 README、目录结构、配置文件等
"""

import logging
from pathlib import Path
from typing import Optional

from state import AgentState
from config_loader import Config
from tools.file_tools import get_directory_tree


logger = logging.getLogger(__name__)


# 常见的项目配置文件
PROJECT_CONFIG_FILES = [
    "README.md", "readme.md", "README.rst", "README.txt",
    "pyproject.toml", "setup.py", "setup.cfg",
    "package.json", "package-lock.json",
    "pom.xml", "build.gradle", "build.gradle.kts",
    "Cargo.toml",
    "go.mod", "go.sum",
    "Gemfile",
    "composer.json",
    "Makefile", "CMakeLists.txt",
    ".env.example", ".env.sample",
    "docker-compose.yml", "Dockerfile",
    "requirements.txt", "Pipfile",
]

# 文档目录
DOC_DIRS = ["docs", "doc", "documentation", "wiki"]


def init_node(state: AgentState, config: Config) -> AgentState:
    """
    初始化节点：收集仓库高层信息
    
    1. 读取 README 文件
    2. 生成目录结构树
    3. 收集项目配置文件
    4. 汇总高层信息
    
    Args:
        state: 当前状态
        config: 配置对象
    
    Returns:
        更新后的状态
    """
    logger.info("开始初始化，收集仓库信息...")
    
    repo_path = state["repo_path"]
    repo = Path(repo_path)
    
    if not repo.exists():
        state["status"] = "error"
        state["error"] = f"仓库路径不存在: {repo_path}"
        return state
    
    # 1. 读取 README
    readme_content = _read_readme(repo)
    state["readme_content"] = readme_content
    logger.info(f"README 内容长度: {len(readme_content)} 字符")
    
    # 2. 生成目录结构
    directory_tree = get_directory_tree.invoke({
        "repo_path": repo_path,
        "max_depth": 3,
        "include_files": True
    })
    state["directory_tree"] = directory_tree
    logger.info("目录结构生成完成")
    
    # 3. 收集项目配置文件
    project_files = _collect_project_files(repo)
    state["project_files"] = project_files
    logger.info(f"找到 {len(project_files)} 个项目配置文件")
    
    # 4. 读取关键配置文件内容
    config_contents = _read_config_files(repo, project_files)
    
    # 5. 汇总高层信息
    high_level_info = _build_high_level_info(
        readme_content, 
        directory_tree, 
        project_files,
        config_contents
    )
    state["high_level_info"] = high_level_info
    
    state["status"] = "initialized"
    logger.info("初始化完成")
    
    return state


def _read_readme(repo: Path) -> str:
    """读取 README 文件"""
    readme_patterns = ["README.md", "readme.md", "README.rst", "README.txt", "README"]
    
    for pattern in readme_patterns:
        readme_path = repo / pattern
        if readme_path.exists():
            try:
                with open(readme_path, "r", encoding="utf-8", errors="ignore") as f:
                    content = f.read()
                # 限制长度
                if len(content) > 10000:
                    content = content[:10000] + "\n\n... (内容已截断)"
                return content
            except Exception as e:
                logger.warning(f"读取 README 失败: {e}")
    
    return "（未找到 README 文件）"


def _collect_project_files(repo: Path) -> list[str]:
    """收集项目配置文件"""
    found_files = []
    
    for filename in PROJECT_CONFIG_FILES:
        file_path = repo / filename
        if file_path.exists():
            found_files.append(filename)
    
    # 检查文档目录
    for doc_dir in DOC_DIRS:
        doc_path = repo / doc_dir
        if doc_path.exists() and doc_path.is_dir():
            found_files.append(f"{doc_dir}/")
    
    return found_files


def _read_config_files(repo: Path, project_files: list[str]) -> dict[str, str]:
    """读取关键配置文件内容"""
    config_contents = {}
    
    # 只读取重要的配置文件
    important_files = [
        "pyproject.toml", "package.json", "pom.xml", 
        "build.gradle", "Cargo.toml", "go.mod"
    ]
    
    for filename in project_files:
        if filename in important_files:
            file_path = repo / filename
            try:
                with open(file_path, "r", encoding="utf-8", errors="ignore") as f:
                    content = f.read()
                # 限制长度
                if len(content) > 3000:
                    content = content[:3000] + "\n... (内容已截断)"
                config_contents[filename] = content
            except Exception:
                pass
    
    return config_contents


def _build_high_level_info(
    readme: str, 
    tree: str, 
    files: list[str],
    config_contents: dict[str, str]
) -> str:
    """构建高层信息汇总"""
    info = []
    
    info.append("# 仓库高层信息\n")
    
    # README
    info.append("## README\n")
    if readme and readme != "（未找到 README 文件）":
        # 只取 README 的前部分
        readme_preview = readme[:3000]
        if len(readme) > 3000:
            readme_preview += "\n\n... (README 内容已截断)"
        info.append(readme_preview)
    else:
        info.append("（未找到 README 文件）")
    info.append("\n")
    
    # 目录结构
    info.append("## 目录结构\n")
    info.append("```")
    info.append(tree)
    info.append("```\n")
    
    # 项目配置文件
    info.append("## 项目配置文件\n")
    for f in files:
        info.append(f"- {f}")
    info.append("\n")
    
    # 关键配置内容
    if config_contents:
        info.append("## 关键配置内容\n")
        for filename, content in config_contents.items():
            info.append(f"### {filename}\n")
            info.append(f"```")
            info.append(content)
            info.append("```\n")
    
    return "\n".join(info)
