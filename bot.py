
import os
import json
import requests
import threading
from aiohttp import web
from telegram import Update
from telegram.ext import ApplicationBuilder, CommandHandler, ContextTypes

# ================= CONFIG =================
BOT_TOKEN = os.getenv("BOT_TOKEN")
API_KEY = os.getenv("OSINT_API_KEY")
API_ROOT = "https://relay-wzlz.onrender.com"
REQUEST_TIMEOUT = 25
PORT = int(os.getenv("PORT", 10000))  # Render port

if not BOT_TOKEN or not API_KEY:
    raise RuntimeError("BOT_TOKEN or OSINT_API_KEY not set")

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
def format_response(text: str):
    text = text.replace("```json", "").replace("```", "").strip()
    try:
        return format_dict(json.loads(text))
    except Exception:
        return [text[:4000]]

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
    return lines

# ================= HANDLERS =================
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        "🕵️ OSINT Bot Online\n\n"
        "/num <number>\n"
        "/ip <ip>\n"
        "/insta <username>\n"
        "/tg <username>\n"
        "/gst <gst>\n"
        "/ff <id>"
    )

async def osint_command(update, context, token):
    if not context.args:
        await update.message.reply_text("❌ Missing argument")
        return

    msg = await update.message.reply_text("🔍 Processing...")
    result = call_api(f"2/{token} {' '.join(context.args)}")

    if not result.get("ok"):
        await msg.edit_text("❌ API Error")
        return

    body = result["json"]
    if body.get("success"):
        out = []
        for r in body.get("responses", []):
            out.extend(format_response(r))
        await msg.edit_text(f"```\n{chr(10).join(out)[:4000]}\n```", parse_mode="Markdown")
    else:
        await msg.edit_text("❌ No data found")

# Command wrappers
async def num(u, c): await osint_command(u, c, "num")
async def ip(u, c): await osint_command(u, c, "ip")
async def insta(u, c): await osint_command(u, c, "insta")
async def tg(u, c): await osint_command(u, c, "tg")
async def gst(u, c): await osint_command(u, c, "gst")
async def ff(u, c): await osint_command(u, c, "ff")

# ================= RENDER PORT SERVER =================
def run_web_server():
    async def health(request):
        return web.Response(text="OK")

    app = web.Application()
    app.router.add_get("/", health)
    web.run_app(app, host="0.0.0.0", port=PORT)

# ================= MAIN =================
def main():
    # Start Render HTTP server in background
    threading.Thread(target=run_web_server, daemon=True).start()
    print(f"🌐 Health server running on port {PORT}")

    # Telegram bot (owns event loop)
    app = ApplicationBuilder().token(BOT_TOKEN).build()

    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("num", num))
    app.add_handler(CommandHandler("ip", ip))
    app.add_handler(CommandHandler("insta", insta))
    app.add_handler(CommandHandler("tg", tg))
    app.add_handler(CommandHandler("gst", gst))
    app.add_handler(CommandHandler("ff", ff))

    print("🤖 OSINT Bot Running (Polling)")
    app.run_polling()

if __name__ == "__main__":
    main()
