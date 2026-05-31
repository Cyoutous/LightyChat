
| 设计要素 |内容 |
|:---|:---|
|类名	|ProtocolHandler|
|职责	|系统中唯一直接操作协议字节流的类，负责编码和解码|
|公开方法	|encode(msg) -> bytes、feed(data) -> list[Message]、validate_magic(data) -> bool（静态）
|内部状态	|self._buffer: bytes（接收缓冲区，应对粘包/半包）
|依赖	|entities.py 中的 Message、MessageType
|被依赖方	|发送模块、接收模块、连接接收器