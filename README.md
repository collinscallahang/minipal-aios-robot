# MiniPal: AIOS 桌面机器人 MVP

`MiniPal` 是一个桌宠风格的最小可用桌面 AI 机器人系统，目标是用尽量少的模块完成一个完整闭环：

- 输入：按钮 + HC-SR04 距离传感器
- 控制：ESP32 实时控制 + Python AI 桥接
- 输出：SG90 舵机 + WS2812 RGB LED + 蜂鸣器
- 通信：USB UART，支持可选云端 HTTP API

机器人前脸直接利用 HC-SR04 的双探头作为“眼睛”，既保留真实传感器功能，也形成更容易展示的桌宠外观。

## 交付物对应关系

- 系统架构图：[docs/02_architecture.md](docs/02_architecture.md)
- 方案定稿与模块选型：[docs/00_alignment.md](docs/00_alignment.md)
- 实施方案：[docs/01_fast_plan.md](docs/01_fast_plan.md)
- 可交互仿真 Demo：[simulation/index.html](simulation/index.html)
- 控制逻辑与状态机：[firmware/src/main.cpp](firmware/src/main.cpp)
- 结构设计与尺寸：[mechanical/minipal_structure_layout.svg](mechanical/minipal_structure_layout.svg) 、 [mechanical/minipal_case.scad](mechanical/minipal_case.scad)
- 一页设计说明：[docs/04_one_pager.md](docs/04_one_pager.md)
- 工程问题分析：[docs/03_engineering_analysis.md](docs/03_engineering_analysis.md)
- 演示说明：[docs/05_demo_notes.md](docs/05_demo_notes.md)
- 提交说明：[docs/06_submission.md](docs/06_submission.md)

## 核心闭环

1. 用户按下顶部按钮，`MiniPal` 进入唤醒状态。
2. ESP32 通过串口把事件发送给主机侧 Python 桥接程序。
3. Python 根据本地规则或云端 AI 生成动作指令。
4. ESP32 控制舵机、灯光和蜂鸣器输出反馈。
5. 当前方距离过近时，机器人直接进入告警状态并执行避让姿态。

## 结构尺寸

- 外形尺寸：`100 x 90 x 70 mm`
- 壁厚：`3 mm`
- 结构风格：桌宠型双层壳体
- 布局原则：上层动作、下层配重、前脸感知

## 仓库结构

```text
docs/                 作业文档与展示材料
firmware/             ESP32 / Arduino 控制代码
host/                 Python AI 桥接脚本
mechanical/           结构草图与 OpenSCAD 结构文件
simulation/           浏览器交互仿真 Demo
```

## 快速开始

### 1. 浏览器仿真

直接用浏览器打开 https://raw.githack.com/collinscallahang/minipal-aios-robot/codex-ai-bridge-access/simulation/index.html
即可演示按钮唤醒、距离告警、状态机迁移、AI 动作建议和输出反馈。

### 2. 固件

如果有实体硬件，可用 PlatformIO 打开 [firmware/platformio.ini](firmware/platformio.ini) 并烧录到 `esp32dev`。

### 3. 主机侧 AI 桥接

实体硬件调试时可运行：

```bash
pip install -r host/requirements.txt
python host/ai_bridge.py --port COM5 --mode local
```

如需切换到云端模式，配置环境变量：

```bash
set OPENAI_API_KEY=your_key
set OPENAI_BASE_URL=https://api.openai.com/v1
set OPENAI_MODEL=gpt-4o-mini
python host/ai_bridge.py --port COM5 --mode cloud
```

## 展示建议

- 先打开仿真 Demo，演示按钮唤醒和问候动作。
- 再拖动距离滑块，演示距离触发告警。
- 最后说明本地规则与云端 AI 的分层设计。

## GitHub Pages

如果仓库启用 GitHub Pages，并将 source 设置为 `main` 分支根目录，仿真演示地址为：

```text
https://<github-username>.github.io/<repo-name>/simulation/
```
