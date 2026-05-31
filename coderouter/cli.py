"""
CLI命令处理模块 / CLI Command Handler Module

使用argparse实现命令行接口，提供serve、config、stats、test、tui等子命令。
Implements CLI using argparse, providing serve, config, stats, test, tui subcommands.
"""

import argparse
import json
import sys
from typing import Any, Dict, List, Optional

from . import __version__
from .config import (
    load_config, save_config, get_config_path,
    add_model, remove_model, update_model,
    get_enabled_models, validate_config
)
from .server import ProxyServer
from .tracker import CostTracker
from .health import HealthChecker
from .router import Router


def cmd_serve(args: argparse.Namespace) -> None:
    """
    启动API代理服务器 / Start API proxy server

    Args:
        args: 命令行参数 / Command line arguments
    """
    print(f"[CLI] 启动CodeRouter API代理服务器...")
    print(f"[CLI] Starting CodeRouter API proxy server...")

    config = load_config(args.config)

    # 命令行参数覆盖 / Command line argument overrides
    if args.host:
        config["server"]["host"] = args.host
    if args.port:
        config["server"]["port"] = args.port

    server = ProxyServer()
    server.initialize(config)
    server.start(blocking=True)


def cmd_config(args: argparse.Namespace) -> None:
    """
    管理模型配置 / Manage model configuration

    Args:
        args: 命令行参数 / Command line arguments
    """
    config = load_config(args.config)

    if args.action == "show":
        # 显示当前配置 / Show current config
        config_path = get_config_path()
        print(f"[CONFIG] 配置文件路径 / Config path: {config_path}")
        print(json.dumps(config, indent=2, ensure_ascii=False))

    elif args.action == "list":
        # 列出所有模型 / List all models
        models = config.get("models", [])
        if not models:
            print("[CONFIG] 没有配置任何模型 / No models configured")
            return

        print(f"{'名称 / Name':<20} {'优先级 / P':<8} {'启用 / On':<6} {'端点 / Endpoint'}")
        print("-" * 80)
        for model in models:
            name = model.get("name", "?")
            priority = model.get("priority", 999)
            enabled = "是 / Y" if model.get("enabled", True) else "否 / N"
            endpoint = model.get("endpoint", "")
            print(f"{name:<20} {priority:<8} {enabled:<6} {endpoint}")

    elif args.action == "add":
        # 添加模型 / Add model
        if not args.name or not args.endpoint or not args.api_key:
            print("[ERROR] 添加模型需要 --name, --endpoint, --api_key 参数")
            print("[ERROR] Adding model requires --name, --endpoint, --api_key arguments")
            sys.exit(1)

        new_model = {
            "name": args.name,
            "endpoint": args.endpoint,
            "api_key": args.api_key,
            "priority": args.priority if args.priority is not None else 999,
            "cost_per_million_input": args.cost_input if args.cost_input is not None else 0.0,
            "cost_per_million_output": args.cost_output if args.cost_output is not None else 0.0,
            "max_tokens": args.max_tokens if args.max_tokens is not None else 4096,
            "enabled": True
        }

        config = add_model(config, new_model)
        save_config(config)
        print(f"[CONFIG] 已添加模型 '{args.name}' / Model '{args.name}' added")

    elif args.action == "remove":
        # 删除模型 / Remove model
        if not args.name:
            print("[ERROR] 删除模型需要 --name 参数 / Remove model requires --name argument")
            sys.exit(1)

        try:
            config = remove_model(config, args.name)
            save_config(config)
            print(f"[CONFIG] 已删除模型 '{args.name}' / Model '{args.name}' removed")
        except ValueError as e:
            print(f"[ERROR] {e}")
            sys.exit(1)

    elif args.action == "edit":
        # 编辑模型 / Edit model
        if not args.name:
            print("[ERROR] 编辑模型需要 --name 参数 / Edit model requires --name argument")
            sys.exit(1)

        updates: Dict[str, Any] = {}
        if args.endpoint:
            updates["endpoint"] = args.endpoint
        if args.api_key:
            updates["api_key"] = args.api_key
        if args.priority is not None:
            updates["priority"] = args.priority
        if args.cost_input is not None:
            updates["cost_per_million_input"] = args.cost_input
        if args.cost_output is not None:
            updates["cost_per_million_output"] = args.cost_output
        if args.max_tokens is not None:
            updates["max_tokens"] = args.max_tokens
        if args.enabled is not None:
            updates["enabled"] = args.enabled

        if not updates:
            print("[ERROR] 没有指定要更新的字段 / No fields specified for update")
            sys.exit(1)

        try:
            config = update_model(config, args.name, updates)
            save_config(config)
            print(f"[CONFIG] 已更新模型 '{args.name}' / Model '{args.name}' updated")
        except ValueError as e:
            print(f"[ERROR] {e}")
            sys.exit(1)

    elif args.action == "validate":
        # 验证配置 / Validate config
        errors = validate_config(config)
        if errors:
            print("[CONFIG] 配置验证失败 / Config validation failed:")
            for error in errors:
                print(f"  - {error}")
            sys.exit(1)
        else:
            print("[CONFIG] 配置验证通过 / Config validation passed")

    elif args.action == "init":
        # 重新初始化默认配置 / Re-initialize default config
        from .config import DEFAULT_CONFIG
        save_config(DEFAULT_CONFIG)
        print(f"[CONFIG] 已重新初始化默认配置 / Default config re-initialized")


