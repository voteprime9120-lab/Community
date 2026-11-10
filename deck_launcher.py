#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Deck Launcher - 스팀덱 스타일 앱 런처

타일(앱)을 클릭하면 그 앱이 바로 실행되고, 런처는 뒤로 물러납니다.

  * 마우스 클릭 / Enter / 게임패드 A 버튼  -> 바로 실행
  * 방향키 / 게임패드 D-Pad·스틱          -> 이동
  * 우클릭 / F2 / 게임패드 Y              -> 편집 메뉴 (즐겨찾기, 카테고리, 아이콘, 순서, 삭제)
  * Tab / 게임패드 LB·RB                 -> 목록 전환 (전체 / 즐겨찾기 / 최근 / 카테고리)
  * Ctrl+N / 게임패드 X                  -> 앱 추가
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
# 밝은 회색 배경 위에 둥근 반투명 패널이 떠 있는 느낌의 라이트 테마
BG = "#d6d9df"          # 창 배경
SHADOW = "#c9ccd3"      # 패널 그림자
PANEL = "#eceef2"       # 메인/메뉴 패널
RAIL = "#f2f3f6"        # 왼쪽 아이콘 레일
CARD = "#f7f8fa"        # 앱 카드
CARD_LINE = "#e0e3e8"
INK = "#17181c"         # 선택 항목 (검정 알약)
TEXT = "#2b2e35"
DIM = "#80858f"
LINE = "#d9dce2"
WHITE = "#ffffff"
HOVER = "#e3e5ea"
PINK = "#e48ad9"        # 즐겨찾기 점

# (아이콘 상자 배경, 글자색) 파스텔 팔레트
PASTELS = [
    ("#dde6fb", "#3f5fa8"), ("#fbe0e3", "#a8475a"), ("#e0f0d2", "#4e7a2c"),
    ("#fbefc8", "#94701c"), ("#e6def7", "#6a4fa8"), ("#d4efec", "#2f7d75"),
    ("#f7e1d0", "#9a5a2c"), ("#e3e6ea", "#4b5260"),
]

M = 18              # 바깥 여백
RAIL_W = 72
SIDE_W = 268
PANEL_GAP = 14
FOOTER_H = 46
TILE_W, TILE_H = 172, 204
GAP = 16
BODY_PAD = 10
WEEKDAYS = ["월", "화", "수", "목", "금", "토", "일"]

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

    def __init__(self, root, on_move, buttons, is_active):
        """buttons: {버튼 번호: 콜백}  (Xbox 배치 기준 0=A, 1=B, 2=X, 3=Y, 4=LB, 5=RB)"""
        self.root = root
        self.on_move, self.buttons = on_move, buttons
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
                for b in sorted(new):
                    if b in self.buttons:
                        self.buttons[b]()
                        break
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



# ---------------------------------------------------------------- 그리기 도우미
def pick_font_family(root):
    families = set(tkfont.families(root))
    for name in ("Pretendard", "Malgun Gothic", "맑은 고딕", "Apple SD Gothic Neo", "AppleGothic",
                 "Noto Sans CJK KR", "Noto Sans KR", "NanumGothic", "나눔고딕",
                 "WenQuanYi Zen Hei", "Segoe UI", "Helvetica"):
        if name in families:
            return name
    return "TkDefaultFont"


def round_rect(canvas, x1, y1, x2, y2, r=12, **kw):
    r = max(0, min(r, (x2 - x1) / 2, (y2 - y1) / 2))
    pts = [x1 + r, y1, x2 - r, y1, x2, y1, x2, y1 + r, x2, y2 - r, x2, y2,
           x2 - r, y2, x1 + r, y2, x1, y2, x1, y2 - r, x1, y1 + r, x1, y1]
    return canvas.create_polygon(pts, smooth=True, **kw)


