import os
import json
import requests
from telegram import Update
from telegram.ext import ApplicationBuilder, CommandHandler, ContextTypes

# ================= CONFIG =================
BOT_TOKEN = os.getenv("BOT_TOKEN")
API_KEY = os.getenv("OSINT_API_KEY")
API_ROOT = "https://relay-wzlz.onrender.com"
REQUEST_TIMEOUT = 25

if not BOT_TOKEN or not API_KEY:
    raise RuntimeError("BOT_TOKEN or OSINT_API_KEY not set")

# Optional user restriction
# ALLOWED_USERS = {123456789}

# ================= API =================
def call_api(command: str) -> dict:
    url = f"{API_ROOT.rstrip('/')}/api/command"
    payload = {"api_key": API_KEY, "command": command}

    try:
        r = requests.post(url, json=payload, timeout=REQUEST_TIMEOUT)
        r.raise_for_status()
        return {"ok": True, "json": r.json()}
    except Exception as e:
        return {"ok": False, "error": str(e)}

# ================= FORMATTER =================
def format_response(text: str) -> str:
    text = text.replace("```json", "").replace("```", "").strip()

    try:
        data = json.loads(text)
        return format_dict(data)
    except Exception:
        return text[:4000]

def format_dict(data, indent=0):
    lines = []
    space = "  " * indent

    if isinstance(data, dict):
        for k, v in data.items():
            key = k.replace("_", " ").title()
            if isinstance(v, (dict, list)):
                lines.append(f"{space}• {key}")
                lines.extend(format_dict(v, indent + 1))
            else:
                lines.append(f"{space}• {key}: {v}")
    elif isinstance(data, list):
        for i, item in enumerate(data, 1):
            lines.append(f"{space}#{i}")
            lines.extend(format_dict(item, indent + 1))
    else:
        lines.append(f"{space}{data}")

    return lines

# ================= HANDLERS =================
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        "🕵️ *OSINT Bot Online*\n\n"
        "Available Commands:\n"
        "/num <number>\n"
        "/ip <ip>\n"
        "/insta <username>\n"
        "/tg <username>\n"
        "/gst <gst>\n"
        "/ff <id>\n\n"
        "_Use responsibly_",
        parse_mode="Markdown"
    )

async def osint_command(update: Update, context: ContextTypes.DEFAULT_TYPE, token: str):
    if not context.args:
        await update.message.reply_text("❌ Missing argument")
        return

    query = " ".join(context.args)
    cmd = f"2/{token} {query}"

    msg = await update.message.reply_text("🔍 Processing...")

    result = call_api(cmd)

    if not result.get("ok"):
        await msg.edit_text("❌ API Error")
        return

    body = result["json"]

    if body.get("success"):
        output = []
        for r in body.get("responses", []):
            formatted = format_response(r)
            if isinstance(formatted, list):
                output.extend(formatted)
            else:
                output.append(formatted)

        text = "\n".join(output)[:4000]
        await msg.edit_text(f"```\n{text}\n```", parse_mode="Markdown")
    else:
        await msg.edit_text("❌ No data found")

# ===== INDIVIDUAL COMMANDS =====
async def num(update, context): await osint_command(update, context, "num")
async def ip(update, context): await osint_command(update, context, "ip")
async def insta(update, context): await osint_command(update, context, "insta")
async def tg(update, context): await osint_command(update, context, "tg")
async def gst(update, context): await osint_command(update, context, "gst")
async def ff(update, context): await osint_command(update, context, "ff")

# ================= MAIN =================
def main():
    app = ApplicationBuilder().token(BOT_TOKEN).build()

    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("num", num))
    app.add_handler(CommandHandler("ip", ip))
    app.add_handler(CommandHandler("insta", insta))
    app.add_handler(CommandHandler("tg", tg))
    app.add_handler(CommandHandler("gst", gst))
    app.add_handler(CommandHandler("ff", ff))

    print("🤖 OSINT Telegram Bot Running...")
    app.run_polling()

if __name__ == "__main__":
    main()
