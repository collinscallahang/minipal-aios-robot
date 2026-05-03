# AI 能力接入说明

## 模块目标

本项目采用 `Python 主机桥接，默认本地规则，可切换云端 API` 的方案。它把 AI 决策放在主机侧，实体 ESP32 和浏览器仿真平台都只需要发送事件，不需要直接关心 AI 模型细节。

```text
仿真页面 / ESP32
        |
        | EVENT:BUTTON、MESSAGE、DIST
        v
host/ai_bridge.py
        |
        | local  本地规则
        | cloud  OpenAI-compatible HTTP API
        v
ACT:GREET / ACT:THINK / ACT:RETREAT / ACT:IDLE
```

## 为什么默认选择本地规则

默认用本地规则，是因为桌面机器人有一些动作必须稳定、低延迟、低成本：

- 距离过近时必须马上避让，不能等待网络。
- 按钮唤醒、问候、简单思考动作不需要大模型也能完成。
- 本地规则没有 API 调用费用，离线也能演示。

云端 API 保留为可切换能力，适合后续扩展语音理解、自然语言对话和更复杂的动作策略。

## 延迟和成本权衡

- 本地规则：通常是毫秒级，成本为 0，适合安全兜底和固定交互。
- 云端 API：通常需要几百毫秒到数秒，按调用计费或按 token 计费，适合需要语言理解的场景。
- 本项目的安全策略：`实时安全 = ESP32/本地规则`，`高层表达 = 可选云端 AI`。

如果云端不可用，`host/ai_bridge.py` 会自动回退到本地规则，并在返回结果里标记 `source=local-fallback`。

## Python 桥接如何运行

安装依赖：

```bash
pip install -r host/requirements.txt
```

只连接浏览器仿真平台：

```bash
python host/ai_bridge.py --mode local
```

实体 ESP32 串口 + 浏览器仿真同时使用：

```bash
python host/ai_bridge.py --port COM5 --mode local
```

切换云端 API：

```bash
set OPENAI_API_KEY=your_key
set OPENAI_BASE_URL=https://api.openai.com/v1
set OPENAI_MODEL=gpt-4o-mini
python host/ai_bridge.py --mode cloud
```

默认 HTTP 地址是：

```text
http://127.0.0.1:8890
```

## 仿真平台如何和 AI 沟通

1. 先运行 Python 桥接：

   ```bash
   python host/ai_bridge.py --mode local
   ```

2. 打开 [simulation/index.html](../simulation/index.html)。
3. 页面右侧 `Python AI 桥接` 显示 `已连接` 后，可以：
   - 点击 `按钮唤醒`，页面会发送 `EVENT:BUTTON` 给 Python。
   - 在输入框里输入一句话，页面会发送 `MESSAGE` 给 Python。
   - 切换 `本地规则 / 云端 API`，页面会在请求里携带 `mode`。
4. Python 返回动作，例如：

   ```json
   {
     "action": "GREET",
     "reply": "你好，我是 MiniPal，已经准备好互动啦。",
     "mode": "local",
     "source": "local-rules"
   }
   ```

5. 仿真平台收到动作后，会把它显示为 `ACT:GREET`，并驱动舵机角度、LED、蜂鸣器和状态机变化。

如果 Python 桥接没启动，仿真页面仍能运行，但状态会显示 `离线回退`，这时使用浏览器内置的简化规则。

## 接口格式

仿真平台调用：

```http
POST http://127.0.0.1:8890/ai/decide
Content-Type: application/json
```

请求示例：

```json
{
  "mode": "local",
  "event": "MESSAGE",
  "distanceCm": 36,
  "robotState": "IDLE",
  "message": "你好，和我打个招呼"
}
```

返回示例：

```json
{
  "ok": true,
  "action": "GREET",
  "reply": "你好，我是 MiniPal，已经准备好互动啦。",
  "mode": "local",
  "source": "local-rules",
  "reason": "wake or greeting intent",
  "latency_ms": 0
}
```

动作只允许四种：

- `GREET`：问候动作
- `THINK`：思考动作
- `RETREAT`：避让/告警动作
- `IDLE`：保持待机

## 实体硬件如何复用

实体 ESP32 使用同一套动作协议：

- ESP32 -> Python：`EVENT:BUTTON`
- ESP32 -> Python：`DIST:36.0,RAW:35.5,V:0.0`
- Python -> ESP32：`ACT:GREET`

所以仿真平台和实体硬件不是两套 AI，而是共用 `host/ai_bridge.py` 里的同一套决策层。
