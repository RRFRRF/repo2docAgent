"""
代码分析工具

提供函数、类、文件大纲等代码结构分析功能
"""

import ast
import re
from pathlib import Path
from typing import Optional

from langchain_core.tools import tool


def _parse_python_file(file_path: Path) -> Optional[ast.Module]:
    """解析 Python 文件"""
    try:
        with open(file_path, "r", encoding="utf-8", errors="ignore") as f:
            content = f.read()
        return ast.parse(content)
    except (SyntaxError, Exception):
        return None


def _get_docstring(node) -> str:
    """获取节点的文档字符串"""
    docstring = ast.get_docstring(node)
    return docstring if docstring else ""


def _get_function_signature(node: ast.FunctionDef) -> str:
    """获取函数签名"""
    args = []
    
    # 普通参数
    for arg in node.args.args:
        arg_str = arg.arg
        if arg.annotation:
            arg_str += f": {ast.unparse(arg.annotation)}"
        args.append(arg_str)
    
    # *args
    if node.args.vararg:
        args.append(f"*{node.args.vararg.arg}")
    
    # **kwargs
    if node.args.kwarg:
        args.append(f"**{node.args.kwarg.arg}")
    
    # 返回类型
    returns = ""
    if node.returns:
        returns = f" -> {ast.unparse(node.returns)}"
    
    return f"def {node.name}({', '.join(args)}){returns}"


@tool
def get_file_outline(file_path: str, repo_path: str) -> str:
    """
    获取文件的代码大纲（类、函数列表）。
    
    Args:
        file_path: 相对于仓库根目录的文件路径
        repo_path: 仓库根目录路径
    
    Returns:
        文件的代码大纲
    """
    try:
        full_path = Path(repo_path) / file_path
        
        if not full_path.exists():
            return f"错误：文件不存在: {file_path}"
        
        if not full_path.is_file():
            return f"错误：路径不是文件: {file_path}"
        
        # 目前只支持 Python 文件
        if full_path.suffix not in [".py"]:
            # 对于非 Python 文件，使用正则表达式匹配
            return _get_outline_regex(full_path, file_path)
        
        tree = _parse_python_file(full_path)
        if tree is None:
            return f"错误：无法解析文件: {file_path}"
        
        lines = [f"=== 文件大纲: {file_path} ===\n"]
        
        # 提取导入
        imports = []
        for node in ast.iter_child_nodes(tree):
            if isinstance(node, ast.Import):
                for alias in node.names:
                    imports.append(alias.name)
            elif isinstance(node, ast.ImportFrom):
                module = node.module or ""
                for alias in node.names:
                    imports.append(f"{module}.{alias.name}")
        
        if imports:
            lines.append("## 导入:")
            for imp in imports[:10]:  # 限制数量
                lines.append(f"  - {imp}")
            if len(imports) > 10:
                lines.append(f"  - ... 还有 {len(imports) - 10} 个导入")
            lines.append("")
        
        # 提取类
        classes = [node for node in ast.iter_child_nodes(tree) 
                   if isinstance(node, ast.ClassDef)]
        
        if classes:
            lines.append("## 类:")
            for cls in classes:
                docstring = _get_docstring(cls)
                doc_preview = docstring[:100] + "..." if len(docstring) > 100 else docstring
                lines.append(f"  class {cls.name}")
                if doc_preview:
                    lines.append(f"    \"\"\"{doc_preview}\"\"\"")
                
                # 类方法
                methods = [node for node in ast.iter_child_nodes(cls) 
                          if isinstance(node, ast.FunctionDef)]
                for method in methods[:5]:  # 限制数量
                    lines.append(f"    - {_get_function_signature(method)}")
                if len(methods) > 5:
                    lines.append(f"    - ... 还有 {len(methods) - 5} 个方法")
                lines.append("")
        
        # 提取顶级函数
        functions = [node for node in ast.iter_child_nodes(tree) 
                     if isinstance(node, ast.FunctionDef)]
        
        if functions:
            lines.append("## 函数:")
            for func in functions:
                docstring = _get_docstring(func)
                doc_preview = docstring[:80] + "..." if len(docstring) > 80 else docstring
                lines.append(f"  {_get_function_signature(func)}")
                if doc_preview:
                    lines.append(f"    \"\"\"{doc_preview}\"\"\"")
            lines.append("")
        
        return "\n".join(lines)
    
    except Exception as e:
        return f"错误：获取文件大纲失败: {e}"


