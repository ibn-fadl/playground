# Xiaozhi ↔︎ Gmail Bridge

Bridge the Xiaozhi MCP tool interface to your Gmail agent running inside n8n. The bridge keeps a persistent WebSocket connection to Xiaozhi and forwards every `tools/call` invocation to the Gmail webhook you already have.

## Prerequisites

- Python 3.10 or newer
- Access to the Xiaozhi MCP endpoint (WebSocket URL + token)
- The n8n Gmail webhook URL that should receive forwarded requests

## Installation

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```

## Configuration

Set the following environment variables or pass them as CLI flags (defaults are baked into the script for this experiment):

- `XIAOZHI_MCP_WS_URL` – defaults to the provided Xiaozhi tokenised URL.
- `N8N_GMAIL_WEBHOOK_URL` – defaults to `https://n8n-elrsppnn.n8x.web.id/webhook/xiaozhi`.
- Optional overrides: `MCP_TOOL_NAME`, `MCP_TOOL_DESCRIPTION`, `MCP_RECONNECT_DELAY`, `LOG_LEVEL`

You can place them in an `.env` file and export before launching the bridge:

```bash
export XIAOZHI_MCP_WS_URL="wss://api.xiaozhi.me/mcp/?token=..."
export N8N_GMAIL_WEBHOOK_URL="https://n8n-elrsppnn.n8x.web.id/webhook/xiaozhi"
```

## Running the bridge

```bash
python bridge.py
```

The bridge will:

1. Connect to the Xiaozhi MCP WebSocket and register a `gmail_action` tool.
2. Wait for `tools/call` requests and forward them to your n8n webhook as JSON:
   ```json
   {
     "tool": "gmail_action",
     "call_id": "...",
     "arguments": { "action": "send_email", "payload": { ... } }
   }
   ```
3. Return the webhook response back to Xiaozhi so your agent can show the outcome to the user.

Logs are emitted to stdout. Run with `--log-level DEBUG` for verbose tracing.

## Verifying end-to-end

1. Start the bridge (`python bridge.py`).
2. Trigger a Gmail-related command inside Xiaozhi.
3. Confirm that the n8n workflow receives the payload and answers.
4. Check the bridge logs for `forwarding Gmail request to n8n` entries.

If the webhook returns an error or non-JSON body, the bridge will forward the text back to Xiaozhi and log the failure for troubleshooting.

## Graceful shutdown

Press `Ctrl+C` (SIGINT) or send SIGTERM to stop the bridge. It will close the WebSocket session and exit cleanly.