def draw_icon(c, kind, cx, cy, color, s=1.0, tags=()):
    """외부 폰트 없이 캔버스 선으로 그리는 라인 아이콘 (18px 기준)."""
    w = max(1, round(1.6 * s))
    kw = dict(fill=color, width=w, tags=tags, capstyle="round", joinstyle="round")

    def P(dx, dy):
        return cx + dx * s, cy + dy * s

    if kind == "logo":  # 4각 반짝임
        pts = [P(0, -10), P(2.2, -2.2), P(10, 0), P(2.2, 2.2), P(0, 10), P(-2.2, 2.2), P(-10, 0), P(-2.2, -2.2)]
        c.create_polygon([v for p in pts for v in p], fill=color, outline="", smooth=False, tags=tags)
    elif kind == "home":
        pts = [P(0, -8), P(8, -2), P(6, 8), P(-6, 8), P(-8, -2), P(0, -8)]
        c.create_line([v for p in pts for v in p], **kw)
        c.create_line(*P(-2.5, 3.5), *P(2.5, 3.5), **kw)
    elif kind == "grid":
        for dx, dy in ((-4.5, -4.5), (4.5, -4.5), (-4.5, 4.5), (4.5, 4.5)):
            x, y = P(dx, dy)
            c.create_rectangle(x - 3.2 * s, y - 3.2 * s, x + 3.2 * s, y + 3.2 * s, outline=color, width=w, tags=tags)
    elif kind == "star":
        import math
        pts = []
        for k in range(10):
            r = 9 if k % 2 == 0 else 4
            a = -math.pi / 2 + k * math.pi / 5
            pts.append(P(r * math.cos(a), r * math.sin(a)))
        pts.append(pts[0])
        c.create_line([v for p in pts for v in p], **kw)
    elif kind == "clock":
        x1, y1 = P(-8, -8)
        x2, y2 = P(8, 8)
        c.create_oval(x1, y1, x2, y2, outline=color, width=w, tags=tags)
        c.create_line(*P(0, -4.5), *P(0, 0), *P(3.5, 2), **kw)
    elif kind == "folder":
        pts = [P(-8, -6), P(-2.5, -6), P(-0.5, -3.5), P(8, -3.5), P(8, 7), P(-8, 7), P(-8, -6)]
        c.create_line([v for p in pts for v in p], **kw)
        c.create_line(*P(-8, -0.5), *P(8, -0.5), **kw)
    elif kind == "plus":
        c.create_line(*P(-6, 0), *P(6, 0), **kw)
        c.create_line(*P(0, -6), *P(0, 6), **kw)
    elif kind == "sliders":
        for y, kx in ((-4.5, 3), (4.5, -3)):
            c.create_line(*P(-8, y), *P(8, y), **kw)
            x, yy = P(kx, y)
            c.create_oval(x - 2.6 * s, yy - 2.6 * s, x + 2.6 * s, yy + 2.6 * s, fill=RAIL, outline=color, width=w, tags=tags)
    elif kind == "expand":
        for sx, sy in ((-1, -1), (1, -1), (-1, 1), (1, 1)):
            c.create_line(*P(8 * sx, 3 * sy), *P(8 * sx, 8 * sy), *P(3 * sx, 8 * sy), **kw)
    elif kind == "power":
        x1, y1 = P(-8, -7)
        x2, y2 = P(8, 9)
        c.create_arc(x1, y1, x2, y2, start=120, extent=300, style="arc", outline=color, width=w, tags=tags)
        c.create_line(*P(0, -9), *P(0, -1), **kw)


def app_kind(app):
    t = app.get("target", "").lower()
    if t.startswith("steam://"):
        return "Steam"
    if t.startswith(("http://", "https://")):
        return "웹 링크"
    if t.endswith((".exe", ".app", ".lnk", ".desktop", ".bat", ".cmd")):
        return "프로그램"
    if "/" in t or "\\" in t or t.startswith("~"):
        return "파일 / 폴더"
    return "명령어"