def _get_outline_regex(full_path: Path, file_path: str) -> str:
    """使用正则表达式获取非 Python 文件的大纲"""
    try:
        with open(full_path, "r", encoding="utf-8", errors="ignore") as f:
            content = f.read()
        
        lines = [f"=== 文件大纲: {file_path} ===\n"]
        
        # JavaScript/TypeScript 函数和类
        if full_path.suffix in [".js", ".jsx", ".ts", ".tsx"]:
            # 类
            class_pattern = r"(?:export\s+)?class\s+(\w+)"
            classes = re.findall(class_pattern, content)
            if classes:
                lines.append("## 类:")
                for cls in classes[:10]:
                    lines.append(f"  - {cls}")
                lines.append("")
            
            # 函数
            func_pattern = r"(?:export\s+)?(?:async\s+)?function\s+(\w+)"
            functions = re.findall(func_pattern, content)
            if functions:
                lines.append("## 函数:")
                for func in functions[:15]:
                    lines.append(f"  - {func}")
                lines.append("")
            
            # 箭头函数（导出的常量）
            arrow_pattern = r"(?:export\s+)?const\s+(\w+)\s*=\s*(?:async\s+)?\("
            arrows = re.findall(arrow_pattern, content)
            if arrows:
                lines.append("## 箭头函数/常量:")
                for arrow in arrows[:10]:
                    lines.append(f"  - {arrow}")
                lines.append("")
        
        # Java 类和方法
        elif full_path.suffix in [".java"]:
            class_pattern = r"(?:public\s+)?class\s+(\w+)"
            classes = re.findall(class_pattern, content)
            if classes:
                lines.append("## 类:")
                for cls in classes:
                    lines.append(f"  - {cls}")
                lines.append("")
            
            method_pattern = r"(?:public|private|protected)?\s*(?:static\s+)?(?:\w+)\s+(\w+)\s*\("
            methods = re.findall(method_pattern, content)
            if methods:
                lines.append("## 方法:")
                for method in methods[:20]:
                    if method not in ["if", "for", "while", "switch"]:
                        lines.append(f"  - {method}")
                lines.append("")
        
        else:
            lines.append("（暂不支持此文件类型的大纲分析）")
        
        return "\n".join(lines)
    
    except Exception as e:
        return f"错误：获取文件大纲失败: {e}"


@tool
def get_function_info(
    file_path: str, 
    function_name: str, 
    repo_path: str
) -> str:
    """
    获取指定函数的详细信息（定义、文档字符串、实现）。
    
    Args:
        file_path: 相对于仓库根目录的文件路径
        function_name: 函数名称
        repo_path: 仓库根目录路径
    
    Returns:
        函数的详细信息
    """
    try:
        full_path = Path(repo_path) / file_path
        
        if not full_path.exists():
            return f"错误：文件不存在: {file_path}"
        
        if full_path.suffix != ".py":
            # 使用正则表达式匹配非 Python 文件
            return _get_function_regex(full_path, function_name, file_path)
        
        tree = _parse_python_file(full_path)
        if tree is None:
            return f"错误：无法解析文件: {file_path}"
        
        # 查找函数（包括类方法）
        for node in ast.walk(tree):
            if isinstance(node, ast.FunctionDef) and node.name == function_name:
                with open(full_path, "r", encoding="utf-8", errors="ignore") as f:
                    lines = f.readlines()
                
                # 获取函数源代码
                start = node.lineno - 1
                end = node.end_lineno
                source = "".join(lines[start:end])
                
                result = f"=== 函数: {function_name} ===\n"
                result += f"文件: {file_path}\n"
                result += f"行号: {node.lineno}-{node.end_lineno}\n"
                result += f"签名: {_get_function_signature(node)}\n\n"
                
                docstring = _get_docstring(node)
                if docstring:
                    result += f"文档:\n{docstring}\n\n"
                
                result += f"源代码:\n```python\n{source}\n```"
                
                return result
        
        return f"错误：在文件 {file_path} 中未找到函数 {function_name}"
    
    except Exception as e:
        return f"错误：获取函数信息失败: {e}"


