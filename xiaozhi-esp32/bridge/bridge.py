#!/usr/bin/env python3
"""Bridge Xiaozhi MCP tool calls to an n8n Gmail webhook."""

from __future__ import annotations

import argparse
import asyncio
import json
import logging
import os
import signal
from collections.abc import Mapping
from dataclasses import dataclass
from typing import Any

import httpx
import websockets
from websockets.client import WebSocketClientProtocol


DEFAULT_WS_URL = (
    "wss://api.xiaozhi.me/mcp/?token="
    "eyJhbGciOiJFUzI1NiIsInR5cCI6IkpXVCJ9.eyJ1c2VySWQiOjUxNTY3MiwiYWdlbnRJZCI6NzQ4OTQ3LCJlbmRwb2ludElkIjoiYWdlbnRfNzQ4OTQ3IiwicHVycG9zZSI6Im1jcC1lbmRwb2ludCIsImlhdCI6MTc1OTc0MTQ0MCwiZXhwIjoxNzkxMjk5MDQwfQ.JjNoGRc8_3Khep5vmsa7MKT4ZxNkZqI84SO-1C0NPVZTyHTEmXbE1QOaQ8-gchX9G7Kaqz8POxgsymk2bOK7lA"
)
DEFAULT_WEBHOOK_URL = (
    "https://n8n-elrsppnn.n8x.web.id/webhook/xiaozhi"
)


@dataclass(slots=True)
class ToolSpec:
    """Describe the MCP tool that this bridge exposes."""

    name: str
    description: str

    def to_mcp_dict(self) -> dict[str, Any]:
        return {
            "name": self.name,
            "description": self.description,
            "inputSchema": {
                "type": "object",
                "properties": {
                    "action": {
                        "type": "string",
                        "description": "Short Gmail action identifier (e.g. 'send_email').",
                    },
                    "payload": {
                        "type": "object",
                        "description": "Details needed to execute the Gmail action.",
                    },
                },
                "required": ["action"],
                "additionalProperties": True,
            },
        }


