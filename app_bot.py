import os
import sys
import asyncio
import logging
from dotenv import load_dotenv
from datetime import datetime
from aiogram import Bot, Dispatcher, html, F
from aiogram.client.default import DefaultBotProperties
from aiogram.enums import ParseMode
from aiogram.filters import CommandStart
from aiogram.types import Message, ReplyKeyboardMarkup, KeyboardButton, FSInputFile
from controllers.detector_manager import DetectorManager


load_dotenv()
TOKEN = os.getenv("BOT_TOKEN")

dp = Dispatcher()
detector_status = False  # Флаг состояния детектора: True — запущен, False — остановлен
user_settings = {}
video_file_cache = []

detector = DetectorManager(model_mode="classic", yolo_model_path="yolo11x.pt", source=0)

main_keyboard = ReplyKeyboardMarkup(
    keyboard=[
        [KeyboardButton(text="🚀 Старт")],
        [KeyboardButton(text="🛑 Стоп")],
        [KeyboardButton(text="⚙️ Настройки")],
        [KeyboardButton(text="📜 Журнал")]
    ],
    resize_keyboard=True
)

settings_keyboard = ReplyKeyboardMarkup(
    keyboard=[
        [KeyboardButton(text="📦 YOLO-модель")],
        [KeyboardButton(text="🧠 Классический алгоритм")],
        [KeyboardButton(text="🧹 Очистить журнал")],
        [KeyboardButton(text="🔙 Назад")]
    ],
    resize_keyboard=True
)


@dp.message(CommandStart())
async def command_start_handler(message: Message) -> None:
    await message.answer(
        f"Привет, {html.bold(message.from_user.full_name)}!\nВыбери действие:",
        reply_markup=main_keyboard
    )


@dp.message(F.text == "🚀 Старт")
async def handle_start(message: Message):
    global detector_status

    selected_model = user_settings.get(message.chat.id)
    if selected_model is None:
        await message.answer("⚠️ Сначала выберите модель в настройках.")
        return

    detector.set_model_mode('yolo' if selected_model == "YOLO" else 'classic')
    detector.set_notification_target(bot=message.bot, chat_id=message.chat.id)
    detector.start()

    detector_status = True
    await message.answer("Детектор запущен.")



@dp.message(F.text == "🛑 Стоп")
async def handle_stop(message: Message):
    global detector_status
    detector_status = False
    detector.stop()
    await message.answer("Детектор остановлен.")


@dp.message(F.text == "⚙️ Настройки")
async def handle_settings(message: Message):
    status_text = "🟢 <b>Сервис запущен</b>" if detector_status else "🔴 <b>Сервис остановлен</b>"
    current_model = user_settings.get(message.chat.id, "не выбрана")
    await message.answer(
        f"{status_text}\nМодель: <b>{current_model}</b>\n\nВыберите модель детектирования:",
        reply_markup=settings_keyboard
    )


@dp.message(F.text == "📦 YOLO-модель")
async def handle_yolo_choice(message: Message):
    user_settings[message.chat.id] = "YOLO"
    detector.set_model_mode('yolo')
    await message.answer("Вы выбрали модель: YOLO ✅")



@dp.message(F.text == "🧠 Классический алгоритм")
async def handle_classic_choice(message: Message):
    user_settings[message.chat.id] = "classic"
    detector.set_model_mode('classic')
    await message.answer("Вы выбрали классический алгоритм ✅")


@dp.message(F.text == "🔙 Назад")
async def handle_back(message: Message):
    await message.answer("Возврат в главное меню:", reply_markup=main_keyboard)


@dp.message(F.text == "🧹 Очистить журнал")
async def handle_clear_history(message: Message):
    deleted = 0

    if os.path.exists("videos"):
        for fname in os.listdir("videos"):
            try:
                os.remove(os.path.join("videos", fname))
                deleted += 1
            except Exception:
                pass

    if os.path.exists("log.txt"):
        try:
            os.remove("log.txt")
        except Exception:
            pass

    await message.answer(f"🧹 История очищена. Удалено видеофайлов: {deleted}")


def extract_timestamp(fname):
    try:
        timestamp_str = fname.split("_", 2)[:2]
        return datetime.strptime("_".join(timestamp_str), "%Y-%m-%d_%H-%M-%S")
    except Exception:
        return datetime.min

@dp.message(F.text == "📜 Журнал")
async def handle_log(message: Message):
    global video_file_cache

    if not os.path.exists("videos"):
        await message.answer("Журнал пока пуст.")
        return

    files = sorted(os.listdir("videos"), key=extract_timestamp, reverse=False)
    if not files:
        await message.answer("Журнал пока пуст.")
        return

    video_file_cache = files[:10]

    text = "📼 <b>Список событий:</b>\n\n"
    for i, fname in enumerate(video_file_cache):
        text += f"{i+1}. {fname}\n"

    text += "\nНапиши номер, чтобы получить видео (1–10)."
    await message.answer(text, parse_mode="HTML")


@dp.message()
async def send_video_by_index(msg: Message):
    global video_file_cache

    if msg.text.isdigit():
        idx = int(msg.text)
        if 1 <= idx <= len(video_file_cache):
            fname = video_file_cache[idx - 1]
            path = os.path.join("videos", fname)
            if os.path.exists(path):
                await msg.answer_video(FSInputFile(path), caption=f"🎥 {fname}")
            else:
                await msg.answer("⚠️ Файл не найден.")



async def main() -> None:
    bot = Bot(token=TOKEN, default=DefaultBotProperties(parse_mode=ParseMode.HTML))
    await dp.start_polling(bot)


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO, stream=sys.stdout)
    asyncio.run(main())
