from dataclasses import dataclass
from enum import IntEnum


class MessageType(IntEnum):
    TYPE_MESSAGE         = 0x0001
    TYPE_COMMAND         = 0x0002
    TYPE_SYSTEM          = 0x0003
    TYPE_MESSAGE_DELIVER = 0x0004
    TYPE_RESPONSE        = 0x0005
    TYPE_HEARTBEAT       = 0x0008
    TYPE_HEARTBEAT_ACK   = 0x0009


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


"""协议层异常基类"""
class ProtocolException(Exception):
    pass


class InvalidMagicError(ProtocolException):
    pass


class MessageTooLongError(ProtocolException):
    pass