class XiaozhiMCPBridge:
    """Maintain a WebSocket session with Xiaozhi MCP and forward tool calls."""

    def __init__(
        self,
        ws_url: str,
        webhook_url: str,
        tool: ToolSpec,
        reconnect_delay: float = 5.0,
    ) -> None:
        self.ws_url = ws_url
        self.webhook_url = webhook_url
        self.tool = tool
        self.reconnect_delay = reconnect_delay
        self._stopping = asyncio.Event()
        self._http_client: httpx.AsyncClient | None = None

    async def run(self) -> None:
        """Keep the bridge connected until stopped."""

        async with httpx.AsyncClient(timeout=httpx.Timeout(30.0)) as client:
            self._http_client = client
            backoff = self.reconnect_delay
            while not self._stopping.is_set():
                try:
                    logging.info("connecting to Xiaozhi MCP at %s", self.ws_url)
                    async with websockets.connect(
                        self.ws_url,
                        ping_interval=30,
                        ping_timeout=30,
                        max_queue=None,
                    ) as ws:
                        logging.info("connected to Xiaozhi MCP")
                        backoff = self.reconnect_delay
                        await self._handle_session(ws)
                except asyncio.CancelledError:
                    raise
                except Exception as exc:  # noqa: BLE001
                    logging.warning("connection error: %s", exc, exc_info=True)
                    await asyncio.sleep(backoff)
                    backoff = min(backoff * 2, 60)

    async def stop(self) -> None:
        self._stopping.set()

    async def _handle_session(self, ws: WebSocketClientProtocol) -> None:
        while not self._stopping.is_set():
            try:
                raw = await ws.recv()
            except websockets.ConnectionClosedOK:
                logging.info("connection closed cleanly by server")
                return
            except websockets.ConnectionClosedError as exc:
                logging.warning("connection closed with error: %s", exc)
                return

            if isinstance(raw, bytes):
                try:
                    raw = raw.decode("utf-8")
                except UnicodeDecodeError:
                    logging.error("received non-UTF payload; ignoring")
                    continue

            try:
                message = json.loads(raw)
            except json.JSONDecodeError:
                logging.error("failed to parse message: %s", raw)
                continue

            await self._dispatch(ws, message)

    async def _dispatch(self, ws: WebSocketClientProtocol, message: Mapping[str, Any]) -> None:
        method = message.get("method")
        message_id = message.get("id")
        logging.debug("received %s", message)

        if method == "initialize":
            await self._handle_initialize(ws, message)
        elif method == "notifications/initialized":
            logging.info("xiaozhi agent reports initialized")
        elif method == "tools/list":
            await self._handle_tools_list(ws, message)
        elif method == "tools/call":
            await self._handle_tools_call(ws, message)
        elif method == "ping":
            await self._send_json(ws, {"jsonrpc": "2.0", "id": message_id, "result": {}})
        elif method == "shutdown":
            logging.info("received shutdown notification")
            await self._send_json(ws, {"jsonrpc": "2.0", "id": message_id, "result": {}})
            await self.stop()
        else:
            logging.warning("unhandled MCP method: %s", method)
            if message_id is not None:
                await self._send_json(
                    ws,
                    {
                        "jsonrpc": "2.0",
                        "id": message_id,
                        "error": {
                            "code": -32601,
                            "message": f"Method '{method}' not implemented by gmail bridge",
                        },
                    },
                )

    async def _handle_initialize(self, ws: WebSocketClientProtocol, message: Mapping[str, Any]) -> None:
        message_id = message.get("id")
        params = message.get("params") or {}
        requested_version = params.get("protocolVersion", "2024-11-05")
        response = {
            "jsonrpc": "2.0",
            "id": message_id,
            "result": {
                "protocolVersion": requested_version,
                "capabilities": {
                    "tools": {"call": {}},
                },
            },
        }
        await self._send_json(ws, response)

    async def _handle_tools_list(self, ws: WebSocketClientProtocol, message: Mapping[str, Any]) -> None:
        message_id = message.get("id")
        response = {
            "jsonrpc": "2.0",
            "id": message_id,
            "result": {
                "tools": [self.tool.to_mcp_dict()],
            },
        }
        await self._send_json(ws, response)

    async def _handle_tools_call(self, ws: WebSocketClientProtocol, message: Mapping[str, Any]) -> None:
        message_id = message.get("id")
        params = message.get("params") or {}
        tool_name = params.get("name")
        arguments = params.get("arguments")
        call_id = params.get("callId")

        if tool_name != self.tool.name:
            logging.warning("received call for unknown tool '%s'", tool_name)
            await self._send_json(
                ws,
                {
                    "jsonrpc": "2.0",
                    "id": message_id,
                    "error": {
                        "code": -32602,
                        "message": f"Unsupported tool '{tool_name}'",
                    },
                },
            )
            return

        if not isinstance(arguments, Mapping):
            await self._send_json(
                ws,
                {
                    "jsonrpc": "2.0",
                    "id": message_id,
                    "error": {
                        "code": -32602,
                        "message": "Tool arguments must be an object",
                    },
                },
            )
            return

        action = arguments.get("action")
        if not isinstance(action, str) or not action.strip():
            await self._send_json(
                ws,
                {
                    "jsonrpc": "2.0",
                    "id": message_id,
                    "error": {
                        "code": -32602,
                        "message": "Tool arguments must include non-empty 'action'",
                    },
                },
            )
            return

        payload_data: Mapping[str, Any] | None = None
        raw_payload = arguments.get("payload")
        if isinstance(raw_payload, Mapping):
            payload_data = raw_payload

        payload = {
            "action": action,
            "payload": payload_data,
            "call_id": call_id,
            "tool": tool_name,
            "arguments": arguments,
        }
        logging.info("forwarding Gmail request to n8n: %s", payload)

        try:
            webhook_response = await self._post_to_webhook(payload)
        except httpx.HTTPStatusError as exc:
            status = exc.response.status_code
            body_preview = exc.response.text[:2000]
            logging.error(
                "webhook HTTP %s error: %s", status, body_preview, exc_info=True
            )
            await self._send_json(
                ws,
                {
                    "jsonrpc": "2.0",
                    "id": message_id,
                    "error": {
                        "code": -32010,
                        "message": (
                            f"Gmail webhook returned HTTP {status}: {body_preview}"
                        ),
                    },
                },
            )
            return
        except Exception as exc:  # noqa: BLE001
            logging.error("webhook call failed: %s", exc, exc_info=True)
            await self._send_json(
                ws,
                {
                    "jsonrpc": "2.0",
                    "id": message_id,
                    "error": {
                        "code": -32001,
                        "message": f"Gmail agent error: {exc}",
                    },
                },
            )
            return

        content_text = self._format_webhook_response(webhook_response)
        result = {
            "content": [
                {
                    "type": "text",
                    "text": content_text,
                }
            ],
            "isError": False,
        }

        if call_id:
            result["callId"] = call_id

        logging.info("returning result to Xiaozhi: %s", result)

        await self._send_json(
            ws,
            {
                "jsonrpc": "2.0",
                "id": message_id,
                "result": result,
            },
        )

    async def _post_to_webhook(self, payload: dict[str, Any]) -> Any:
        if not self._http_client:
            raise RuntimeError("HTTP client is not initialised")
        response = await self._http_client.post(self.webhook_url, json=payload)
        try:
            response.raise_for_status()
        except httpx.HTTPStatusError:
            # Raise again so the caller can format the error, but preserve body text.
            raise
        try:
            return response.json()
        except json.JSONDecodeError:
            return response.text

    @staticmethod
    def _format_webhook_response(data: Any) -> str:
        if isinstance(data, Mapping):
            message = data.get("message")
            if isinstance(message, str) and message.strip():
                return message
            return json.dumps(data, ensure_ascii=False)
        if isinstance(data, (list, tuple)):
            outputs: list[str] = []
            for item in data:
                if isinstance(item, Mapping):
                    output = item.get("output")
                    if isinstance(output, str) and output.strip():
                        outputs.append(output.strip())
            if outputs:
                return "\n\n".join(outputs)
            return json.dumps(data, ensure_ascii=False)
        return str(data)

    @staticmethod
    async def _send_json(ws: WebSocketClientProtocol, payload: dict[str, Any]) -> None:
        text = json.dumps(payload)
        logging.debug("sending %s", text)
        await ws.send(text)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--ws-url",
        default=os.environ.get("XIAOZHI_MCP_WS_URL", DEFAULT_WS_URL),
        help="Xiaozhi MCP WebSocket endpoint",
    )
    parser.add_argument(
        "--webhook-url",
        default=os.environ.get("N8N_GMAIL_WEBHOOK_URL", DEFAULT_WEBHOOK_URL),
        help="n8n Gmail agent webhook endpoint",
    )
    parser.add_argument(
        "--tool-name",
        default=os.environ.get("MCP_TOOL_NAME", "gmail_action"),
        help="Tool name exposed to Xiaozhi",
    )
    parser.add_argument(
        "--tool-description",
        default=os.environ.get(
            "MCP_TOOL_DESCRIPTION",
            "Forward Gmail-related commands to the Gmail n8n workflow.",
        ),
        help="Human-readable tool description",
    )
    parser.add_argument(
        "--reconnect-delay",
        type=float,
        default=float(os.environ.get("MCP_RECONNECT_DELAY", 5.0)),
        help="Seconds to wait before reconnecting after a failure",
    )
    parser.add_argument(
        "--log-level",
        default=os.environ.get("LOG_LEVEL", "INFO"),
        help="Python logging level",
    )
    return parser.parse_args()


