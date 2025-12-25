"""
文件操作工具

提供文件内容读取、目录树生成等功能
"""

import os
from pathlib import Path
from typing import Optional

from langchain_core.tools import tool
import pathspec


def _get_gitignore_spec(repo_path: str) -> Optional[pathspec.PathSpec]:
    """获取 .gitignore 规则"""
    gitignore_path = Path(repo_path) / ".gitignore"
    if gitignore_path.exists():
        with open(gitignore_path, "r", encoding="utf-8", errors="ignore") as f:
            patterns = f.read().splitlines()
        return pathspec.PathSpec.from_lines("gitwildmatch", patterns)
    return None


def _should_exclude(path: str, repo_path: str, exclude_patterns: list[str]) -> bool:
    """检查是否应该排除此路径"""
    rel_path = os.path.relpath(path, repo_path)
    
    # 默认排除的目录
    default_excludes = [
        ".git", "__pycache__", "node_modules", ".venv", "venv",
        "dist", "build", ".idea", ".vscode"
    ]
    
    for part in Path(rel_path).parts:
        if part in default_excludes:
            return True
    
    # 检查自定义排除规则
    if exclude_patterns:
        spec = pathspec.PathSpec.from_lines("gitwildmatch", exclude_patterns)
        if spec.match_file(rel_path):
            return True
    
    return False


@tool
def get_file_content(file_path: str, repo_path: str) -> str:
    """
    获取指定文件的内容。
    
    Args:
        file_path: 相对于仓库根目录的文件路径
        repo_path: 仓库根目录路径
    
    Returns:
        文件内容，如果文件不存在或读取失败则返回错误信息
    """
    try:
        full_path = Path(repo_path) / file_path
        
        if not full_path.exists():
            return f"错误：文件不存在: {file_path}"
        
        if not full_path.is_file():
            return f"错误：路径不是文件: {file_path}"
        
        # 检查文件大小
        file_size = full_path.stat().st_size
        if file_size > 100 * 1024:  # 100KB
            return f"错误：文件过大 ({file_size} 字节)，超过 100KB 限制"
        
        with open(full_path, "r", encoding="utf-8", errors="ignore") as f:
            content = f.read()
        
        return f"=== 文件: {file_path} ===\n{content}"
    
    except Exception as e:
        return f"错误：读取文件失败: {e}"


@tool
def get_directory_tree(
    repo_path: str, 
    max_depth: int = 3,
    include_files: bool = True
) -> str:
    """
    获取仓库的目录结构树。
    
    Args:
        repo_path: 仓库根目录路径
        max_depth: 最大深度，默认为 3
        include_files: 是否包含文件，默认为 True
    
    Returns:
        目录结构的树形表示
    """
    try:
        repo = Path(repo_path)
        if not repo.exists():
            return f"错误：目录不存在: {repo_path}"
        
        lines = [repo.name + "/"]
        
        def add_tree(path: Path, prefix: str, depth: int):
            if depth > max_depth:
                return
            
            try:
                entries = sorted(path.iterdir(), key=lambda x: (x.is_file(), x.name.lower()))
            except PermissionError:
                return
            
            # 过滤
            filtered_entries = []
            for entry in entries:
                if _should_exclude(str(entry), repo_path, []):
                    continue
                if entry.is_file() and not include_files:
                    continue
                filtered_entries.append(entry)
            
            for i, entry in enumerate(filtered_entries):
                is_last = i == len(filtered_entries) - 1
                connector = "└── " if is_last else "├── "
                
                if entry.is_dir():
                    lines.append(f"{prefix}{connector}{entry.name}/")
                    extension = "    " if is_last else "│   "
                    add_tree(entry, prefix + extension, depth + 1)
                else:
                    lines.append(f"{prefix}{connector}{entry.name}")
        
        add_tree(repo, "", 1)
        
        return "\n".join(lines)
    
    except Exception as e:
        return f"错误：生成目录树失败: {e}"


@tool
def list_files_by_extension(
    repo_path: str, 
    extension: str,
    max_files: int = 50
) -> str:
    """
    按扩展名列出仓库中的文件。
    
    Args:
        repo_path: 仓库根目录路径
        extension: 文件扩展名（如 ".py"、".js"）
        max_files: 最大返回文件数，默认为 50
    
    Returns:
        匹配扩展名的文件列表
    """
    try:
        repo = Path(repo_path)
        if not repo.exists():
            return f"错误：目录不存在: {repo_path}"
        
        # 确保扩展名以点开头
        if not extension.startswith("."):
            extension = "." + extension
        
        files = []
        for root, _, filenames in os.walk(repo):
            if _should_exclude(root, repo_path, []):
                continue
            
            for filename in filenames:
                if filename.endswith(extension):
                    rel_path = os.path.relpath(os.path.join(root, filename), repo_path)
                    files.append(rel_path)
                    
                    if len(files) >= max_files:
                        break
            
            if len(files) >= max_files:
                break
        
        if not files:
            return f"未找到扩展名为 {extension} 的文件"
        
        result = f"=== 扩展名为 {extension} 的文件（共 {len(files)} 个）===\n"
        result += "\n".join(files)
        
        if len(files) >= max_files:
            result += f"\n\n（已达到最大文件数 {max_files}，可能还有更多文件）"
        
        return result
    
    except Exception as e:
        return f"错误：列出文件失败: {e}"
