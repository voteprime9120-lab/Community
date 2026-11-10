# Deck Launcher

스팀덱(Steam Deck) 스타일의 앱 런처입니다. **타일을 클릭하면 그 앱이 바로 실행되고**, 런처는 자동으로 최소화되어 실행한 앱 화면으로 넘어갑니다.

- Windows / macOS / Linux(스팀덱 데스크톱 모드 포함)에서 동작
- 파이썬 기본 라이브러리(tkinter)만 있으면 실행됨
- 마우스, 키보드, 게임패드(선택) 조작 지원
- 밝은 라이트 테마: 왼쪽 아이콘 레일, 메뉴 패널(전체 / 즐겨찾기 / 최근 실행 / 카테고리), 아날로그 시계 카드
- 앱을 카테고리(폴더)로 묶고, 즐겨찾기로 표시할 수 있음

## 실행 방법

1. [Python 3](https://www.python.org/downloads/)을 설치합니다. (Windows는 설치할 때 *Add python.exe to PATH* 체크)
2. 실행합니다.
   - **Windows**: `run_windows.bat` 더블클릭
   - **macOS / Linux**: `./run.sh` 실행 또는 `python3 deck_launcher.py`

### 선택 기능

```bash
pip install pillow pygame
```

- `pillow`를 설치하면 JPG, WEBP, ICO 등 PNG 외의 아이콘 이미지도 쓸 수 있습니다.
- `pygame`을 설치하면 게임패드(Xbox 패드, 스팀덱 컨트롤러 등)로 조작할 수 있습니다.

### exe 파일로 만들기 (Windows)

`build_exe.bat`를 실행하면 `dist\DeckLauncher.exe`가 만들어집니다. 파이썬이 없는 PC에서도 실행할 수 있습니다.

## 조작법

| 동작 | 마우스 | 키보드 | 게임패드 |
|---|---|---|---|
| 앱 실행 | 타일 **클릭** | Enter / Space | A |
| 이동 | 마우스 올리기 | 방향키, Home/End | D-Pad / 왼쪽 스틱 |
| 편집 메뉴 | 우클릭 | F2 | Y |
| 목록 전환 (전체/즐겨찾기/최근/카테고리) | 왼쪽 메뉴 클릭 | Tab / Shift+Tab | LB / RB |
| 앱 추가 | `앱 추가하기` 바 클릭 | Ctrl + N | X |
| 삭제 | 우클릭 → 삭제 | Delete | |
| 전체화면 | | F11 | |
| 전체화면 해제 / 종료 | | Esc | |

## 앱 추가하기

위쪽의 **`+ 앱 추가하기`** 바를 클릭하거나 Ctrl + N 을 누릅니다. 카테고리나 즐겨찾기 목록을 보고 있을 때 추가하면 그 목록에 바로 들어갑니다.

- **프로그램 / 바로가기 파일 선택**: `.exe`, `.lnk`(바탕화면 바로가기), `.app`, `.desktop` 등을 고릅니다.
- **명령어 또는 URL 직접 입력**: 예를 들면 아래처럼 넣을 수 있습니다.
  - `notepad.exe`
  - `steam://rungameid/570` (스팀 게임 바로 실행. 숫자는 게임의 App ID)
  - `https://www.youtube.com`

앱 카드를 우클릭하면 즐겨찾기, 카테고리 지정, 이름, 실행 대상, 아이콘 이미지, 아이콘 색상, 순서를 바꾸거나 삭제할 수 있습니다.
왼쪽 레일의 설정 버튼에서 **앱 실행 후 런처 최소화**를 끄면 앱을 실행해도 런처가 그대로 남습니다.

## 설정 파일 (`apps.json`)

앱 목록은 프로그램 옆의 `apps.json`에 저장됩니다. 직접 고쳐도 됩니다.

```json
{
  "settings": {
    "fullscreen": false,
    "minimize_on_launch": true
  },
  "apps": [
    { "name": "메모장", "target": "notepad.exe" },
    { "name": "도타 2", "target": "steam://rungameid/570", "category": "게임", "favorite": true, "icon": "icons/dota2.png" },
    { "name": "내 게임", "target": "C:\\Games\\MyGame\\game.exe", "args": ["-windowed"] }
  ]
}
```

| 키 | 설명 |
|---|---|
| `name` | 타일에 표시할 이름 |
| `target` | 실행 파일 경로, 바로가기, 폴더, URL 또는 명령어 |
| `args` | (선택) 실행 인자 목록 |
| `icon` | (선택) 아이콘 이미지 경로 (상대경로는 프로그램 폴더 기준) |
| `category` | (선택) 카테고리 이름. 왼쪽 메뉴에 폴더처럼 표시됨 |
| `favorite` | (선택) `true` 면 즐겨찾기 |
| `color` | (선택) 아이콘 상자 색상 |
