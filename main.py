"""
Repo2Doc Agent 主入口

命令行接口和主程序入口
"""

import argparse
import logging
import sys
from pathlib import Path

from rich.console import Console
from rich.panel import Panel
from rich.progress import Progress, SpinnerColumn, TextColumn

from agent_workflow import create_workflow
from config_loader import Config, setup_logging


console = Console()
logger = logging.getLogger(__name__)


def main():
    """主函数"""
    # 解析命令行参数
    parser = argparse.ArgumentParser(
        description="Repo2Doc Agent - 基于 Agent 的代码库需求文档生成工具",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
示例:
  # 使用默认配置分析仓库
  python main.py /path/to/repo

  # 使用自定义配置
  python main.py /path/to/repo -c config.yaml

  # 指定输出目录
  python main.py /path/to/repo -o ./output
        """
    )
    
    parser.add_argument(
        "repo_path",
        type=str,
        help="要分析的仓库路径"
    )
    
    parser.add_argument(
        "-c", "--config",
        type=str,
        default=None,
        help="配置文件路径（默认使用内置配置）"
    )
    
    parser.add_argument(
        "-o", "--output",
        type=str,
        default=None,
        help="输出目录（覆盖配置文件中的设置）"
    )
    
    parser.add_argument(
        "-v", "--verbose",
        action="store_true",
        help="显示详细日志"
    )
    
    parser.add_argument(
        "-m", "--max-iterations",
        type=int,
        default=None,
        help="最大迭代次数（覆盖配置文件中的设置）"
    )
    
    args = parser.parse_args()
    
    # 验证仓库路径
    repo_path = Path(args.repo_path).resolve()
    if not repo_path.exists():
        console.print(f"[red]错误: 仓库路径不存在: {repo_path}[/red]")
        sys.exit(1)
    
    if not repo_path.is_dir():
        console.print(f"[red]错误: 路径不是目录: {repo_path}[/red]")
        sys.exit(1)
    
    # 查找配置文件
    config_path = args.config
    if config_path is None:
        # 尝试在当前目录查找
        default_config = Path(__file__).parent / "config.yaml"
        if default_config.exists():
            config_path = str(default_config)
    
    # 显示欢迎信息
    console.print(Panel.fit(
        "[bold blue]Repo2Doc Agent[/bold blue]\n"
        "[dim]基于 Agent 的代码库需求文档生成工具[/dim]",
        border_style="blue"
    ))
    
    console.print(f"\n[bold]仓库路径:[/bold] {repo_path}")
    if config_path:
        console.print(f"[bold]配置文件:[/bold] {config_path}")
    console.print()
    
    # 加载配置
    config = Config.load(config_path)
    
    # 设置日志级别
    if args.verbose:
        config.logging.level = "DEBUG"
    
    setup_logging(config.logging)
    
    # 覆盖配置（如果有命令行参数）
    if args.output:
        config.output.output_dir = args.output
    
    if args.max_iterations:
        config.agent.max_iterations = args.max_iterations
    
    # 运行工作流
    try:
        with Progress(
            SpinnerColumn(),
            TextColumn("[progress.description]{task.description}"),
            console=console,
        ) as progress:
            task = progress.add_task("[cyan]正在处理...", total=None)
            
            # 创建并运行工作流
            workflow = create_workflow(config_path)
            
            # 覆盖配置（如果有命令行参数）
            if args.output:
                workflow.config.output.output_dir = args.output
            if args.max_iterations:
                workflow.config.agent.max_iterations = args.max_iterations
            
            final_state = workflow.run(str(repo_path), config_path)
            
            progress.update(task, completed=True)
        
        # 显示结果
        if final_state.get("status") == "completed":
            console.print("\n[bold green]✅ 处理完成！[/bold green]\n")
            
            # 显示统计信息
            console.print("[bold]统计信息:[/bold]")
            console.print(f"  • 迭代次数: {final_state.get('iteration_count', 0)}")
            console.print(f"  • 文档长度: {len(final_state.get('current_document', '')):,} 字符")
            console.print(f"  • 置信度: {final_state.get('confidence_score', 0):.2f}")
            console.print(f"  • 文档版本数: {len(final_state.get('document_versions', []))}")
            
            # 显示输出路径
            output_dir = repo_path / config.output.output_dir
            console.print(f"\n[bold]输出目录:[/bold] {output_dir}")
            console.print(f"[bold]需求文档:[/bold] {output_dir / config.output.filename}")
            
        else:
            console.print("\n[bold red]❌ 处理失败[/bold red]")
            console.print(f"[red]错误: {final_state.get('error')}[/red]")
            sys.exit(1)
            
    except KeyboardInterrupt:
        console.print("\n[yellow]用户中断[/yellow]")
        sys.exit(130)
    except Exception as e:
        console.print("\n[bold red]❌ 发生错误[/bold red]")
        console.print(f"[red]{e}[/red]")
        if args.verbose:
            console.print_exception()
        sys.exit(1)


if __name__ == "__main__":
    main()
