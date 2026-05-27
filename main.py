import os
import logging
import config
from telegram import Update
from telegram.ext import (
    Application,
    CommandHandler,
    MessageHandler,
    filters,
    ContextTypes
)
from core.agent import ZAIAgent

logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)
logger = logging.getLogger(__name__)

agent = ZAIAgent()


async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    if user_id != config.OWNER_TELEGRAM_ID:
        await update.message.reply_text("عذراً، ليس لديك صلاحية استخدام هذا البوت.")
        return

    await update.message.reply_text(
        f"مرحباً! أنا {config.AGENT_NAME}\n\n"
        f"مساعدك الذكي الشخصي.\n\n"
        f"ما أستطيع فعله:\n"
        f"- البحث في الإنترنت\n"
        f"- البحث في يوتيوب\n"
        f"- البحث في غيت هوب\n"
        f"- آخر الأخبار\n"
        f"- تصفح المواقع بأمان\n"
        f"- حماية من الروابط المشبوهة\n"
        f"- تحويل الصوت لنص\n\n"
        f"اكتب \"مساعد\" لعرض الأوامر\n"
        f"أو تحدث معي بشكل طبيعي!"
    )


async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    if user_id != config.OWNER_TELEGRAM_ID:
        return

    user_message = update.message.text
    if not user_message:
        return

    processing = await update.message.reply_text("أفكر...")

    try:
        response = agent.process_message(user_message)

        if len(response) > 4096:
            await processing.edit_text(response[:4096])
            remaining = response[4096:]
            while remaining:
                await update.message.reply_text(remaining[:4096])
                remaining = remaining[4096:]
        else:
            await processing.edit_text(response)

    except Exception as e:
        logger.error(f"Error: {e}")
        await processing.edit_text(f"حدث خطأ: {str(e)}")


async def voice_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    if user_id != config.OWNER_TELEGRAM_ID:
        return

    try:
        voice = update.message.voice or update.message.audio
        if not voice:
            return

        processing = await update.message.reply_text("أحول صوتك لنص...")

        voice_file = await voice.get_file()

        import tempfile

        with tempfile.NamedTemporaryFile(delete=False, suffix='.ogg') as f:
            await voice_file.download_to_drive(f.name)
            temp_path = f.name

        try:
            from groq import Groq
            client = Groq(api_key=config.GROQ_API_KEY)

            with open(temp_path, 'rb') as audio_file:
                transcription = client.audio.transcriptions.create(
                    model="whisper-large-v3",
                    file=audio_file,
                    language="ar",
                    response_format="text"
                )

            text = transcription.strip()
            if not text:
                await processing.edit_text("لم أتمكن من فهم الصوت. حاول مرة أخرى.")
                return

            await processing.edit_text(f"قلت: \"{text}\"\n\nأفكر...")

            reply = agent.process_message(text)

            if len(reply) > 4096:
                await processing.edit_text(reply[:4096])
                remaining = reply[4096:]
                while remaining:
                    await update.message.reply_text(remaining[:4096])
                    remaining = remaining[4096:]
            else:
                await processing.edit_text(f"قلت: \"{text}\"\n\n{reply}")

        finally:
            if os.path.exists(temp_path):
                os.remove(temp_path)

    except Exception as e:
        logger.error(f"Voice error: {e}")
        try:
            await processing.edit_text("حدث خطأ في معالجة الصوت.")
        except Exception:
            pass


def main():
    print(f"{config.AGENT_NAME} يبدأ العمل...")
    print(f"النموذج: {config.MODEL_NAME}")
    print(f"درع الحماية: نشط")
    print(f"المالك: {config.OWNER_TELEGRAM_ID}")

    app = Application.builder().token(config.TELEGRAM_BOT_TOKEN).build()

    app.add_handler(CommandHandler("start", start))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))
    app.add_handler(MessageHandler(filters.VOICE | filters.AUDIO, voice_handler))

    print("البوت يعمل!")
    app.run_polling(allowed_updates=Update.ALL_TYPES)


if __name__ == '__main__':
    main()
