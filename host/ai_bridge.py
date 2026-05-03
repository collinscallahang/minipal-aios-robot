import argparse
import os
import time
from dataclasses import dataclass
from typing import Optional

import requests
import serial


@dataclass
class RobotEvent:
    kind: str
    distance_cm: Optional[float] = None


class LocalDecisionEngine:
    def decide(self, event: RobotEvent) -> str:
        if event.kind == "BUTTON":
            if event.distance_cm is not None and event.distance_cm < 20:
                return "RETREAT"
            return "GREET"
        return "IDLE"


class CloudDecisionEngine:
    def __init__(self) -> None:
        self.api_key = os.getenv("OPENAI_API_KEY", "")
        self.base_url = os.getenv("OPENAI_BASE_URL", "https://api.openai.com/v1").rstrip("/")
        self.model = os.getenv("OPENAI_MODEL", "gpt-4o-mini")

    def decide(self, event: RobotEvent) -> str:
        if not self.api_key:
            return "GREET"

        prompt = (
            "You are deciding a tiny desktop robot action. "
            "Return only one token from: GREET, THINK, RETREAT, IDLE. "
            f"Event={event.kind}. DistanceCm={event.distance_cm}."
        )
        payload = {
            "model": self.model,
            "messages": [
                {"role": "system", "content": "Return exactly one allowed action token."},
                {"role": "user", "content": prompt},
            ],
            "temperature": 0.1,
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
            content = data["choices"][0]["message"]["content"].strip().upper()
        except Exception:
            return "GREET"

        if content in {"GREET", "THINK", "RETREAT", "IDLE"}:
            return content
        return "GREET"


class RobotBridge:
    def __init__(self, port: str, baudrate: int, mode: str) -> None:
        self.serial_port = serial.Serial(port=port, baudrate=baudrate, timeout=0.5)
        self.mode = mode
        self.last_distance_cm: Optional[float] = None
        self.local_engine = LocalDecisionEngine()
        self.cloud_engine = CloudDecisionEngine()

    def log(self, message: str) -> None:
        print(message, flush=True)

    def send_action(self, action: str) -> None:
        command = f"ACT:{action}\n".encode("utf-8")
        self.serial_port.write(command)
        self.log(f"[HOST] send -> {command.decode().strip()}")

    def choose_action(self, event: RobotEvent) -> str:
        if self.mode == "cloud":
            return self.cloud_engine.decide(event)
        return self.local_engine.decide(event)

    def handle_line(self, raw_line: str) -> None:
        line = raw_line.strip()
        if not line:
            return

        self.log(f"[MCU ] {line}")

        if line.startswith("DIST:"):
            try:
                self.last_distance_cm = float(line.split(":", 1)[1])
            except ValueError:
                self.last_distance_cm = None
            return

        if line == "EVENT:BUTTON":
            event = RobotEvent(kind="BUTTON", distance_cm=self.last_distance_cm)
            action = self.choose_action(event)
            self.send_action(action)

    def run(self) -> None:
        self.log(f"[HOST] bridge started in {self.mode} mode")
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


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="MiniPal AI bridge")
    parser.add_argument("--port", required=True, help="Serial port, for example COM5")
    parser.add_argument("--baudrate", type=int, default=115200)
    parser.add_argument(
        "--mode",
        choices=["local", "cloud"],
        default="local",
        help="Use local rules or a cloud chat-completions endpoint",
    )
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    bridge = RobotBridge(args.port, args.baudrate, args.mode)
    bridge.run()


if __name__ == "__main__":
    main()
