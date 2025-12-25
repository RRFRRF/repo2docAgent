"""
仓库工具函数

提供仓库分析相关的辅助函数
"""

import os
from pathlib import Path
from collections import Counter


# 文件扩展名到编程语言的映射
EXTENSION_LANGUAGE_MAP = {
    ".py": "Python",
    ".js": "JavaScript",
    ".jsx": "JavaScript (React)",
    ".ts": "TypeScript",
    ".tsx": "TypeScript (React)",
    ".java": "Java",
    ".go": "Go",
    ".rs": "Rust",
    ".cpp": "C++",
    ".c": "C",
    ".h": "C/C++ Header",
    ".hpp": "C++ Header",
    ".cs": "C#",
    ".rb": "Ruby",
    ".php": "PHP",
    ".swift": "Swift",
    ".kt": "Kotlin",
    ".scala": "Scala",
    ".vue": "Vue",
    ".svelte": "Svelte",
}


def get_file_language(file_path: str) -> str:
    """
    根据文件扩展名获取编程语言
    
    Args:
        file_path: 文件路径
    
    Returns:
        编程语言名称
    """
    ext = Path(file_path).suffix.lower()
    return EXTENSION_LANGUAGE_MAP.get(ext, "Unknown")


def get_repo_language(repo_path: str) -> dict[str, int]:
    """
    分析仓库的主要编程语言
    
    Args:
        repo_path: 仓库路径
    
    Returns:
        语言及其文件数量的字典
    """
    language_counter = Counter()
    
    for root, _, files in os.walk(repo_path):
        # 跳过常见的排除目录
        if any(excluded in root for excluded in [
            ".git", "node_modules", "__pycache__", ".venv", "venv"
        ]):
            continue
        
        for filename in files:
            ext = Path(filename).suffix.lower()
            if ext in EXTENSION_LANGUAGE_MAP:
                language = EXTENSION_LANGUAGE_MAP[ext]
                language_counter[language] += 1
    
    return dict(language_counter.most_common())
