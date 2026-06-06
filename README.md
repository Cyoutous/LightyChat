# LightyChat - 一个简易命令行局域网聊天室

一个基于 TCP 的轻量级 LAN 聊天工具。一个人创建房间，同个局域网里的其他人加入即可聊天。纯终端运行，开箱即用。

## 快速开始

### 安装

```
git clone https://github.com/Cyoutous/LightyChat.git
cd LightyChat
pip install .
```

### 使用

启动后进入本地大厅，输入命令：

- **创建房间：**
`/create <房间名> <昵称> <端口>`

- **加入房间：**
`/join <昵称> <房主IP:端口>`

- 更多命令（踢人、禁言、私聊等）输入 `/help` 查看。

## 已知问题

- **宽字符输入渲染异常**：输入框中输入中文、日文等宽字符时可能出现宽字符渲染失败问题，不影响消息的实际收发，仅为显示问题。

## 许可证

本项目采用 [MIT License](LICENSE) 许可。

## 贡献

本项目暂不接受 Pull Request，欢迎提 Issue 交流。
