"""
健康检测模块 / Health Check Module

定期检测各AI模型端点的可用性，记录响应时间和成功率，
自动标记不健康端点并定期重试恢复。
Periodically checks availability of AI model endpoints, records response time
and success rate, auto-marks unhealthy endpoints and periodically retries recovery.
"""

import json
import time
import threading
from typing import Any, Dict, List, Optional
from urllib.request import Request, urlopen
from urllib.error import URLError, HTTPError


class EndpointHealth:
    """
    单个端点的健康状态 / Health status of a single endpoint
    """

    def __init__(self, name: str, endpoint: str, api_key: str) -> None:
        """
        初始化端点健康状态 / Initialize endpoint health status

        Args:
            name: 模型名称 / Model name
            endpoint: API端点URL / API endpoint URL
            api_key: API密钥 / API key
        """
        self.name: str = name
        self.endpoint: str = endpoint
        self.api_key: str = api_key
        self.healthy: bool = True
        self.last_check_time: float = 0.0
        self.last_response_time_ms: float = 0.0
        self.consecutive_failures: int = 0
        self.consecutive_successes: int = 0
        self.total_checks: int = 0
        self.successful_checks: int = 0
        self.last_error: Optional[str] = None

    @property
    def success_rate(self) -> float:
        """
        计算成功率 / Calculate success rate

        Returns:
            float: 成功率百分比 / Success rate percentage
        """
        if self.total_checks == 0:
            return 100.0
        return round((self.successful_checks / self.total_checks) * 100, 2)

    @property
    def avg_response_time_ms(self) -> float:
        """
        获取平均响应时间 / Get average response time

        Returns:
            float: 平均响应时间（毫秒）/ Average response time in milliseconds
        """
        if self.total_checks == 0:
            return 0.0
        return round(self.last_response_time_ms, 2)

    def to_dict(self) -> Dict[str, Any]:
        """
        转换为字典 / Convert to dictionary

        Returns:
            Dict[str, Any]: 健康状态字典 / Health status dict
        """
        return {
            "name": self.name,
            "healthy": self.healthy,
            "last_check_time": self.last_check_time,
            "last_response_time_ms": self.last_response_time_ms,
            "consecutive_failures": self.consecutive_failures,
            "consecutive_successes": self.consecutive_successes,
            "total_checks": self.total_checks,
            "successful_checks": self.successful_checks,
            "success_rate": self.success_rate,
            "last_error": self.last_error
        }


