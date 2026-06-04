from dataclasses import dataclass
from enum import IntEnum


class MessageType(IntEnum):
    TYPE_MESSAGE         = 0x0001
    TYPE_COMMAND         = 0x0002
    TYPE_SYSTEM          = 0x0003
    TYPE_MESSAGE_DELIVER = 0x0004
    TYPE_RESPONSE        = 0x0005
    TYPE_PRIVATE_DELIVER = 0x0006  # 服务器转发的私聊消息 
    TYPE_HEARTBEAT       = 0x0008  # 心跳ping
    TYPE_HEARTBEAT_ACK   = 0x0009  # 心跳pong

    # 本地消息类型（仅用于终端显示，不进入网络协议）
    TYPE_LOCAL_INFO      = 0x0101   # 本地信息提示（帮助、设置成功等）
    TYPE_LOCAL_ERROR     = 0x0102   # 本地错误提示（参数错误、权限不足等）


@dataclass
class Message:
    type: MessageType
    sender_id: str
    receiver_id: str
    payload: bytes


@dataclass
class User:
    user_id: str
    short_id: int
    sock: object
    is_host: bool
    is_muted: bool
    last_active: float
    addr: tuple[str, int]

    sender: object = None    # Sender 实例，类型用 object 避免循环导入
    receiver: object = None  # Receiver 实例


"""协议层异常基类"""
class ProtocolException(Exception):
    pass


class InvalidMagicError(ProtocolException):
    pass


class MessageTooLongError(ProtocolException):
    pass