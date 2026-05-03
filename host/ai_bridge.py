import argparse
import json
import os
import re
import threading
import time
from dataclasses import asdict, dataclass
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from typing import Any, Optional
from urllib.parse import urlparse

try:
    import requests
except ImportError:  # pragma: no cover - handled at runtime for local-only demos
    requests = None

try:
    import serial
except ImportError:  # pragma: no cover - HTTP-only mode can still run
    serial = None


ALLOWED_ACTIONS = {"GREET", "THINK", "RETREAT", "IDLE"}


@dataclass
class RobotEvent:
    kind: str
    distance_cm: Optional[float] = None
    message: str = ""
    robot_state: str = ""


@dataclass
class Decision:
    action: str
    reply: str
    mode: str
    source: str
    reason: str
    latency_ms: int = 0


class LocalDecisionEngine:
    """Small deterministic policy used by default and as cloud fallback."""

    def decide(self, event: RobotEvent, mode: str = "local", source: str = "local-rules") -> Decision:
        text = event.message.strip().lower()
        distance = event.distance_cm

        if distance is not None and distance < 14:
            return Decision(
                action="RETREAT",
                reply="我看到前方太近了，先后退避让。",
                mode=mode,
                source=source,
                reason="distance below emergency threshold",
            )

        if distance is not None and distance < 20:
            return Decision(
                action="RETREAT",
                reply="前方距离偏近，我先保持安全距离。",
                mode=mode,
                source=source,
                reason="distance below alert threshold",
            )

        if any(keyword in text for keyword in ("退", "避让", "危险", "靠太近", "后退", "retreat", "danger")):
            return Decision(
                action="RETREAT",
                reply="收到，我会切到避让动作。",
                mode=mode,
                source=source,
                reason="user asked for retreat or safety behavior",
            )

        if any(keyword in text for keyword in ("想", "思考", "分析", "为什么", "?", "？", "think")):
            return Decision(
                action="THINK",
                reply="我先想一想，再给出动作反馈。",
                mode=mode,
                source=source,
                reason="user asked a thinking-style prompt",
            )

        if event.kind == "BUTTON" or any(
            keyword in text for keyword in ("你好", "hello", "hi", "嗨", "打招呼", "问候", "greet")
        ):
            return Decision(
                action="GREET",
                reply="你好，我是 MiniPal，已经准备好互动啦。",
                mode=mode,
                source=source,
                reason="wake or greeting intent",
            )

        if text:
            return Decision(
                action="THINK",
                reply=f"我听到了：{event.message}。我会用思考动作回应你。",
                mode=mode,
                source=source,
                reason="general text message",
            )

        return Decision(
            action="IDLE",
            reply="我先保持待机，等待下一次唤醒。",
            mode=mode,
            source=source,
            reason="no actionable event",
        )


class CloudDecisionEngine:
    """OpenAI-compatible chat-completions adapter.

    Configure with:
      OPENAI_API_KEY, OPENAI_BASE_URL, OPENAI_MODEL
    """

    def __init__(self, fallback: LocalDecisionEngine) -> None:
        self.api_key = os.getenv("OPENAI_API_KEY", "")
        self.base_url = os.getenv("OPENAI_BASE_URL", "https://api.openai.com/v1").rstrip("/")
        self.model = os.getenv("OPENAI_MODEL", "gpt-4o-mini")
        self.fallback = fallback

    def decide(self, event: RobotEvent) -> Decision:
        if not self.api_key:
            decision = self.fallback.decide(event, mode="cloud", source="local-fallback")
            decision.reply = f"未配置云端 API，已使用本地规则。{decision.reply}"
            decision.reason = "OPENAI_API_KEY is not set; " + decision.reason
            return decision

        if requests is None:
            decision = self.fallback.decide(event, mode="cloud", source="local-fallback")
            decision.reply = f"requests 依赖未安装，已使用本地规则。{decision.reply}"
            decision.reason = "requests package is missing; " + decision.reason
            return decision

        payload = {
            "model": self.model,
            "messages": [
                {
                    "role": "system",
                    "content": (
                        "You are the high-level policy for a tiny desktop robot. "
                        "Return a compact JSON object only. "
                        "Allowed action values: GREET, THINK, RETREAT, IDLE. "
                        "Use RETREAT whenever distance is unsafe. "
                        "Fields: action, reply, reason. Reply should be short Chinese."
                    ),
                },
                {
                    "role": "user",
                    "content": json.dumps(
                        {
                            "event": event.kind,
                            "distanceCm": event.distance_cm,
                            "message": event.message,
                            "robotState": event.robot_state,
                        },
                        ensure_ascii=False,
                    ),
                },
            ],
            "temperature": 0.2,
            "response_format": {"type": "json_object"},
        }
        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json",
        }

        try:
            response = requests.post(
                f"{self.base_url}/chat/completions",
                headers=headers,
                json=payload,
                timeout=8,
            )
            response.raise_for_status()
            data = response.json()
            content = data["choices"][0]["message"]["content"]
            parsed = parse_cloud_json(content)
            action = normalize_action(parsed.get("action"))
            return Decision(
                action=action,
                reply=str(parsed.get("reply") or cloud_default_reply(action)),
                mode="cloud",
                source="cloud-api",
                reason=str(parsed.get("reason") or "cloud model decision"),
            )
        except Exception as exc:
            decision = self.fallback.decide(event, mode="cloud", source="local-fallback")
            decision.reply = f"云端暂时不可用，已使用本地规则。{decision.reply}"
            decision.reason = f"cloud request failed: {exc}; {decision.reason}"
            return decision


