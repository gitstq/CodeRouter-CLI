"""
成本追踪引擎 / Cost Tracking Engine

记录每次请求的Token消耗和成本，支持日/周/月统计和按模型分类汇总。
Records token consumption and cost per request, supports daily/weekly/monthly
statistics and per-model category summaries.

数据持久化到JSON文件 / Data persisted to JSON file
"""

import json
import os
import time
from datetime import datetime, timedelta
from typing import Any, Dict, List, Optional

from .config import get_stats_path


class CostTracker:
    """
    成本追踪器 / Cost Tracker

    负责记录、计算和统计AI模型调用的Token消耗和成本。
    Responsible for recording, calculating and summarizing token consumption
    and costs of AI model invocations.
    """

    def __init__(self, data_file: Optional[str] = None) -> None:
        """
        初始化成本追踪器 / Initialize cost tracker

        Args:
            data_file: 统计数据文件路径 / Stats data file path
        """
        self.data_file: str = data_file or get_stats_path()
        self._data: Dict[str, Any] = self._load_data()

    def _load_data(self) -> Dict[str, Any]:
        """
        加载统计数据 / Load statistics data

        Returns:
            Dict[str, Any]: 统计数据字典 / Statistics data dict
        """
        data_path = os.path.expanduser(self.data_file)
        if os.path.exists(data_path):
            try:
                with open(data_path, "r", encoding="utf-8") as f:
                    return json.load(f)
            except (json.JSONDecodeError, OSError) as e:
                print(f"[WARN] 加载统计数据失败，将创建新文件: {e}")
                print(f"[WARN] Failed to load stats data, will create new file: {e}")
        # 返回空数据结构 / Return empty data structure
        return {
            "requests": [],
            "summary": {
                "total_requests": 0,
                "total_cost": 0.0,
                "total_prompt_tokens": 0,
                "total_completion_tokens": 0
            }
        }

    def _save_data(self) -> None:
        """
        保存统计数据到文件 / Save statistics data to file

        Raises:
            OSError: 文件写入失败时 / When file write fails
        """
        data_path = os.path.expanduser(self.data_file)
        data_dir = os.path.dirname(data_path)
        os.makedirs(data_dir, exist_ok=True)

        with open(data_path, "w", encoding="utf-8") as f:
            json.dump(self._data, f, indent=2, ensure_ascii=False)

    def record_request(
        self,
        model_name: str,
        prompt_tokens: int,
        completion_tokens: int,
        cost_per_million_input: float = 0.0,
        cost_per_million_output: float = 0.0,
        success: bool = True,
        latency_ms: float = 0.0,
        error: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        记录一次请求 / Record a request

        Args:
            model_name: 模型名称 / Model name
            prompt_tokens: 输入Token数 / Input token count
            completion_tokens: 输出Token数 / Output token count
            cost_per_million_input: 每百万输入Token价格 / Cost per million input tokens
            cost_per_million_output: 每百万输出Token价格 / Cost per million output tokens
            success: 请求是否成功 / Whether request succeeded
            latency_ms: 请求延迟（毫秒）/ Request latency in milliseconds
            error: 错误信息（如果失败）/ Error message if failed

        Returns:
            Dict[str, Any]: 记录的请求条目 / Recorded request entry
        """
        # 计算成本 / Calculate cost
        input_cost = (prompt_tokens / 1_000_000) * cost_per_million_input
        output_cost = (completion_tokens / 1_000_000) * cost_per_million_output
        total_cost = input_cost + output_cost

        entry: Dict[str, Any] = {
            "timestamp": datetime.now().isoformat(),
            "model": model_name,
            "prompt_tokens": prompt_tokens,
            "completion_tokens": completion_tokens,
            "total_tokens": prompt_tokens + completion_tokens,
            "input_cost": round(input_cost, 6),
            "output_cost": round(output_cost, 6),
            "total_cost": round(total_cost, 6),
            "success": success,
            "latency_ms": round(latency_ms, 2),
            "error": error
        }

        self._data["requests"].append(entry)

        # 更新汇总 / Update summary
        self._data["summary"]["total_requests"] = len(self._data["requests"])
        self._data["summary"]["total_cost"] = round(
            self._data["summary"]["total_cost"] + total_cost, 6
        )
        self._data["summary"]["total_prompt_tokens"] += prompt_tokens
        self._data["summary"]["total_completion_tokens"] += completion_tokens

        self._save_data()
        return entry

    def get_summary(self) -> Dict[str, Any]:
        """
        获取总体统计汇总 / Get overall summary statistics

        Returns:
            Dict[str, Any]: 汇总统计信息 / Summary statistics
        """
        return {
            "total_requests": self._data["summary"]["total_requests"],
            "total_cost": self._data["summary"]["total_cost"],
            "total_prompt_tokens": self._data["summary"]["total_prompt_tokens"],
            "total_completion_tokens": self._data["summary"]["total_completion_tokens"],
            "total_tokens": (
                self._data["summary"]["total_prompt_tokens"]
                + self._data["summary"]["total_completion_tokens"]
            ),
            "success_rate": self._calculate_success_rate(),
            "avg_latency_ms": self._calculate_avg_latency()
        }

    def get_daily_stats(self, days: int = 7) -> List[Dict[str, Any]]:
        """
        获取按日统计 / Get daily statistics

        Args:
            days: 统计最近几天的数据 / Number of recent days to include

        Returns:
            List[Dict[str, Any]]: 每日统计列表 / Daily statistics list
        """
        now = datetime.now()
        daily: Dict[str, Dict[str, Any]] = {}

        for i in range(days):
            date_str = (now - timedelta(days=i)).strftime("%Y-%m-%d")
            daily[date_str] = {
                "date": date_str,
                "requests": 0,
                "cost": 0.0,
                "prompt_tokens": 0,
                "completion_tokens": 0,
                "success_count": 0,
                "fail_count": 0
            }

        for entry in self._data["requests"]:
            try:
                entry_date = entry["timestamp"][:10]
                if entry_date in daily:
                    daily[entry_date]["requests"] += 1
                    daily[entry_date]["cost"] += entry.get("total_cost", 0)
                    daily[entry_date]["prompt_tokens"] += entry.get("prompt_tokens", 0)
                    daily[entry_date]["completion_tokens"] += entry.get("completion_tokens", 0)
                    if entry.get("success", True):
                        daily[entry_date]["success_count"] += 1
                    else:
                        daily[entry_date]["fail_count"] += 1
            except (KeyError, TypeError, ValueError):
                continue

        # 按日期排序 / Sort by date
        result = sorted(daily.values(), key=lambda x: x["date"], reverse=True)
        for item in result:
            item["cost"] = round(item["cost"], 6)
        return result

    def get_model_stats(self) -> List[Dict[str, Any]]:
        """
        获取按模型分类统计 / Get per-model statistics

        Returns:
            List[Dict[str, Any]]: 按模型分类的统计列表 / Per-model statistics list
        """
        model_stats: Dict[str, Dict[str, Any]] = {}

        for entry in self._data["requests"]:
            model = entry.get("model", "unknown")
            if model not in model_stats:
                model_stats[model] = {
                    "model": model,
                    "requests": 0,
                    "cost": 0.0,
                    "prompt_tokens": 0,
                    "completion_tokens": 0,
                    "success_count": 0,
                    "fail_count": 0,
                    "total_latency_ms": 0.0
                }
            model_stats[model]["requests"] += 1
            model_stats[model]["cost"] += entry.get("total_cost", 0)
            model_stats[model]["prompt_tokens"] += entry.get("prompt_tokens", 0)
            model_stats[model]["completion_tokens"] += entry.get("completion_tokens", 0)
            model_stats[model]["total_latency_ms"] += entry.get("latency_ms", 0)
            if entry.get("success", True):
                model_stats[model]["success_count"] += 1
            else:
                model_stats[model]["fail_count"] += 1

        result = list(model_stats.values())
        for item in result:
            item["cost"] = round(item["cost"], 6)
            if item["requests"] > 0:
                item["avg_latency_ms"] = round(item["total_latency_ms"] / item["requests"], 2)
            else:
                item["avg_latency_ms"] = 0.0
            item.pop("total_latency_ms", None)

        return sorted(result, key=lambda x: x["cost"], reverse=True)

    def get_recent_requests(self, limit: int = 20) -> List[Dict[str, Any]]:
        """
        获取最近的请求记录 / Get recent request records

        Args:
            limit: 返回记录数量限制 / Limit of records to return

        Returns:
            List[Dict[str, Any]]: 最近的请求记录列表 / Recent request records
        """
        return self._data["requests"][-limit:][::-1]

    def _calculate_success_rate(self) -> float:
        """
        计算总体成功率 / Calculate overall success rate

        Returns:
            float: 成功率（0-100）/ Success rate (0-100)
        """
        total = len(self._data["requests"])
        if total == 0:
            return 0.0
        success_count = sum(1 for r in self._data["requests"] if r.get("success", True))
        return round((success_count / total) * 100, 2)

    def _calculate_avg_latency(self) -> float:
        """
        计算平均延迟 / Calculate average latency

        Returns:
            float: 平均延迟（毫秒）/ Average latency in milliseconds
        """
        total = len(self._data["requests"])
        if total == 0:
            return 0.0
        total_latency = sum(r.get("latency_ms", 0) for r in self._data["requests"])
        return round(total_latency / total, 2)

    def reset_stats(self) -> None:
        """
        重置所有统计数据 / Reset all statistics data
        """
        self._data = {
            "requests": [],
            "summary": {
                "total_requests": 0,
                "total_cost": 0.0,
                "total_prompt_tokens": 0,
                "total_completion_tokens": 0
            }
        }
        self._save_data()
        print("[INFO] 统计数据已重置 / Statistics data has been reset")
