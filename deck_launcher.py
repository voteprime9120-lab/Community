#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Deck Launcher - 스팀덱 스타일 앱 런처

타일(앱)을 클릭하면 그 앱이 바로 실행되고, 런처는 뒤로 물러납니다.

  * 마우스 클릭 / Enter / 게임패드 A 버튼  -> 바로 실행
  * 방향키 / 게임패드 D-Pad·스틱          -> 이동
  * 우클릭 / F2                          -> 편집 메뉴 (이름, 아이콘, 색상, 순서, 삭제)
  * F11                                  -> 전체화면 전환
  * Esc                                  -> 전체화면 해제 / 종료

추가 설치 없이 파이썬 기본 tkinter 만으로 동작합니다.
  - Pillow 가 있으면 JPG 등 다양한 아이콘 이미지를 쓸 수 있습니다.  (pip install pillow)
  - pygame 이 있으면 게임패드로 조작할 수 있습니다.                (pip install pygame)

앱 목록은 실행 파일 옆의 apps.json 에 저장됩니다.
"""

import json
import os
import platform
import shlex
import subprocess
import sys
import time
import tkinter as tk
import tkinter.font as tkfont
from tkinter import colorchooser, filedialog, messagebox, simpledialog

try:  # 선택: 더 많은 이미지 형식 + 고품질 리사이즈
    from PIL import Image, ImageTk
except Exception:  # pragma: no cover
    Image = ImageTk = None

SYSTEM = platform.system()  # "Windows" | "Darwin" | "Linux"

if getattr(sys, "frozen", False):  # PyInstaller 로 만든 exe
    APP_DIR = os.path.dirname(os.path.abspath(sys.executable))
else:
    APP_DIR = os.path.dirname(os.path.abspath(__file__))
CONFIG_PATH = os.path.join(APP_DIR, "apps.json")

# ---------------------------------------------------------------- 디자인 상수
BG = "#0e141b"
BG_BAR = "#171d25"
TEXT = "#dcdedf"
TEXT_DIM = "#8b929a"
ACCENT = "#1a9fff"
TILE_PALETTE = [
    "#2a475e", "#4c6b22", "#6b2d5c", "#7a4b12", "#1f5f5b",
    "#3d3a8a", "#8a2f2f", "#365314", "#5b3a29", "#234e70",
]

TILE_W, TILE_H = 200, 262
ART_H = 200
GAP = 28
MARGIN_X = 48
PAD_TOP = 24
HEADER_H = 84
FOOTER_H = 48


# ---------------------------------------------------------------- 설정 파일
def default_apps():
    """처음 실행할 때 OS 별로 넣어두는 예시 앱들."""
    if SYSTEM == "Windows":
        return [
            {"name": "파일 탐색기", "target": "explorer.exe"},
            {"name": "메모장", "target": "notepad.exe"},
            {"name": "계산기", "target": "calc.exe"},
            {"name": "그림판", "target": "mspaint.exe"},
            {"name": "웹 브라우저", "target": "https://www.google.com"},
        ]
    if SYSTEM == "Darwin":
        return [
            {"name": "Finder", "target": "/System/Library/CoreServices/Finder.app"},
            {"name": "Safari", "target": "/Applications/Safari.app"},
            {"name": "계산기", "target": "/System/Applications/Calculator.app"},
            {"name": "텍스트 편집기", "target": "/System/Applications/TextEdit.app"},
        ]
    return [
        {"name": "파일", "target": "~"},
        {"name": "웹 브라우저", "target": "https://www.google.com"},
        {"name": "터미널", "target": "x-terminal-emulator"},
    ]


def default_config():
    return {
        "settings": {
            "fullscreen": False,          # 시작할 때 전체화면
            "minimize_on_launch": True,   # 앱 실행 후 런처 최소화 (앱으로 바로 전환)
        },
        "apps": default_apps(),
    }


def load_config():
    if os.path.exists(CONFIG_PATH):
        try:
            with open(CONFIG_PATH, "r", encoding="utf-8") as f:
                data = json.load(f)
            data.setdefault("settings", {})
            for k, v in default_config()["settings"].items():
                data["settings"].setdefault(k, v)
            data.setdefault("apps", [])
            return data
        except Exception as e:
            messagebox.showwarning(
                "설정 파일 오류",
                f"apps.json 을 읽지 못했습니다. 기본 설정으로 시작합니다.\n\n{e}")
    data = default_config()
    save_config(data)
    return data


def save_config(data):
    tmp = CONFIG_PATH + ".tmp"
    try:
        with open(tmp, "w", encoding="utf-8") as f:
            json.dump(data, f, ensure_ascii=False, indent=2)
        os.replace(tmp, CONFIG_PATH)
    except OSError as e:
        messagebox.showerror("저장 실패", f"apps.json 을 저장하지 못했습니다.\n\n{e}")


# ---------------------------------------------------------------- 앱 실행
def _popen(cmd, cwd=None):
    kwargs = {"cwd": cwd or None, "stdin": subprocess.DEVNULL,
              "stdout": subprocess.DEVNULL, "stderr": subprocess.DEVNULL}
    if SYSTEM == "Windows":
        kwargs["creationflags"] = 0x00000008 | 0x00000200  # DETACHED | NEW_PROCESS_GROUP
    else:
        kwargs["start_new_session"] = True  # 런처를 닫아도 앱은 계속 실행
    subprocess.Popen(cmd, **kwargs)


def _open_with_system(target):
    if SYSTEM == "Windows":
        os.startfile(target)  # noqa: 윈도우 전용
    elif SYSTEM == "Darwin":
        _popen(["open", target])
    else:
        _popen(["xdg-open", target])


def launch_app(app):
    """apps.json 항목 하나를 실행한다.

    target 에는 다음을 넣을 수 있다.
      - 실행 파일 경로     C:\\Games\\game.exe, /Applications/Steam.app
      - 바로가기/문서      C:\\Users\\me\\Desktop\\게임.lnk, ~/문서/메모.txt
      - URL/프로토콜       https://..., steam://rungameid/570
      - PATH 상의 명령어   notepad.exe, firefox --new-window
    """
    target = os.path.expandvars(os.path.expanduser(app["target"].strip()))
    args = [str(a) for a in app.get("args", [])]

    if "://" in target and not os.path.exists(target):
        _open_with_system(target)
        return

    if os.path.exists(target):
        cwd = target if os.path.isdir(target) else os.path.dirname(target)
        low = target.lower()
        if SYSTEM == "Windows":
            if args and low.endswith((".exe", ".bat", ".cmd")):
                _popen([target, *args], cwd=cwd)
            else:
                os.startfile(target)
        elif SYSTEM == "Darwin":
            if low.endswith(".app") or os.path.isdir(target) or not os.access(target, os.X_OK):
                _popen(["open", target] + (["--args", *args] if args else []))
            else:
                _popen([target, *args], cwd=cwd)
        else:
            if low.endswith(".desktop"):
                _popen(["gio", "launch", target, *args])
            elif os.path.isfile(target) and os.access(target, os.X_OK):
                _popen([target, *args], cwd=cwd)
            else:
                _open_with_system(target)
        return

    # 경로가 아니면 명령어로 취급 (PATH 에서 찾음)
    cmd = [target, *args] if args else shlex.split(target, posix=SYSTEM != "Windows")
    try:
        _popen(cmd)
    except FileNotFoundError:
        if SYSTEM == "Windows":
            os.startfile(target)  # App Paths 에 등록된 프로그램 (예: chrome.exe)
        else:
            raise


# ---------------------------------------------------------------- 게임패드 (선택)
class Gamepad:
    """pygame 이 설치되어 있으면 게임패드 입력을 폴링한다. 없으면 아무것도 안 함."""

    DEADZONE = 0.55
    REPEAT_DELAY = 0.35
    REPEAT_RATE = 0.11

    def __init__(self, root, on_move, on_activate, on_menu, is_active):
        self.root = root
        self.on_move, self.on_activate, self.on_menu = on_move, on_activate, on_menu
        self.is_active = is_active
        self.sticks = {}
        self.prev_buttons = set()
        self.cur_dir = None
        self.next_repeat = 0.0
        self.pg = None
        try:
            os.environ.setdefault("SDL_JOYSTICK_ALLOW_BACKGROUND_EVENTS", "1")
            os.environ.setdefault("PYGAME_HIDE_SUPPORT_PROMPT", "1")
            import pygame
            pygame.joystick.init()
            try:
                pygame.event.pump()
            except pygame.error:
                if SYSTEM == "Darwin":
                    raise
                pygame.display.init()  # 창은 만들지 않음, 이벤트 큐만 사용
                pygame.event.pump()
            self.pg = pygame
            for i in range(pygame.joystick.get_count()):
                self._add(i)
            self.root.after(40, self.poll)
        except Exception:
            self.pg = None

    @property
    def available(self):
        return self.pg is not None

    def _add(self, index):
        try:
            js = self.pg.joystick.Joystick(index)
            js.init()
            self.sticks[js.get_instance_id()] = js
        except Exception:
            pass

    def _direction(self):
        for js in self.sticks.values():
            try:
                for h in range(js.get_numhats()):
                    hx, hy = js.get_hat(h)
                    if hx or hy:
                        return (hx, 0) if hx else (0, -hy)
                if js.get_numaxes() >= 2:
                    ax, ay = js.get_axis(0), js.get_axis(1)
                    if abs(ax) > self.DEADZONE or abs(ay) > self.DEADZONE:
                        return (1 if ax > 0 else -1, 0) if abs(ax) >= abs(ay) else (0, 1 if ay > 0 else -1)
            except Exception:
                continue
        return None

    def poll(self):
        pg = self.pg
        try:
            for e in pg.event.get():
                if e.type == pg.JOYDEVICEADDED:
                    self._add(e.device_index)
                elif e.type == pg.JOYDEVICEREMOVED:
                    self.sticks.pop(e.instance_id, None)

            pressed = set()
            for js in self.sticks.values():
                for b in range(min(js.get_numbuttons(), 8)):
                    if js.get_button(b):
                        pressed.add(b)
            new = pressed - self.prev_buttons
            self.prev_buttons = pressed

            d = self._direction()
            now = time.monotonic()
            active = self.is_active()
            if active:
                if 0 in new:        # A
                    self.on_activate()
                elif 3 in new:      # Y
                    self.on_menu()
                if d is not None:
                    if d != self.cur_dir:
                        self.on_move(*d)
                        self.next_repeat = now + self.REPEAT_DELAY
                    elif now >= self.next_repeat:
                        self.on_move(*d)
                        self.next_repeat = now + self.REPEAT_RATE
            self.cur_dir = d
        except Exception:
            pass
        self.root.after(30, self.poll)


# ---------------------------------------------------------------- 런처 UI
def pick_font_family(root):
    families = set(tkfont.families(root))
    for name in ("Malgun Gothic", "맑은 고딕", "Apple SD Gothic Neo", "AppleGothic",
                 "Noto Sans CJK KR", "Noto Sans KR", "NanumGothic", "나눔고딕",
                 "WenQuanYi Zen Hei", "Segoe UI", "Helvetica"):
        if name in families:
            return name
    return "TkDefaultFont"


def round_rect(canvas, x1, y1, x2, y2, r=12, **kw):
    pts = [x1 + r, y1, x2 - r, y1, x2, y1, x2, y1 + r, x2, y2 - r, x2, y2,
           x2 - r, y2, x1 + r, y2, x1, y2, x1, y2 - r, x1, y1 + r, x1, y1]
    return canvas.create_polygon(pts, smooth=True, **kw)


def shade(hex_color, factor):
    hex_color = hex_color.lstrip("#")
    r, g, b = (int(hex_color[i:i + 2], 16) for i in (0, 2, 4))
    if factor >= 1:
        r, g, b = (int(c + (255 - c) * (factor - 1)) for c in (r, g, b))
    else:
        r, g, b = (int(c * factor) for c in (r, g, b))
    return "#%02x%02x%02x" % (max(0, min(255, r)), max(0, min(255, g)), max(0, min(255, b)))


class DeckLauncher:
    def __init__(self, root):
        self.root = root
        self.data = load_config()
        self.apps = self.data["apps"]
        self.settings = self.data["settings"]
        self.sel = 0
        self.img_cache = {}
        self.toast_job = None
        self.last_launch = 0.0
        self.last_mouse = None

        fam = pick_font_family(root)
        self.f_title = (fam, 20, "bold")
        self.f_clock = (fam, 16)
        self.f_section = (fam, 13, "bold")
        self.f_name = (fam, 12, "bold")
        self.f_letter = (fam, 64, "bold")
        self.f_hint = (fam, 10)

        root.title("Deck Launcher")
        root.configure(bg=BG)
        root.geometry("1280x800")
        root.minsize(560, 480)

        self.header = tk.Canvas(root, bg=BG_BAR, height=HEADER_H, highlightthickness=0)
        self.header.pack(fill="x")
        self.footer = tk.Canvas(root, bg=BG_BAR, height=FOOTER_H, highlightthickness=0)
        self.footer.pack(fill="x", side="bottom")
        self.body = tk.Canvas(root, bg=BG, highlightthickness=0, takefocus=1)
        self.body.pack(fill="both", expand=True)

        self.header.bind("<Configure>", lambda e: self.draw_header())
        self.footer.bind("<Configure>", lambda e: self.draw_footer())
        self.body.bind("<Configure>", lambda e: self.redraw(scroll=True))
        self.body.bind("<Motion>", self.on_motion)
        self.body.bind("<Button-1>", self.on_click)
        for seq in (("<Button-2>", "<Button-3>", "<Control-Button-1>") if SYSTEM == "Darwin"
                    else ("<Button-3>",)):
            self.body.bind(seq, self.on_right_click)
        self.body.bind("<MouseWheel>", self.on_wheel)
        self.body.bind("<Button-4>", lambda e: self.scroll_by(-1))
        self.body.bind("<Button-5>", lambda e: self.scroll_by(1))

        for key, d in (("<Left>", (-1, 0)), ("<Right>", (1, 0)), ("<Up>", (0, -1)), ("<Down>", (0, 1))):
            root.bind(key, lambda e, d=d: self.move(*d))
        root.bind("<Return>", lambda e: self.activate())
        root.bind("<KP_Enter>", lambda e: self.activate())
        root.bind("<space>", lambda e: self.activate())
        root.bind("<Home>", lambda e: self.select(0))
        root.bind("<End>", lambda e: self.select(len(self.apps)))
        root.bind("<F2>", lambda e: self.open_menu())
        root.bind("<Delete>", lambda e: self.delete_app(self.sel))
        root.bind("<F11>", lambda e: self.toggle_fullscreen())
        root.bind("<Escape>", lambda e: self.on_escape())
        root.protocol("WM_DELETE_WINDOW", self.quit)

        if self.settings.get("fullscreen"):
            self.set_fullscreen(True)

        self.gamepad = Gamepad(root, self.move, self.activate, self.open_menu, self.is_active)
        self.draw_header()
        self.tick_clock()
        self.body.focus_set()

    # ------------------------------------------------------------ 상태 헬퍼
    @property
    def count(self):
        return len(self.apps) + 1  # 마지막은 "앱 추가" 타일

    def is_active(self):
        try:
            return self.root.state() != "iconic" and self.root.focus_get() is not None
        except Exception:
            return False

    def color_of(self, i):
        app = self.apps[i]
        return app.get("color") or TILE_PALETTE[i % len(TILE_PALETTE)]

    def layout(self):
        w = max(self.body.winfo_width(), TILE_W + 2 * MARGIN_X)
        cols = max(1, (w - 2 * MARGIN_X + GAP) // (TILE_W + GAP))
        total = cols * TILE_W + (cols - 1) * GAP
        return cols, (w - total) // 2

    def tile_pos(self, i, cols, x0):
        r, c = divmod(i, cols)
        return x0 + c * (TILE_W + GAP), PAD_TOP + 40 + r * (TILE_H + GAP)

    def hit_test(self, ex, ey):
        x, y = self.body.canvasx(ex), self.body.canvasy(ey)
        cols, x0 = self.layout()
        for i in range(self.count):
            tx, ty = self.tile_pos(i, cols, x0)
            if tx <= x <= tx + TILE_W and ty <= y <= ty + TILE_H:
                return i
        return None

    # ------------------------------------------------------------ 그리기
    def draw_header(self):
        h = self.header
        h.delete("all")
        w = h.winfo_width()
        h.create_text(MARGIN_X, HEADER_H // 2, text="DECK", anchor="w", fill=ACCENT, font=self.f_title)
        h.create_text(MARGIN_X + 82, HEADER_H // 2, text="LAUNCHER", anchor="w", fill=TEXT, font=self.f_title)
        self.clock_id = h.create_text(w - MARGIN_X, HEADER_H // 2, anchor="e", fill=TEXT,
                                      font=self.f_clock, text=time.strftime("%H:%M"))
        if self.gamepad_ok():
            h.create_text(w - MARGIN_X - 90, HEADER_H // 2, anchor="e", fill=TEXT_DIM,
                          font=self.f_hint, text=f"🎮 {len(self.gamepad.sticks)}")

    def gamepad_ok(self):
        return getattr(self, "gamepad", None) is not None and self.gamepad.available

    def draw_footer(self, message=None):
        f = self.footer
        f.delete("all")
        w = f.winfo_width()
        hints = [("Enter / 클릭", "실행"), ("방향키", "이동"), ("F2 / 우클릭", "편집"),
                 ("F11", "전체화면"), ("Esc", "나가기")]
        x = w - MARGIN_X
        for key, label in reversed(hints):
            t = f.create_text(x, FOOTER_H // 2, anchor="e", text=label, fill=TEXT_DIM, font=self.f_hint)
            x = f.bbox(t)[0] - 14
            k = f.create_text(x, FOOTER_H // 2, anchor="e", text=key, fill=TEXT, font=self.f_hint)
            bx1, by1, bx2, by2 = f.bbox(k)
            r = round_rect(f, bx1 - 6, by1 - 3, bx2 + 6, by2 + 3, r=6, fill="#2a313b", outline="")
            f.tag_lower(r, k)
            x = bx1 - 26
        if message:
            f.create_text(MARGIN_X, FOOTER_H // 2, anchor="w", text=message, fill=ACCENT, font=self.f_section)

    def toast(self, message, ms=2500):
        self.draw_footer(message)
        if self.toast_job:
            self.root.after_cancel(self.toast_job)
        self.toast_job = self.root.after(ms, self.draw_footer)

    def load_icon(self, path, box_w, box_h):
        path = os.path.expandvars(os.path.expanduser(path))
        if not os.path.isabs(path):
            path = os.path.join(APP_DIR, path)
        key = (path, box_w, box_h)
        if key in self.img_cache:
            return self.img_cache[key]
        img = None
        try:
            if Image is not None:
                im = Image.open(path).convert("RGBA")
                scale = min(box_w / im.width, box_h / im.height)
                im = im.resize((max(1, int(im.width * scale)), max(1, int(im.height * scale))), Image.LANCZOS)
                img = ImageTk.PhotoImage(im)
            else:
                ph = tk.PhotoImage(file=path)
                factor = max(1, -(-max(ph.width() // box_w, ph.height() // box_h, 1)))
                while ph.width() // factor > box_w or ph.height() // factor > box_h:
                    factor += 1
                img = ph.subsample(factor) if factor > 1 else ph
        except Exception:
            img = None
        self.img_cache[key] = img
        return img

    def redraw(self, scroll=False):
        c = self.body
        c.delete("all")
        cols, x0 = self.layout()
        c.create_text(x0, PAD_TOP + 14, anchor="w", fill=TEXT, font=self.f_section,
                      text=f"라이브러리  ·  {len(self.apps)}개")

        for i in range(self.count):
            x, y = self.tile_pos(i, cols, x0)
            selected = i == self.sel
            if selected:
                round_rect(c, x - 6, y - 6, x + TILE_W + 6, y + TILE_H + 6, r=16, fill="", outline=ACCENT, width=3)
            if i == len(self.apps):
                self.draw_add_tile(x, y, selected)
            else:
                self.draw_app_tile(i, x, y, selected)

        rows = -(-self.count // cols)
        height = PAD_TOP + 40 + rows * (TILE_H + GAP) + PAD_TOP
        c.configure(scrollregion=(0, 0, c.winfo_width(), height))
        if scroll:
            self.ensure_visible()

    def draw_app_tile(self, i, x, y, selected):
        c = self.body
        app = self.apps[i]
        base = self.color_of(i)
        fill = shade(base, 1.25) if selected else base
        round_rect(c, x, y, x + TILE_W, y + TILE_H, r=12, fill=shade(base, 0.55), outline="")
        round_rect(c, x, y, x + TILE_W, y + ART_H, r=12, fill=fill, outline="")
        c.create_rectangle(x, y + ART_H - 14, x + TILE_W, y + ART_H, fill=fill, outline="")

        img = self.load_icon(app["icon"], TILE_W - 40, ART_H - 40) if app.get("icon") else None
        if img is not None:
            c.create_image(x + TILE_W // 2, y + ART_H // 2, image=img)
        else:
            letter = (app.get("name") or "?").strip()[:1].upper() or "?"
            c.create_text(x + TILE_W // 2 + 3, y + ART_H // 2 + 4, text=letter, fill=shade(base, 0.45), font=self.f_letter)
            c.create_text(x + TILE_W // 2, y + ART_H // 2, text=letter, fill="#ffffff", font=self.f_letter)

        c.create_text(x + 14, y + ART_H + (TILE_H - ART_H) // 2, anchor="w", width=TILE_W - 28,
                      text=self.ellipsize(app.get("name", "이름 없음")), fill="#ffffff" if selected else TEXT,
                      font=self.f_name)
        if selected:
            c.create_text(x + TILE_W - 14, y + 16, anchor="ne", text="▶ 실행", fill="#ffffff", font=self.f_hint)

    def draw_add_tile(self, x, y, selected):
        c = self.body
        col = ACCENT if selected else "#3a4250"
        round_rect(c, x, y, x + TILE_W, y + TILE_H, r=12, fill="#141b23" if not selected else "#18222e",
                   outline=col, width=2, dash=(6, 4))
        c.create_text(x + TILE_W // 2, y + ART_H // 2, text="+", fill=col, font=self.f_letter)
        c.create_text(x + TILE_W // 2, y + ART_H + (TILE_H - ART_H) // 2, text="앱 추가",
                      fill=TEXT if selected else TEXT_DIM, font=self.f_name)

    def ellipsize(self, text, max_chars=18):
        return text if len(text) <= max_chars else text[:max_chars - 1] + "…"

    def tick_clock(self):
        try:
            self.header.itemconfigure(self.clock_id, text=time.strftime("%H:%M"))
        except Exception:
            pass
        self.root.after(5000, self.tick_clock)

    # ------------------------------------------------------------ 스크롤
    def ensure_visible(self):
        c = self.body
        cols, x0 = self.layout()
        _, y = self.tile_pos(self.sel, cols, x0)
        sr = c.cget("scrollregion").split()
        total = float(sr[3]) if len(sr) == 4 else 1
        view_h = c.winfo_height()
        if total <= view_h:
            c.yview_moveto(0)
            return
        top = c.canvasy(0)
        if y - 20 < top:
            c.yview_moveto(max(0, (y - 20 - (40 if self.sel < cols else 0)) / total))
        elif y + TILE_H + 20 > top + view_h:
            c.yview_moveto((y + TILE_H + 20 - view_h) / total)

    def scroll_by(self, units):
        self.body.yview_scroll(units * 2, "units")

    def on_wheel(self, e):
        if SYSTEM == "Darwin":
            self.body.yview_scroll(-e.delta, "units")
        else:
            self.body.yview_scroll(int(-e.delta / 40) or (-1 if e.delta > 0 else 1), "units")

    # ------------------------------------------------------------ 입력 처리
    def select(self, i):
        i = max(0, min(self.count - 1, i))
        if i != self.sel:
            self.sel = i
            self.redraw(scroll=True)

    def move(self, dx, dy):
        cols, _ = self.layout()
        if dx:
            self.select(self.sel + dx)
        elif dy:
            target = self.sel + dy * cols
            if dy > 0 and target >= self.count:
                # 아래 줄이 짧으면 마지막 타일로
                if self.sel // cols < (self.count - 1) // cols:
                    target = self.count - 1
                else:
                    return
            if target >= 0:
                self.select(target)

    def on_motion(self, e):
        if self.last_mouse == (e.x_root, e.y_root):
            return
        self.last_mouse = (e.x_root, e.y_root)
        i = self.hit_test(e.x, e.y)
        if i is not None:
            self.select(i)
        self.body.configure(cursor="hand2" if i is not None else "")

    def on_click(self, e):
        self.body.focus_set()
        i = self.hit_test(e.x, e.y)
        if i is not None:
            self.sel = i
            self.redraw()
            self.activate()

    def on_right_click(self, e):
        i = self.hit_test(e.x, e.y)
        if i is not None:
            self.sel = i
            self.redraw()
            self.open_menu(e.x_root, e.y_root)

    def activate(self):
        if self.sel >= len(self.apps):
            self.add_menu()
            return
        now = time.monotonic()
        if now - self.last_launch < 0.8:  # 더블클릭 등으로 두 번 실행되는 것 방지
            return
        self.last_launch = now
        app = self.apps[self.sel]
        try:
            launch_app(app)
        except Exception as ex:
            messagebox.showerror("실행 실패", f"'{app.get('name')}' 을(를) 실행하지 못했습니다.\n\n"
                                            f"대상: {app.get('target')}\n오류: {ex}")
            return
        app["launch_count"] = int(app.get("launch_count", 0)) + 1
        app["last_launched"] = time.strftime("%Y-%m-%d %H:%M:%S")
        save_config(self.data)
        self.toast(f"▶  {app.get('name')} 실행 중…")
        if self.settings.get("minimize_on_launch", True):
            self.root.after(350, self.minimize)

    def minimize(self):
        try:
            if self.root.attributes("-fullscreen"):
                self.set_fullscreen(False)
                self._restore_fullscreen = True
                self.root.bind("<Map>", self._on_map, add="+")
            self.root.iconify()
        except Exception:
            pass

    def _on_map(self, _e=None):
        if getattr(self, "_restore_fullscreen", False):
            self._restore_fullscreen = False
            self.root.after(50, lambda: self.set_fullscreen(True))

    def set_fullscreen(self, on):
        try:
            self.root.attributes("-fullscreen", bool(on))
        except tk.TclError:
            pass

    def toggle_fullscreen(self):
        on = not bool(self.root.attributes("-fullscreen"))
        self.set_fullscreen(on)
        self.settings["fullscreen"] = on
        save_config(self.data)

    def on_escape(self):
        if self.root.attributes("-fullscreen"):
            self.toggle_fullscreen()
        else:
            self.quit()

    def quit(self):
        save_config(self.data)
        self.root.destroy()

    # ------------------------------------------------------------ 편집 메뉴
    def popup(self, menu, x=None, y=None):
        if x is None:
            cols, x0 = self.layout()
            tx, ty = self.tile_pos(self.sel, cols, x0)
            x = self.body.winfo_rootx() + tx + TILE_W // 2
            y = self.body.winfo_rooty() + ty - int(self.body.canvasy(0)) + ART_H // 2
        try:
            menu.tk_popup(x, y)
        finally:
            menu.grab_release()

    def open_menu(self, x=None, y=None):
        i = self.sel
        if i >= len(self.apps):
            self.add_menu(x, y)
            return
        m = tk.Menu(self.root, tearoff=0)
        m.add_command(label="▶  실행", command=self.activate)
        m.add_separator()
        m.add_command(label="이름 변경", command=lambda: self.rename_app(i))
        m.add_command(label="실행 대상 변경", command=lambda: self.change_target(i))
        m.add_command(label="아이콘 이미지 선택", command=lambda: self.change_icon(i))
        if self.apps[i].get("icon"):
            m.add_command(label="아이콘 제거", command=lambda: self.set_field(i, "icon", None))
        m.add_command(label="타일 색상 변경", command=lambda: self.change_color(i))
        m.add_separator()
        m.add_command(label="◀  앞으로 이동", command=lambda: self.reorder(i, -1),
                      state="normal" if i > 0 else "disabled")
        m.add_command(label="▶  뒤로 이동", command=lambda: self.reorder(i, 1),
                      state="normal" if i < len(self.apps) - 1 else "disabled")
        m.add_separator()
        m.add_command(label="삭제", command=lambda: self.delete_app(i))
        m.add_separator()
        m.add_checkbutton(label="실행 후 런처 최소화", command=self.toggle_minimize,
                          variable=tk.BooleanVar(m, self.settings.get("minimize_on_launch", True)))
        self.popup(m, x, y)

    def add_menu(self, x=None, y=None):
        m = tk.Menu(self.root, tearoff=0)
        m.add_command(label="프로그램 / 바로가기 파일 선택…", command=self.add_from_file)
        m.add_command(label="명령어 또는 URL 직접 입력…", command=self.add_from_text)
        self.popup(m, x, y)

    def toggle_minimize(self):
        self.settings["minimize_on_launch"] = not self.settings.get("minimize_on_launch", True)
        save_config(self.data)

    def add_from_file(self):
        if SYSTEM == "Windows":
            types = [("프로그램", "*.exe *.lnk *.bat *.cmd *.url"), ("모든 파일", "*.*")]
            initial = os.environ.get("ProgramFiles", "C:\\")
        elif SYSTEM == "Darwin":
            types = [("모든 파일", "*")]
            initial = "/Applications"
        else:
            types = [("모든 파일", "*"), ("데스크톱 항목", "*.desktop")]
            initial = "/usr/share/applications" if os.path.isdir("/usr/share/applications") else os.path.expanduser("~")
        path = filedialog.askopenfilename(parent=self.root, title="실행할 프로그램 선택",
                                          initialdir=initial, filetypes=types)
        if not path:
            return
        guess = os.path.splitext(os.path.basename(path.rstrip("/")))[0]
        name = simpledialog.askstring("앱 이름", "타일에 표시할 이름:", initialvalue=guess, parent=self.root)
        if name is None:
            return
        self.add_app({"name": name.strip() or guess, "target": path})

    def add_from_text(self):
        target = simpledialog.askstring(
            "명령어 / URL", "실행할 명령어, 경로 또는 URL\n(예: notepad.exe, steam://rungameid/570, https://youtube.com)",
            parent=self.root)
        if not target or not target.strip():
            return
        name = simpledialog.askstring("앱 이름", "타일에 표시할 이름:", parent=self.root)
        if name is None:
            return
        self.add_app({"name": name.strip() or target.strip(), "target": target.strip()})

    def add_app(self, app):
        self.apps.append(app)
        save_config(self.data)
        self.sel = len(self.apps) - 1
        self.redraw(scroll=True)
        self.toast(f"'{app['name']}' 추가됨")

    def set_field(self, i, key, value):
        if value is None:
            self.apps[i].pop(key, None)
        else:
            self.apps[i][key] = value
        save_config(self.data)
        self.redraw()

    def rename_app(self, i):
        name = simpledialog.askstring("이름 변경", "새 이름:", initialvalue=self.apps[i].get("name", ""),
                                      parent=self.root)
        if name and name.strip():
            self.set_field(i, "name", name.strip())

    def change_target(self, i):
        t = simpledialog.askstring("실행 대상", "경로 / 명령어 / URL:", initialvalue=self.apps[i].get("target", ""),
                                   parent=self.root)
        if t and t.strip():
            self.set_field(i, "target", t.strip())

    def change_icon(self, i):
        types = [("이미지", "*.png *.gif *.jpg *.jpeg *.webp *.bmp *.ico"), ("모든 파일", "*.*")] if Image \
            else [("이미지 (PNG/GIF)", "*.png *.gif"), ("모든 파일", "*.*")]
        path = filedialog.askopenfilename(parent=self.root, title="아이콘 이미지 선택", filetypes=types)
        if path:
            self.set_field(i, "icon", path)

    def change_color(self, i):
        _, hex_color = colorchooser.askcolor(color=self.color_of(i), parent=self.root, title="타일 색상")
        if hex_color:
            self.set_field(i, "color", hex_color)

    def reorder(self, i, d):
        j = i + d
        if 0 <= j < len(self.apps):
            self.apps[i], self.apps[j] = self.apps[j], self.apps[i]
            self.sel = j
            save_config(self.data)
            self.redraw(scroll=True)

    def delete_app(self, i):
        if i >= len(self.apps):
            return
        name = self.apps[i].get("name")
        if messagebox.askyesno("삭제", f"'{name}' 을(를) 목록에서 삭제할까요?\n(프로그램 자체는 지워지지 않습니다)",
                               parent=self.root):
            del self.apps[i]
            self.sel = min(self.sel, self.count - 1)
            save_config(self.data)
            self.redraw(scroll=True)


def main():
    if SYSTEM == "Windows":
        try:  # 고해상도 화면에서 흐릿하지 않게
            import ctypes
            ctypes.windll.shcore.SetProcessDpiAwareness(1)
        except Exception:
            pass
    root = tk.Tk()
    DeckLauncher(root)
    root.mainloop()


if __name__ == "__main__":
    main()
