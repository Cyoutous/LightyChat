# lightychat/client/session_controller.py
import socket
import threading
from typing import Optional, Any

from lightychat.client.message_queue import MessageQueue
from lightychat.client.input_switch import InputSwitch
from lightychat.client.heartbeat_client import HeartbeatClient
from lightychat.common.entities import Message, MessageType
from lightychat.common.protocol_handler import ProtocolHandler
from lightychat.common.sender import Sender
from lightychat.common.receiver import Receiver
from lightychat.common.settings import Settings
from lightychat.server.server_controller import ServerController


class SessionController:
    """客户端会话管理：创建/加入聊天室，维护收发线程和连接状态。"""

    def __init__(
        self,
        message_queue: MessageQueue,
        input_switch: InputSwitch,
        settings: Settings,
    ) -> None:
        self._queue = message_queue
        self._switch = input_switch
        self._settings = settings

        self._sock: Optional[socket.socket] = None
        self._sender: Optional[Sender] = None
        self._receiver: Optional[Receiver] = None
        self._server: Optional[ServerController] = None
        self._admin_token: Optional[str] = None
        self._heartbeat: Optional[HeartbeatClient] = None

    # ---------- 公开接口 ----------

    def create_chat(
        self, host: str, port: int, user_id: str, admin_token: str
    ) -> None:
        """创建聊天室：启动服务端线程 + 连接本机 + 注册房主身份。"""
        if self._sock is not None:
            self._queue.put(
                "[系统] 已经在一个聊天室中，请先退出。",
                MessageType.TYPE_LOCAL_ERROR,
            )
            return

        self._admin_token = admin_token

        # 1. 启动服务端线程
        server_config: dict[str, Any] = {
            "port": port,
            "room_name": self._settings.get("roomname"),
            "max_users": self._settings.get("max_users"),
            "admin_token": admin_token,
        }
        self._server = ServerController(server_config)
        server_thread = threading.Thread(
            target=self._server.start, daemon=True
        )
        server_thread.start()

        # 等待服务端线程准备就绪，再尝试连接本机
        if not self._server.wait_until_ready(timeout=5.0):
            self._queue.put(
                "[系统] 服务端启动超时，请重试。",
                MessageType.TYPE_LOCAL_ERROR,
            )
            return

        # 2. 客户端连接本机
        self._connect_and_register(host, port, user_id, is_host=True)

    def join_chat(self, address: str, user_id: str) -> None:
        """加入聊天室：解析地址、连接、注册普通用户。"""
        if self._sock is not None:
            self._queue.put(
                "[系统] 已经在一个聊天室中，请先退出。",
                MessageType.TYPE_LOCAL_ERROR,
            )
            return

        # 解析地址 host:port
        if ":" not in address:
            self._queue.put(
                "[系统] 地址格式错误，应为 host:port。",
                MessageType.TYPE_LOCAL_ERROR,
            )
            return
        host, _, port_str = address.rpartition(":")
        try:
            port = int(port_str)
        except ValueError:
            self._queue.put("[系统] 端口必须为整数。", MessageType.TYPE_LOCAL_ERROR)
            return

        self._admin_token = None
        self._connect_and_register(host, port, user_id, is_host=False)

    def disconnect(self) -> None:
        """断开当前连接，停止收发线程，清理资源。"""
        # 1. 停止心跳模块（必须在收发线程停止之前）
        if self._heartbeat:
            self._heartbeat.stop()
            self._heartbeat = None

        # 2. 停止客户端收发
        if self._sender:
            self._sender.stop()
            self._sender = None
        if self._receiver:
            self._receiver.stop()
            self._receiver = None
        if self._sock:
            try:
                self._sock.close()
            except OSError:
                pass
            self._sock = None

        # 2. 如果是房主，停止服务端线程
        if self._server:
            self._server.stop()
            self._server = None

        # 3. 通知输入转移模块
        self._switch.set_disconnected()
        self._admin_token = None

    # 发送消息 （测试时添加，不确定是否保留）
    def send_message(self, text: str) -> None:
        """发送公屏聊天消息。"""
        if self._sender is None:
            self._queue.put(
                "[系统] 尚未连接到服务器。",
                MessageType.TYPE_LOCAL_ERROR,
            )
            return
        msg = Message(
            type=MessageType.TYPE_MESSAGE,
            sender_id=self._switch.get_cached_user()["user_id"],
            receiver_id="",
            payload=text.encode("utf-8"),
        )
        self._sender.send(msg)

    # session_controller.py，紧接在 send_message 方法后面
    def send_command(self, payload: str) -> None:
        """发送指令到服务器。"""
        if self._sender is None:
            self._queue.put(
                "[系统] 尚未连接到服务器。",
                MessageType.TYPE_LOCAL_ERROR,
            )
            return
        user_info = self._switch.get_cached_user()
        msg = Message(
            type=MessageType.TYPE_COMMAND,
            sender_id=user_info.get("user_id", ""),
            receiver_id="",
            payload=payload.encode("utf-8"),
        )
        self._sender.send(msg)

    # ---------- 内部 ----------

    def _connect_and_register(
        self, host: str, port: int, user_id: str, is_host: bool
    ) -> None:
        """建立 TCP 连接、创建收发线程、发送注册消息。"""
        try:
            sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            sock.settimeout(5)  # 连接超时
            sock.connect((host, port))
            sock.settimeout(None)  # 连接建立后恢复阻塞模式
        except OSError as e:
            self._queue.put(
                f"[系统] 无法连接到服务器 {host}:{port}：{e}",
                MessageType.TYPE_LOCAL_ERROR,
            )
            return

        self._sock = sock
        proto = ProtocolHandler()

        # 创建收发模块
        self._sender = Sender(sock, proto)
        self._receiver = Receiver(sock, proto)

        # 注入回调
        self._receiver.set_on_message(self._on_message)
        self._receiver.set_on_disconnect(self._on_disconnect)
        self._sender.set_on_disconnect(self._on_disconnect)

        # 启动收发线程
        self._sender.start()
        self._receiver.start()

        # 发送注册消息：TYPE_COMMAND，内容为 "/register <user_id> <is_host>"
        # is_host 为 "1" 或 "0"，便于服务端解析
        register_payload = f"/register {user_id} {1 if is_host else 0}".encode("utf-8")
        register_msg = Message(
            type=MessageType.TYPE_COMMAND,
            sender_id=user_id,    # 暂时用请求的昵称，服务端可能重命名
            receiver_id="",
            payload=register_payload,
        )
        self._sender.send(register_msg)

        self._queue.put(
            f"[系统] 已连接到 {host}:{port}，正在注册...",
            MessageType.TYPE_LOCAL_INFO,
        )

    def _on_message(self, msg: Message) -> None:
        """处理收到的消息：注册响应 -> 更新状态；其他消息 -> 推入显示队列。"""
        # 心跳应答消息不显示，由心跳模块内部消化
        if msg.type == MessageType.TYPE_HEARTBEAT_ACK:
            return

        if msg.type == MessageType.TYPE_RESPONSE:
            # 检查是否为注册响应（简单约定：内容以 "/register" 开头）
            payload_text = msg.payload.decode("utf-8", errors="replace")
            if payload_text.startswith("/register"):
                self._handle_register_response(payload_text)
                return
            # 指令响应直接显示内容，不加标签
            self._queue.put(payload_text, msg.type)
            return

        payload_text = msg.payload.decode("utf-8", errors="replace")

        # 仅对需要标签的类型做处理
        if msg.type == MessageType.TYPE_SYSTEM:
            formatted = f"[系统] {payload_text}"
        elif msg.type == MessageType.TYPE_PRIVATE_DELIVER:
            formatted = f"[私聊] {payload_text}"
        else:
            # TYPE_MESSAGE_DELIVER 等：直接显示
            formatted = f"{msg.sender_id}: {payload_text}" if msg.sender_id else payload_text

        self._queue.put(formatted, msg.type)

    def _handle_register_response(self, payload: str) -> None:
        """解析注册响应，更新 InputSwitch 状态。"""
        # 格式：/register <status> <actual_id> <is_host> [extra...]
        parts = payload.split(" ", 3)
        if len(parts) < 4:
            self._queue.put(
                "[系统] 注册响应格式错误，连接失败。",
                MessageType.TYPE_LOCAL_ERROR,
            )
            self.disconnect()
            return

        status = parts[1]       # "ok" 或 "err"
        actual_id = parts[2]    # 服务端分配的实际 ID
        is_host_str = parts[3]  # "1" 或 "0"

        if status != "ok":
            self._queue.put(
                f"[系统] 注册失败：{actual_id}",
                MessageType.TYPE_LOCAL_ERROR,
            )
            self.disconnect()
            return

        is_host = is_host_str == "1"
        self._switch.set_connected(actual_id, is_host, self._admin_token or "")
        self._queue.put(
            f"[系统] 注册成功！你的 ID 为 {actual_id}。",
            MessageType.TYPE_SYSTEM,
        )

        # 启动心跳模块
        if self._sender is not None:
            self._heartbeat = HeartbeatClient(self._sender)
            self._heartbeat.start()

    def _on_disconnect(self) -> None:
        """连接断开回调：通知 UI 并清理资源。"""
        self._queue.put(
            "[系统] 与服务器的连接已断开。",
            MessageType.TYPE_SYSTEM,
        )

        # 关闭心跳模块
        if self._heartbeat:
            self._heartbeat.stop()
            self._heartbeat = None

        # 断开
        self.disconnect()