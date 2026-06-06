# test_sender_receiver.py
import socket
import time

from lightychat.common.entities import Message, MessageType
from lightychat.common.protocol_handler import ProtocolHandler
from lightychat.common.sender import Sender
from lightychat.common.receiver import Receiver


def main() -> None:
    # 1. 创建一对已连接的 socket
    a_sock, b_sock = socket.socketpair()

    # 2. 每端各一个 ProtocolHandler
    proto_a = ProtocolHandler()
    proto_b = ProtocolHandler()

    # 3. 创建 Sender（用 a_sock 发送）和 Receiver（用 b_sock 接收）
    sender = Sender(a_sock, proto_a)
    receiver = Receiver(b_sock, proto_b)

    # 4. 注册回调：收到消息时打印
    def on_message(msg: Message) -> None:
        payload_text = msg.payload.decode("utf-8")
        print(f"[收到] type={msg.type.name}, sender={msg.sender_id}, "
              f"receiver={msg.receiver_id}, payload={payload_text}")

    def on_disconnect() -> None:
        print("[断连] 连接已断开")

    receiver.set_on_message(on_message)
    receiver.set_on_disconnect(on_disconnect)

    # 5. 启动收发线程
    sender.start()
    receiver.start()

    # 6. 发送几条测试消息
    msg1 = Message(
        type=MessageType.TYPE_MESSAGE,
        sender_id="Alice",
        receiver_id="",
        payload="Hello 世界".encode("utf-8"),
    )
    sender.send(msg1)

    msg2 = Message(
        type=MessageType.TYPE_SYSTEM,
        sender_id="",
        receiver_id="",
        payload="系统消息：测试".encode("utf-8"),
    )
    sender.send(msg2)

    # 7. 稍等一会让消息传输完成
    time.sleep(0.3)

    # 8. 关闭连接
    sender.stop()
    receiver.stop()
    a_sock.close()
    b_sock.close()

    print("测试完成")


if __name__ == "__main__":
    main()