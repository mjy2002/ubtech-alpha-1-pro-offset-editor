# UBTECH Alpha 1 Pro 舵机 Offset 编辑器

这是一个**独立运行的 Windows 图形界面工具**，用于通过 **USB HID** 接口读取和写入 UBTECH Alpha 1 Pro / Alpha 1S 机器人的**舵机 EEPROM 偏移量（Offset）**。

该编辑器：

* 显示原版 **AlphaRobot 的关节/舵机映射图**；
* 读取全部 **16 个舵机的 Offset 值**；
* 可以以 **1°（1度）**为步进调整 Offset；
* 在第一次写入之前，会自动创建一个 **JSON 格式的备份文件**。

项目由 **Maslodium** 维护。

---

# 硬件

* **机器人：** UBTECH Alpha 1 Pro / Alpha 1S
* **USB 设备：** HID
* **USB VID / PID：** `VID 0483 / PID 5750`
* **产品名称：** `Alpha1`
* 使用原厂 USB 连接时，**不需要 COM 串口**。

使用此编辑器之前，请先关闭 **`AlphaRobot1s_QT`**。

因为通过 HID 与机器人通信时，**同一时间只能有一个程序与机器人建立 HID 通信**。

---

# 从源代码运行

首先安装依赖：

```text
python -m pip install --user -r requirements.txt
```

然后运行：

```text
python .\alpha_offset_editor.py
```

也可以直接双击：

```text
run_alpha_offset_editor.cmd
```

---

# 检查通信

如果只想检查电脑与机器人的 USB HID 通信是否正常，而**不打开 GUI，也不进行任何写入操作**，可以运行：

```text
python .\alpha_offset_editor.py --check
```

这个功能适合在正式修改 EEPROM 之前确认 USB 通信是否正常。

---

# 文件说明

* **`alpha_offset_editor.py`**
  基于 Tkinter 编写的图形化 Offset 编辑器。

* **`alpha_joint_map.png`**
  原版 AlphaRobot 的关节/舵机位置映射图，编辑器使用这张图显示 16 个舵机的位置。

* **`run_alpha_offset_editor.cmd`**
  Windows 启动脚本。

* **`docs/Alpha1s.xml`**
  从原厂 AlphaRobot 软件中获取的舵机配置文件/舵机参数配置。

* **`docs/README-alpha-offset-editor.md`**
  俄文版使用说明。

* **`docs/README-alpha-servo-id.md`**
  关于实验性舵机 ID 识别程序的说明。这个实验性程序**没有包含在当前源码包中**。

---

# 安全注意事项

这个编辑器写入的是**绝对 EEPROM Offset（偏移量）**。

因此：

1. **每次只进行小幅度修改。**
2. 调整机器人舵机时，要确保机器人具有可靠的**机械支撑**，避免机器人突然动作导致摔倒或损坏。
3. **每次写入之后都要检查结果**，确认舵机位置和机器人姿态正常后，再进行下一次修改。
4. 在第一次写入之前，程序会生成一个 JSON 备份文件。

生成的备份文件类似：

```text
alpha-offsets-backup-*.json
```

这些文件会被 Git 忽略，因为其中包含**特定机器人设备的校准数据**。

---

# 这个项目实际上能做什么？

简单来说，这个程序不是普通的舵机控制软件，而是一个针对 **Alpha 1 Pro / Alpha 1S 舵机零位校准**的工具。

它的工作流程大致是：

```text
电脑
 │
 │ USB
 ▼
Alpha 1 Pro / Alpha 1S
 │
 │ USB HID
 ▼
读取 16 个舵机 EEPROM
 │
 ▼
显示每个舵机的 Offset
 │
 ├── Servo 1
 ├── Servo 2
 ├── Servo 3
 ├── ...
 └── Servo 16
       │
       ▼
    ±1° 调整
       │
       ▼
写回 EEPROM
```

这里最关键的一点是：**它使用的是 USB HID 通信，而不是 Alpha 舵机本身的普通 TTL/串口通信。**

因此，如果你的目标是研究 **Alpha 1 / Alpha 1S 的舵机通信协议、USB HID 协议以及 EEPROM Offset 数据格式**，这个项目其实非常有价值。

尤其值得进一步分析的是：

**`alpha_offset_editor.py` + `docs/Alpha1s.xml`**

从这两个文件里很可能可以直接找到：

* USB HID 的通信报文；
* 16 个舵机对应的 ID；
* 舵机 Offset 在 EEPROM 中的读写方式；
* Offset 数据格式；
* USB HID 的 Report 格式；
* AlphaRobot 主控与舵机之间的映射关系；
* 读取 EEPROM 的命令；
* 写入 EEPROM 的命令。

如果你把这个项目的 **`alpha_offset_editor.py` 和 `docs/Alpha1s.xml` 上传给我**，我可以直接帮你把**USB HID 通信协议逐字节逆向出来，并画出“PC → USB HID → Alpha 主控 → 舵机”的完整通信结构和数据帧格式**。
