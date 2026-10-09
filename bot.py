TOKEN = os.environ.get("BOT_TOKEN")
if not TOKEN: raise RuntimeError( "Не задан BOT_TOKEN. Добавь его в Railway → Variables." )
async def start( update: Update, context: ContextTypes.DEFAULT_TYPE, ): if update.message: await update.message.reply_text( "👋 Привет!Отправь мне фотографию\n\n" "Я подготовлю обычный WEBP и анимированный WEBM " "варианты изображения." )
def make_emoji(source: str, folder: str): # Открываем изображение и учитываем поворот фотографии. with Image.open(source) as original: image = ImageOps.exif_transpose(original).convert("RGBA")
# Обрезаем изображение по центру до квадратного формата.
image = ImageOps.fit(
    image,
    (100, 100),
    method=Image.Resampling.LANCZOS,
    centering=(0.5, 0.5),
)

webp_path = os.path.join(folder, "emoji.webp")
png_path = os.path.join(folder, "emoji.png")
webm_path = os.path.join(folder, "emoji.webm")

# Обычная версия.
image.save(
    webp_path,
    "WEBP",
    quality=90,
    method=6,
)

# Исходник для анимации.
image.save(png_path, "PNG")

# Плавное приближение и отдаление изображения.
command = [
    "ffmpeg",
    "-y",
    "-hide_banner",
    "-loglevel", "error",
    "-loop", "1",
    "-framerate", "30",
    "-i", png_path,
    "-vf",
    (
        "scale=200:200,"
        "zoompan="
        "z='1+0.06*(1-cos(2*PI*on/72))/2':"
        "x='iw/2-(iw/zoom/2)':"
        "y='ih/2-(ih/zoom/2)':"
        "d=1:s=100x100:fps=30,"
        "format=yuv420p"
    ),
    "-t", "2.4",
    "-an",
    "-c:v", "libvpx-vp9",
    "-b:v", "150k",
    "-deadline", "realtime",
    "-cpu-used", "5",
    webm_path,
]

subprocess.run(
    command,
    check=True,
    timeout=60,
    capture_output=True,
    text=True,
)

# Ограничиваем размер анимированного файла.
if os.path.getsize(webm_path) > 256_000:
    raise ValueError(
        "Анимация слишком большая. Попробуй другое фото."
    )

return webp_path, webm_path
async def handle_photo( update: Update, context: ContextTypes.DEFAULT_TYPE, ): message = update.message
if not message or not message.photo:
    return

status = await message.reply_text(
    "⏳ Обрабатываю фото, подожди немного..."
)

try:
    with tempfile.TemporaryDirectory() as folder:
        source = os.path.join(folder, "photo.jpg")

        # Загружаем фотографию из Telegram.
        telegram_file = await context.bot.get_file(
            message.photo[-1].file_id
        )
        await telegram_file.download_to_drive(source)

        # Обработка изображения не блокирует цикл бота.
        webp_path, webm_path = await asyncio.to_thread(
            make_emoji,
            source,
            folder,
        )

        # Отправляем обычную версию.
        with open(webp_path, "rb") as file:
            await message.reply_document(
                document=file,
                filename="emoji.webp",
                caption="🖼 Обычный вариант (WEBP)",
            )

        # Отправляем анимированную версию.
        import os import asyncio import subprocess import tempfile