class DecisionService:
    def __init__(self, default_mode: str) -> None:
        self.default_mode = default_mode
        self.local_engine = LocalDecisionEngine()
        self.cloud_engine = CloudDecisionEngine(self.local_engine)

    def decide(self, event: RobotEvent, mode: Optional[str] = None) -> Decision:
        selected_mode = mode or self.default_mode
        started_at = time.perf_counter()
        if selected_mode == "cloud":
            decision = self.cloud_engine.decide(event)
        else:
            decision = self.local_engine.decide(event)

        decision.action = normalize_action(decision.action)
        decision.latency_ms = int((time.perf_counter() - started_at) * 1000)
        return decision


class RobotBridge:
    def __init__(self, port: str, baudrate: int, decisions: DecisionService) -> None:
        if serial is None:
            raise RuntimeError("pyserial is not installed. Run: pip install -r host/requirements.txt")

        self.serial_port = serial.Serial(port=port, baudrate=baudrate, timeout=0.5)
        self.decisions = decisions
        self.last_distance_cm: Optional[float] = None

    def log(self, message: str) -> None:
        print(message, flush=True)

    def send_action(self, action: str) -> None:
        command = f"ACT:{normalize_action(action)}\n".encode("utf-8")
        self.serial_port.write(command)
        self.log(f"[HOST] send -> {command.decode().strip()}")

    def handle_line(self, raw_line: str) -> None:
        line = raw_line.strip()
        if not line:
            return

        self.log(f"[MCU ] {line}")

        if line.startswith("DIST:"):
            self.last_distance_cm = parse_distance(line)
            return

        if line == "EVENT:BUTTON":
            event = RobotEvent(kind="BUTTON", distance_cm=self.last_distance_cm)
            decision = self.decisions.decide(event)
            self.log(
                f"[AI  ] {decision.mode}/{decision.source} -> {decision.action} "
                f"({decision.latency_ms} ms, {decision.reason})"
            )
            self.send_action(decision.action)

    def run(self) -> None:
        self.log(f"[HOST] serial bridge started in {self.decisions.default_mode} mode")
        while True:
            try:
                raw = self.serial_port.readline().decode("utf-8", errors="ignore")
                if raw:
                    self.handle_line(raw)
                else:
                    time.sleep(0.05)
            except KeyboardInterrupt:
                self.log("[HOST] stopped by user")
                break


class AiHttpHandler(BaseHTTPRequestHandler):
    server_version = "MiniPalAiBridge/1.0"

    def do_OPTIONS(self) -> None:
        self.send_response(204)
        self.send_cors_headers()
        self.end_headers()

    def do_GET(self) -> None:
        parsed = urlparse(self.path)
        if parsed.path not in {"/", "/health", "/ai/health"}:
            self.write_json({"ok": False, "error": "not found"}, status=404)
            return

        self.write_json(
            {
                "ok": True,
                "service": "MiniPal AI bridge",
                "defaultMode": self.server.decisions.default_mode,
                "endpoints": ["/ai/decide"],
            }
        )

    def do_POST(self) -> None:
        parsed = urlparse(self.path)
        if parsed.path not in {"/ai/decide", "/ai/message"}:
            self.write_json({"ok": False, "error": "not found"}, status=404)
            return

        try:
            payload = self.read_json_body()
            event = event_from_payload(payload)
            mode = normalize_mode(payload.get("mode"), self.server.decisions.default_mode)
            decision = self.server.decisions.decide(event, mode=mode)
            response = {"ok": True, **asdict(decision)}
            self.write_json(response)
        except Exception as exc:
            self.write_json({"ok": False, "error": str(exc)}, status=400)

    def read_json_body(self) -> dict[str, Any]:
        length = int(self.headers.get("Content-Length") or 0)
        raw = self.rfile.read(length).decode("utf-8") if length else "{}"
        data = json.loads(raw)
        if not isinstance(data, dict):
            raise ValueError("request body must be a JSON object")
        return data

    def write_json(self, payload: dict[str, Any], status: int = 200) -> None:
        body = json.dumps(payload, ensure_ascii=False).encode("utf-8")
        self.send_response(status)
        self.send_cors_headers()
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def send_cors_headers(self) -> None:
        self.send_header("Access-Control-Allow-Origin", "*")
        self.send_header("Access-Control-Allow-Methods", "GET, POST, OPTIONS")
        self.send_header("Access-Control-Allow-Headers", "Content-Type")

    def log_message(self, fmt: str, *args: Any) -> None:
        print(f"[HTTP] {self.address_string()} - {fmt % args}", flush=True)