async def _run_bridge(args: argparse.Namespace) -> None:
    if not args.ws_url:
        raise SystemExit("--ws-url or XIAOZHI_MCP_WS_URL is required")
    if not args.webhook_url:
        raise SystemExit("--webhook-url or N8N_GMAIL_WEBHOOK_URL is required")

    logging.basicConfig(
        level=getattr(logging, args.log_level.upper(), logging.INFO),
        format="%(asctime)s %(levelname)s %(name)s :: %(message)s",
    )

    bridge = XiaozhiMCPBridge(
        ws_url=args.ws_url,
        webhook_url=args.webhook_url,
        tool=ToolSpec(name=args.tool_name, description=args.tool_description),
        reconnect_delay=args.reconnect_delay,
    )

    loop = asyncio.get_running_loop()

    stop_event = asyncio.Event()

    def _handle_signal(_: int, __: Any) -> None:  # noqa: ANN001
        logging.info("signal received, shutting down bridge")
        stop_event.set()

    for sig in (signal.SIGINT, signal.SIGTERM):
        try:
            loop.add_signal_handler(sig, _handle_signal, sig, None)
        except NotImplementedError:
            signal.signal(sig, lambda *_: stop_event.set())

    bridge_task = asyncio.create_task(bridge.run())

    await stop_event.wait()
    await bridge.stop()
    bridge_task.cancel()
    try:
        await bridge_task
    except asyncio.CancelledError:
        pass


def main() -> None:
    args = parse_args()
    asyncio.run(_run_bridge(args))


if __name__ == "__main__":
    main()