def _get_function_regex(full_path: Path, function_name: str, file_path: str) -> str:
    """使用正则表达式获取函数信息"""
    try:
        with open(full_path, "r", encoding="utf-8", errors="ignore") as f:
            content = f.read()
            lines = content.splitlines()
        
        # 简单的函数查找
        pattern = rf"(?:export\s+)?(?:async\s+)?function\s+{function_name}"
        for i, line in enumerate(lines):
            if re.search(pattern, line):
                # 获取函数周围的代码
                start = max(0, i)
                end = min(len(lines), i + 30)
                source = "\n".join(lines[start:end])
                
                result = f"=== 函数: {function_name} ===\n"
                result += f"文件: {file_path}\n"
                result += f"行号: {i + 1}\n\n"
                result += f"源代码:\n```\n{source}\n```"
                
                return result
        
        return f"错误：在文件 {file_path} 中未找到函数 {function_name}"
    
    except Exception as e:
        return f"错误：获取函数信息失败: {e}"


@tool
def get_class_info(
    file_path: str, 
    class_name: str, 
    repo_path: str
) -> str:
    """
    获取指定类的详细信息（定义、文档字符串、方法列表）。
    
    Args:
        file_path: 相对于仓库根目录的文件路径
        class_name: 类名称
        repo_path: 仓库根目录路径
    
    Returns:
        类的详细信息
    """
    try:
        full_path = Path(repo_path) / file_path
        
        if not full_path.exists():
            return f"错误：文件不存在: {file_path}"
        
        if full_path.suffix != ".py":
            return f"错误：暂不支持非 Python 文件的类分析"
        
        tree = _parse_python_file(full_path)
        if tree is None:
            return f"错误：无法解析文件: {file_path}"
        
        # 查找类
        for node in ast.walk(tree):
            if isinstance(node, ast.ClassDef) and node.name == class_name:
                result = f"=== 类: {class_name} ===\n"
                result += f"文件: {file_path}\n"
                result += f"行号: {node.lineno}-{node.end_lineno}\n"
                
                # 基类
                bases = [ast.unparse(base) for base in node.bases]
                if bases:
                    result += f"继承: {', '.join(bases)}\n"
                
                result += "\n"
                
                # 文档字符串
                docstring = _get_docstring(node)
                if docstring:
                    result += f"文档:\n{docstring}\n\n"
                
                # 方法列表
                methods = [n for n in ast.iter_child_nodes(node) 
                          if isinstance(n, ast.FunctionDef)]
                
                if methods:
                    result += "方法:\n"
                    for method in methods:
                        sig = _get_function_signature(method)
                        doc = _get_docstring(method)
                        doc_preview = doc[:50] + "..." if len(doc) > 50 else doc
                        result += f"  - {sig}\n"
                        if doc_preview:
                            result += f"      \"{doc_preview}\"\n"
                
                # 类属性
                attrs = []
                for n in ast.iter_child_nodes(node):
                    if isinstance(n, ast.AnnAssign) and isinstance(n.target, ast.Name):
                        attrs.append(n.target.id)
                    elif isinstance(n, ast.Assign):
                        for target in n.targets:
                            if isinstance(target, ast.Name):
                                attrs.append(target.id)
                
                if attrs:
                    result += f"\n属性: {', '.join(attrs)}\n"
                
                return result
        
        return f"错误：在文件 {file_path} 中未找到类 {class_name}"
    
    except Exception as e:
        return f"错误：获取类信息失败: {e}"