# ---------------------------------------------------------------- 런처 UI
class DeckLauncher:
    def __init__(self, root):
        self.root = root
        self.data = load_config()
        self.apps = self.data["apps"]
        self.settings = self.data["settings"]
        self.view = "all"
        self.sel = 0
        self.img_cache = {}
        self.hot = []            # (x1, y1, x2, y2, key) 클릭 가능한 영역
        self.hover = None
        self.toast_msg = None
        self.toast_job = None
        self.last_launch = 0.0
        self.last_mouse = None
        self.geo = {}

        fam = pick_font_family(root)
        self.f_brand = (fam, 16, "bold")
        self.f_title = (fam, 22, "bold")
        self.f_item = (fam, 12)
        self.f_item_b = (fam, 12, "bold")
        self.f_small = (fam, 10)
        self.f_small_b = (fam, 10, "bold")
        self.f_name = (fam, 12, "bold")
        self.f_letter = (fam, 30, "bold")
        self.f_time = (fam, 20, "bold")

        root.title("Deck Launcher")
        root.configure(bg=BG)
        root.geometry("1280x800")
        root.minsize(640, 520)

        self.cv = tk.Canvas(root, bg=BG, highlightthickness=0)
        self.cv.pack(fill="both", expand=True)
        self.body = tk.Canvas(self.cv, bg=PANEL, highlightthickness=0, takefocus=1)

        self.cv.bind("<Configure>", lambda e: self.redraw_all())
        self.cv.bind("<Motion>", self.on_chrome_motion)
        self.cv.bind("<Leave>", lambda e: self.set_hover(None))
        self.cv.bind("<Button-1>", self.on_chrome_click)
        self.body.bind("<Configure>", lambda e: self.redraw_body(scroll=True))
        self.body.bind("<Motion>", self.on_motion)
        self.body.bind("<Button-1>", self.on_click)
        for seq in (("<Button-2>", "<Button-3>", "<Control-Button-1>") if SYSTEM == "Darwin"
                    else ("<Button-3>",)):
            self.body.bind(seq, self.on_right_click)
        self.body.bind("<MouseWheel>", self.on_wheel)
        self.body.bind("<Button-4>", lambda e: self.body.yview_scroll(-2, "units"))
        self.body.bind("<Button-5>", lambda e: self.body.yview_scroll(2, "units"))

        for key, d in (("<Left>", (-1, 0)), ("<Right>", (1, 0)), ("<Up>", (0, -1)), ("<Down>", (0, 1))):
            root.bind(key, lambda e, d=d: self.move(*d))
        root.bind("<Return>", lambda e: self.activate())
        root.bind("<KP_Enter>", lambda e: self.activate())
        root.bind("<space>", lambda e: self.activate())
        root.bind("<Home>", lambda e: self.select(0))
        root.bind("<End>", lambda e: self.select(len(self.visible()) - 1))
        root.bind("<Tab>", lambda e: (self.cycle_view(1), "break")[1])
        root.bind("<Shift-Tab>", lambda e: (self.cycle_view(-1), "break")[1])
        root.bind("<ISO_Left_Tab>", lambda e: (self.cycle_view(-1), "break")[1])
        root.bind("<Control-n>", lambda e: self.add_menu())
        root.bind("<F2>", lambda e: self.open_menu())
        root.bind("<Delete>", lambda e: self.delete_app(self.cur_index()))
        root.bind("<F11>", lambda e: self.toggle_fullscreen())
        root.bind("<Escape>", lambda e: self.on_escape())
        root.protocol("WM_DELETE_WINDOW", self.quit)

        if self.settings.get("fullscreen"):
            self.set_fullscreen(True)

        self.gamepad = Gamepad(root, self.move, {
            0: self.activate,                 # A  실행
            2: self.add_menu,                 # X  앱 추가
            3: self.open_menu,                # Y  편집 메뉴
            4: lambda: self.cycle_view(-1),   # LB 이전 목록
            5: lambda: self.cycle_view(1),    # RB 다음 목록
        }, self.is_active)
        self.tick_clock()
        self.body.focus_set()

    # ------------------------------------------------------------ 데이터 / 목록
    def categories(self):
        seen = []
        for a in self.apps:
            c = (a.get("category") or "").strip()
            if c and c not in seen:
                seen.append(c)
        return seen

    def views(self):
        v = [("all", "전체 앱", "grid"), ("fav", "즐겨찾기", "star"), ("recent", "최근 실행", "clock")]
        return v + [("cat:" + c, c, "folder") for c in self.categories()]

    def view_title(self):
        for key, label, _ in self.views():
            if key == self.view:
                return label
        return "전체 앱"

    def visible(self, view=None):
        view = view or self.view
        idx = range(len(self.apps))
        if view == "fav":
            return [i for i in idx if self.apps[i].get("favorite")]
        if view == "recent":
            items = [i for i in idx if self.apps[i].get("last_launched")]
            return sorted(items, key=lambda i: self.apps[i]["last_launched"], reverse=True)
        if view.startswith("cat:"):
            name = view[4:]
            return [i for i in idx if (self.apps[i].get("category") or "").strip() == name]
        return list(idx)

    def cur_index(self):
        vis = self.visible()
        return vis[self.sel] if 0 <= self.sel < len(vis) else None

    def set_view(self, view):
        if view != self.view:
            self.view = view
            self.sel = 0
            self.body.yview_moveto(0)
            self.redraw_all()

    def cycle_view(self, d):
        keys = [k for k, _, _ in self.views()]
        i = keys.index(self.view) if self.view in keys else 0
        self.set_view(keys[(i + d) % len(keys)])

    def is_active(self):
        try:
            return self.root.state() != "iconic" and self.root.focus_get() is not None
        except Exception:
            return False

    def pastel(self, i):
        app = self.apps[i]
        if app.get("color"):
            return app["color"], WHITE
        return PASTELS[i % len(PASTELS)]

    # ------------------------------------------------------------ 바깥 틀 (레일, 메뉴, 헤더, 푸터)
    def panel(self, x1, y1, x2, y2, r, fill):
        c = self.cv
        round_rect(c, x1, y1 + 5, x2, y2 + 5, r=r, fill=SHADOW, outline="")
        round_rect(c, x1, y1, x2, y2, r=r, fill=fill, outline=WHITE, width=1)

    def redraw_all(self):
        c = self.cv
        c.delete("all")
        self.hot = []
        W, H = c.winfo_width(), c.winfo_height()
        if W < 10:
            return
        top, bottom = M, H - FOOTER_H
        show_side = W >= 900

        # --- 왼쪽 아이콘 레일
        rx1, rx2 = M, M + RAIL_W
        rcx = (rx1 + rx2) / 2
        self.panel(rx1, top, rx2, bottom, RAIL_W / 2, RAIL)
        draw_icon(c, "logo", rcx, top + 46, INK, 1.1)
        c.create_line(rx1 + 16, top + 84, rx2 - 16, top + 84, fill=LINE)
        y = top + 122
        for key, _label, icon in self.views()[:3]:
            self.rail_button(rcx, y, icon, "view:" + key, selected=self.view == key)
            y += 54
        if self.view.startswith("cat:") and not show_side:
            self.rail_button(rcx, y, "folder", "view:" + self.view, selected=True)
            y += 54
        line_top, line_bot = y - 8, bottom - 186
        if line_bot - line_top > 40:  # 장식용 세로선
            c.create_line(rcx, line_top, rcx, line_bot, fill="#b9bdc5")
            mid = (line_top + line_bot) / 2
            c.create_oval(rcx - 2, mid - 2, rcx + 2, mid + 2, fill="#9ca1aa", outline="")
        self.rail_button(rcx, bottom - 146, "sliders", "settings")
        self.rail_button(rcx, bottom - 92, "expand", "fullscreen")
        self.rail_button(rcx, bottom - 38, "power", "exit")

        # --- 메뉴 패널
        mx1 = rx2 + PANEL_GAP
        if show_side:
            sx1, sx2 = mx1, mx1 + SIDE_W
            self.draw_sidebar(sx1, top, sx2, bottom)
            mx1 = sx2 + PANEL_GAP
        mx2 = W - M

        # --- 메인 패널
        self.panel(mx1, top, mx2, bottom, 28, PANEL)
        hx = mx1 + 30
        t1 = c.create_text(hx, top + 34, anchor="w", text="라이브러리", fill=DIM, font=self.f_item)
        c.create_text(c.bbox(t1)[2] + 8, top + 34, anchor="w", text=self.view_title(), fill=TEXT, font=self.f_item_b)
        tt = c.create_text(hx, top + 76, anchor="w", text=self.view_title(), fill=INK, font=self.f_title)
        n = len(self.visible())
        bx = c.bbox(tt)[2] + 12
        nt = c.create_text(bx + 10, top + 78, anchor="w", text=str(n), fill=TEXT, font=self.f_small_b)
        x1, y1, x2, y2 = c.bbox(nt)
        r = round_rect(c, x1 - 8, y1 - 3, x2 + 8, y2 + 3, r=7, fill="#dfe2e7", outline="")
        c.tag_lower(r, nt)

        # 오른쪽 위: 날짜 (메뉴 패널이 없을 때는 시계 대신)
        c.create_text(mx2 - 30, top + 34, anchor="e", fill=DIM, font=self.f_item, tags="clock_text",
                      text=self.date_text() + ("" if show_side else "   " + time.strftime("%H:%M")))

        # 앱 추가 바 ("Add todo, press ENTER" 스타일)
        ax1, ay1, ax2, ay2 = mx1 + 22, top + 106, mx2 - 22, top + 150
        hov = self.hover == "add"
        round_rect(c, ax1, ay1, ax2, ay2, r=14, fill=WHITE if hov else "#f4f5f8", outline=CARD_LINE)
        draw_icon(c, "plus", ax1 + 24, (ay1 + ay2) / 2, TEXT, 0.9)
        t = c.create_text(ax1 + 44, (ay1 + ay2) / 2, anchor="w", text="앱 추가하기,", fill=TEXT, font=self.f_item)
        x = c.bbox(t)[2] + 8
        x = self.key_chip(x, (ay1 + ay2) / 2, "Ctrl + N", fill="#e3e6ea")
        c.create_text(x + 8, (ay1 + ay2) / 2, anchor="w", text="또는 클릭", fill=DIM, font=self.f_item)
        self.hot.append((ax1, ay1, ax2, ay2, "add"))

        # 앱 목록 영역 (스크롤되는 내부 캔버스)
        bx1, by1, bx2, by2 = mx1 + 14, top + 164, mx2 - 14, bottom - 14
        self.body.place(x=bx1, y=by1, width=max(1, bx2 - bx1), height=max(1, by2 - by1))
        self.geo = dict(top=top, bottom=bottom, show_side=show_side)

        self.draw_footer(W, H)
        self.redraw_body(scroll=True)

    def rail_button(self, cx, cy, icon, key, selected=False):
        c = self.cv
        if selected:
            c.create_oval(cx - 23, cy - 23 + 3, cx + 23, cy + 23 + 3, fill="#e2e4e9", outline="")
            c.create_oval(cx - 23, cy - 23, cx + 23, cy + 23, fill=WHITE, outline="")
        elif self.hover == key:
            c.create_oval(cx - 23, cy - 23, cx + 23, cy + 23, fill=HOVER, outline="")
        draw_icon(c, icon, cx, cy, INK)
        self.hot.append((cx - 24, cy - 24, cx + 24, cy + 24, key))

    def draw_sidebar(self, x1, top, x2, bottom):
        c = self.cv
        self.panel(x1, top, x2, bottom, 28, PANEL)
        draw_icon(c, "logo", x1 + 34, top + 46, INK, 1.1)
        c.create_text(x1 + 56, top + 46, anchor="w", text="Menu", fill=INK, font=self.f_brand)
        c.create_line(x1 + 22, top + 84, x2 - 22, top + 84, fill=LINE)

        y = top + 122
        views = self.views()
        for key, label, icon in views[:3]:
            count = len(self.visible(key))
            self.side_item(x1, x2, y, key, label, icon, count, dark_badge=(key == "all"))
            y += 48

        cats = views[3:]
        clock_h = 168
        room_for_clock = bottom - 16 - clock_h
        y += 4
        c.create_line(x1 + 22, y - 18, x2 - 22, y - 18, fill=LINE)
        c.create_text(x1 + 26, y + 6, anchor="w", text=f"카테고리  ({len(cats)})", fill=TEXT, font=self.f_item)
        draw_icon(c, "folder", x2 - 34, y + 6, TEXT, 0.85)
        y += 48
        if not cats:
            c.create_text(x1 + 26, y, anchor="w", width=x2 - x1 - 52, fill=DIM, font=self.f_small,
                          text="앱을 우클릭 → '카테고리 지정' 으로\n폴더처럼 묶을 수 있어요.")
            y += 34
        limit = bottom - 30 if len(cats) * 48 + y > room_for_clock else room_for_clock
        for key, label, icon in cats:
            if y + 20 > limit:
                break
            self.side_item(x1, x2, y, key, label, icon, len(self.visible(key)))
            y += 48

        if y + 10 <= room_for_clock:
            self.clock_card(x1 + 14, bottom - 14 - clock_h, x2 - 14, bottom - 14)

    def side_item(self, x1, x2, y, key, label, icon, count, dark_badge=False):
        c = self.cv
        hk = "view:" + key
        selected = self.view == key
        px1, px2 = x1 + 12, x2 - 12
        if selected:
            round_rect(c, px1, y - 20, px2, y + 20, r=20, fill=INK, outline="")
        elif self.hover == hk:
            round_rect(c, px1, y - 20, px2, y + 20, r=20, fill=WHITE, outline="")
        fg = WHITE if selected else TEXT
        draw_icon(c, icon, x1 + 36, y, WHITE if selected else INK)
        c.create_text(x1 + 62, y, anchor="w", text=label, fill=fg, font=self.f_item)
        if count:
            if dark_badge or selected:
                bg, tc = (WHITE, INK) if selected else (INK, WHITE)
                c.create_oval(px2 - 36, y - 11, px2 - 14, y + 11, fill=bg, outline="")
                c.create_text(px2 - 25, y, text=str(count), fill=tc, font=self.f_small_b)
            else:
                c.create_text(px2 - 25, y, text=str(count), fill=DIM, font=self.f_small)
        self.hot.append((px1, y - 20, px2, y + 20, hk))

    def clock_card(self, x1, y1, x2, y2):
        c = self.cv
        round_rect(c, x1, y1 + 4, x2, y2 + 4, r=22, fill="#dfe2e7", outline="")
        round_rect(c, x1, y1, x2, y2, r=22, fill="#f6f7f9", outline=WHITE)
        self.clock_geo = (x1 + 68, (y1 + y2) / 2, 50, x1 + 134, (y1 + y2) / 2)
        self.draw_clock()

    def draw_clock(self):
        import math
        c = self.cv
        c.delete("clock")
        if not getattr(self, "clock_geo", None) or not self.geo.get("show_side"):
            return
        cx, cy, R, tx, ty = self.clock_geo
        for k in range(60):
            a = k * math.pi / 30
            r1 = R - (7 if k % 5 == 0 else 3)
            col = "#3a3d44" if k % 5 == 0 else "#c3c7ce"
            c.create_line(cx + r1 * math.sin(a), cy - r1 * math.cos(a),
                          cx + (R - 1) * math.sin(a), cy - (R - 1) * math.cos(a),
                          fill=col, width=1.4 if k % 5 == 0 else 1, tags="clock")
        t = time.localtime()
        sec = t.tm_sec
        mins = t.tm_min + sec / 60
        hrs = t.tm_hour % 12 + mins / 60
        for ang, length, width, col in ((hrs * 30, R * 0.5, 3, INK), (mins * 6, R * 0.78, 2, INK),
                                        (sec * 6, R * 0.85, 1, "#7ea6c4")):
            a = math.radians(ang)
            c.create_line(cx, cy, cx + length * math.sin(a), cy - length * math.cos(a),
                          fill=col, width=width, capstyle="round", tags="clock")
        c.create_oval(cx - 4, cy - 4, cx + 4, cy + 4, fill=INK, outline="", tags="clock")
        ampm = "오전" if t.tm_hour < 12 else "오후"
        h12 = t.tm_hour % 12 or 12
        c.create_text(tx, ty - 22, anchor="w", text=f"{h12}:{t.tm_min:02d}", fill=INK, font=self.f_time, tags="clock")
        c.create_text(tx, ty + 6, anchor="w", text=ampm, fill=TEXT, font=self.f_item, tags="clock")
        c.create_text(tx, ty + 28, anchor="w", text=f"{t.tm_mon}월 {t.tm_mday}일 ({WEEKDAYS[t.tm_wday]})",
                      fill=DIM, font=self.f_small, tags="clock")

    def date_text(self):
        t = time.localtime()
        return f"{t.tm_year}년 {t.tm_mon}월 {t.tm_mday}일 {WEEKDAYS[t.tm_wday]}요일"

    def tick_clock(self):
        try:
            self.draw_clock()
            if not self.geo.get("show_side"):
                self.cv.itemconfigure("clock_text", text=self.date_text() + "   " + time.strftime("%H:%M"))
        except Exception:
            pass
        self.root.after(1000, self.tick_clock)

    def key_chip(self, x, y, text, fill=WHITE):
        """x 에서 시작하는 키 모양 칩을 그리고 끝 x 좌표를 돌려준다."""
        c = self.cv
        t = c.create_text(x + 8, y, anchor="w", text=text, fill=TEXT, font=self.f_small_b)
        bx1, by1, bx2, by2 = c.bbox(t)
        r = round_rect(c, bx1 - 7, by1 - 3, bx2 + 7, by2 + 3, r=7, fill=fill, outline="")
        c.tag_lower(r, t)
        return bx2 + 7

    def draw_footer(self, W, H):
        c = self.cv
        y = H - FOOTER_H / 2 + 2
        hints = [("Enter", "실행"), ("방향키", "이동"), ("Tab", "목록 전환"), ("F2", "편집"),
                 ("F11", "전체화면"), ("Esc", "나가기")]
        left_limit = M
        if self.toast_msg:
            t = c.create_text(M + 18, y, anchor="w", text=self.toast_msg, fill=WHITE, font=self.f_small_b)
            bx1, by1, bx2, by2 = c.bbox(t)
            r = round_rect(c, bx1 - 14, by1 - 6, bx2 + 14, by2 + 6, r=14, fill=INK, outline="")
            c.tag_lower(r, t)
            left_limit = bx2 + 30
        # 오른쪽부터 배치, 자리가 모자라면 남은 힌트는 생략
        x = W - M
        for key, label in reversed(hints):
            t = c.create_text(x, y, anchor="e", text=label, fill=DIM, font=self.f_small)
            k = c.create_text(c.bbox(t)[0] - 15, y, anchor="e", text=key, fill=TEXT, font=self.f_small_b)
            bx1, by1, bx2, by2 = c.bbox(k)
            if bx1 - 7 < left_limit:
                c.delete(t, k)
                break
            r = round_rect(c, bx1 - 7, by1 - 3, bx2 + 7, by2 + 3, r=7, fill="#eef0f3", outline="")
            c.tag_lower(r, k)
            x = bx1 - 26

    def toast(self, message, ms=2500):
        self.toast_msg = message
        self.redraw_all()
        if self.toast_job:
            self.root.after_cancel(self.toast_job)

        def clear():
            self.toast_msg = None
            self.redraw_all()
        self.toast_job = self.root.after(ms, clear)

    # ------------------------------------------------------------ 바깥 틀 마우스
    def hot_at(self, x, y):
        for x1, y1, x2, y2, key in self.hot:
            if x1 <= x <= x2 and y1 <= y <= y2:
                return key
        return None

    def set_hover(self, key):
        if key != self.hover:
            self.hover = key
            self.cv.configure(cursor="hand2" if key else "")
            self.redraw_all()

    def on_chrome_motion(self, e):
        self.set_hover(self.hot_at(e.x, e.y))

    def on_chrome_click(self, e):
        key = self.hot_at(e.x, e.y)
        if not key:
            return
        if key.startswith("view:"):
            self.set_view(key[5:])
        elif key == "add":
            self.add_menu(e.x_root, e.y_root)
        elif key == "settings":
            self.settings_menu(e.x_root, e.y_root)
        elif key == "fullscreen":
            self.toggle_fullscreen()
        elif key == "exit":
            self.quit()
        self.body.focus_set()

    # ------------------------------------------------------------ 앱 카드 영역
    def layout(self):
        w = max(self.body.winfo_width(), TILE_W + 2 * BODY_PAD)
        cols = max(1, (w - 2 * BODY_PAD + GAP) // (TILE_W + GAP))
        return cols, BODY_PAD

    def tile_pos(self, i, cols, x0):
        r, col = divmod(i, cols)
        return x0 + col * (TILE_W + GAP), BODY_PAD + r * (TILE_H + GAP)

    def hit_test(self, ex, ey):
        x, y = self.body.canvasx(ex), self.body.canvasy(ey)
        cols, x0 = self.layout()
        for n in range(len(self.visible())):
            tx, ty = self.tile_pos(n, cols, x0)
            if tx <= x <= tx + TILE_W and ty <= y <= ty + TILE_H:
                return n
        return None

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
                factor = 1
                while ph.width() // factor > box_w or ph.height() // factor > box_h:
                    factor += 1
                img = ph.subsample(factor) if factor > 1 else ph
        except Exception:
            img = None
        self.img_cache[key] = img
        return img

    def redraw_body(self, scroll=False):
        c = self.body
        c.delete("all")
        vis = self.visible()
        self.sel = max(0, min(self.sel, len(vis) - 1)) if vis else 0
        cols, x0 = self.layout()
        if not vis:
            w, h = c.winfo_width(), c.winfo_height()
            msg = {"fav": "즐겨찾기한 앱이 없어요.\n앱을 우클릭해서 '즐겨찾기에 추가' 를 눌러 보세요.",
                   "recent": "아직 실행한 앱이 없어요."}.get(self.view, "앱이 없어요.\n위의 '앱 추가하기' 를 눌러 추가하세요.")
            draw_icon(c, "folder", w / 2, h / 2 - 50, DIM, 2.0)
            c.create_text(w / 2, h / 2 + 10, text=msg, fill=DIM, font=self.f_item, justify="center")
            c.configure(scrollregion=(0, 0, w, h))
            return
        for n, i in enumerate(vis):
            x, y = self.tile_pos(n, cols, x0)
            self.draw_tile(i, x, y, n == self.sel)
        rows = -(-len(vis) // cols)
        height = BODY_PAD * 2 + rows * (TILE_H + GAP)
        c.configure(scrollregion=(0, 0, c.winfo_width(), height))
        if scroll:
            self.ensure_visible()

    def draw_tile(self, i, x, y, selected):
        c = self.body
        app = self.apps[i]
        x2, y2 = x + TILE_W, y + TILE_H
        if selected:
            round_rect(c, x, y + 6, x2, y2 + 4, r=22, fill="#c4c8cf", outline="")
            round_rect(c, x, y, x2, y2, r=22, fill=INK, outline="")
        else:
            round_rect(c, x, y, x2, y2, r=22, fill=CARD, outline=CARD_LINE)

        cx = x + TILE_W / 2
        box_bg, box_fg = self.pastel(i)
        img = self.load_icon(app["icon"], 72, 72) if app.get("icon") else None
        round_rect(c, cx - 42, y + 22, cx + 42, y + 106, r=22, fill=box_bg, outline="")
        if img is not None:
            c.create_image(cx, y + 64, image=img)
        else:
            letter = (app.get("name") or "?").strip()[:1].upper() or "?"
            c.create_text(cx, y + 64, text=letter, fill=box_fg, font=self.f_letter)

        name = app.get("name", "이름 없음")
        if len(name) > 14:
            name = name[:13] + "…"
        c.create_text(cx, y + 130, text=name, fill=WHITE if selected else INK, font=self.f_name)
        sub = (app.get("category") or "").strip() or app_kind(app)
        c.create_text(cx, y + 152, text=sub, fill="#9a9ea6" if selected else DIM, font=self.f_small)

        if app.get("favorite"):
            c.create_oval(x2 - 24, y + 14, x2 - 12, y + 26, fill=PINK, outline="")
        if selected:
            t = c.create_text(cx, y + 181, text="↵  실행", fill=INK, font=self.f_small_b)
            bx1, by1, bx2, by2 = c.bbox(t)
            r = round_rect(c, bx1 - 14, by1 - 4, bx2 + 14, by2 + 4, r=12, fill=WHITE, outline="")
            c.tag_lower(r, t)

    def ensure_visible(self):
        c = self.body
        vis = self.visible()
        if not vis:
            return
        cols, x0 = self.layout()
        _, y = self.tile_pos(self.sel, cols, x0)
        sr = c.cget("scrollregion").split()
        total = float(sr[3]) if len(sr) == 4 else 1
        view_h = c.winfo_height()
        if total <= view_h:
            c.yview_moveto(0)
            return
        top = c.canvasy(0)
        if y - BODY_PAD < top:
            c.yview_moveto(max(0, (y - BODY_PAD) / total))
        elif y + TILE_H + BODY_PAD > top + view_h:
            c.yview_moveto((y + TILE_H + BODY_PAD - view_h) / total)

    def on_wheel(self, e):
        if SYSTEM == "Darwin":
            self.body.yview_scroll(-e.delta, "units")
        else:
            self.body.yview_scroll(int(-e.delta / 40) or (-1 if e.delta > 0 else 1), "units")

    # ------------------------------------------------------------ 입력 처리
    def select(self, n):
        count = len(self.visible())
        n = max(0, min(count - 1, n))
        if n != self.sel:
            self.sel = n
            self.redraw_body(scroll=True)

    def move(self, dx, dy):
        cols, _ = self.layout()
        count = len(self.visible())
        if dx:
            self.select(self.sel + dx)
        elif dy:
            target = self.sel + dy * cols
            if dy > 0 and target >= count:
                if self.sel // cols < (count - 1) // cols:
                    target = count - 1
                else:
                    return
            if target >= 0:
                self.select(target)

    def on_motion(self, e):
        if self.hover:
            self.set_hover(None)
        if self.last_mouse == (e.x_root, e.y_root):
            return
        self.last_mouse = (e.x_root, e.y_root)
        n = self.hit_test(e.x, e.y)
        if n is not None:
            self.select(n)
        self.body.configure(cursor="hand2" if n is not None else "")

    def on_click(self, e):
        self.body.focus_set()
        n = self.hit_test(e.x, e.y)
        if n is not None:
            self.sel = n
            self.redraw_body()
            self.activate()

    def on_right_click(self, e):
        n = self.hit_test(e.x, e.y)
        if n is not None:
            self.sel = n
            self.redraw_body()
            self.open_menu(e.x_root, e.y_root)

    def activate(self):
        i = self.cur_index()
        if i is None:
            self.add_menu()
            return
        now = time.monotonic()
        if now - self.last_launch < 0.8:  # 더블클릭 등으로 두 번 실행되는 것 방지
            return
        self.last_launch = now
        app = self.apps[i]
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
        if self.view == "recent":
            self.sel = 0
            self.redraw_body(scroll=True)
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

    # ------------------------------------------------------------ 메뉴 / 편집
    def make_menu(self):
        fam = self.f_item[0]
        return tk.Menu(self.root, tearoff=0, bg=WHITE, fg=TEXT, activebackground=INK,
                       activeforeground=WHITE, relief="flat", bd=0, font=(fam, 11))

    def popup(self, menu, x=None, y=None):
        if x is None:
            vis = self.visible()
            if vis:
                cols, x0 = self.layout()
                tx, ty = self.tile_pos(self.sel, cols, x0)
                x = self.body.winfo_rootx() + tx + TILE_W // 2
                y = self.body.winfo_rooty() + ty - int(self.body.canvasy(0)) + TILE_H // 2
            else:
                x, y = self.body.winfo_rootx() + 40, self.body.winfo_rooty() + 40
        try:
            menu.tk_popup(x, y)
        finally:
            menu.grab_release()

    def open_menu(self, x=None, y=None):
        i = self.cur_index()
        if i is None:
            self.add_menu(x, y)
            return
        app = self.apps[i]
        vis = self.visible()
        n = self.sel
        m = self.make_menu()
        m.add_command(label="▶  실행", command=self.activate)
        m.add_command(label="즐겨찾기에서 빼기" if app.get("favorite") else "즐겨찾기에 추가",
                      command=lambda: self.set_field(i, "favorite", None if app.get("favorite") else True))
        m.add_separator()
        m.add_command(label="이름 변경", command=lambda: self.rename_app(i))
        m.add_command(label="실행 대상 변경", command=lambda: self.change_target(i))
        m.add_command(label="카테고리 지정", command=lambda: self.change_category(i))
        m.add_command(label="아이콘 이미지 선택", command=lambda: self.change_icon(i))
        if app.get("icon"):
            m.add_command(label="아이콘 제거", command=lambda: self.set_field(i, "icon", None))
        m.add_command(label="아이콘 색상 변경", command=lambda: self.change_color(i))
        if self.view != "recent":
            m.add_separator()
            m.add_command(label="◀  앞으로 이동", command=lambda: self.reorder(n, -1),
                          state="normal" if n > 0 else "disabled")
            m.add_command(label="▶  뒤로 이동", command=lambda: self.reorder(n, 1),
                          state="normal" if n < len(vis) - 1 else "disabled")
        m.add_separator()
        m.add_command(label="삭제", command=lambda: self.delete_app(i))
        self.popup(m, x, y)

    def settings_menu(self, x=None, y=None):
        m = self.make_menu()
        self._v_min = tk.BooleanVar(m, self.settings.get("minimize_on_launch", True))
        self._v_full = tk.BooleanVar(m, self.settings.get("fullscreen", False))
        m.add_checkbutton(label="앱 실행 후 런처 최소화", variable=self._v_min, command=self.toggle_minimize)
        m.add_checkbutton(label="전체화면", variable=self._v_full, command=self.toggle_fullscreen)
        m.add_separator()
        m.add_command(label="앱 추가…", command=self.add_menu)
        m.add_command(label="설정 파일(apps.json) 폴더 열기", command=lambda: _open_with_system(APP_DIR))
        self.popup(m, x, y)

    def add_menu(self, x=None, y=None):
        m = self.make_menu()
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
        name = simpledialog.askstring("앱 이름", "표시할 이름:", initialvalue=guess, parent=self.root)
        if name is None:
            return
        self.add_app({"name": name.strip() or guess, "target": path})

    def add_from_text(self):
        target = simpledialog.askstring(
            "명령어 / URL", "실행할 명령어, 경로 또는 URL\n(예: notepad.exe, steam://rungameid/570, https://youtube.com)",
            parent=self.root)
        if not target or not target.strip():
            return
        name = simpledialog.askstring("앱 이름", "표시할 이름:", parent=self.root)
        if name is None:
            return
        self.add_app({"name": name.strip() or target.strip(), "target": target.strip()})

    def add_app(self, app):
        if self.view.startswith("cat:"):
            app["category"] = self.view[4:]
        elif self.view == "fav":
            app["favorite"] = True
        elif self.view == "recent":
            self.view = "all"
        self.apps.append(app)
        save_config(self.data)
        vis = self.visible()
        self.sel = vis.index(len(self.apps) - 1) if (len(self.apps) - 1) in vis else 0
        self.toast(f"'{app['name']}' 추가됨")

    def set_field(self, i, key, value):
        if value is None:
            self.apps[i].pop(key, None)
        else:
            self.apps[i][key] = value
        save_config(self.data)
        self.redraw_all()

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

    def change_category(self, i):
        cats = self.categories()
        hint = ("기존 카테고리: " + ", ".join(cats) + "\n") if cats else ""
        t = simpledialog.askstring("카테고리 지정", hint + "카테고리 이름 (비우면 카테고리 해제):",
                                   initialvalue=self.apps[i].get("category", ""), parent=self.root)
        if t is None:
            return
        self.set_field(i, "category", t.strip() or None)
        if self.view.startswith("cat:") and self.view[4:] not in self.categories():
            self.set_view("all")

    def change_icon(self, i):
        types = [("이미지", "*.png *.gif *.jpg *.jpeg *.webp *.bmp *.ico"), ("모든 파일", "*.*")] if Image \
            else [("이미지 (PNG/GIF)", "*.png *.gif"), ("모든 파일", "*.*")]
        path = filedialog.askopenfilename(parent=self.root, title="아이콘 이미지 선택", filetypes=types)
        if path:
            self.set_field(i, "icon", path)

    def change_color(self, i):
        _, hex_color = colorchooser.askcolor(color=self.pastel(i)[0], parent=self.root, title="아이콘 색상")
        if hex_color:
            self.set_field(i, "color", hex_color)

    def reorder(self, n, d):
        vis = self.visible()
        m = n + d
        if 0 <= m < len(vis):
            a, b = vis[n], vis[m]
            self.apps[a], self.apps[b] = self.apps[b], self.apps[a]
            self.sel = m
            save_config(self.data)
            self.redraw_body(scroll=True)

    def delete_app(self, i):
        if i is None:
            return
        name = self.apps[i].get("name")
        if messagebox.askyesno("삭제", f"'{name}' 을(를) 목록에서 삭제할까요?\n(프로그램 자체는 지워지지 않습니다)",
                               parent=self.root):
            del self.apps[i]
            save_config(self.data)
            if self.view.startswith("cat:") and self.view[4:] not in self.categories():
                self.view = "all"
            self.redraw_all()


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
