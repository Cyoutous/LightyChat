import struct
from lightychat.common.entities import Message, MessageType, InvalidMagicError, MessageTooLongError


class ProtocolHandler:
    MAGIC = b'LCHT'
    HEADER_SIZE = 14
    MAX_MESSAGE_LENGTH = 4096

    def __init__(self):
        self._buffer = b""

    # ---------- 公开接口 ----------
    def encode(self, msg: Message) -> bytes:
        """将 Message 对象编码为字节流"""
        sender_bytes = msg.sender_id.encode('utf-8')
        receiver_bytes = msg.receiver_id.encode('utf-8')

        total_len = (self.HEADER_SIZE
                     + len(sender_bytes)
                     + len(receiver_bytes)
                     + len(msg.payload))

        if total_len > self.MAX_MESSAGE_LENGTH:
            raise MessageTooLongError(
                f"消息总长度 {total_len} 超过上限 {self.MAX_MESSAGE_LENGTH}"
            )

        header = struct.pack(
            '!4s H I H H',  
            self.MAGIC,
            int(msg.type),
            total_len,
            len(sender_bytes),
            len(receiver_bytes)
        )
        return header + sender_bytes + receiver_bytes + msg.payload

    def feed(self, data: bytes) -> list[Message]:
        """追加字节数据，返回本次解析出的所有完整消息"""
        self._buffer += data
        messages: list[Message]  = []

        while len(self._buffer) >= self.HEADER_SIZE:
            magic, msg_type, total_len, sender_len, receiver_len = \
                struct.unpack('!4s H I H H', self._buffer[:self.HEADER_SIZE])

            if magic != self.MAGIC:
                raise InvalidMagicError(f"非法魔数: {magic!r}")

            if total_len > self.MAX_MESSAGE_LENGTH:
                raise MessageTooLongError(
                    f"总长度字段 {total_len} 超过上限 {self.MAX_MESSAGE_LENGTH}"
                )

            if len(self._buffer) < total_len:
                break  # 半包，等待更多数据

            # 提取完整消息
            body_start = self.HEADER_SIZE
            sender_id = self._buffer[body_start:body_start + sender_len].decode('utf-8')
            body_start += sender_len
            receiver_id = self._buffer[body_start:body_start + receiver_len].decode('utf-8')
            body_start += receiver_len
            payload = self._buffer[body_start:total_len]

            messages.append(Message( 
                type=MessageType(msg_type),
                sender_id=sender_id,
                receiver_id=receiver_id,
                payload=payload
            ))

            self._buffer = self._buffer[total_len:]

        return messages

    @staticmethod
    def validate_magic(data: bytes) -> bool:
        """快速校验魔数"""
        return len(data) >= 4 and data[:4] == ProtocolHandler.MAGIC