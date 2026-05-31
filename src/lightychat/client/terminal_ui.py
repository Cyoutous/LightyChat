"""
终端聊天室 - 基于 Curses 的双面板 UI，接入输入转移模块与消息队列
"""
import curses
import locale
import time
from typing import Any, Callable, List, Optional, Tuple

from lightychat.client.message_queue import MessageQueue

try:
    locale.setlocale(locale.LC_ALL, '')
except:
    pass

# ========== 工具函数 ==========

def display_width(s: str) -> int:
    import unicodedata
    w = 0
    for ch in s:
        if unicodedata.east_asian_width(ch) in ('W', 'F'):
            w += 2
        else:
            w += 1
    return w

def char_width(ch: str) -> int:
    import unicodedata
    return 2 if unicodedata.east_asian_width(ch) in ('W', 'F') else 1

def wrap_text(text: str, max_width: int) -> List[str]:
    lines: List[str] = []
    current_line = ""
    current_width = 0
    for ch in text:
        cw = char_width(ch)
        if current_width + cw > max_width:
            lines.append(current_line)
            current_line = ch
            current_width = cw
        else:
            current_line += ch
            current_width += cw
    if current_line or not lines:
        lines.append(current_line)
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


# ========== TerminalUI 类 ==========

class TerminalUI:
    """终端 UI 模块：管理消息面板和输入面板，提供输入回调与消息队列接口。"""

    PREFIX = "> "
    MAX_INPUT_ROWS = 10
    PAD_MAX_WIDTH = 500
    PAD_MAX_HEIGHT = 10000

    def __init__(self, message_queue: MessageQueue) -> None:
        self._queue = message_queue
        self._on_input: Optional[Callable[[str], None]] = None
        self._quit: bool = False

        self._stdscr: Any = None
        self._msg_pad: Any = None
        self._input_pad: Any = None
        self._current_msg_row: int = 1
        self._input_buffer: str = ""
        self._cursor_index: int = 0

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
        self._msg_pad = curses.newpad(self.PAD_MAX_HEIGHT, self.PAD_MAX_WIDTH)
        #self._msg_pad.leaveok(True)
        self._msg_pad.scrollok(True)
        self._msg_pad.addstr(0, 0, "Chat started! Type /quit to exit. Ctrl+Q to quit UI.")
        self._input_pad = curses.newpad(self.MAX_INPUT_ROWS, self.PAD_MAX_WIDTH)
        self._input_pad.keypad(True)

        while not self._quit:
            rows, cols = self._refresh_screen_size(rows, cols)

            # 1. 检查消息队列，更新消息面板
            self._flush_messages(cols)

            # 2. 绘制输入面板
            display_lines = self._draw_input_panel(cols, rows)

            # 3. 光标定位
            self._position_cursor(display_lines, cols, rows)

            # + 或许有用的光标设置方式 （补：不要加这个指令，有问题。这里留下这个注释用于以后研究
            #curses.doupdate()

            # 4. 处理键盘输入（非阻塞）
            self._handle_input(stdscr)

            # 5. 短暂休眠，避免空转
            time.sleep(0.02)

    def _setup_curses(self) -> None:
        curses.curs_set(1)
        # self._input_pad = curses.newpad(self.MAX_INPUT_ROWS, self.PAD_MAX_WIDTH)
        self._stdscr.keypad(True)
        # self._input_pad.leaveok(True)
        curses.cbreak()
        curses.noecho()
        self._stdscr.nodelay(True)

    def _refresh_screen_size(self, old_rows: int, old_cols: int) -> Tuple[int, int]:
        new_rows, new_cols = self._stdscr.getmaxyx()
        if new_rows != old_rows or new_cols != old_cols:
            self._stdscr.clear()
            self._stdscr.refresh()
        return new_rows, new_cols

    # ---------- 内部：消息队列轮询 ----------

    def _flush_messages(self, cols: int) -> None:
        """非阻塞检查消息队列，将所有待显示文本追加到消息面板。"""
        while True:
            text = self._queue.get_nowait()
            if text is None:
                break
            wrapped = wrap_text(text, cols)
            for line in wrapped:
                self._msg_pad.addstr(self._current_msg_row, 0, line)
                self._current_msg_row += 1

    # ---------- 内部：输入面板绘制 ----------

    def _draw_input_panel(self, cols: int, rows: int) -> List[Tuple[int, str]]:
        max_input_rows = min(self.MAX_INPUT_ROWS, rows - 2)
        if max_input_rows < 1:
            max_input_rows = 1

        display_lines = wrap_lines_with_prefix(self._input_buffer, self.PREFIX, cols)
        if len(display_lines) > max_input_rows:
            display_lines = display_lines[-max_input_rows:]

        input_height = len(display_lines)
        msg_area_height = max(1, rows - input_height)

        # 刷新消息面板
        if self._current_msg_row >= msg_area_height:
            scroll_start = self._current_msg_row - msg_area_height + 1
        else:
            scroll_start = 0

        pad_bottom = min(msg_area_height - 1, rows - 1)
        pad_right = min(cols - 1, self.PAD_MAX_WIDTH - 1)
        self._msg_pad.noutrefresh(scroll_start, 0, 0, 0, pad_bottom, pad_right)

        # 绘制输入面板
        self._input_pad.clear()
        for i, (_, line_text) in enumerate(display_lines):
            try:
                self._input_pad.addstr(i, 0, line_text)
            except curses.error:
                pass

        input_top_row = rows - input_height
        in_bottom = min(input_top_row + input_height - 1, rows - 1)
        in_right = min(cols - 1, self.PAD_MAX_WIDTH - 1)
        self._input_pad.noutrefresh(0, 0, input_top_row, 0, in_bottom, in_right)

        return display_lines

    # ---------- 内部：光标定位 ----------

    def _position_cursor(
        self,
        display_lines: List[Tuple[int, str]],
        cols: int,
        rows: int,
    ) -> None:
        input_height = len(display_lines)
        input_top_row = rows - input_height
        cursor_line = self._find_cursor_line(display_lines)
        # cursor_col = 0

        # 计算光标所在列
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
        elif ch in ('\x7f', '\b'):
            if self._cursor_index > 0:
                self._input_buffer = (
                    self._input_buffer[:self._cursor_index - 1]
                    + self._input_buffer[self._cursor_index:]
                )
                self._cursor_index -= 1
        else:
            self._input_buffer = (
                self._input_buffer[:self._cursor_index]
                + ch
                + self._input_buffer[self._cursor_index:]
            )
            self._cursor_index += len(ch)

    def _handle_function_key(self, ch: int) -> None:
        if ch == 3:                     # Ctrl+C
            self._quit = True
        elif ch == 17:                  # Ctrl+Q
            self._quit = True
        elif ch == curses.KEY_RESIZE:
            pass
        elif ch == curses.KEY_LEFT:
            if self._cursor_index > 0:
                self._cursor_index -= 1
        elif ch == curses.KEY_RIGHT:
            if self._cursor_index < len(self._input_buffer):
                self._cursor_index += 1
        elif ch == curses.KEY_UP:
            lines = self._get_current_display_lines()
            cur_line = self._find_cursor_line(lines)
            if cur_line > 0:
                # 移到上一行末尾
                prev_line_end = lines[cur_line][0] - 1
                self._cursor_index = max(0, prev_line_end)
        elif ch == curses.KEY_DOWN:
            lines = self._get_current_display_lines()
            cur_line = self._find_cursor_line(lines)
            if cur_line < len(lines) - 1:
                next_line_start = lines[cur_line + 1][0]
                self._cursor_index = min(next_line_start, len(self._input_buffer))
        elif ch == curses.KEY_HOME:
            self._cursor_index = 0
        elif ch == curses.KEY_END:
            self._cursor_index = len(self._input_buffer)
        elif ch in (curses.KEY_BACKSPACE, 8, 127):
            if self._cursor_index > 0:
                self._input_buffer = (
                    self._input_buffer[:self._cursor_index - 1]
                    + self._input_buffer[self._cursor_index:]
                )
                self._cursor_index -= 1
        elif ch == curses.KEY_DC:
            if self._cursor_index < len(self._input_buffer):
                self._input_buffer = (
                    self._input_buffer[:self._cursor_index]
                    + self._input_buffer[self._cursor_index + 1:]
                )

    def _submit_input(self) -> None:
        """用户按下回车，将输入文本通过回调提交给上层，并清空输入区。"""
        text = self._input_buffer
        self._input_buffer = ""
        self._cursor_index = 0

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