def cmd_stats(args: argparse.Namespace) -> None:
    """
    查看成本统计 / View cost statistics

    Args:
        args: 命令行参数 / Command line arguments
    """
    config = load_config(args.config)
    tracker_config = config.get("tracker", {})

    if not tracker_config.get("enabled", True):
        print("[STATS] 成本追踪未启用 / Cost tracking not enabled")
        return

    tracker = CostTracker(data_file=tracker_config.get("data_file"))

    if args.reset:
        tracker.reset_stats()
        return

    # 显示总体统计 / Show overall summary
    summary = tracker.get_summary()
    print("=" * 60)
    print("  CodeRouter 成本统计 / Cost Statistics")
    print("=" * 60)
    print(f"  总请求数 / Total Requests:      {summary['total_requests']}")
    print(f"  总成本 / Total Cost:            ${summary['total_cost']:.6f}")
    print(f"  总Token / Total Tokens:         {summary['total_tokens']:,}")
    print(f"    输入Token / Input Tokens:      {summary['total_prompt_tokens']:,}")
    print(f"    输出Token / Output Tokens:    {summary['total_completion_tokens']:,}")
    print(f"  成功率 / Success Rate:           {summary['success_rate']}%")
    print(f"  平均延迟 / Avg Latency:          {summary['avg_latency_ms']}ms")
    print()

    # 按模型统计 / Per-model stats
    model_stats = tracker.get_model_stats()
    if model_stats:
        print("-" * 60)
        print(f"  {'模型 / Model':<20} {'请求数 / Req':<10} {'成本 / Cost':<15} {'延迟 / Lat'}")
        print("-" * 60)
        for stat in model_stats:
            print(f"  {stat['model']:<20} {stat['requests']:<10} ${stat['cost']:<14.6f} {stat['avg_latency_ms']:.0f}ms")
        print()

    # 每日统计 / Daily stats
    daily_stats = tracker.get_daily_stats(days=7)
    if daily_stats:
        print("-" * 60)
        print(f"  {'日期 / Date':<12} {'请求数 / Req':<10} {'成本 / Cost':<15} {'成功/失败 / S/F'}")
        print("-" * 60)
        for stat in daily_stats:
            sf = f"{stat['success_count']}/{stat['fail_count']}"
            print(f"  {stat['date']:<12} {stat['requests']:<10} ${stat['cost']:<14.6f} {sf}")
        print()


def cmd_test(args: argparse.Namespace) -> None:
    """
    测试模型连通性 / Test model connectivity

    Args:
        args: 命令行参数 / Command line arguments
    """
    config = load_config(args.config)
    models = get_enabled_models(config)

    if not models:
        print("[TEST] 没有已启用的模型 / No enabled models")
        return

    print(f"[TEST] 开始测试 {len(models)} 个模型端点...")
    print(f"[TEST] Testing {len(models)} model endpoints...")
    print()

    health_checker = HealthChecker()
    for model in models:
        health_checker.add_endpoint(model["name"], model["endpoint"], model["api_key"])

    timeout = args.timeout if args.timeout else 10

    for model in models:
        name = model["name"]
        endpoint = model["endpoint"]
        print(f"  测试中 / Testing: {name} ({endpoint[:50]}...)", end=" ", flush=True)

        success = health_checker.check_endpoint(name, timeout=timeout)
        status = health_checker.get_all_status()
        model_status = next((s for s in status if s["name"] == name), None)

        if success:
            latency = model_status["last_response_time_ms"] if model_status else 0
            print(f"成功 / OK ({latency:.0f}ms)")
        else:
            error = model_status["last_error"] if model_status else "未知错误 / Unknown"
            print(f"失败 / FAIL ({error[:50]})")

    print()
    print("[TEST] 测试完成 / Test complete")

    # 显示汇总 / Show summary
    all_status = health_checker.get_all_status()
    healthy = sum(1 for s in all_status if s["healthy"])
    total = len(all_status)
    print(f"[TEST] 结果 / Results: {healthy}/{total} 健康 / healthy")


