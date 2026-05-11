"""Minimal Alertmanager webhook relay for Discord or Slack.

Alertmanager's slack_configs payload is not accepted by Discord's
Slack-compatible endpoint in this lab setup. This relay accepts the generic
Alertmanager webhook payload and posts a compact native message to Discord.
It also supports Slack incoming webhooks with a simple text payload.
"""
from __future__ import annotations

import json
import os
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from urllib import request
from urllib.error import HTTPError, URLError

WEBHOOK_URL = os.environ.get("ALERT_WEBHOOK_URL", "").strip()
PORT = int(os.environ.get("PORT", "9097"))


def _target_url() -> str:
    if WEBHOOK_URL.endswith("/slack") and "discord.com/api/webhooks/" in WEBHOOK_URL:
        return WEBHOOK_URL[: -len("/slack")]
    return WEBHOOK_URL


def _message_from_alertmanager(payload: dict) -> str:
    status = payload.get("status", "unknown").upper()
    alerts = payload.get("alerts", [])
    lines = [f"[{status}] {payload.get('groupKey', 'Alertmanager')}"]

    for alert in alerts[:5]:
        labels = alert.get("labels", {})
        annotations = alert.get("annotations", {})
        name = labels.get("alertname", "alert")
        severity = labels.get("severity", "unknown")
        instance = labels.get("instance", "")
        summary = annotations.get("summary", "")
        description = annotations.get("description", "")
        lines.append(f"- {name} ({severity}) {instance}".strip())
        if summary:
            lines.append(f"  {summary}")
        if description:
            lines.append(f"  {description}")

    if len(alerts) > 5:
        lines.append(f"... and {len(alerts) - 5} more alert(s)")

    return "\n".join(lines)[:1900]


def _post_message(text: str) -> tuple[int, str]:
    url = _target_url()
    if not url:
        return 500, "ALERT_WEBHOOK_URL is not set"

    if "discord.com/api/webhooks/" in url or "discordapp.com/api/webhooks/" in url:
        body = {"content": text, "username": "Alertmanager"}
    else:
        body = {"text": text}

    data = json.dumps(body).encode("utf-8")
    req = request.Request(
        url,
        data=data,
        headers={
            "Content-Type": "application/json",
            "User-Agent": "day23-alertmanager-relay/1.0",
        },
        method="POST",
    )
    try:
        with request.urlopen(req, timeout=10) as response:
            return response.status, response.read().decode("utf-8", errors="replace")
    except HTTPError as exc:
        return exc.code, exc.read().decode("utf-8", errors="replace")
    except URLError as exc:
        return 502, str(exc.reason)


class Handler(BaseHTTPRequestHandler):
    def do_GET(self) -> None:
        if self.path == "/healthz":
            self.send_response(200)
            self.end_headers()
            self.wfile.write(b"ok")
            return
        self.send_response(404)
        self.end_headers()

    def do_POST(self) -> None:
        if self.path != "/alert":
            self.send_response(404)
            self.end_headers()
            return

        length = int(self.headers.get("Content-Length", "0"))
        raw = self.rfile.read(length)
        try:
            payload = json.loads(raw.decode("utf-8"))
        except json.JSONDecodeError:
            self.send_response(400)
            self.end_headers()
            self.wfile.write(b"invalid json")
            return

        status, body = _post_message(_message_from_alertmanager(payload))
        if 200 <= status < 300:
            self.send_response(200)
            self.end_headers()
            self.wfile.write(b"sent")
            return

        self.send_response(502)
        self.end_headers()
        self.wfile.write(f"webhook returned {status}: {body}".encode("utf-8"))

    def log_message(self, fmt: str, *args: object) -> None:
        print(f"{self.address_string()} - {fmt % args}")


def main() -> int:
    print(f"alert relay listening on :{PORT}")
    server = ThreadingHTTPServer(("0.0.0.0", PORT), Handler)
    server.serve_forever()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
