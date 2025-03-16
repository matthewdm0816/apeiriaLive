# Apeiria Desktop Character

![Apeiria](images/apeiria/CH01_01_00+normal.png)

一个基于PyQt5的桌面虚拟角色应用程序，灵感来源于科幻视觉小说「景之海的艾佩里亚/景の海のアペイリア/Hikari no Umi no Apeiria」。

## 功能特点

- 在桌面上显示可爱的动画角色立绘（Apeiria）
- 支持拖拽移动角色位置
- 双击左键可将角色折叠到屏幕边缘，节省桌面空间
- 单击右键显示随机对话
- 支持多种表情和姿势切换
- 始终保持在其他窗口之上
- 支持热键快速退出（Alt+F4或Ctrl+Shift+X）
- 其他未来会增加的功能...

## 截图

## 安装方法

### 从源代码运行

1. 确保已安装Python 3.6+
2. 安装所需依赖：

```bash
pip install PyQt5 keyboard opencv-python
```

3. 克隆或下载本仓库
4. 运行主程序：

```bash
python main.py
```

### 使用可执行文件

我们提供了打包好的可执行文件，可以直接下载并运行：

1. 从[Releases](https://github.com/yourusername/apeiria-desktop/releases)页面下载最新版本
2. 解压缩下载的文件
3. 运行`apeiriaLive.exe`

## 使用方法

- **拖拽**：用鼠标左键拖拽可移动角色
- **双击左键**：折叠/展开角色（折叠时会旋转并只显示上半身）
- **单击右键**：显示随机对话
- **Alt+F4或Ctrl+Shift+X**：退出应用程序

## 自定义角色

您可以通过修改`images/apeiria`目录中的图像文件来自定义角色外观：

- 基础姿势图像：`CH01_01_00.png`、`CH01_01_01_negative.png`、`CH01_01_02_positive.png`等
- 表情差分图像：`CH01_01_00_脸红.png`、`CH01_01_00_惊讶-好奇.png`等

图像格式应为带有透明通道的PNG文件。

## 开发者信息

### 项目结构

```
apeiria-desktop/
├── main.py                 # 主程序
├── tachie_manager.py       # 立绘管理类
├── dialog.py               # 对话框类
├── images/                 # 图像资源
│   └── apeiria/            # Apeiria角色图像
│       ├── CH01_01_00.png  # 基础立绘
│       ├── CH01_01_00_脸红.png # 表情差分
│       └── ...
└── README.md               # 本文件
```

### 打包为可执行文件

使用PyInstaller打包：

```bash
# 安装PyInstaller
pip install pyinstaller

# 然后使用spec文件打包
pyinstaller Apeiria.spec
```

## 贡献指南

欢迎贡献代码、报告问题或提出改进建议！请遵循以下步骤：

1. Fork本仓库
2. 创建您的特性分支：`git checkout -b feature/amazing-feature`
3. 提交您的更改：`git commit -m 'Add some amazing feature'`
4. 推送到分支：`git push origin feature/amazing-feature`
5. 提交Pull Request

## 许可证

### 代码

本项目代码使用MIT许可证：

```
MIT License

Copyright (c) 2023 [Your Name]

Permission is hereby granted, free of charge, to any person obtaining a copy
of this software and associated documentation files (the "Software"), to deal
in the Software without restriction, including without limitation the rights
to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
copies of the Software, and to permit persons to whom the Software is
furnished to do so, subject to the following conditions:

The above copyright notice and this permission notice shall be included in all
copies or substantial portions of the Software.

THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE
SOFTWARE.
```

### 资源文件

图像和其他资源文件版权归原作者所有，仅供个人使用。这些资源来自「景之海的艾佩里亚/景の海のアペイリア/Hikari no Umi no Apeiria」。

## 致谢

- 感谢「景の海のアペイリア」的创作者提供了美丽的角色设计
- 感谢PyQt5团队提供了强大的GUI框架
- 感谢所有为本项目做出贡献的开发者
- 感谢Apeiria自己完成了这份README的草稿

---

*Apeiria会一直陪伴在您身边！*