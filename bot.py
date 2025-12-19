import os
import json
import requests
import asyncio
from aiohttp import web
from telegram import Update
from telegram.ext import ApplicationBuilder, CommandHandler, ContextTypes

# ================= CONFIG =================
BOT_TOKEN = os.getenv("BOT_TOKEN")
API_KEY = os.getenv("OSINT_API_KEY")
API_ROOT = "https://relay-wzlz.onrender.com"
REQUEST_TIMEOUT = 25
PORT = int(os.getenv("PORT", 10000))  # Render provides this

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
        "🕵️ OSINT Bot Online\n\n"
        "/num <number>\n"
        "/ip <ip>\n"
        "/insta <username>\n"
        "/tg <username>\n"
        "/gst <gst>\n"
        "/ff <id>"
    )

async def osint_command(update, context, token: str):
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
            output.extend(formatted if isinstance(formatted, list) else [formatted])

        await msg.edit_text(f"```\n{chr(10).join(output)[:4000]}\n```", parse_mode="Markdown")
    else:
        await msg.edit_text("❌ No data found")

# ===== COMMAND WRAPPERS =====
async def num(u, c): await osint_command(u, c, "num")
async def ip(u, c): await osint_command(u, c, "ip")
async def insta(u, c): await osint_command(u, c, "insta")
async def tg(u, c): await osint_command(u, c, "tg")
async def gst(u, c): await osint_command(u, c, "gst")
async def ff(u, c): await osint_command(u, c, "ff")

# ================= WEB SERVER (RENDER PORT) =================
async def health(request):
    return web.Response(text="OK")

async def start_web_server():
    app = web.Application()
    app.router.add_get("/", health)

    runner = web.AppRunner(app)
    await runner.setup()
    site = web.TCPSite(runner, "0.0.0.0", PORT)
    await site.start()

    print(f"🌐 Web server running on port {PORT}")

# ================= MAIN =================
async def main():
    await start_web_server()

    bot = ApplicationBuilder().token(BOT_TOKEN).build()
    bot.add_handler(CommandHandler("start", start))
    bot.add_handler(CommandHandler("num", num))
    bot.add_handler(CommandHandler("ip", ip))
    bot.add_handler(CommandHandler("insta", insta))
    bot.add_handler(CommandHandler("tg", tg))
    bot.add_handler(CommandHandler("gst", gst))
    bot.add_handler(CommandHandler("ff", ff))

    print("🤖 OSINT Bot Running (Polling)")
    await bot.run_polling()

if __name__ == "__main__":
    asyncio.run(main())
