"""
代码搜索工具

提供全局代码搜索、导入搜索等功能
"""

import os
import re
from pathlib import Path
from typing import Optional

from langchain_core.tools import tool


def _should_exclude(path: str, repo_path: str) -> bool:
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
    
    return False


@tool
def search_code(
    query: str, 
    repo_path: str,
    file_pattern: Optional[str] = None,
    max_results: int = 20
) -> str:
    """
    在代码库中搜索包含指定内容的代码。
    
    Args:
        query: 搜索关键词
        repo_path: 仓库根目录路径
        file_pattern: 可选的文件模式（如 "*.py"）
        max_results: 最大结果数，默认为 20
    
    Returns:
        搜索结果，包含文件路径、行号和匹配内容
    """
    try:
        repo = Path(repo_path)
        if not repo.exists():
            return f"错误：目录不存在: {repo_path}"
        
        results = []
        
        for root, _, filenames in os.walk(repo):
            if _should_exclude(root, repo_path):
                continue
            
            for filename in filenames:
                # 检查文件模式
                if file_pattern:
                    if not Path(filename).match(file_pattern.lstrip("*")):
                        continue
                
                file_path = os.path.join(root, filename)
                rel_path = os.path.relpath(file_path, repo_path)
                
                # 跳过二进制文件
                try:
                    with open(file_path, "r", encoding="utf-8", errors="ignore") as f:
                        content = f.read()
                except Exception:
                    continue
                
                # 搜索
                lines = content.splitlines()
                for i, line in enumerate(lines):
                    if query.lower() in line.lower():
                        results.append({
                            "file": rel_path,
                            "line": i + 1,
                            "content": line.strip()[:100]
                        })
                        
                        if len(results) >= max_results:
                            break
                
                if len(results) >= max_results:
                    break
            
            if len(results) >= max_results:
                break
        
        if not results:
            return f"未找到包含 \"{query}\" 的代码"
        
        output = f"=== 搜索 \"{query}\" 的结果（共 {len(results)} 个）===\n\n"
        
        for r in results:
            output += f"{r['file']}:{r['line']}\n"
            output += f"  {r['content']}\n\n"
        
        if len(results) >= max_results:
            output += f"\n（已达到最大结果数 {max_results}，可能还有更多匹配）"
        
        return output
    
    except Exception as e:
        return f"错误：搜索失败: {e}"


@tool
def search_imports(
    module_name: str, 
    repo_path: str,
    max_results: int = 20
) -> str:
    """
    搜索导入指定模块的文件。
    
    Args:
        module_name: 模块名称
        repo_path: 仓库根目录路径
        max_results: 最大结果数，默认为 20
    
    Returns:
        导入该模块的文件列表
    """
    try:
        repo = Path(repo_path)
        if not repo.exists():
            return f"错误：目录不存在: {repo_path}"
        
        results = []
        
        # Python 导入模式
        py_patterns = [
            rf"import\s+{re.escape(module_name)}",
            rf"from\s+{re.escape(module_name)}\s+import",
            rf"from\s+\S+\s+import\s+.*{re.escape(module_name)}",
        ]
        
        # JavaScript/TypeScript 导入模式
        js_patterns = [
            rf"import\s+.*from\s+['\"].*{re.escape(module_name)}.*['\"]",
            rf"require\s*\(\s*['\"].*{re.escape(module_name)}.*['\"]\s*\)",
        ]
        
        for root, _, filenames in os.walk(repo):
            if _should_exclude(root, repo_path):
                continue
            
            for filename in filenames:
                file_path = os.path.join(root, filename)
                rel_path = os.path.relpath(file_path, repo_path)
                
                # 确定使用哪种模式
                ext = Path(filename).suffix
                if ext == ".py":
                    patterns = py_patterns
                elif ext in [".js", ".jsx", ".ts", ".tsx"]:
                    patterns = js_patterns
                else:
                    continue
                
                try:
                    with open(file_path, "r", encoding="utf-8", errors="ignore") as f:
                        content = f.read()
                except Exception:
                    continue
                
                # 搜索导入语句
                for pattern in patterns:
                    matches = re.findall(pattern, content)
                    if matches:
                        results.append({
                            "file": rel_path,
                            "imports": matches[:3]  # 限制每个文件的匹配数
                        })
                        break
                
                if len(results) >= max_results:
                    break
            
            if len(results) >= max_results:
                break
        
        if not results:
            return f"未找到导入 \"{module_name}\" 的文件"
        
        output = f"=== 导入 \"{module_name}\" 的文件（共 {len(results)} 个）===\n\n"
        
        for r in results:
            output += f"{r['file']}\n"
            for imp in r['imports']:
                output += f"  {imp[:80]}\n"
            output += "\n"
        
        if len(results) >= max_results:
            output += f"\n（已达到最大结果数 {max_results}，可能还有更多匹配）"
        
        return output
    
    except Exception as e:
        return f"错误：搜索导入失败: {e}"
