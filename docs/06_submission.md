# 提交说明

## 推荐提交链接

提交 GitHub 仓库链接即可。仓库中包含完整的系统架构、控制逻辑、结构设计、工程分析和可交互仿真 Demo。

如果启用 GitHub Pages，可将演示地址设置为：

```text
https://<github-username>.github.io/<repo-name>/simulation/
```

## 评审查看顺序

1. 打开 [README.md](../README.md)，了解项目目标和交付物。
2. 打开 [simulation/index.html](../simulation/index.html)，运行交互仿真 Demo。
3. 查看 [docs/02_architecture.md](02_architecture.md)，确认系统架构和数据流。
4. 查看 [firmware/src/main.cpp](../firmware/src/main.cpp)，确认嵌入式状态机控制逻辑。
5. 查看 [mechanical/minipal_structure_layout.svg](../mechanical/minipal_structure_layout.svg)，确认结构布局和关键尺寸。
6. 查看 [docs/03_engineering_analysis.md](03_engineering_analysis.md)，确认失败场景和工程问题分析。

## 当前版本说明

当前版本以浏览器仿真作为主要演示方式。仿真器用于展示没有实体硬件时的系统闭环，包括：

- 按钮输入
- 距离传感器输入
- 状态机迁移
- AI 动作建议
- 舵机、LED、蜂鸣器输出反馈
- UART 风格日志

实体硬件方案仍保留在固件代码、结构文件和工程分析中，后续接入 ESP32 时可以复用相同的状态机和串口动作协议。