from PIL import Image, ImageOps from telegram import Update from telegram.ext import ( Application, CommandHandler, MessageHandler, ContextTypes, filters, )
TOKEN = os.environ.get("BOT_TOKEN")
if not TOKEN: raise RuntimeError("Добавь BOT_TOKEN в Railway → Variables")
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE): await update.message.reply_text( "👋 Отправь мне фото, GIF или видео.\n" "Я подготовлю анимированный WEBM-файл.\n\n" "Важно: Telegram может предъявлять отдельные требования " "к эмодзи и видеоаватару." )
def convert_to_webm(input_path: str, output_path: str): # Квадратное видео 100×100, 30 кадров/с, до 3 секунд. # Для фото создаётся лёгкое приближение. is_image = input_path.lower().endswith( (".jpg", ".jpeg", ".png", ".webp") )
if is_image:

    with Image.open(input_path) as im:
        im = ImageOps.exif_transpose(im).convert("RGB")
        im = ImageOps.fit(im, (200, 200))
        still_path = input_path + ".jpg"
        im.save(still_path, "JPEG", quality=90)

    source = still_path
    video_filter = (
        "zoompan="
        "z='min(zoom+0.0008,1.08)':"
        "x='iw/2-(iw/zoom/2)':"
        "y='ih/2-(ih/zoom/2)':"
        "d=90:s=100x100:fps=30,"
        "format=yuv420p"
    )
    input_args = [
        "-loop", "1", "-framerate", "30", "-i", source
    ]
else:
    video_filter = (
        "scale=100:100:force_original_aspect_ratio=increase,"
        "crop=100:100,"
        "fps=30,format=yuv420p"
    )
    input_args = ["-i", input_path]

command = [
    "ffmpeg", "-y", "-hide_banner", "-loglevel", "error",
    *input_args,
    "-vf", video_filter,
    "-t", "3",
    "-an",
    "-c:v", "libvpx-vp9",
    "-b:v", "180k",
    "-deadline", "realtime",
    "-cpu-used", "5",
    "-loop", "0",
    output_path,
]

subprocess.run(command, check=True, timeout=90)

if os.path.getsize(output_path) > 256_000:
    raise ValueError(
        "Файл больше 256 КБ. Попробуй более короткую GIF или видео."
    )
async def process_media( update: Update, context: ContextTypes.DEFAULT_TYPE, ): message = update.message if not message: return
media = None
suffix = ".bin"

if message.photo:
    media = message.photo[-1]
    suffix = ".jpg"
elif message.animation:
    media = message.animation
    suffix = ".gif"
elif message.video:
    media = message.video
    suffix = ".mp4"
elif message.document:
    doc = message.document
    mime = doc.mime_type or ""
    name = (doc.file_name or "").lower()

    if mime == "image/gif" or name.endswith(".gif"):
        media, suffix = doc, ".gif"
    elif mime.startswith("video/") or name.endswith(
        (".mp4", ".mov", ".webm")
    ):
        media, suffix = doc, ".mp4"
    elif mime.startswith("image/") or name.endswith(
        (".jpg", ".jpeg", ".png", ".webp")
    ):
        media, suffix = doc, ".jpg"

if not media:
    await message.reply_text(
        "Отправь фото, GIF или видеофайл."
    )
    return

status = await message.reply_text("⏳ Создаю анимацию...")

try:
    with tempfile.TemporaryDirectory() as folder:
        source = os.path.join(folder, "input" + suffix)
        output = os.path.join(folder, "animated.webm")

        tg_file = await context.bot.get_file(media.file_id)
        await tg_file.download_to_drive(source)

        await asyncio.to_thread(
            convert_to_webm, source, output
        )

        with open(output, "rb") as f:
            await message.reply_document(
                document=f,
                filename="animated_emoji.webm",
                caption=(
                    "🎞 Готово! Это анимированный WEBM-файл. "
                    "Для установки в профиль или набор эмодзи "
                    "может понадобиться дополнительная конвертация."
                ),
            )

    await status.edit_text("✅ Обработка завершена!")

except Exception as e:
    print("Conversion error:", repr(e))
    await status.edit_text(
        "❌ Не удалось преобразовать файл. "
        "Попробуй другую GIF или видео короче 3 секунд."
    )

    

    source = still_path
    video_filter = (
        "zoompan="
        "z='min(zoom+0.0008,1.08)':"
        "x='iw/2-(iw/zoom/2)':"
        "y='ih/2-(ih/zoom/2)':"
        "d=90:s=100x100:fps=30,"
        "format=yuv420p"
    )
    input_args = [
        "-loop", "1", "-framerate", "30", "-i", source
    ]
