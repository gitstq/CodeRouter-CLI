"""
TUI配置界面 / TUI Configuration Interface

使用curses库实现终端交互界面，提供模型管理、状态查看、成本统计等功能。
Terminal interactive interface using curses library, providing model management,
status viewing, cost statistics and other features.

注意: curses在Windows上可能不可用，需要使用windows-curses包。
Note: curses may not be available on Windows, requires windows-curses package.
"""

import curses
import curses.textpad
import time
from typing import Any, Dict, List, Optional

from .config import load_config, save_config, add_model, remove_model, update_model
from .tracker import CostTracker
from .health import HealthChecker


class TUIApp:
    """
    TUI应用程序 / TUI Application

    基于curses的终端交互界面，用于管理CodeRouter配置和查看状态。
    Curses-based terminal interactive interface for managing CodeRouter
    configuration and viewing status.
    """

    # 颜色定义 / Color definitions
    COLOR_HEADER = 1
    COLOR_HIGHLIGHT = 2
    COLOR_SUCCESS = 3
    COLOR_ERROR = 4
    COLOR_WARNING = 5
    COLOR_INFO = 6

    def __init__(self) -> None:
        """
        初始化TUI应用 / Initialize TUI application
        """
        self.stdscr: Optional[curses.window] = None
        self.config: Dict[str, Any] = {}
        self.tracker: Optional[CostTracker] = None
        self.health_checker: Optional[HealthChecker] = None
        self.current_tab: int = 0
        self.selected_index: int = 0
        self.running: bool = True
        self.message: str = ""
        self.message_time: float = 0
        self.tabs: List[str] = [
            "模型列表 / Models",
            "成本统计 / Stats",
            "请求日志 / Logs",
            "配置编辑 / Config"
        ]

    def _init_colors(self) -> None:
        """
        初始化颜色 / Initialize colors
        """
        curses.start_color()
        curses.use_default_colors()
        curses.init_pair(self.COLOR_HEADER, curses.COLOR_WHITE, curses.COLOR_BLUE)
        curses.init_pair(self.COLOR_HIGHLIGHT, curses.COLOR_BLACK, curses.COLOR_CYAN)
        curses.init_pair(self.COLOR_SUCCESS, curses.COLOR_GREEN, curses.COLOR_BLACK)
        curses.init_pair(self.COLOR_ERROR, curses.COLOR_RED, curses.COLOR_BLACK)
        curses.init_pair(self.COLOR_WARNING, curses.COLOR_YELLOW, curses.COLOR_BLACK)
        curses.init_pair(self.COLOR_INFO, curses.COLOR_CYAN, curses.COLOR_BLACK)

    def _draw_header(self) -> None:
        """
        绘制头部 / Draw header
        """
        if self.stdscr is None:
            return
        height, width = self.stdscr.getmaxyx()
        header_text = " CodeRouter-CLI v1.0.0 | AI模型智能路由引擎 / AI Model Intelligent Router "
        try:
            self.stdscr.addstr(0, 0, header_text.ljust(width), curses.color_pair(self.COLOR_HEADER))
        except curses.error:
            pass

    def _draw_tabs(self) -> None:
        """
        绘制标签栏 / Draw tab bar
        """
        if self.stdscr is None:
            return
        height, width = self.stdscr.getmaxyx()

        x = 0
        for i, tab in enumerate(self.tabs):
            tab_text = f" {tab} "
            if i == self.current_tab:
                try:
                    self.stdscr.addstr(1, x, tab_text, curses.color_pair(self.COLOR_HIGHLIGHT))
                except curses.error:
                    pass
            else:
                try:
                    self.stdscr.addstr(1, x, tab_text)
                except curses.error:
                    pass
            x += len(tab_text) + 1

    def _draw_status_bar(self) -> None:
        """
        绘制状态栏 / Draw status bar
        """
        if self.stdscr is None:
            return
        height, width = self.stdscr.getmaxyx()

        status_parts = [
            "Tab: 切换面板 / Switch",
            "↑↓: 选择 / Select",
            "A: 添加 / Add",
            "D: 删除 / Delete",
            "E: 编辑 / Edit",
            "R: 刷新 / Refresh",
            "Q: 退出 / Quit"
        ]
        status_text = " | ".join(status_parts)

        try:
            self.stdscr.addstr(height - 2, 0, status_text.ljust(width), curses.A_REVERSE)
        except curses.error:
            pass

        # 显示消息 / Show message
        if self.message and (time.time() - self.message_time) < 5:
            try:
                self.stdscr.addstr(height - 1, 0, self.message.ljust(width), curses.color_pair(self.COLOR_INFO))
            except curses.error:
                pass

    def _draw_models_tab(self) -> None:
        """
        绘制模型列表面板 / Draw models list panel
        """
        if self.stdscr is None:
            return
        height, width = self.stdscr.getmaxyx()
        models = self.config.get("models", [])

        y = 3
        try:
            self.stdscr.addstr(y, 0, f"{'名称 / Name':<20} {'端点 / Endpoint':<40} {'优先级 / P':<8} {'状态 / Status':<10}")
            y += 1
            self.stdscr.addstr(y, 0, "-" * min(width - 1, 80))
            y += 1

            for i, model in enumerate(models):
                name = model.get("name", "unknown")[:18]
                endpoint = model.get("endpoint", "")[:38]
                priority = str(model.get("priority", 999))
                enabled = "启用 / ON" if model.get("enabled", True) else "禁用 / OFF"

                is_healthy = True
                if self.health_checker:
                    is_healthy = self.health_checker.is_healthy(model["name"])
                health_status = "健康 / OK" if is_healthy else "异常 / ERR"

                line = f"{name:<20} {endpoint:<40} {priority:<8} {enabled:<10} {health_status}"

                if i == self.selected_index:
                    try:
                        self.stdscr.addstr(y, 0, line[:width - 1], curses.color_pair(self.COLOR_HIGHLIGHT))
                    except curses.error:
                        pass
                else:
                    color = curses.color_pair(self.COLOR_SUCCESS) if is_healthy else curses.color_pair(self.COLOR_ERROR)
                    try:
                        self.stdscr.addstr(y, 0, line[:width - 1], color)
                    except curses.error:
                        pass
                y += 1

            if not models:
                try:
                    self.stdscr.addstr(y, 0, "  (无模型配置，按 A 添加 / No models, press A to add)")
                except curses.error:
                    pass

        except curses.error:
            pass

    def _draw_stats_tab(self) -> None:
        """
        绘制成本统计面板 / Draw cost statistics panel
        """
        if self.stdscr is None:
            return
        height, width = self.stdscr.getmaxyx()

        y = 3
        try:
            if self.tracker is None:
                self.stdscr.addstr(y, 0, "成本追踪未启用 / Cost tracking not enabled")
                return

            # 总体统计 / Overall summary
            summary = self.tracker.get_summary()
            self.stdscr.addstr(y, 0, "=== 总体统计 / Overall Summary ===")
            y += 1
            self.stdscr.addstr(y, 0, f"  总请求数 / Total Requests:    {summary['total_requests']}")
            y += 1
            self.stdscr.addstr(y, 0, f"  总成本 / Total Cost:         ${summary['total_cost']:.6f}")
            y += 1
            self.stdscr.addstr(y, 0, f"  总Token / Total Tokens:      {summary['total_tokens']}")
            y += 1
            self.stdscr.addstr(y, 0, f"  成功率 / Success Rate:       {summary['success_rate']}%")
            y += 1
            self.stdscr.addstr(y, 0, f"  平均延迟 / Avg Latency:      {summary['avg_latency_ms']}ms")
            y += 1

            y += 1
            self.stdscr.addstr(y, 0, "=== 按模型统计 / Per-Model Stats ===")
            y += 1

            model_stats = self.tracker.get_model_stats()
            for stat in model_stats:
                if y >= height - 3:
                    break
                self.stdscr.addstr(y, 0, f"  {stat['model']:<20} 请求:{stat['requests']}  成本:${stat['cost']:.6f}")
                y += 1

            y += 1
            self.stdscr.addstr(y, 0, "=== 每日统计 / Daily Stats (最近7天 / Last 7 days) ===")
            y += 1

            daily_stats = self.tracker.get_daily_stats(days=7)
            for stat in daily_stats:
                if y >= height - 3:
                    break
                self.stdscr.addstr(y, 0,
                    f"  {stat['date']}  请求:{stat['requests']}  成本:${stat['cost']:.6f}")
                y += 1

        except curses.error:
            pass

    def _draw_logs_tab(self) -> None:
        """
        绘制请求日志面板 / Draw request logs panel
        """
        if self.stdscr is None:
            return
        height, width = self.stdscr.getmaxyx()

        y = 3
        try:
            self.stdscr.addstr(y, 0, "=== 最近请求日志 / Recent Request Logs ===")
            y += 1

            if self.tracker is None:
                self.stdscr.addstr(y, 0, "  (无日志数据 / No log data)")
                return

            recent = self.tracker.get_recent_requests(limit=height - 6)
            for entry in recent:
                if y >= height - 3:
                    break
                ts = entry.get("timestamp", "")[:19]
                model = entry.get("model", "?")[:15]
                success = "OK" if entry.get("success", True) else "FAIL"
                tokens = entry.get("total_tokens", 0)
                cost = entry.get("total_cost", 0)
                latency = entry.get("latency_ms", 0)

                color = curses.color_pair(self.COLOR_SUCCESS) if success == "OK" else curses.color_pair(self.COLOR_ERROR)
                line = f"  {ts} | {model:<15} | {success:<4} | tokens:{tokens:<6} | ${cost:.6f} | {latency:.0f}ms"
                try:
                    self.stdscr.addstr(y, 0, line[:width - 1], color)
                except curses.error:
                    pass
                y += 1

        except curses.error:
            pass

    def _draw_config_tab(self) -> None:
        """
        绘制配置编辑面板 / Draw config edit panel
        """
        if self.stdscr is None:
            return
        height, width = self.stdscr.getmaxyx()

        y = 3
        try:
            server = self.config.get("server", {})
            routing = self.config.get("routing", {})
            tracker = self.config.get("tracker", {})

            self.stdscr.addstr(y, 0, "=== 服务器配置 / Server Config ===")
            y += 1
            self.stdscr.addstr(y, 0, f"  监听地址 / Host:    {server.get('host', '127.0.0.1')}")
            y += 1
            self.stdscr.addstr(y, 0, f"  监听端口 / Port:    {server.get('port', 8199)}")
            y += 1

            y += 1
            self.stdscr.addstr(y, 0, "=== 路由配置 / Routing Config ===")
            y += 1
            self.stdscr.addstr(y, 0, f"  策略 / Strategy:    {routing.get('strategy', 'priority')}")
            y += 1
            self.stdscr.addstr(y, 0, f"  超时 / Timeout:      {routing.get('timeout', 30)}s")
            y += 1
            self.stdscr.addstr(y, 0, f"  最大重试 / Retries:  {routing.get('max_retries', 3)}")
            y += 1
            self.stdscr.addstr(y, 0, f"  健康检测间隔 / HC:   {routing.get('health_check_interval', 60)}s")
            y += 1

            y += 1
            self.stdscr.addstr(y, 0, "=== 追踪配置 / Tracker Config ===")
            y += 1
            self.stdscr.addstr(y, 0, f"  启用 / Enabled:     {tracker.get('enabled', True)}")
            y += 1
            self.stdscr.addstr(y, 0, f"  数据文件 / File:    {tracker.get('data_file', '~/.coderouter/stats.json')}")
            y += 1

            y += 1
            self.stdscr.addstr(y, 0, "  配置文件路径 / Config path: ~/.coderouter/config.json")
            y += 1
            self.stdscr.addstr(y, 0, "  (配置编辑请使用 'coderouter config' 命令)")
            y += 1
            self.stdscr.addstr(y, 0, "  (Use 'coderouter config' command to edit config)")

        except curses.error:
            pass

    def _draw(self) -> None:
        """
        绘制整个界面 / Draw entire interface
        """
        if self.stdscr is None:
            return
        self.stdscr.clear()
        self._draw_header()
        self._draw_tabs()

        if self.current_tab == 0:
            self._draw_models_tab()
        elif self.current_tab == 1:
            self._draw_stats_tab()
        elif self.current_tab == 2:
            self._draw_logs_tab()
        elif self.current_tab == 3:
            self._draw_config_tab()

        self._draw_status_bar()
        self.stdscr.refresh()

    def _show_message(self, msg: str) -> None:
        """
        显示临时消息 / Show temporary message

        Args:
            msg: 消息内容 / Message content
        """
        self.message = msg
        self.message_time = time.time()

    def _add_model_dialog(self) -> None:
        """
        显示添加模型对话框 / Show add model dialog
        """
        if self.stdscr is None:
            return
        height, width = self.stdscr.getmaxyx()

        # 创建对话框窗口 / Create dialog window
        dialog_height = 12
        dialog_width = 60
        dialog_y = (height - dialog_height) // 2
        dialog_x = (width - dialog_width) // 2

        dialog = curses.newwin(dialog_height, dialog_width, dialog_y, dialog_x)
        dialog.box()
        dialog.keypad(True)

        fields = [
            ("名称 / Name", "new-model"),
            ("端点 / Endpoint", "https://api.example.com/v1/chat/completions"),
            ("API Key", "sk-xxx"),
            ("优先级 / Priority", "1"),
            ("输入价格 / Input $/M", "2.5"),
            ("输出价格 / Output $/M", "10.0"),
        ]

        values: List[str] = [f[1] for f in fields]
        current_field = 0

        while True:
            dialog.clear()
            dialog.box()
            dialog.addstr(0, 2, " 添加模型 / Add Model ")

            for i, (label, _) in enumerate(fields):
                prefix = "> " if i == current_field else "  "
                dialog.addstr(i + 1, 1, f"{prefix}{label}:")
                dialog.addstr(i + 1, 1 + len(label) + 4, values[i][:dialog_width - len(label) - 8])

            dialog.addstr(dialog_height - 2, 2, "Enter:确认 / OK  Esc:取消 / Cancel")
            dialog.refresh()

            key = dialog.getch()
            if key == 27:  # ESC
                break
            elif key == curses.KEY_UP:
                current_field = max(0, current_field - 1)
            elif key == curses.KEY_DOWN:
                current_field = min(len(fields) - 1, current_field + 1)
            elif key == 10:  # Enter
                try:
                    new_model = {
                        "name": values[0],
                        "endpoint": values[1],
                        "api_key": values[2],
                        "priority": int(values[3]),
                        "cost_per_million_input": float(values[4]),
                        "cost_per_million_output": float(values[5]),
                        "max_tokens": 4096,
                        "enabled": True
                    }
                    self.config = add_model(self.config, new_model)
                    save_config(self.config)
                    self._show_message(f"已添加模型 '{values[0]}' / Model '{values[0]}' added")
                except (ValueError, TypeError) as e:
                    self._show_message(f"输入错误: {e} / Input error: {e}")
                break
            elif key == curses.KEY_BACKSPACE or key == 127:
                if values[current_field]:
                    values[current_field] = values[current_field][:-1]
            elif 32 <= key <= 126:
                values[current_field] += chr(key)

    def _delete_model(self) -> None:
        """
        删除选中的模型 / Delete selected model
        """
        models = self.config.get("models", [])
        if 0 <= self.selected_index < len(models):
            name = models[self.selected_index].get("name", "")
            self.config = remove_model(self.config, name)
            save_config(self.config)
            self.selected_index = max(0, self.selected_index - 1)
            self._show_message(f"已删除模型 '{name}' / Model '{name}' deleted")

    def _toggle_model(self) -> None:
        """
        切换选中模型的启用状态 / Toggle selected model's enabled status
        """
        models = self.config.get("models", [])
        if 0 <= self.selected_index < len(models):
            name = models[self.selected_index].get("name", "")
            current = models[self.selected_index].get("enabled", True)
            self.config = update_model(self.config, name, {"enabled": not current})
            save_config(self.config)
            status = "启用 / Enabled" if not current else "禁用 / Disabled"
            self._show_message(f"模型 '{name}' 已{status}")

    def run(self) -> None:
        """
        运行TUI应用 / Run TUI application
        """
        try:
            self.stdscr = curses.initscr()
            curses.noecho()
            curses.cbreak()
            self.stdscr.keypad(True)
            curses.curs_set(0)
            self._init_colors()

            # 加载配置 / Load config
            self.config = load_config()

            # 初始化追踪器 / Initialize tracker
            tracker_config = self.config.get("tracker", {})
            if tracker_config.get("enabled", True):
                self.tracker = CostTracker(data_file=tracker_config.get("data_file"))

            # 初始化健康检测器 / Initialize health checker
            routing_config = self.config.get("routing", {})
            self.health_checker = HealthChecker(
                check_interval=routing_config.get("health_check_interval", 60)
            )
            for model in self.config.get("models", []):
                if model.get("enabled", True):
                    self.health_checker.add_endpoint(
                        model["name"], model["endpoint"], model["api_key"]
                    )

            while self.running:
                self._draw()

                key = self.stdscr.getch()

                if key == ord('q') or key == ord('Q'):
                    self.running = False
                elif key == 9:  # Tab
                    self.current_tab = (self.current_tab + 1) % len(self.tabs)
                    self.selected_index = 0
                elif key == curses.KEY_UP:
                    self.selected_index = max(0, self.selected_index - 1)
                elif key == curses.KEY_DOWN:
                    models = self.config.get("models", [])
                    max_index = len(models) - 1 if self.current_tab == 0 else 0
                    self.selected_index = min(max_index, self.selected_index + 1)
                elif key == ord('a') or key == ord('A'):
                    if self.current_tab == 0:
                        self._add_model_dialog()
                elif key == ord('d') or key == ord('D'):
                    if self.current_tab == 0:
                        self._delete_model()
                elif key == ord('e') or key == ord('E'):
                    if self.current_tab == 0:
                        self._toggle_model()
                elif key == ord('r') or key == ord('R'):
                    self.config = load_config()
                    self._show_message("配置已刷新 / Config refreshed")

        except curses.error:
            pass
        finally:
            if self.stdscr:
                curses.nocbreak()
                self.stdscr.keypad(False)
                curses.echo()
                curses.endwin()


def run_tui() -> None:
    """
    启动TUI界面 / Launch TUI interface

    这是TUI模块的入口函数。
    This is the entry function for the TUI module.
    """
    app = TUIApp()
    app.run()
