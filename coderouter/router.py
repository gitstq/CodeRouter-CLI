"""
智能路由引擎 / Intelligent Routing Engine

支持基于优先级、响应时间、成功率的智能负载均衡路由。
支持自动降级与故障转移，以及流式(SSE)和非流式响应代理。
Supports intelligent load-balanced routing based on priority, response time,
and success rate. Supports automatic degradation, failover, and both
streaming (SSE) and non-streaming response proxying.
"""

import json
import time
import random
from typing import Any, Dict, Generator, List, Optional, Tuple
from urllib.request import Request, urlopen
from urllib.error import URLError, HTTPError

from .health import HealthChecker
from .tracker import CostTracker


class Router:
    """
    智能路由器 / Intelligent Router

    根据配置的路由策略，将请求智能分发到合适的AI模型端点。
    Intelligently distributes requests to appropriate AI model endpoints
    based on configured routing strategy.
    """

    def __init__(
        self,
        models: List[Dict[str, Any]],
        routing_config: Optional[Dict[str, Any]] = None,
        tracker: Optional[CostTracker] = None,
        health_checker: Optional[HealthChecker] = None
    ) -> None:
        """
        初始化路由器 / Initialize router

        Args:
            models: 模型配置列表 / Model config list
            routing_config: 路由配置 / Routing config
            tracker: 成本追踪器 / Cost tracker
            health_checker: 健康检测器 / Health checker
        """
        self.models: List[Dict[str, Any]] = models
        self.routing_config: Dict[str, Any] = routing_config or {
            "strategy": "priority",
            "timeout": 30,
            "max_retries": 3
        }
        self.tracker: Optional[CostTracker] = tracker
        self.health_checker: Optional[HealthChecker] = health_checker
        self._round_robin_index: int = 0
        self._request_log: List[Dict[str, Any]] = []

    def _get_strategy(self) -> str:
        """
        获取当前路由策略 / Get current routing strategy

        Returns:
            str: 路由策略名称 / Routing strategy name
        """
        return self.routing_config.get("strategy", "priority")

    def _get_timeout(self) -> int:
        """
        获取请求超时时间 / Get request timeout

        Returns:
            int: 超时时间（秒）/ Timeout in seconds
        """
        return self.routing_config.get("timeout", 30)

    def _get_max_retries(self) -> int:
        """
        获取最大重试次数 / Get max retry count

        Returns:
            int: 最大重试次数 / Max retry count
        """
        return self.routing_config.get("max_retries", 3)

    def _get_enabled_models(self) -> List[Dict[str, Any]]:
        """
        获取已启用且健康的模型列表 / Get enabled and healthy model list

        Returns:
            List[Dict[str, Any]]: 可用模型列表 / Available model list
        """
        enabled = [m for m in self.models if m.get("enabled", True)]

        # 如果有健康检测器，过滤掉不健康的端点 / Filter unhealthy if health checker exists
        if self.health_checker:
            enabled = [m for m in enabled if self.health_checker.is_healthy(m["name"])]

        return enabled

    def select_model(self, model_name: Optional[str] = None) -> Optional[Dict[str, Any]]:
        """
        选择目标模型 / Select target model

        根据路由策略选择一个模型端点。如果指定了模型名称则优先使用。
        Selects a model endpoint based on routing strategy. Uses specified name if provided.

        Args:
            model_name: 指定的模型名称 / Specified model name

        Returns:
            Optional[Dict[str, Any]]: 选中的模型配置 / Selected model config
        """
        available = self._get_enabled_models()

        if not available:
            return None

        # 如果指定了模型名称，尝试找到它 / If model name specified, try to find it
        if model_name:
            for model in available:
                if model["name"] == model_name:
                    return model
            # 指定的模型不可用，尝试其他模型 / Specified model unavailable, try others
            print(f"[ROUTER] 模型 '{model_name}' 不可用，尝试其他模型...")
            print(f"[ROUTER] Model '{model_name}' unavailable, trying alternatives...")

        strategy = self._get_strategy()

        if strategy == "priority":
            return self._select_by_priority(available)
        elif strategy == "round_robin":
            return self._select_round_robin(available)
        elif strategy == "least_latency":
            return self._select_least_latency(available)
        elif strategy == "random":
            return self._select_random(available)
        else:
            return self._select_by_priority(available)

    def _select_by_priority(self, models: List[Dict[str, Any]]) -> Dict[str, Any]:
        """
        按优先级选择模型 / Select model by priority

        Args:
            models: 可用模型列表 / Available model list

        Returns:
            Dict[str, Any]: 优先级最高的模型 / Highest priority model
        """
        return sorted(models, key=lambda m: m.get("priority", 999))[0]

    def _select_round_robin(self, models: List[Dict[str, Any]]) -> Dict[str, Any]:
        """
        轮询选择模型 / Select model by round-robin

        Args:
            models: 可用模型列表 / Available model list

        Returns:
            Dict[str, Any]: 轮询选中的模型 / Round-robin selected model
        """
        if not models:
            raise ValueError("没有可用的模型 / No available models")
        model = models[self._round_robin_index % len(models)]
        self._round_robin_index += 1
        return model

    def _select_least_latency(self, models: List[Dict[str, Any]]) -> Dict[str, Any]:
        """
        按最低延迟选择模型 / Select model by least latency

        Args:
            models: 可用模型列表 / Available model list

        Returns:
            Dict[str, Any]: 延迟最低的模型 / Lowest latency model
        """
        if not self.health_checker:
            return self._select_by_priority(models)

        best_model = models[0]
        best_latency = float("inf")

        for model in models:
            status = self.health_checker.get_all_status()
            for s in status:
                if s["name"] == model["name"]:
                    latency = s.get("last_response_time_ms", float("inf"))
                    if latency < best_latency:
                        best_latency = latency
                        best_model = model
                    break

        return best_model

    def _select_random(self, models: List[Dict[str, Any]]) -> Dict[str, Any]:
        """
        随机选择模型 / Select model randomly

        Args:
            models: 可用模型列表 / Available model list

        Returns:
            Dict[str, Any]: 随机选中的模型 / Randomly selected model
        """
        return random.choice(models)

    def send_request(
        self,
        messages: List[Dict[str, str]],
        model_name: Optional[str] = None,
        stream: bool = False,
        temperature: float = 0.7,
        max_tokens: Optional[int] = None,
        **kwargs: Any
    ) -> Dict[str, Any]:
        """
        发送非流式请求 / Send non-streaming request

        自动进行故障转移和重试。
        Automatically performs failover and retries.

        Args:
            messages: 消息列表 / Message list
            model_name: 指定模型名称 / Specified model name
            stream: 是否流式 / Whether to stream
            temperature: 温度参数 / Temperature parameter
            max_tokens: 最大Token数 / Max tokens
            **kwargs: 其他参数 / Other parameters

        Returns:
            Dict[str, Any]: 响应结果 / Response result
        """
        max_retries = self._get_max_retries()
        last_error: Optional[str] = None

        for attempt in range(max_retries):
            model = self.select_model(model_name)
            if model is None:
                return self._error_response("没有可用的模型端点 / No available model endpoints")

            try:
                result = self._do_request(model, messages, stream=False,
                                           temperature=temperature,
                                           max_tokens=max_tokens, **kwargs)
                # 记录请求日志 / Log request
                self._log_request(model["name"], True, result.get("latency_ms", 0))
                return result

            except (URLError, HTTPError, OSError, Exception) as e:
                last_error = str(e)
                print(f"[ROUTER] 请求失败 (尝试 {attempt + 1}/{max_retries}): {last_error}")
                print(f"[ROUTER] Request failed (attempt {attempt + 1}/{max_retries}): {last_error}")

                # 标记当前端点不健康 / Mark current endpoint unhealthy
                if self.health_checker:
                    self.health_checker.check_endpoint(model["name"])

                # 记录失败 / Log failure
                self._log_request(model["name"], False, 0, error=last_error)

        return self._error_response(f"所有重试均失败: {last_error}")

    def send_request_stream(
        self,
        messages: List[Dict[str, str]],
        model_name: Optional[str] = None,
        temperature: float = 0.7,
        max_tokens: Optional[int] = None,
        **kwargs: Any
    ) -> Generator[Dict[str, Any], None, None]:
        """
        发送流式请求 / Send streaming request

        通过生成器逐块返回SSE事件数据。
        Returns SSE event data chunk by chunk via generator.

        Args:
            messages: 消息列表 / Message list
            model_name: 指定模型名称 / Specified model name
            temperature: 温度参数 / Temperature parameter
            max_tokens: 最大Token数 / Max tokens
            **kwargs: 其他参数 / Other parameters

        Yields:
            Dict[str, Any]: SSE事件数据 / SSE event data
        """
        model = self.select_model(model_name)
        if model is None:
            error_event = {
                "error": "没有可用的模型端点 / No available model endpoints"
            }
            yield error_event
            return

        try:
            start_time = time.time()
            for chunk in self._do_stream_request(model, messages,
                                                  temperature=temperature,
                                                  max_tokens=max_tokens, **kwargs):
                yield chunk

            latency = (time.time() - start_time) * 1000
            self._log_request(model["name"], True, latency)

        except (URLError, HTTPError, OSError, Exception) as e:
            last_error = str(e)
            print(f"[ROUTER] 流式请求失败: {last_error}")
            print(f"[ROUTER] Streaming request failed: {last_error}")
            self._log_request(model["name"], False, 0, error=last_error)
            yield {"error": last_error}

    def _do_request(
        self,
        model: Dict[str, Any],
        messages: List[Dict[str, str]],
        stream: bool,
        temperature: float = 0.7,
        max_tokens: Optional[int] = None,
        **kwargs: Any
    ) -> Dict[str, Any]:
        """
        执行单次HTTP请求 / Execute single HTTP request

        Args:
            model: 模型配置 / Model config
            messages: 消息列表 / Message list
            stream: 是否流式 / Whether to stream
            temperature: 温度 / Temperature
            max_tokens: 最大Token数 / Max tokens

        Returns:
            Dict[str, Any]: 响应结果 / Response result
        """
        payload = {
            "model": model["name"],
            "messages": messages,
            "temperature": temperature,
            "stream": stream
        }
        if max_tokens is not None:
            payload["max_tokens"] = max_tokens
        payload.update(kwargs)

        data = json.dumps(payload).encode("utf-8")

        req = Request(
            model["endpoint"],
            data=data,
            headers={
                "Content-Type": "application/json",
                "Authorization": f"Bearer {model['api_key']}"
            },
            method="POST"
        )

        start_time = time.time()
        response = urlopen(req, timeout=self._get_timeout())
        response_body = response.read().decode("utf-8")
        latency = (time.time() - start_time) * 1000

        result = json.loads(response_body)
        result["latency_ms"] = round(latency, 2)
        result["_model"] = model["name"]

        # 追踪成本 / Track cost
        if self.tracker:
            usage = result.get("usage", {})
            self.tracker.record_request(
                model_name=model["name"],
                prompt_tokens=usage.get("prompt_tokens", 0),
                completion_tokens=usage.get("completion_tokens", 0),
                cost_per_million_input=model.get("cost_per_million_input", 0),
                cost_per_million_output=model.get("cost_per_million_output", 0),
                success=True,
                latency_ms=latency
            )

        return result

    def _do_stream_request(
        self,
        model: Dict[str, Any],
        messages: List[Dict[str, str]],
        temperature: float = 0.7,
        max_tokens: Optional[int] = None,
        **kwargs: Any
    ) -> Generator[Dict[str, Any], None, None]:
        """
        执行流式HTTP请求 / Execute streaming HTTP request

        Args:
            model: 模型配置 / Model config
            messages: 消息列表 / Message list
            temperature: 温度 / Temperature
            max_tokens: 最大Token数 / Max tokens

        Yields:
            Dict[str, Any]: 解析后的SSE事件 / Parsed SSE event
        """
        payload = {
            "model": model["name"],
            "messages": messages,
            "temperature": temperature,
            "stream": True
        }
        if max_tokens is not None:
            payload["max_tokens"] = max_tokens
        payload.update(kwargs)

        data = json.dumps(payload).encode("utf-8")

        req = Request(
            model["endpoint"],
            data=data,
            headers={
                "Content-Type": "application/json",
                "Authorization": f"Bearer {model['api_key']}"
            },
            method="POST"
        )

        response = urlopen(req, timeout=self._get_timeout())

        # 逐行读取SSE流 / Read SSE stream line by line
        buffer = b""
        total_prompt_tokens = 0
        total_completion_tokens = 0

        while True:
            chunk = response.read(1)
            if not chunk:
                break
            buffer += chunk

            while b"\n" in buffer:
                line, buffer = buffer.split(b"\n", 1)
                line_str = line.decode("utf-8", errors="replace").strip()

                if not line_str:
                    continue

                if line_str.startswith("data: "):
                    data_str = line_str[6:]
                    if data_str.strip() == "[DONE]":
                        # 流结束 / Stream done
                        if self.tracker:
                            self.tracker.record_request(
                                model_name=model["name"],
                                prompt_tokens=total_prompt_tokens,
                                completion_tokens=total_completion_tokens,
                                cost_per_million_input=model.get("cost_per_million_input", 0),
                                cost_per_million_output=model.get("cost_per_million_output", 0),
                                success=True,
                                latency_ms=0
                            )
                        return

                    try:
                        event = json.loads(data_str)
                        # 提取token使用信息 / Extract token usage info
                        if "usage" in event:
                            usage = event["usage"]
                            total_prompt_tokens = usage.get("prompt_tokens", 0)
                            total_completion_tokens = usage.get("completion_tokens", 0)
                        event["_model"] = model["name"]
                        yield event
                    except json.JSONDecodeError:
                        continue

    def _error_response(self, message: str) -> Dict[str, Any]:
        """
        生成错误响应 / Generate error response

        Args:
            message: 错误信息 / Error message

        Returns:
            Dict[str, Any]: 错误响应字典 / Error response dict
        """
        return {
            "error": {
                "message": message,
                "type": "router_error",
                "code": None
            }
        }

    def _log_request(
        self,
        model_name: str,
        success: bool,
        latency_ms: float,
        error: Optional[str] = None
    ) -> None:
        """
        记录请求日志 / Log request

        Args:
            model_name: 模型名称 / Model name
            success: 是否成功 / Whether succeeded
            latency_ms: 延迟 / Latency
            error: 错误信息 / Error message
        """
        import datetime
        entry = {
            "timestamp": datetime.datetime.now().isoformat(),
            "model": model_name,
            "success": success,
            "latency_ms": round(latency_ms, 2),
            "error": error
        }
        self._request_log.append(entry)
        # 保留最近100条日志 / Keep last 100 log entries
        if len(self._request_log) > 100:
            self._request_log = self._request_log[-100:]

    def get_request_log(self, limit: int = 20) -> List[Dict[str, Any]]:
        """
        获取请求日志 / Get request log

        Args:
            limit: 返回条数限制 / Return limit

        Returns:
            List[Dict[str, Any]]: 最近的请求日志 / Recent request logs
        """
        return self._request_log[-limit:][::-1]

    def update_models(self, models: List[Dict[str, Any]]) -> None:
        """
        更新模型列表 / Update model list

        Args:
            models: 新的模型配置列表 / New model config list
        """
        self.models = models