class AiHttpServer(ThreadingHTTPServer):
    def __init__(self, server_address: tuple[str, int], decisions: DecisionService) -> None:
        super().__init__(server_address, AiHttpHandler)
        self.decisions = decisions


def parse_cloud_json(content: str) -> dict[str, Any]:
    cleaned = content.strip()
    if cleaned.startswith("```"):
        cleaned = re.sub(r"^```(?:json)?", "", cleaned, flags=re.IGNORECASE).strip()
        cleaned = re.sub(r"```$", "", cleaned).strip()

    try:
        data = json.loads(cleaned)
    except json.JSONDecodeError:
        match = re.search(r"\{.*\}", cleaned, flags=re.DOTALL)
        if not match:
            action = first_allowed_action(cleaned)
            return {"action": action, "reply": cloud_default_reply(action), "reason": "plain text response"}
        data = json.loads(match.group(0))

    if not isinstance(data, dict):
        raise ValueError("cloud response JSON must be an object")
    return data


def first_allowed_action(text: str) -> str:
    upper = text.upper()
    for action in ALLOWED_ACTIONS:
        if action in upper:
            return action
    return "GREET"


def cloud_default_reply(action: str) -> str:
    return {
        "GREET": "你好，我来和你打个招呼。",
        "THINK": "我会先做一个思考动作。",
        "RETREAT": "我会先避让，保持安全。",
        "IDLE": "我先保持待机。",
    }[normalize_action(action)]


def normalize_action(value: Any) -> str:
    action = str(value or "").strip().upper()
    return action if action in ALLOWED_ACTIONS else "GREET"


def normalize_mode(value: Any, default: str = "local") -> str:
    mode = str(value or default).strip().lower()
    return mode if mode in {"local", "cloud"} else default


def parse_distance(line: str) -> Optional[float]:
    match = re.search(r"DIST:([-+]?\d+(?:\.\d+)?)", line)
    if not match:
        return None
    try:
        return float(match.group(1))
    except ValueError:
        return None


def optional_float(value: Any) -> Optional[float]:
    if value in (None, ""):
        return None
    try:
        return float(value)
    except (TypeError, ValueError):
        return None


def event_from_payload(payload: dict[str, Any]) -> RobotEvent:
    kind = str(payload.get("event") or payload.get("kind") or "MESSAGE").strip().upper()
    distance = optional_float(payload.get("distanceCm", payload.get("distance_cm")))
    message = str(payload.get("message") or payload.get("text") or "")
    robot_state = str(payload.get("robotState") or payload.get("robot_state") or "")
    return RobotEvent(kind=kind, distance_cm=distance, message=message, robot_state=robot_state)


def start_http_server(host: str, port: int, decisions: DecisionService) -> AiHttpServer:
    server = AiHttpServer((host, port), decisions)
    thread = threading.Thread(target=server.serve_forever, name="ai-http-server", daemon=True)
    thread.start()
    print(f"[HOST] HTTP AI bridge listening at http://{host}:{port}", flush=True)
    return server


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="MiniPal AI bridge")
    parser.add_argument("--port", help="Optional serial port, for example COM5. Omit for simulation-only HTTP mode.")
    parser.add_argument("--baudrate", type=int, default=115200)
    parser.add_argument(
        "--mode",
        choices=["local", "cloud"],
        default="local",
        help="Default AI mode. HTTP requests can still override this per request.",
    )
    parser.add_argument("--http-host", default="127.0.0.1", help="HTTP host for the browser simulator bridge.")
    parser.add_argument("--http-port", type=int, default=8890, help="HTTP port for the browser simulator bridge.")
    parser.add_argument("--no-http", action="store_true", help="Disable the HTTP bridge.")
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    decisions = DecisionService(default_mode=args.mode)
    http_server: Optional[AiHttpServer] = None

    if not args.no_http:
        http_server = start_http_server(args.http_host, args.http_port, decisions)

    if args.port:
        RobotBridge(args.port, args.baudrate, decisions).run()
        return

    if http_server is None:
        print("[HOST] no --port and --no-http was set, nothing to run", flush=True)
        return

    print("[HOST] simulation-only mode. Press Ctrl+C to stop.", flush=True)
    try:
        while True:
            time.sleep(1)
    except KeyboardInterrupt:
        print("[HOST] stopped by user", flush=True)
    finally:
        http_server.shutdown()


if __name__ == "__main__":
    main()