else:
    video_filter = (
        "scale=100:100:force_original_aspect_ratio=increase,"
        "crop=100:100,"
        "fps=30,format=yuv420p"
    )
    input_args = ["-i", input_path]

command = [
    "ffmpeg", "-y", "-hide_banner", "-loglevel", "error",
    *input_args,
    "-vf", video_filter,
    "-t", "3",
    "-an",
    "-c:v", "libvpx-vp9",
    "-b:v", "180k",
    "-deadline", "realtime",
    "-cpu-used", "5",
    "-loop", "0",
    output_path,
]

subprocess.run(command, check=True, timeout=90)

if os.path.getsize(output_path) > 256_000:
    raise ValueError(
        "Файл больше 256 КБ. Попробуй более короткую GIF или видео."
    )
async def process_media( update: Update, context: ContextTypes.DEFAULT_TYPE, ): message = update.message if not message: return
media = None
suffix = ".bin"

if message.photo:
    media = message.photo[-1]
    suffix = ".jpg"
elif message.animation:
    media = message.animation
    suffix = ".gif"
elif message.video:
    media = message.video
    suffix = ".mp4"
elif message.document:
    doc = message.document
    mime = doc.mime_type or ""
    name = (doc.file_name or "").lower()

    if mime == "image/gif" or name.endswith(".gif"):
        media, suffix = doc, ".gif"
    elif mime.startswith("video/") or name.endswith(
        (".mp4", ".mov", ".webm")
    ):
        media, suffix = doc, ".mp4"
    elif mime.startswith("image/") or name.endswith(
        (".jpg", ".jpeg", ".png", ".webp")
    ):
        media, suffix = doc, ".jpg"

if not media:
    await message.reply_text(
        "Отправь фото, GIF или видеофайл."
    )
    return

status = await message.reply_text("⏳ Создаю анимацию...")

try:
    with tempfile.TemporaryDirectory() as folder:
        source = os.path.join(folder, "input" + suffix)
        output = os.path.join(folder, "animated.webm")

        tg_file = await context.bot.get_file(media.file_id)
        await tg_file.download_to_drive(source)

        await asyncio.to_thread(
            convert_to_webm, source, output
        )

        with open(output, "rb") as f:
            await message.reply_document(
                document=f,
                filename="animated_emoji.webm",
                caption=(
                    "🎞 Готово! Это анимированный WEBM-файл. "
                    "Для установки в профиль или набор эмодзи "
                    "может понадобиться дополнительная конвертация."
                ),
            )

    await status.edit_text("✅ Обработка завершена!")

except Exception as e:
    print("Conversion error:", repr(e))
    await status.edit_text(
        "❌ Не удалось преобразовать файл. "
        "Попробуй другую GIF или видео короче 3 секунд."
    )
 open(webm_path, "rb") as file:
            await message.reply_document(
                document=file,
                filename="emoji.webm",
                caption="🎬 Анимированный вариант (WEBM)",
            )

    await status.edit_text(
        "✅ Готово! Оба файла отправлены.\n\n"
        "Их можно использовать как исходники для набора "
        "эмодзи в Telegram. Автоматическое добавление "
        "в набор пока не настроено."
    )

except subprocess.TimeoutExpired:
    await status.edit_text(
        "⌛ Обработка заняла слишком много времени. "
        "Попробуй отправить другое фото."
    )

except Exception as error:
    print(f"Ошибка обработки: {error!r}")
    await status.edit_text(
        "❌ Не удалось обработать фото. "
        "Попробуй другое изображение."
    )
async def help_command( update: Update, context: ContextTypes.DEFAULT_TYPE, ): if update.message: await update.message.reply_text( "Отправь фотографию как обычное фото в чат. " "Я верну WEBP и WEBM файлы." )
def main(): app = Application.builder().token(TOKEN).build()
app.add_handler(CommandHandler("start", start))
app.add_handler(CommandHandler("help", help_command))
app.add_handler(
    MessageHandler(filters.PHOTO, handle_photo)
)

print("Бот запущен и ожидает фотографии.")
app.run_polling()
if name == "main": main()
