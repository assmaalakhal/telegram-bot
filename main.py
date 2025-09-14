from telegram.ext import Application, CommandHandler
import os

TOKEN = os.getenv("8215699455:AAHinn40aXh2M4BhSfyxZ_AbOzy_nXrjLP0")  # التوكن يجي من Render

async def start(update, context):
    await update.message.reply_text("مرحبا! البوت شغال 🎉")

def main():
    app = Application.builder().token(TOKEN).build()
    app.add_handler(CommandHandler("start", start))
    app.run_polling()

if __name__ == "__main__":
    main()
