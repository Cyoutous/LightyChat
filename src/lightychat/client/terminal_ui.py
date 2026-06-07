"""
终端聊天室 - 基于 Curses 的双面板 UI，接入输入转移模块与消息队列
"""
import curses
import locale
import time
import unicodedata
from typing import Any, Callable, List, Optional, Tuple

from lightychat.client.message_queue import MessageQueue
from lightychat.common.entities import MessageType

try:
    locale.setlocale(locale.LC_ALL, '')
except:
    pass

# ========== 工具函数 ==========

def display_width(s: str) -> int:
    w = 0
    for ch in s:
        if unicodedata.east_asian_width(ch) in ('W', 'F'):
            w += 2
        else:
            w += 1
    return w

def char_width(ch: str) -> int:
    return 2 if unicodedata.east_asian_width(ch) in ('W', 'F') else 1


def trim_text_to_width(text: str, max_width: int) -> str:
    result = ""
    width = 0
    for ch in text:
        cw = char_width(ch)
        if width + cw > max_width:
            break
        result += ch
        width += cw
    return result


def wrap_text(text: str, max_width: int) -> List[str]:
    lines: List[str] = []
    current_line = ""
    current_width = 0
    for ch in text:
        if ch == '\n':                     # 遇到换行，强制换行
            lines.append(current_line)
            current_line = ""
            current_width = 0
            continue
        cw = char_width(ch)
        if current_width + cw > max_width:
            lines.append(current_line)
            current_line = ch
            current_width = cw
        else:
            current_line += ch
            current_width += cw
    lines.append(current_line)             # 最后一行
    return lines

def wrap_lines_with_prefix(text: str, prefix: str, max_width: int) -> List[Tuple[int, str]]:
    lines: List[Tuple[int, str]] = []
    prefix_width = display_width(prefix)
    current_start = 0
    current_text = prefix
    current_width = prefix_width
    for i, ch in enumerate(text):
        cw = char_width(ch)
        if current_width + cw > max_width:
            lines.append((current_start, current_text))
            current_start = i
            current_text = ch
            current_width = cw
        else:
            current_text += ch
            current_width += cw
    lines.append((current_start, current_text))
    return lines


# ================================================================================================

# ========== TerminalUI 类 ==========

