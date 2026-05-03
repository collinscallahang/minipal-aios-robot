# MiniPal: AIOS 桌面机器人 MVP

`MiniPal` 是一个桌宠风格的最小可用桌面 AI 机器人系统，目标是用尽量少的模块完成一个完整闭环：

- 输入：按钮 + HC-SR04 距离传感器
- 控制：ESP32 实时控制 + Python AI 桥接
- 输出：SG90 舵机 + WS2812 RGB LED + 蜂鸣器
- 通信：USB UART，支持可选云端 HTTP API

机器人前脸直接利用 HC-SR04 的双探头作为“眼睛”，既保留真实传感器功能，也形成更容易展示的桌宠外观。

## 在线仿真平台

直接打开网页体验：

[MiniPal 仿真平台](https://raw.githack.com/collinscallahang/minipal-aios-robot/codex-ai-bridge-access/simulation/index.html)

这个链接会打开可交互网页。

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
- AI 能力接入说明：[docs/08_ai_access.md](docs/08_ai_access.md)

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

直接用浏览器打开 [MiniPal 仿真平台](https://raw.githack.com/collinscallahang/minipal-aios-robot/codex-ai-bridge-access/simulation/index.html)，即可演示按钮唤醒、距离告警、状态机迁移、AI 动作建议和输出反馈。

### 2. 固件

如果有实体硬件，可用 PlatformIO 打开 [firmware/platformio.ini](firmware/platformio.ini) 并烧录到 `esp32dev`。

### 3. 主机侧 AI 桥接

只连接浏览器仿真平台时可运行：

```bash
pip install -r host/requirements.txt
python host/ai_bridge.py --mode local
```

然后打开 [MiniPal 仿真平台](https://raw.githack.com/collinscallahang/minipal-aios-robot/codex-ai-bridge-access/simulation/index.html)，在输入框里直接和 `MiniPal` 对话。

实体硬件调试时可指定串口：

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

## GitHub Pages

如果仓库启用 GitHub Pages，并将 source 设置为 `codex-ai-bridge-access` 分支根目录，仿真演示地址为：

```text
https://collinscallahang.github.io/minipal-aios-robot/
```
未来量产考虑：
1. 外壳材料：从 3D 打印转向注塑工艺
目前的开发阶段多采用 3D 打印，但量产必须考虑注塑（Injection Molding）。

材料选择 - ABS 或 ABS+PC：

优点： 强度高、耐摔、着色性好。

质感处理： 建议表面采用细磨砂晒纹（VDI纹理），不仅能有效防止指纹，还能掩盖注塑带来的微小缩水痕跡，提升“高级感”。

半透明材质的应用：

如果 MiniPal 的面部或胸部有 LED 灯光交互，可以使用半透明 PC 材质。

工艺技巧： 内壁喷涂遮光漆，仅在灯珠位置留出透光点，实现“光从材料中透出来”的呼吸感，而非廉价的直接漏光。

2. 内部结构：模组化与“减法”逻辑
量产的逻辑是“易组装、高良率”。

骨架模组化：

将内部的舵机固定架、主板支架集成到一个内骨架（Skeleton）上，外壳仅作为皮囊包裹。这样可以实现“内外解耦”，即便外壳更换设计，内部结构也能通用。

弃用散乱跳线：

量产版必须定制 FPC（柔性电路板） 或插拔式线束。

散乱的杜邦线在长期的舵机摆动下极易发生断裂或接触不良。

3. 核心部件优化：舵机与传感器
舵机寿命（核心痛点）：

原型机常用的 9g 舵机（如 SG90）寿命仅有几十小时，量产版需换成金属齿轮舵机或无刷磁编码舵机。

静音处理： 桌面机器人离人很近，舵机运作的“吱吱”声很破坏沉浸感。量产时需选用带静音驱动算法的数字舵机。

传感器集成：

目前的距离传感器可能是超声波或简单的红外，量产建议集成 ToF (Time of Flight) 传感器。

ToF 传感器体积更小，可以隐藏在黑色的半透明面板后，保持机器人脸部的完整性，而不像超声波那样有两个“大眼睛”空洞。

4. 表面工艺：赋予“生命力”
类肤涂层（Soft Touch Coating）：

在 ABS 外壳上增加一层类肤漆。作为陪伴机器人，用户可能会去摸它，类肤漆能提供温暖、柔软的手感，消除塑料的冰冷感。

IML（模内镶件注塑）：

如果脸部有显示屏或触摸交互，可以使用 IML 工艺，将图案和防护膜一体成型，抗划伤且不掉漆。