def cmd_tui(args: argparse.Namespace) -> None:
    """
    启动TUI界面 / Launch TUI interface

    Args:
        args: 命令行参数 / Command line arguments
    """
    try:
        from .tui import run_tui
        run_tui()
    except ImportError as e:
        print(f"[ERROR] 无法导入TUI模块: {e}")
        print(f"[ERROR] Cannot import TUI module: {e}")
        sys.exit(1)
    except Exception as e:
        print(f"[ERROR] TUI启动失败: {e}")
        print(f"[ERROR] TUI launch failed: {e}")
        sys.exit(1)


def build_parser() -> argparse.ArgumentParser:
    """
    构建命令行参数解析器 / Build CLI argument parser

    Returns:
        argparse.ArgumentParser: 参数解析器 / Argument parser
    """
    parser = argparse.ArgumentParser(
        prog="coderouter",
        description="CodeRouter-CLI — 轻量级终端AI编程模型智能路由引擎",
        epilog="CodeRouter-CLI — Lightweight Terminal AI Model Intelligent Router",
        formatter_class=argparse.RawDescriptionHelpFormatter
    )
    parser.add_argument(
        "-v", "--version",
        action="version",
        version=f"CodeRouter-CLI v{__version__}"
    )
    parser.add_argument(
        "-c", "--config",
        type=str,
        default=None,
        help="配置文件路径 / Config file path (default: ~/.coderouter/config.json)"
    )

    subparsers = parser.add_subparsers(dest="command", help="子命令 / Subcommands")

    # serve 子命令 / serve subcommand
    serve_parser = subparsers.add_parser(
        "serve",
        help="启动API代理服务器 / Start API proxy server",
        description="启动OpenAI兼容的API代理服务器 / Start OpenAI-compatible API proxy server"
    )
    serve_parser.add_argument("--host", type=str, default=None, help="监听地址 / Listen host")
    serve_parser.add_argument("--port", type=int, default=None, help="监听端口 / Listen port")
    serve_parser.set_defaults(func=cmd_serve)

    # config 子命令 / config subcommand
    config_parser = subparsers.add_parser(
        "config",
        help="管理模型配置 / Manage model configuration",
        description="查看、添加、删除、编辑模型配置 / View, add, remove, edit model configs"
    )
    config_parser.add_argument(
        "action",
        choices=["show", "list", "add", "remove", "edit", "validate", "init"],
        help="操作类型 / Action type"
    )
    config_parser.add_argument("--name", type=str, default=None, help="模型名称 / Model name")
    config_parser.add_argument("--endpoint", type=str, default=None, help="API端点 / API endpoint")
    config_parser.add_argument("--api-key", type=str, default=None, help="API密钥 / API key")
    config_parser.add_argument("--priority", type=int, default=None, help="优先级 / Priority")
    config_parser.add_argument("--cost-input", type=float, default=None, help="输入价格($/MToken) / Input cost")
    config_parser.add_argument("--cost-output", type=float, default=None, help="输出价格($/MToken) / Output cost")
    config_parser.add_argument("--max-tokens", type=int, default=None, help="最大Token数 / Max tokens")
    config_parser.add_argument("--enabled", type=lambda x: x.lower() in ("true", "1", "yes"),
                                default=None, help="是否启用 / Enable or disable")
    config_parser.set_defaults(func=cmd_config)

    # stats 子命令 / stats subcommand
    stats_parser = subparsers.add_parser(
        "stats",
        help="查看成本统计 / View cost statistics",
        description="显示Token消耗和成本统计 / Show token consumption and cost statistics"
    )
    stats_parser.add_argument("--reset", action="store_true", help="重置统计数据 / Reset statistics")
    stats_parser.set_defaults(func=cmd_stats)

    # test 子命令 / test subcommand
    test_parser = subparsers.add_parser(
        "test",
        help="测试模型连通性 / Test model connectivity",
        description="检测所有已启用模型端点的可用性 / Check availability of all enabled endpoints"
    )
    test_parser.add_argument("--timeout", type=int, default=10, help="超时时间(秒) / Timeout (seconds)")
    test_parser.set_defaults(func=cmd_test)

    # tui 子命令 / tui subcommand
    tui_parser = subparsers.add_parser(
        "tui",
        help="启动TUI界面 / Launch TUI interface",
        description="启动终端交互管理界面 / Launch terminal interactive management interface"
    )
    tui_parser.set_defaults(func=cmd_tui)

    return parser


def main(argv: Optional[List[str]] = None) -> int:
    """
    CLI主入口函数 / CLI main entry function

    Args:
        argv: 命令行参数列表，为None时使用sys.argv / CLI args list, uses sys.argv if None

    Returns:
        int: 退出码 / Exit code
    """
    parser = build_parser()
    args = parser.parse_args(argv)

    if not args.command:
        parser.print_help()
        return 0

    try:
        args.func(args)
        return 0
    except KeyboardInterrupt:
        print("\n[CLI] 操作已取消 / Operation cancelled")
        return 130
    except Exception as e:
        print(f"[ERROR] {e}")
        return 1