class TerminalUI:
    """终端 UI 模块：管理消息面板和输入面板，提供输入回调与消息队列接口。"""

    # ===================
    # ====== 常量 =======

    PREFIX = "> "
    MAX_INPUT_ROWS = 10
    MAX_MESSAGE_HISTORY = 10000

    # 颜色对编号
    COLOR_DEFAULT = 1       # 默认前景色（终端默认）
    COLOR_SYSTEM = 2        # 系统消息
    COLOR_CHAT = 3          # 公屏消息
    COLOR_PRIVATE = 4       # 私聊消息
    COLOR_RESPONSE = 5      # 指令响应
    COLOR_ERROR = 6         # 错误提示

     # 消息类型 → 颜色对编号 映射
    TYPE_COLOR_MAP: dict[MessageType | None, int] = {
        MessageType.TYPE_SYSTEM:          COLOR_SYSTEM,
        MessageType.TYPE_MESSAGE_DELIVER: COLOR_CHAT,
        MessageType.TYPE_PRIVATE_DELIVER: COLOR_PRIVATE,
        MessageType.TYPE_RESPONSE:        COLOR_RESPONSE,
        MessageType.TYPE_LOCAL_INFO:      COLOR_SYSTEM,
        MessageType.TYPE_LOCAL_ERROR:     COLOR_ERROR,
        None:                             COLOR_DEFAULT,
    }

    # ==================
    # ====== 方法 ======

    def __init__(self, message_queue: MessageQueue) -> None:
        self._queue = message_queue
        self._on_input: Optional[Callable[[str], None]] = None
        self._quit: bool = False

        self._stdscr: Any = None
        self._message_history: list[tuple[str, Optional[MessageType]]] = []
        self._input_buffer: str = ""
        self._cursor_index: int = 0
        self._needs_refresh: bool = True

    # ---------- 公开接口 ----------

    def run(self, on_input: Callable[[str], None]) -> None:
        """启动事件循环，阻塞直到退出。用户输入通过 on_input 回调返回。"""
        self._on_input = on_input
        curses.wrapper(self._main_loop)

    def request_shutdown(self) -> None:
        """请求退出事件循环（由其他线程调用）。"""
        self._quit = True

    # ---------- 内部：事件循环 ----------

    def _main_loop(self, stdscr: Any) -> None:
        self._stdscr = stdscr
        self._setup_curses()
        rows, cols = stdscr.getmaxyx()

        # 初始欢迎信息
        self._message_history.append(("⭐ Welcome to LIGHTYCHAT! ⭐", None))
        self._message_history.append(
            ("- 使用 /create <房间名> <昵称> <端口> 创建房间", None)
        )
        self._message_history.append(
            ("- 使用 /join <昵称> <IP:端口> 加入房间", None)
        )
        self._message_history.append(
            ("- 使用 /help 查询更多操作", None)
        )

        # 首次阻塞等待，避免启动时闪烁过快
        stdscr.getch()
        time.sleep(0.02)

        # 主循环
        while not self._quit:
            rows, cols = self._refresh_screen_size(rows, cols)

            # 1. 检查消息队列，更新消息历史
            self._flush_messages(cols)

            # 2. 预计算输入面板折行，并限制最大行数
            display_lines = self._get_input_display_lines(cols)
            max_input_rows = min(self.MAX_INPUT_ROWS, rows - 2)
            if max_input_rows < 1:
                max_input_rows = 1
            if len(display_lines) > max_input_rows:
                display_lines = display_lines[-max_input_rows:]
            input_height = len(display_lines)

            if self._needs_refresh:
                # 3. 显式将每一格填为空格 → 绘制内容 → 光标 → refresh 全量写出
                #    不用 erase/clear/clrtoeol —— PDCurses 增量 diff 对宽字符有 bug，
                #    显式触碰每格让 diff 认为全屏变化，绕过去。
                self._fill_screen(rows, cols)
                self._draw_message_panel(cols, rows, input_height)
                self._draw_input_panel(cols, rows, display_lines)
                self._set_input_cursor(display_lines, cols, rows)
                self._stdscr.refresh()
                self._needs_refresh = False

            # 4. 处理键盘输入（非阻塞）
            self._handle_input(stdscr)

            # 5. 短暂休眠，避免空转
            time.sleep(0.02)

    def _fill_screen(self, rows: int, cols: int) -> None:
        """将 stdscr 所有格显式填为空格，强制 diff 引擎输出全量屏幕。"""
        blank = " " * cols
        for row in range(rows):
            try:
                self._stdscr.addstr(row, 0, blank)
            except curses.error:
                pass

    def _setup_curses(self) -> None:
        curses.curs_set(1)
        self._stdscr.keypad(True)
        curses.cbreak()
        curses.noecho()
        self._stdscr.timeout(50) # 50ms 超时，既非阻塞又能周期性刷新

        # 初始化颜色支持
        if curses.has_colors():
            curses.start_color()
            # 颜色对定义（可根据终端外观调整）
            curses.init_pair(self.COLOR_DEFAULT,  curses.COLOR_WHITE, curses.COLOR_BLACK)
            curses.init_pair(self.COLOR_SYSTEM,   curses.COLOR_YELLOW, curses.COLOR_BLACK)
            curses.init_pair(self.COLOR_CHAT,     curses.COLOR_GREEN,  curses.COLOR_BLACK)
            curses.init_pair(self.COLOR_PRIVATE,  curses.COLOR_MAGENTA,curses.COLOR_BLACK)
            curses.init_pair(self.COLOR_RESPONSE, curses.COLOR_CYAN,   curses.COLOR_BLACK)
            curses.init_pair(self.COLOR_ERROR,    curses.COLOR_WHITE,    curses.COLOR_RED)


    def _refresh_screen_size(self, old_rows: int, old_cols: int) -> Tuple[int, int]:
        curses.update_lines_cols()  # 强制 PDCurses 立即检测终端尺寸变化，避免 refresh() 时越界崩溃
        new_rows, new_cols = self._stdscr.getmaxyx()
        if new_rows != old_rows or new_cols != old_cols:
            self._stdscr.clear()
            self._stdscr.refresh()
            self._needs_refresh = True
        return new_rows, new_cols

    # ---------- 内部：消息队列轮询 ----------

    def _flush_messages(self, cols: int) -> None:
        """非阻塞检查消息队列，将所有待显示文本追加到消息历史。"""
        updated = False
        while True:
            item = self._queue.get_nowait()
            if item is None:
                break
            text, msg_type = item
            updated = True

            wrapped = wrap_text(text, cols)
            for line in wrapped:
                self._message_history.append((line, msg_type))

            # 保持历史不超过缓冲高度
            if len(self._message_history) > self.MAX_MESSAGE_HISTORY:
                self._message_history = self._message_history[-self.MAX_MESSAGE_HISTORY:]

        if updated:
            self._needs_refresh = True

    # ---------- 内部：输入面板绘制 ----------

    def _draw_message_panel(self, cols: int, rows: int, input_height: int) -> None:
        msg_area_height = max(1, rows - input_height)
        visible_messages = self._message_history[-msg_area_height:]

        for row in range(msg_area_height):
            if row < len(visible_messages):
                line, msg_type = visible_messages[row]
                attr = curses.color_pair(
                    self.TYPE_COLOR_MAP.get(msg_type, self.COLOR_DEFAULT)
                )
                safe_line = trim_text_to_width(line, cols)
                try:
                    self._stdscr.addstr(row, 0, safe_line, attr)
                except curses.error:
                    pass

    def _draw_input_panel(self, cols: int, rows: int, display_lines: List[Tuple[int, str]]) -> None:
        """在 stdscr 上绘制底部输入面板（_fill_screen 已清空全屏，不需要清行尾）。"""
        input_height = len(display_lines)
        if input_height < 1:
            return
        input_top_row = rows - input_height

        for i, (_, line_text) in enumerate(display_lines):
            safe_line = trim_text_to_width(line_text, cols)
            try:
                self._stdscr.addstr(input_top_row + i, 0, safe_line)
            except curses.error:
                pass

    def _set_input_cursor(
        self,
        display_lines: List[Tuple[int, str]],
        cols: int,
        rows: int,
    ) -> None:
        """将 stdscr 光标定位到输入行的插入位置。"""
        input_height = len(display_lines)
        if input_height < 1:
            return
        input_top_row = rows - input_height
        cursor_line = self._find_cursor_line(display_lines)

        start_idx = display_lines[cursor_line][0]
        before = self._input_buffer[start_idx:self._cursor_index]
        if cursor_line == 0:
            cursor_col = display_width(self.PREFIX) + display_width(before)
        else:
            cursor_col = display_width(before)

        cursor_screen_row = min(input_top_row + cursor_line, rows - 1)
        cursor_col = min(cursor_col, cols - 1)

        try:
            self._stdscr.move(cursor_screen_row, cursor_col)
        except curses.error:
            pass

    def _get_input_display_lines(self, cols: int) -> List[Tuple[int, str]]:
        display_lines = wrap_lines_with_prefix(self._input_buffer, self.PREFIX, cols)
        return display_lines

    # ---------- 内部：键盘处理 ----------

    def _handle_input(self, stdscr: Any) -> None:
        try:
            ch = stdscr.get_wch()
        except curses.error:
            return

        if isinstance(ch, int):
            self._handle_function_key(ch)
            return

        # 普通字符或回车
        if ch == '\n':
            self._submit_input()
            self._needs_refresh = True
        elif ch in ('\x7f', '\b'):
            if self._cursor_index > 0:
                self._input_buffer = (
                    self._input_buffer[:self._cursor_index - 1]
                    + self._input_buffer[self._cursor_index:]
                )
                self._cursor_index -= 1
                self._needs_refresh = True
        else:
            self._input_buffer = (
                self._input_buffer[:self._cursor_index]
                + ch
                + self._input_buffer[self._cursor_index:]
            )
            self._cursor_index += len(ch)
            self._needs_refresh = True

    def _handle_function_key(self, ch: int) -> None:
        if ch == 3:                     # Ctrl+C
            self._quit = True
        elif ch == 17:                  # Ctrl+Q
            self._quit = True
            self._needs_refresh = True
        elif ch == curses.KEY_RESIZE:
            self._needs_refresh = True
        elif ch == curses.KEY_LEFT:
            if self._cursor_index > 0:
                self._cursor_index -= 1
                self._needs_refresh = True
        elif ch == curses.KEY_RIGHT:
            if self._cursor_index < len(self._input_buffer):
                self._cursor_index += 1
                self._needs_refresh = True
        elif ch == curses.KEY_UP:
            lines = self._get_current_display_lines()
            cur_line = self._find_cursor_line(lines)
            if cur_line > 0:
                # 移到上一行末尾
                prev_line_end = lines[cur_line][0] - 1
                self._cursor_index = max(0, prev_line_end)
                self._needs_refresh = True
        elif ch == curses.KEY_DOWN:
            lines = self._get_current_display_lines()
            cur_line = self._find_cursor_line(lines)
            if cur_line < len(lines) - 1:
                next_line_start = lines[cur_line + 1][0]
                self._cursor_index = min(next_line_start, len(self._input_buffer))
                self._needs_refresh = True
        elif ch == curses.KEY_HOME:
            self._cursor_index = 0
            self._needs_refresh = True
        elif ch == curses.KEY_END:
            self._cursor_index = len(self._input_buffer)
            self._needs_refresh = True
        elif ch in (curses.KEY_BACKSPACE, 8, 127):
            if self._cursor_index > 0:
                self._input_buffer = (
                    self._input_buffer[:self._cursor_index - 1]
                    + self._input_buffer[self._cursor_index:]
                )
                self._cursor_index -= 1
                self._needs_refresh = True
        elif ch == curses.KEY_DC:
            if self._cursor_index < len(self._input_buffer):
                self._input_buffer = (
                    self._input_buffer[:self._cursor_index]
                    + self._input_buffer[self._cursor_index + 1:]
                )
                self._needs_refresh = True

    def _submit_input(self) -> None:
        """用户按下回车，将输入文本通过回调提交给上层，并清空输入区。"""
        text = self._input_buffer
        self._input_buffer = ""
        self._cursor_index = 0

        # 忽略空内容和纯空白输入
        if not text.strip():
            return

        # /quit 在任何状态下直接退出程序
        if text == "/quit":
            self._quit = True
            return

        if self._on_input is not None:
            self._on_input(text)

    # ---------- 辅助方法 ----------

    def _get_current_display_lines(self) -> List[Tuple[int, str]]:
        """获取当前输入缓冲区的折行信息（不依赖绘制步骤）。"""
        cols = self._stdscr.getmaxyx()[1]
        return wrap_lines_with_prefix(self._input_buffer, self.PREFIX, cols)

    def _find_cursor_line(self, display_lines: List[Tuple[int, str]]) -> int:
        """找到光标当前所在的折行行号。"""
        for i in range(len(display_lines)):
            start_idx = display_lines[i][0]
            end_idx = (
                display_lines[i + 1][0]
                if i + 1 < len(display_lines)
                else len(self._input_buffer)
            )
            if start_idx <= self._cursor_index < end_idx:
                return i
        return len(display_lines) - 1 if display_lines else 0