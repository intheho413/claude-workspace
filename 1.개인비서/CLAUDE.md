# 개인 AI 비서 봇

텔레그램 + Gemini AI + 구글 캘린더 연동 개인 비서 봇.

## 환경 정보
- Python 3.12
- 작업 경로: `C:\Users\inho4\OneDrive\바탕 화면\claude\1.개인비서`
- 텔레그램 봇: @Etelerobot (Lumo)
- AI 모델: Google Gemini 1.5 Flash (무료)

## 파일 구조
```
1.개인비서/
├── bot.py               ← 메인 봇 코드 (여기를 수정)
├── .env                 ← API 키 (GitHub 미업로드)
├── credentials.json     ← 구글 OAuth 인증 (GitHub 미업로드)
├── token.json           ← 구글 로그인 토큰 (GitHub 미업로드, 자동 생성)
├── requirements.txt     ← Python 패키지
├── start_bot.bat        ← 봇 실행 배치파일
├── start_bot.vbs        ← PC 시작 시 자동 실행 스크립트
├── data/
│   ├── schedules.json   ← 일정 데이터
│   └── memos.json       ← 메모 데이터
└── logs/                ← 날짜별 대화 로그
```

## .env 파일 내용 (직접 확인)
```
TELEGRAM_BOT_TOKEN=...   ← 텔레그램 봇 토큰
GEMINI_API_KEY=...       ← Google Gemini API 키 (aistudio.google.com)
ALLOWED_USER_IDS=8158086124
```

## 봇 실행
```powershell
cd "C:\Users\inho4\OneDrive\바탕 화면\claude\1.개인비서"
python bot.py
```

## 패키지 재설치 (필요 시)
```powershell
pip install -r requirements.txt
```

## 텔레그램 명령어
| 명령어 | 기능 |
|--------|------|
| `/add YYYY-MM-DD HH:MM 내용` | 일정 추가 + 구글 캘린더 등록 |
| `/schedules` | 전체 일정 조회 |
| `/today` | 오늘 일정 조회 |
| `/delete 번호` | 일정 삭제 + 구글 캘린더 삭제 |
| `/memo 내용` | 메모 저장 |
| `/memos` | 메모 목록 조회 |
| `/clear` | 대화 기록 초기화 |
| 자유 텍스트 | Gemini AI 응답 |

## 구글 캘린더 연동
- `credentials.json`: Google Cloud Console에서 발급한 OAuth 클라이언트 (데스크톱 앱)
- `token.json`: 최초 인증 후 자동 생성, 이후 자동 로그인
- 프로젝트: personal-bot (Google Cloud Console, 프로젝트 ID: 314562720279)
- 활성화된 API: Google Calendar API

## GitHub 미업로드 파일
아래 파일은 보안상 GitHub에 올리지 않음. 로컬에만 존재:
- `.env` (API 키)
- `credentials.json` (OAuth 인증)
- `token.json` (로그인 토큰)
- `data/` (개인 일정/메모 데이터)

## 자동 실행 설정
`start_bot.vbs`가 Windows 시작 프로그램에 등록되어 있음:
- 경로: `C:\Users\inho4\AppData\Roaming\Microsoft\Windows\Start Menu\Programs\Startup\start_bot.vbs`
- PC 로그인 시 백그라운드에서 자동 실행됨

## 향후 추가 가능한 기능
- 미팅룸 예약 연동 (connect.tdl-cloud.com 오픈 시)
- 날씨 조회
- 웹 검색 요약
