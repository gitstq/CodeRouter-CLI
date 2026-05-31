"""
OpenAI兼容API代理服务器 / OpenAI-Compatible API Proxy Server

对外暴露统一OpenAI格式API（/v1/chat/completions），
接收标准OpenAI格式请求，智能路由到后端模型。
Exposes unified OpenAI-format API (/v1/chat/completions),
receives standard OpenAI format requests, intelligently routes to backend models.

使用http.server标准库实现 / Implemented using http.server standard library
"""

import json
import threading
from http.server import HTTPServer, BaseHTTPRequestHandler
from typing import Any, Dict, List, Optional, Tuple
from urllib.parse import urlparse

from .config import load_config, get_enabled_models
from .router import Router
from .tracker import CostTracker
from .health import HealthChecker


class ProxyHandler(BaseHTTPRequestHandler):
    """
    API代理请求处理器 / API Proxy Request Handler

    处理传入的HTTP请求并路由到后端AI模型。
    Handles incoming HTTP requests and routes to backend AI models.
    """

    # 类变量，由服务器设置 / Class variables set by server
    router: Optional[Router] = None
    health_checker: Optional[HealthChecker] = None
    tracker: Optional[CostTracker] = None

    # 路由表 / Route table
    ROUTES: Dict[str, str] = {
        "/v1/chat/completions": "chat_completions",
        "/v1/models": "list_models",
        "/health": "health_check",
        "/stats": "stats",
    }

    def log_message(self, format: str, *args: Any) -> None:
        """
        自定义日志格式 / Custom log format

        Args:
            format: 格式字符串 / Format string
            *args: 格式参数 / Format arguments
        """
        print(f"[SERVER] {self.address_string()} - {format % args}")

    def _send_json_response(self, status_code: int, data: Dict[str, Any]) -> None:
        """
        发送JSON响应 / Send JSON response

        Args:
            status_code: HTTP状态码 / HTTP status code
            data: 响应数据 / Response data
        """
        response_body = json.dumps(data, ensure_ascii=False).encode("utf-8")
        self.send_response(status_code)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Content-Length", str(len(response_body)))
        self.send_header("Access-Control-Allow-Origin", "*")
        self.end_headers()
        self.wfile.write(response_body)

    def _send_error_response(self, status_code: int, message: str, error_type: str = "invalid_request_error") -> None:
        """
        发送错误响应 / Send error response

        Args:
            status_code: HTTP状态码 / HTTP status code
            message: 错误信息 / Error message
            error_type: 错误类型 / Error type
        """
        self._send_json_response(status_code, {
            "error": {
                "message": message,
                "type": error_type,
                "code": None
            }
        })

    def _read_request_body(self) -> bytes:
        """
        读取请求体 / Read request body

        Returns:
            bytes: 请求体数据 / Request body data
        """
        content_length = int(self.headers.get("Content-Length", 0))
        return self.rfile.read(content_length) if content_length > 0 else b""

    def do_OPTIONS(self) -> None:
        """
        处理OPTIONS预检请求 / Handle OPTIONS preflight request
        """
        self.send_response(200)
        self.send_header("Access-Control-Allow-Origin", "*")
        self.send_header("Access-Control-Allow-Methods", "GET, POST, OPTIONS")
        self.send_header("Access-Control-Allow-Headers", "Content-Type, Authorization")
        self.end_headers()

    def do_GET(self) -> None:
        """
        处理GET请求 / Handle GET request
        """
        parsed_path = urlparse(self.path).path
        handler_name = self.ROUTES.get(parsed_path)

        if handler_name == "list_models":
            self._handle_list_models()
        elif handler_name == "health_check":
            self._handle_health_check()
        elif handler_name == "stats":
            self._handle_stats()
        else:
            self._send_error_response(404, f"未知的端点: {parsed_path} / Unknown endpoint: {parsed_path}")

    def do_POST(self) -> None:
        """
        处理POST请求 / Handle POST request
        """
        parsed_path = urlparse(self.path).path
        handler_name = self.ROUTES.get(parsed_path)

        if handler_name == "chat_completions":
            self._handle_chat_completions()
        else:
            self._send_error_response(404, f"未知的端点: {parsed_path} / Unknown endpoint: {parsed_path}")

    def _handle_chat_completions(self) -> None:
        """
        处理聊天补全请求 / Handle chat completions request

        支持流式和非流式两种模式。
        Supports both streaming and non-streaming modes.
        """
        if self.router is None:
            self._send_error_response(503, "路由器未初始化 / Router not initialized", "server_error")
            return

        try:
            body = self._read_request_body()
            payload = json.loads(body.decode("utf-8")) if body else {}
        except (json.JSONDecodeError, UnicodeDecodeError) as e:
            self._send_error_response(400, f"无效的JSON请求体: {e} / Invalid JSON body: {e}")
            return

        # 提取参数 / Extract parameters
        messages: List[Dict[str, str]] = payload.get("messages", [])
        model_name: Optional[str] = payload.get("model")
        stream: bool = payload.get("stream", False)
        temperature: float = payload.get("temperature", 0.7)
        max_tokens: Optional[int] = payload.get("max_tokens")

        if not messages:
            self._send_error_response(400, "缺少 messages 参数 / Missing 'messages' parameter")
            return

        if stream:
            self._handle_streaming(messages, model_name, temperature, max_tokens)
        else:
            self._handle_non_streaming(messages, model_name, temperature, max_tokens)

    def _handle_non_streaming(
        self,
        messages: List[Dict[str, str]],
        model_name: Optional[str],
        temperature: float,
        max_tokens: Optional[int]
    ) -> None:
        """
        处理非流式请求 / Handle non-streaming request

        Args:
            messages: 消息列表 / Message list
            model_name: 模型名称 / Model name
            temperature: 温度 / Temperature
            max_tokens: 最大Token数 / Max tokens
        """
        try:
            result = self.router.send_request(
                messages=messages,
                model_name=model_name,
                stream=False,
                temperature=temperature,
                max_tokens=max_tokens
            )

            if "error" in result:
                self._send_error_response(502, result["error"]["message"], "upstream_error")
            else:
                # 移除内部字段 / Remove internal fields
                response_data = {k: v for k, v in result.items() if not k.startswith("_")}
                self._send_json_response(200, response_data)

        except Exception as e:
            self._send_error_response(500, f"服务器内部错误: {str(e)} / Internal server error: {str(e)}", "server_error")

    def _handle_streaming(
        self,
        messages: List[Dict[str, str]],
        model_name: Optional[str],
        temperature: float,
        max_tokens: Optional[int]
    ) -> None:
        """
        处理流式请求 / Handle streaming request

        使用SSE格式逐块转发响应数据。
        Forwards response data chunk by chunk in SSE format.

        Args:
            messages: 消息列表 / Message list
            model_name: 模型名称 / Model name
            temperature: 温度 / Temperature
            max_tokens: 最大Token数 / Max tokens
        """
        try:
            self.send_response(200)
            self.send_header("Content-Type", "text/event-stream; charset=utf-8")
            self.send_header("Cache-Control", "no-cache")
            self.send_header("Connection", "keep-alive")
            self.send_header("Access-Control-Allow-Origin", "*")
            self.end_headers()

            for chunk in self.router.send_request_stream(
                messages=messages,
                model_name=model_name,
                temperature=temperature,
                max_tokens=max_tokens
            ):
                if "error" in chunk:
                    error_data = f"data: {json.dumps(chunk, ensure_ascii=False)}\n\n"
                    self.wfile.write(error_data.encode("utf-8"))
                    self.wfile.flush()
                    break

                # 移除内部字段 / Remove internal fields
                clean_chunk = {k: v for k, v in chunk.items() if not k.startswith("_")}
                sse_data = f"data: {json.dumps(clean_chunk, ensure_ascii=False)}\n\n"
                self.wfile.write(sse_data.encode("utf-8"))
                self.wfile.flush()

            # 发送结束标记 / Send done marker
            self.wfile.write(b"data: [DONE]\n\n")
            self.wfile.flush()

        except (BrokenPipeError, ConnectionResetError):
            # 客户端断开连接 / Client disconnected
            pass
        except Exception as e:
            try:
                error_data = f"data: {json.dumps({'error': str(e)}, ensure_ascii=False)}\n\n"
                self.wfile.write(error_data.encode("utf-8"))
                self.wfile.flush()
            except Exception:
                pass

    def _handle_list_models(self) -> None:
        """
        处理模型列表请求 / Handle model list request

        返回所有已配置的模型信息。
        Returns information about all configured models.
        """
        if self.router is None:
            self._send_error_response(503, "路由器未初始化 / Router not initialized", "server_error")
            return

        models_data = {
            "object": "list",
            "data": []
        }

        for model in self.router.models:
            is_healthy = True
            if self.health_checker:
                is_healthy = self.health_checker.is_healthy(model["name"])

            models_data["data"].append({
                "id": model["name"],
                "object": "model",
                "owned_by": "coderouter",
                "enabled": model.get("enabled", True),
                "healthy": is_healthy,
                "priority": model.get("priority", 999)
            })

        self._send_json_response(200, models_data)

    def _handle_health_check(self) -> None:
        """
        处理健康检查请求 / Handle health check request

        返回所有端点的健康状态。
        Returns health status of all endpoints.
        """
        if self.health_checker is None:
            self._send_json_response(200, {
                "status": "ok",
                "message": "健康检测未启用 / Health check not enabled",
                "endpoints": []
            })
            return

        self._send_json_response(200, {
            "status": "ok",
            "endpoints": self.health_checker.get_all_status()
        })

    def _handle_stats(self) -> None:
        """
        处理统计请求 / Handle stats request

        返回成本追踪统计数据。
        Returns cost tracking statistics.
        """
        if self.tracker is None:
            self._send_json_response(200, {
                "message": "成本追踪未启用 / Cost tracking not enabled",
                "summary": {}
            })
            return

        self._send_json_response(200, {
            "summary": self.tracker.get_summary(),
            "daily_stats": self.tracker.get_daily_stats(days=7),
            "model_stats": self.tracker.get_model_stats()
        })


