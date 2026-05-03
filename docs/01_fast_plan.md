# 实施方案

## 一句话方案

做一个“按下按钮会唤醒、前方太近会警觉、可以通过本地规则或云端 AI 决定反馈动作”的桌宠型桌面机器人 `MiniPal`。

## 为什么选这个方案

- 任务闭环完整：输入、决策、执行、反馈都齐。
- 嵌入式部分真实：有状态机、有中断、有主循环。
- AI 接入合理：本地规则负责实时，云端模型负责更灵活的动作策略。
- 结构设计容易讲：前脸放传感器，上层放舵机，下层放主板和电源，重心低。
- 桌宠风格更适合展示，前脸“眼睛”能直接强化交互感。

## 对照作业要求的拆解

### 0. 可运行仿真 Demo

已经在 [simulation/index.html](../simulation/index.html) 中给出：

- 按钮输入仿真
- 距离传感器滑块仿真
- 状态机实时显示
- 舵机、LED、蜂鸣器输出反馈
- UART 日志与 AI 动作建议

### 1. 系统架构设计

已经在 [docs/02_architecture.md](docs/02_architecture.md) 中给出：

- 输入模块
- 控制模块
- 输出模块
- 通信链路
- 数据流说明

### 2. 嵌入式控制设计

已经在 [firmware/src/main.cpp](../firmware/src/main.cpp) 中给出：

- 按钮中断
- 主循环采样
- `IDLE / WAKE / TRACK / ALERT / COOLDOWN` 五态管理
- 事件触发与输出控制

### 3. 3D 结构设计

已经在 [mechanical/minipal_structure_layout.svg](../mechanical/minipal_structure_layout.svg) 和 [mechanical/minipal_case.scad](../mechanical/minipal_case.scad) 中给出：

- 顶视/侧视布局
- 关键尺寸
- 模块位置
- 打印风险说明

### 4. 工程问题分析

已经在 [docs/03_engineering_analysis.md](docs/03_engineering_analysis.md) 中给出：

- 最脆弱环节
- 舵机抖动排查
- 传感器噪声处理
- 至少一个失败场景

### 5. AI 能力接入

已经在 [host/ai_bridge.py](../host/ai_bridge.py) 和 [docs/02_architecture.md](docs/02_architecture.md) 中给出：

- 本地规则模式
- 云端 API 模式
- 延迟与成本权衡

### 6. 无实体硬件时的验证方式

本项目提供浏览器仿真器作为演示原型。仿真器不替代硬件设计，但用于证明系统闭环、状态管理、输入输出映射和 AI 分层逻辑是完整的。

## 推荐实施路线

### 路线 A：仿真交付

- 使用浏览器仿真器演示按钮、距离、状态机和输出反馈
- 保留固件代码作为实体硬件实现依据
- 使用结构图和 OpenSCAD 文件说明装配设计

适合：没有实体硬件时完成完整展示

### 路线 B：推荐交付

- 保留路线 A
- 增加 Python 串口桥接代码
- 在展示里说明实体硬件可通过 UART 复用同一套动作协议

适合：希望既保留稳定性，又体现 AI 接入

### 路线 C：冲加分

- 录制一段仿真演示视频
- 补充供电管理和量产思考

适合：希望进一步增强展示效果

## 最小 BOM

- ESP32 DevKit x1
- HC-SR04 距离传感器 x1
- SG90 舵机 x1
- WS2812 RGB 灯珠或灯环 x1
- 有源或无源蜂鸣器 x1
- 按钮开关 x1
- 5V 电源或移动电源 x1
- 面包板 / 杜邦线若干
- 3D 打印外壳 1 套

条件不太允许做实物硬件就全部仿真了orz