class HealthChecker:
    """
    健康检测器 / Health Checker

    管理多个端点的健康检测，支持后台定期检测。
    Manages health checks for multiple endpoints, supports background periodic checking.
    """

    # 连续失败多少次后标记为不健康 / Consecutive failures before marking unhealthy
    FAILURE_THRESHOLD: int = 3
    # 连续成功多少次后恢复为健康 / Consecutive successes before marking healthy
    RECOVERY_THRESHOLD: int = 2

    def __init__(self, check_interval: int = 60) -> None:
        """
        初始化健康检测器 / Initialize health checker

        Args:
            check_interval: 检测间隔（秒）/ Check interval in seconds
        """
        self.check_interval: int = check_interval
        self._endpoints: Dict[str, EndpointHealth] = {}
        self._running: bool = False
        self._thread: Optional[threading.Thread] = None
        self._lock = threading.Lock()

    def add_endpoint(self, name: str, endpoint: str, api_key: str) -> None:
        """
        添加端点到检测列表 / Add endpoint to check list

        Args:
            name: 模型名称 / Model name
            endpoint: API端点URL / API endpoint URL
            api_key: API密钥 / API key
        """
        with self._lock:
            if name not in self._endpoints:
                self._endpoints[name] = EndpointHealth(name, endpoint, api_key)

    def remove_endpoint(self, name: str) -> None:
        """
        从检测列表中移除端点 / Remove endpoint from check list

        Args:
            name: 模型名称 / Model name
        """
        with self._lock:
            self._endpoints.pop(name, None)

    def update_endpoints(self, models: List[Dict[str, Any]]) -> None:
        """
        根据模型配置更新端点列表 / Update endpoint list based on model config

        Args:
            models: 模型配置列表 / Model config list
        """
        with self._lock:
            current_names = {m["name"] for m in models if m.get("enabled", True)}
            # 移除不再存在的端点 / Remove endpoints that no longer exist
            for name in list(self._endpoints.keys()):
                if name not in current_names:
                    del self._endpoints[name]
            # 添加或更新端点 / Add or update endpoints
            for model in models:
                if model.get("enabled", True):
                    name = model["name"]
                    if name in self._endpoints:
                        self._endpoints[name].endpoint = model["endpoint"]
                        self._endpoints[name].api_key = model["api_key"]
                    else:
                        self._endpoints[name] = EndpointHealth(
                            name, model["endpoint"], model["api_key"]
                        )

    def check_endpoint(self, name: str, timeout: int = 10) -> bool:
        """
        检测单个端点 / Check a single endpoint

        发送一个最小的请求来检测端点是否可用。
        Sends a minimal request to check if the endpoint is available.

        Args:
            name: 模型名称 / Model name
            timeout: 超时时间（秒）/ Timeout in seconds

        Returns:
            bool: 端点是否健康 / Whether endpoint is healthy
        """
        with self._lock:
            health = self._endpoints.get(name)
            if health is None:
                return False

        # 构造最小检测请求 / Build minimal check request
        check_payload = json.dumps({
            "model": name,
            "messages": [{"role": "user", "content": "hi"}],
            "max_tokens": 1,
            "stream": False
        }).encode("utf-8")

        req = Request(
            health.endpoint,
            data=check_payload,
            headers={
                "Content-Type": "application/json",
                "Authorization": f"Bearer {health.api_key}"
            },
            method="POST"
        )

        start_time = time.time()
        try:
            response = urlopen(req, timeout=timeout)
            response_time = (time.time() - start_time) * 1000
            # 读取响应体 / Read response body
            response.read()
            response.close()

            with self._lock:
                health.last_check_time = time.time()
                health.last_response_time_ms = response_time
                health.consecutive_failures = 0
                health.consecutive_successes += 1
                health.total_checks += 1
                health.successful_checks += 1
                health.last_error = None

                # 检查是否需要恢复 / Check if recovery needed
                if not health.healthy and health.consecutive_successes >= self.RECOVERY_THRESHOLD:
                    health.healthy = True
                    print(f"[HEALTH] 端点 '{name}' 已恢复健康 / Endpoint '{name}' recovered")

            return True

        except (URLError, HTTPError, OSError, Exception) as e:
            response_time = (time.time() - start_time) * 1000
            error_msg = str(e)[:200]

            with self._lock:
                health.last_check_time = time.time()
                health.last_response_time_ms = response_time
                health.consecutive_successes = 0
                health.consecutive_failures += 1
                health.total_checks += 1
                health.last_error = error_msg

                # 检查是否需要标记为不健康 / Check if should mark unhealthy
                if health.healthy and health.consecutive_failures >= self.FAILURE_THRESHOLD:
                    health.healthy = False
                    print(f"[HEALTH] 端点 '{name}' 标记为不健康 / Endpoint '{name}' marked unhealthy")

            return False

    def check_all(self, timeout: int = 10) -> Dict[str, bool]:
        """
        检测所有端点 / Check all endpoints

        Args:
            timeout: 超时时间（秒）/ Timeout in seconds

        Returns:
            Dict[str, bool]: 各端点检测结果 / Check results for each endpoint
        """
        results: Dict[str, bool] = {}
        with self._lock:
            names = list(self._endpoints.keys())
        for name in names:
            results[name] = self.check_endpoint(name, timeout)
        return results

    def is_healthy(self, name: str) -> bool:
        """
        检查端点是否健康 / Check if endpoint is healthy

        Args:
            name: 模型名称 / Model name

        Returns:
            bool: 是否健康 / Whether healthy
        """
        with self._lock:
            health = self._endpoints.get(name)
            if health is None:
                return False
            return health.healthy

    def get_healthy_endpoints(self) -> List[str]:
        """
        获取所有健康端点名称 / Get all healthy endpoint names

        Returns:
            List[str]: 健康端点名称列表 / List of healthy endpoint names
        """
        with self._lock:
            return [name for name, health in self._endpoints.items() if health.healthy]

    def get_all_status(self) -> List[Dict[str, Any]]:
        """
        获取所有端点的健康状态 / Get health status of all endpoints

        Returns:
            List[Dict[str, Any]]: 端点健康状态列表 / List of endpoint health statuses
        """
        with self._lock:
            return [health.to_dict() for health in self._endpoints.values()]

    def start_background_check(self) -> None:
        """
        启动后台定期健康检测 / Start background periodic health check

        在独立线程中定期检测所有端点。
        Periodically checks all endpoints in a separate thread.
        """
        if self._running:
            return

        self._running = True
        self._thread = threading.Thread(target=self._background_check_loop, daemon=True)
        self._thread.start()
        print(f"[HEALTH] 后台健康检测已启动，间隔 {self.check_interval} 秒")
        print(f"[HEALTH] Background health check started, interval {self.check_interval}s")

    def stop_background_check(self) -> None:
        """
        停止后台健康检测 / Stop background health check
        """
        self._running = False
        if self._thread and self._thread.is_alive():
            self._thread.join(timeout=5)
        print("[HEALTH] 后台健康检测已停止 / Background health check stopped")

    def _background_check_loop(self) -> None:
        """
        后台检测循环 / Background check loop
        """
        while self._running:
            try:
                self.check_all()
            except Exception as e:
                print(f"[HEALTH] 后台检测异常: {e}")
                print(f"[HEALTH] Background check error: {e}")

            # 等待下一次检测 / Wait for next check
            for _ in range(self.check_interval):
                if not self._running:
                    break
                time.sleep(1)