class ProxyServer:
    """
    API代理服务器 / API Proxy Server

    封装HTTPServer，提供启动和停止功能。
    Wraps HTTPServer, provides start and stop functionality.
    """

    def __init__(self, host: str = "127.0.0.1", port: int = 8199) -> None:
        """
        初始化代理服务器 / Initialize proxy server

        Args:
            host: 监听地址 / Listen address
            port: 监听端口 / Listen port
        """
        self.host: str = host
        self.port: int = port
        self._server: Optional[HTTPServer] = None
        self._server_thread: Optional[threading.Thread] = None
        self.router: Optional[Router] = None
        self.health_checker: Optional[HealthChecker] = None
        self.tracker: Optional[CostTracker] = None

    def initialize(self, config: Dict[str, Any]) -> None:
        """
        根据配置初始化服务器组件 / Initialize server components from config

        Args:
            config: 配置字典 / Config dict
        """
        # 服务器配置 / Server config
        server_config = config.get("server", {})
        self.host = server_config.get("host", "127.0.0.1")
        self.port = server_config.get("port", 8199)

        # 路由配置 / Routing config
        routing_config = config.get("routing", {})

        # 模型列表 / Model list
        models = get_enabled_models(config)

        # 初始化追踪器 / Initialize tracker
        tracker_config = config.get("tracker", {})
        if tracker_config.get("enabled", True):
            self.tracker = CostTracker(data_file=tracker_config.get("data_file"))

        # 初始化健康检测器 / Initialize health checker
        self.health_checker = HealthChecker(
            check_interval=routing_config.get("health_check_interval", 60)
        )
        for model in models:
            self.health_checker.add_endpoint(model["name"], model["endpoint"], model["api_key"])

        # 初始化路由器 / Initialize router
        self.router = Router(
            models=models,
            routing_config=routing_config,
            tracker=self.tracker,
            health_checker=self.health_checker
        )

        # 设置处理器类变量 / Set handler class variables
        ProxyHandler.router = self.router
        ProxyHandler.health_checker = self.health_checker
        ProxyHandler.tracker = self.tracker

    def start(self, blocking: bool = True) -> None:
        """
        启动服务器 / Start server

        Args:
            blocking: 是否阻塞运行 / Whether to run blocking
        """
        self._server = HTTPServer((self.host, self.port), ProxyHandler)

        print(f"[SERVER] CodeRouter API代理服务器启动")
        print(f"[SERVER] CodeRouter API proxy server started")
        print(f"[SERVER] 地址 / Address: http://{self.host}:{self.port}")
        print(f"[SERVER] 端点 / Endpoints:")
        print(f"  POST /v1/chat/completions - 聊天补全 / Chat completions")
        print(f"  GET  /v1/models          - 模型列表 / Model list")
        print(f"  GET  /health              - 健康检查 / Health check")
        print(f"  GET  /stats               - 统计数据 / Statistics")

        # 启动健康检测 / Start health check
        if self.health_checker:
            self.health_checker.start_background_check()

        if blocking:
            try:
                self._server.serve_forever()
            except KeyboardInterrupt:
                print("\n[SERVER] 收到中断信号，正在关闭...")
                print("[SERVER] Interrupt received, shutting down...")
                self.stop()
        else:
            self._server_thread = threading.Thread(target=self._server.serve_forever, daemon=True)
            self._server_thread.start()

    def stop(self) -> None:
        """
        停止服务器 / Stop server
        """
        # 停止健康检测 / Stop health check
        if self.health_checker:
            self.health_checker.stop_background_check()

        # 停止HTTP服务器 / Stop HTTP server
        if self._server:
            self._server.shutdown()
            self._server.server_close()
            print("[SERVER] 服务器已停止 / Server stopped")
