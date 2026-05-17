import os
import json
import logging
import re
from datetime import datetime, date
from pathlib import Path
from dotenv import load_dotenv
import google.generativeai as genai
from googleapiclient.discovery import build
from google_auth_oauthlib.flow import InstalledAppFlow
from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials
from telegram import Update
from telegram.ext import Application, CommandHandler, MessageHandler, filters, ContextTypes

load_dotenv()

TELEGRAM_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")
ALLOWED_IDS = [int(x.strip()) for x in os.getenv("ALLOWED_USER_IDS", "").split(",") if x.strip().isdigit()]

BASE_DIR = Path(__file__).parent
LOG_DIR = BASE_DIR / "logs"
DATA_DIR = BASE_DIR / "data"
MEMO_FILE = DATA_DIR / "memos.json"
SCHEDULE_FILE = DATA_DIR / "schedules.json"
CREDENTIALS_FILE = BASE_DIR / "credentials.json"
TOKEN_FILE = BASE_DIR / "token.json"

SCOPES = ["https://www.googleapis.com/auth/calendar"]

LOG_DIR.mkdir(exist_ok=True)
DATA_DIR.mkdir(exist_ok=True)

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    handlers=[
        logging.FileHandler(LOG_DIR / f"{datetime.now().strftime('%Y-%m-%d')}.log", encoding="utf-8"),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

genai.configure(api_key=GEMINI_API_KEY)

SYSTEM_PROMPT = f"""당신은 친절하고 유능한 개인 AI 비서입니다.
오늘 날짜는 {datetime.now().strftime('%Y년 %m월 %d일')}입니다.
사용자의 질문에 명확하고 간결하게 답변하세요.
한국어로 대화하되, 사용자가 다른 언어를 사용하면 그 언어에 맞춰 응답하세요.

사용 가능한 명령어:
- /일정추가 날짜 시간 내용 (구글 캘린더에 자동 등록)
- /일정 — 전체 일정 조회
- /일정오늘 — 오늘 일정
- /일정삭제 번호
- /memo 내용 — 메모 저장
- /memos — 메모 조회"""

conversation_histories: dict[int, list] = {}


def get_calendar_service():
    creds = None
    if TOKEN_FILE.exists():
        creds = Credentials.from_authorized_user_file(str(TOKEN_FILE), SCOPES)
    if not creds or not creds.valid:
        if creds and creds.expired and creds.refresh_token:
            creds.refresh(Request())
        else:
            flow = InstalledAppFlow.from_client_secrets_file(str(CREDENTIALS_FILE), SCOPES)
            creds = flow.run_local_server(port=0)
        with open(TOKEN_FILE, "w") as f:
            f.write(creds.to_json())
    return build("calendar", "v3", credentials=creds)


def add_to_google_calendar(date_str: str, time_str: str, content: str) -> str | None:
    try:
        service = get_calendar_service()
        start_dt = f"{date_str}T{time_str}:00+09:00"
        # 1시간 일정으로 기본 설정
        end_hour = int(time_str.split(":")[0]) + 1
        end_min = time_str.split(":")[1]
        end_dt = f"{date_str}T{end_hour:02d}:{end_min}:00+09:00"

        event = {
            "summary": content,
            "start": {"dateTime": start_dt, "timeZone": "Asia/Seoul"},
            "end": {"dateTime": end_dt, "timeZone": "Asia/Seoul"},
        }
        result = service.events().insert(calendarId="primary", body=event).execute()
        logger.info(f"[GCAL_ADD] event_id={result['id']}")
        return result["id"]
    except Exception as e:
        logger.error(f"[GCAL_ERROR] {e}")
        return None


def delete_from_google_calendar(event_id: str):
    try:
        service = get_calendar_service()
        service.events().delete(calendarId="primary", eventId=event_id).execute()
        logger.info(f"[GCAL_DEL] event_id={event_id}")
    except Exception as e:
        logger.error(f"[GCAL_ERROR] {e}")


def get_model():
    return genai.GenerativeModel(
        model_name="gemini-1.5-flash",
        system_instruction=SYSTEM_PROMPT
    )


def load_memos() -> list:
    if MEMO_FILE.exists():
        with open(MEMO_FILE, "r", encoding="utf-8") as f:
            return json.load(f)
    return []


def save_memos(memos: list):
    with open(MEMO_FILE, "w", encoding="utf-8") as f:
        json.dump(memos, f, ensure_ascii=False, indent=2)


def load_schedules() -> list:
    if SCHEDULE_FILE.exists():
        with open(SCHEDULE_FILE, "r", encoding="utf-8") as f:
            return json.load(f)
    return []


def save_schedules(schedules: list):
    with open(SCHEDULE_FILE, "w", encoding="utf-8") as f:
        json.dump(schedules, f, ensure_ascii=False, indent=2)


def is_allowed(user_id: int) -> bool:
    if not ALLOWED_IDS:
        return True
    return user_id in ALLOWED_IDS


async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    if not is_allowed(user.id):
        return
    conversation_histories[user.id] = []
    await update.message.reply_text(
        f"안녕하세요 {user.first_name}님! 개인 AI 비서입니다 🤖\n\n"
        "무엇이든 말씀해 주세요.\n\n"
        "📌 *명령어 목록*\n\n"
        "📅 *일정 관리 (구글 캘린더 연동)*\n"
        "/add 날짜 시간 내용\n"
        "/schedules — 전체 일정 조회\n"
        "/today — 오늘 일정 조회\n"
        "/delete 번호 — 일정 삭제\n\n"
        "📝 *메모*\n"
        "/memo 내용 — 메모 저장\n"
        "/memos — 메모 목록 조회\n\n"
        "🗑️ /clear — 대화 기록 초기화\n"
        "❓ /help — 도움말",
        parse_mode="Markdown"
    )
    logger.info(f"[START] user_id={user.id}, username={user.username}")


async def help_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not is_allowed(update.effective_user.id):
        return
    await update.message.reply_text(
        "📌 *명령어 목록*\n\n"
        "📅 *일정 관리*\n"
        "/add 2026-05-20 14:00 팀 미팅\n"
        "/schedules — 전체 일정 조회\n"
        "/today — 오늘 일정만 조회\n"
        "/delete 1 — 1번 일정 삭제\n\n"
        "📝 *메모*\n"
        "/memo 내일 자료 준비\n"
        "/memos — 메모 목록 조회\n\n"
        "🗑️ /clear — 대화 기록 초기화\n\n"
        "💬 그 외 자유롭게 대화하세요!",
        parse_mode="Markdown"
    )


async def schedule_add_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    if not is_allowed(user.id):
        return

    args = context.args
    if len(args) < 3:
        await update.message.reply_text(
            "형식: `/일정추가 날짜 시간 내용`\n"
            "예: `/일정추가 2026-05-20 14:00 팀 미팅`",
            parse_mode="Markdown"
        )
        return

    date_str = args[0]
    time_str = args[1]
    content = " ".join(args[2:])

    if re.match(r"^\d{2}-\d{2}$", date_str):
        date_str = f"{datetime.now().year}-{date_str}"

    try:
        datetime.strptime(f"{date_str} {time_str}", "%Y-%m-%d %H:%M")
    except ValueError:
        await update.message.reply_text(
            "날짜/시간 형식이 맞지 않아요.\n"
            "예: `/일정추가 2026-05-20 14:00 팀 미팅`",
            parse_mode="Markdown"
        )
        return

    await update.message.reply_text("⏳ 구글 캘린더에 등록 중...")

    gcal_event_id = add_to_google_calendar(date_str, time_str, content)

    schedules = load_schedules()
    user_schedules = [s for s in schedules if s.get("user_id") == user.id]
    new_id = max([s["id"] for s in user_schedules], default=0) + 1

    schedule = {
        "id": new_id,
        "date": date_str,
        "time": time_str,
        "content": content,
        "gcal_event_id": gcal_event_id,
        "created_at": datetime.now().strftime("%Y-%m-%d %H:%M"),
        "user_id": user.id
    }
    schedules.append(schedule)
    save_schedules(schedules)

    gcal_status = "📆 구글 캘린더에도 등록됐어요!" if gcal_event_id else "⚠️ 구글 캘린더 등록 실패 (로컬에는 저장됨)"

    await update.message.reply_text(
        f"✅ 일정이 추가됐어요!\n\n"
        f"📅 *{date_str} {time_str}*\n"
        f"📌 {content}\n\n"
        f"{gcal_status}",
        parse_mode="Markdown"
    )
    logger.info(f"[SCHEDULE_ADD] user_id={user.id}, {date_str} {time_str} {content}")


async def schedule_list_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    if not is_allowed(user.id):
        return

    schedules = [s for s in load_schedules() if s.get("user_id") == user.id]
    today = date.today().strftime("%Y-%m-%d")
    upcoming = sorted([s for s in schedules if s["date"] >= today], key=lambda x: (x["date"], x["time"]))

    if not upcoming:
        await update.message.reply_text("예정된 일정이 없어요.")
        return

    text = "📅 *전체 일정*\n\n"
    for s in upcoming:
        gcal = "📆" if s.get("gcal_event_id") else "📋"
        text += f"`{s['id']}.` {gcal} *{s['date']} {s['time']}*\n    {s['content']}\n\n"

    await update.message.reply_text(text, parse_mode="Markdown")


async def schedule_today_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    if not is_allowed(user.id):
        return

    today = date.today().strftime("%Y-%m-%d")
    schedules = [s for s in load_schedules() if s.get("user_id") == user.id and s["date"] == today]
    schedules = sorted(schedules, key=lambda x: x["time"])

    if not schedules:
        await update.message.reply_text(f"오늘 ({today}) 일정이 없어요.")
        return

    text = f"📅 *오늘 일정 ({today})*\n\n"
    for s in schedules:
        gcal = "📆" if s.get("gcal_event_id") else "📋"
        text += f"`{s['id']}.` {gcal} *{s['time']}*  {s['content']}\n\n"

    await update.message.reply_text(text, parse_mode="Markdown")


async def schedule_delete_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    if not is_allowed(user.id):
        return

    if not context.args or not context.args[0].isdigit():
        await update.message.reply_text("삭제할 일정 번호를 입력해주세요.\n예: `/일정삭제 1`", parse_mode="Markdown")
        return

    target_id = int(context.args[0])
    schedules = load_schedules()
    target = next((s for s in schedules if s.get("user_id") == user.id and s["id"] == target_id), None)

    if not target:
        await update.message.reply_text(f"{target_id}번 일정을 찾을 수 없어요.")
        return

    if target.get("gcal_event_id"):
        delete_from_google_calendar(target["gcal_event_id"])

    schedules = [s for s in schedules if not (s.get("user_id") == user.id and s["id"] == target_id)]
    save_schedules(schedules)

    await update.message.reply_text(
        f"🗑️ 일정을 삭제했어요.\n\n"
        f"~~{target['date']} {target['time']} {target['content']}~~\n"
        f"{'📆 구글 캘린더에서도 삭제됐어요.' if target.get('gcal_event_id') else ''}",
        parse_mode="Markdown"
    )
    logger.info(f"[SCHEDULE_DEL] user_id={user.id}, id={target_id}")


async def memo_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    if not is_allowed(user.id):
        return

    content = " ".join(context.args)
    if not content:
        await update.message.reply_text("메모 내용을 입력해주세요.\n예: `/memo 내일 회의 준비`", parse_mode="Markdown")
        return

    memos = load_memos()
    memo = {
        "id": len(memos) + 1,
        "content": content,
        "created_at": datetime.now().strftime("%Y-%m-%d %H:%M"),
        "user_id": user.id
    }
    memos.append(memo)
    save_memos(memos)

    await update.message.reply_text(f"✅ 메모가 저장됐어요!\n\n📝 *{content}*", parse_mode="Markdown")
    logger.info(f"[MEMO] user_id={user.id}, content={content}")


async def memos_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    if not is_allowed(user.id):
        return

    memos = [m for m in load_memos() if m.get("user_id") == user.id]

    if not memos:
        await update.message.reply_text("저장된 메모가 없어요.")
        return

    text = "📋 *저장된 메모 목록*\n\n"
    for m in memos[-20:]:
        text += f"`{m['id']}.` {m['content']}\n    _{m['created_at']}_\n\n"

    await update.message.reply_text(text, parse_mode="Markdown")


async def clear_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    if not is_allowed(user.id):
        return
    conversation_histories[user.id] = []
    await update.message.reply_text("🗑️ 대화 기록을 초기화했어요. 새로 시작합니다!")
    logger.info(f"[CLEAR] user_id={user.id}")


async def chat(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    if not is_allowed(user.id):
        await update.message.reply_text("접근 권한이 없습니다.")
        return

    user_message = update.message.text
    logger.info(f"[CHAT] user_id={user.id} → {user_message}")

    if user.id not in conversation_histories:
        conversation_histories[user.id] = []

    conversation_histories[user.id].append({
        "role": "user",
        "parts": [user_message]
    })

    if len(conversation_histories[user.id]) > 40:
        conversation_histories[user.id] = conversation_histories[user.id][-40:]

    await context.bot.send_chat_action(chat_id=update.effective_chat.id, action="typing")

    try:
        model = get_model()
        chat_session = model.start_chat(history=conversation_histories[user.id][:-1])
        response = chat_session.send_message(user_message)
        reply = response.text

        conversation_histories[user.id].append({
            "role": "model",
            "parts": [reply]
        })

        logger.info(f"[REPLY] user_id={user.id} ← {reply[:80]}...")
        await update.message.reply_text(reply)

    except Exception as e:
        logger.error(f"[ERROR] {e}")
        await update.message.reply_text(f"오류가 발생했어요: {str(e)}")


def main():
    if not TELEGRAM_TOKEN or TELEGRAM_TOKEN == "여기에_텔레그램_봇_토큰_입력":
        print("[오류] .env 파일에 TELEGRAM_BOT_TOKEN을 설정해주세요.")
        return
    if not GEMINI_API_KEY or GEMINI_API_KEY == "여기에_Gemini_API_키_입력":
        print("[오류] .env 파일에 GEMINI_API_KEY를 설정해주세요.")
        return
    if not CREDENTIALS_FILE.exists():
        print("[오류] credentials.json 파일이 없어요. Google Cloud Console에서 다운로드해주세요.")
        return

    app = Application.builder().token(TELEGRAM_TOKEN).build()

    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("help", help_cmd))
    app.add_handler(CommandHandler("add", schedule_add_cmd))
    app.add_handler(CommandHandler("schedules", schedule_list_cmd))
    app.add_handler(CommandHandler("today", schedule_today_cmd))
    app.add_handler(CommandHandler("delete", schedule_delete_cmd))
    app.add_handler(CommandHandler("memo", memo_cmd))
    app.add_handler(CommandHandler("memos", memos_cmd))
    app.add_handler(CommandHandler("clear", clear_cmd))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, chat))

    logger.info("개인 AI 비서 봇 시작!")
    print("봇이 실행 중입니다. 종료하려면 Ctrl+C")
    app.run_polling(drop_pending_updates=True)


if __name__ == "__main__":
    main()
