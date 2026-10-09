import os
import asyncio
import subprocess
import tempfile
from pathlib import Path
from PIL import Image, ImageOps
from telegram import Update
from telegram.ext import (
    Application,
    CommandHandler,
    MessageHandler,
    ContextTypes,
    filters,
)
TOKEN = os.environ["BOT_TOKEN"]
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        "👋 Привет!\n\n"
        "Отправь мне фотографию, и я сделаю из неё:\n"
        "🖼 Обычный эмодзи\n"
        "🎬 Анимированный эмодзи\n\n"
        "Просто отправь фото!"
    )
def make_emoji(source: str, folder: str):
    image = Image.open(source)
    image = ImageOps.exif_transpose(image).convert("RGBA")
    # Квадратная обрезка по центру
    image = ImageOps.fit(
        image,
        (100, 100),
        method=Image.Resampling.LANCZOS,
        centering=(0.5, 0.5),
    )
    webp_path = os.path.join(folder, "emoji.webp")
    image.save(webp_path, "WEBP", lossless=False, quality=90)
    webm_path = os.path.join(folder, "emoji.webm")
    # Анимация приближения и отдаления
    command = [
        "ffmpeg", "-y",
        "-loglevel", "error",
        "-loop", "1",
        "-i", source,
        "-vf",
        (
            "scale=120:120:force_original_aspect_ratio=increase,"
            "crop=120:120,"
            "zoompan=z='1+0.08*sin(2*PI*on/72)':"
            "x='iw/2-(iw/zoom/2)':"
            "y='ih/2-(ih/zoom/2)':"
            "d=72:s=100x100:fps=30,"
            "format=yuv420p"
        ),
        "-t", "2.4",
        "-an",
        "-c:v", "libvpx-vp9",
        "-b:v", "400k",
        "-deadline", "good",
        "-cpu-used", "5",
        "-fs", "250000",
        webm_path,
    ]
    subprocess.run(command, check=True, timeout=60)
    return webp_path, webm_path
async def handle_photo(
    update: Update,
    context: ContextTypes.DEFAULT_TYPE,
):
    message = update.message
    if not message or not message.photo:
        return
    status = await message.reply_text(
        "⏳ Обрабатываю фотографию..."
    )
    try:
        with tempfile.TemporaryDirectory() as folder:
            source = os.path.join(folder, "photo.jpg")
            telegram_file = await context.bot.get_file(
                message.photo[-1].file_id
            )
            await telegram_file.download_to_drive(source)
            # FFmpeg/Pillow обрабатывают файлы отдельно
            webp_path, webm_path = await asyncio.to_thread(
                make_emoji, source, folder
            )
            await status.edit_text("🖼 Обычный эмодзи:")
            with open(webp_path, "rb") as file:
                await message.reply_document(
                    document=file,
                    filename="emoji.webp",
                    caption="🖼 Статичный вариант",
                )
            with open(webm_path, "rb") as file:
                await message.reply_document(
                    document=file,
                    filename="emoji.webm",
                    caption="🎬 Анимированный вариант",
                )
            await message.reply_text(
                "✅ Готово!\n\n"
                "Файлы созданы. Чтобы использовать их "
                "как настоящие Telegram custom emoji, "
                "добавь их в набор эмодзи."
            )
            await status.delete()
    except Exception:
        await status.edit_text(
            "❌ Не получилось обработать фото.\n"
            "Попробуй другое изображение."
        )
def main():
    app = Application.builder().token(TOKEN).build()
    app.add_handler(CommandHandler("start", start))
    app.add_handler(
        MessageHandler(filters.PHOTO, handle_photo)
    )
    print("Бот запущен!")
    app.run_polling()
if __name__ == "__main__":
    main()
