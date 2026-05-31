```
LightyChat/
├── src/
│   ├── main.py                 # 程序入口，启动各组件
│   │
│   ├── network/                # 网络层
│   │   ├── __init__.py
│   │   └── ws_server.py        # WebSocket 服务端（手搓协议）
│   │
│   ├── service/                # 业务层
│   │   ├── __init__.py
│   │   ├── archive_manager.py  # 存档管理（创建、读写、追加）
│   │   └── config.py           # 配置管理（settings.json 读写）
│   │
│   ├── web/                    # Web 层（Flask）
│   │   ├── __init__.py
│   │   ├── app.py              # Flask 应用工厂
│   │   ├── routes.py           # 页面路由 + API 路由
│   │   └── templates/          # HTML 模板
│   │       ├── index.html      # 首页
│   │       └── chat.html       # 聊天室页面
│   │
│   └── ui/                     # 桌面壳（pywebview 相关）
│       ├── __init__.py
│       ├── window.py           # pywebview 窗口创建
│       └── tray.py             # 系统托盘
│
├── static/                     # 前端静态资源
│   ├── css/
│   │   └── style.css
│   └── js/
│       └── script.js
│
├── data/                       # 运行时数据
│   ├── settings.json
│   └── archives/
│       └── <uuid>.json
│
├── requirements.txt
└── README.md
```