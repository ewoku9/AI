import logging
import openai
import os
from dotenv import load_dotenv
from telegram import Update, constants
from telegram.ext import (
    Application,
    CommandHandler,
    MessageHandler,
    ContextTypes,
    filters,
)

logging.basicConfig(
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s", level=logging.INFO
)
logging.getLogger("httpx").setLevel(logging.WARNING)
logger = logging.getLogger(__name__)


load_dotenv()
TELEGRAM_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")

if not TELEGRAM_TOKEN:
    logger.error("Ошибка: Токен Telegram не найден.")
    exit()
if not OPENAI_API_KEY:
    logger.error("Ошибка: Ключ API OpenAI не найден.")
    exit()

try:
    openai_client = openai.AsyncOpenAI(api_key=OPENAI_API_KEY)
    logger.info("Клиент OpenAI успешно инициализирован.")
except Exception as e:
    logger.error(f"Ошибка при инициализации клиента OpenAI: {e}")
    exit()

user_conversations = {}

# Задача роли ИИ
DEFAULT_SYSTEM_MESSAGE = {"role": "system", "content": "Ты полезный ассистент в компании ИИ Лаборатория. ИИ Лаборатория занимается разработкой ИИ для любых целей. Мы еще начинающая команда, но вскором времени наберем обороты."}

# Функции обработчики Telegram
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Отправляет приветственное сообщение при команде /start."""
    user = update.effective_user
    chat_id = update.effective_chat.id
    logger.info(f"Пользователь {user.first_name} (ID: {user.id}) запустил бота в чате {chat_id}.")

    user_conversations[chat_id] = [DEFAULT_SYSTEM_MESSAGE]

    await update.message.reply_html(
        f"Привет, {user.mention_html()}! 👋\n\n"
        "Я ИИ-ассистент компании ИИ Лаборатория. Просто отправь мне сообщение, и я постараюсь ответить.\n\n"
        "История диалога сохраняется в рамках сессии (до перезапуска бота).\n"
        "Чтобы начать заново, используй команду /reset.",
    )

async def reset(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Сбрасывает историю диалога для пользователя."""
    chat_id = update.effective_chat.id
    user = update.effective_user

    user_conversations[chat_id] = [DEFAULT_SYSTEM_MESSAGE]
    logger.info(f"История диалога для чата {chat_id} (Пользователь: {user.first_name}) сброшена.")
    await update.message.reply_text("История диалога сброшена. Можете начать заново.")

# Настройки GPT и хранение в истории
async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Обрабатывает текстовые сообщения пользователя и отвечает с помощью OpenAI."""
    chat_id = update.effective_chat.id
    user_message_text = update.message.text

    if chat_id not in user_conversations:
        user_conversations[chat_id] = [DEFAULT_SYSTEM_MESSAGE]
        logger.info(f"Инициализирована история для чата {chat_id}")

    user_conversations[chat_id].append({"role": "user", "content": user_message_text})

    logger.info(f"Получено сообщение от чата {chat_id}: '{user_message_text}'")

    await context.bot.send_chat_action(chat_id=chat_id, action=constants.ChatAction.TYPING)

    try:
        response = await openai_client.chat.completions.create(
            model="gpt-3.5-turbo", 
            messages=user_conversations[chat_id],
            #max_tokens=500
        )

        assistant_response = response.choices[0].message.content

        user_conversations[chat_id].append({"role": "assistant", "content": assistant_response})

        logger.info(f"Ответ от OpenAI для чата {chat_id}: '{assistant_response[:50]}...'") 

        await update.message.reply_text(assistant_response)
# Ошибки
    except openai.RateLimitError:
        logger.warning(f"Превышен лимит запросов OpenAI для чата {chat_id}")
        await update.message.reply_text("Извините, сейчас слишком много запросов к OpenAI. Попробуйте чуть позже.")
        user_conversations[chat_id].pop()
    except openai.AuthenticationError:
         logger.error("Ошибка аутентификации OpenAI. Проверьте API ключ.")
         await update.message.reply_text("Произошла ошибка с подключением к сервису ИИ (Auth). Пожалуйста, сообщите администратору.")
         user_conversations[chat_id].pop() #
    except openai.APIError as e:
        logger.error(f"Ошибка API OpenAI для чата {chat_id}: {e}")
        await update.message.reply_text("Извините, произошла ошибка при обращении к OpenAI. Попробуйте еще раз.")
        user_conversations[chat_id].pop()
    except Exception as e:
        logger.error(f"Непредвиденная ошибка при обработке сообщения для чата {chat_id}: {e}", exc_info=True)
        await update.message.reply_text("Произошла внутренняя ошибка. Попробуйте позже.")
        user_conversations[chat_id].pop() 

    MAX_HISTORY_LEN = 11 
    if len(user_conversations[chat_id]) > MAX_HISTORY_LEN:
         user_conversations[chat_id] = [user_conversations[chat_id][0]] + user_conversations[chat_id][-(MAX_HISTORY_LEN - 1):]
         logger.info(f"История для чата {chat_id} была обрезана до {MAX_HISTORY_LEN} сообщений.")


def main() -> None:
    """Запускает бота."""
    logger.info("Запуск бота...")

    application = Application.builder().token(TELEGRAM_TOKEN).build()

    application.add_handler(CommandHandler("start", start))
    application.add_handler(CommandHandler("reset", reset))

    application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))

    logger.info("Бот запущен и готов принимать сообщения.")
    application.run_polling(allowed_updates=Update.ALL_TYPES)

if __name__ == "__main__":
    main()