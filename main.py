import random
import asyncpg
from aiogram import Bot, Dispatcher, executor, types
import asyncio
import time
import logging
import os

# Enable logging
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)
logger = logging.getLogger(__name__)

# Read database credentials from environment variables
DB_HOST = os.environ.get('DB_HOST')
DB_PORT = os.environ.get('DB_PORT')
DB_USER = os.environ.get('DB_USER')
DB_PASSWORD = os.environ.get('DB_PASSWORD')
DB_NAME = os.environ.get('DB_NAME')

# Read Telegram bot token from environment variable
BOT_TOKEN = os.environ.get('BOT_TOKEN')

# Create a connection pool
async def get_db_connection():
    return await asyncpg.create_pool(
        user=DB_USER,
        password=DB_PASSWORD,
        host=DB_HOST,
        port=DB_PORT,
        database=DB_NAME
    )

# Generate a random ID
def generate_random_id():
    return random.randint(1, 1000000)  # Adjust range as needed

# Initialize bot and dispatcher
bot = Bot(token=BOT_TOKEN)
dp = Dispatcher(bot)

# Function to insert temp_code
async def insert_temp_code(chat_id, email, message):
    connection = await get_db_connection()
    try:
        random_id = generate_random_id()
        query = """
        INSERT INTO temp_code (id, chat_id, email, message) VALUES ($1, $2, $3, $4);
        """
        await connection.execute(query, random_id, chat_id, email, message)
    except asyncpg.PostgresError as err:
        logger.error(f"Database error during insert: {err}")
    finally:
        await connection.close()

# Function to perform the search
async def perform_search(chat_id: int, email: str):
    connection = await get_db_connection()

    try:
        # Query to get the link from the MESSAGE column where EMAIL matches
        query = "SELECT message FROM temp_code WHERE chat_id = $1 AND email = $2"
        result = await connection.fetchval(query, chat_id, email)

        if result:
            return result
        else:
            return None
    except asyncpg.PostgresError as err:
        logger.error(f"Database error: {err}")
        return None
    finally:
        await connection.close()

# Command handler
@dp.message_handler(commands=['start'])
async def start(message: types.Message):
    await message.reply('Hello! Send an email to search for the corresponding link in the database.')

# Text handler
@dp.message_handler(filters.Text & ~filters.Command)
async def search_email(message: types.Message):
    chat_id = message.chat.id
    email = message.text
    link = await perform_search(chat_id, email)
    if link:
        keyboard = types.InlineKeyboardMarkup()
        keyboard.add(types.InlineKeyboardButton("Link", url=link))
        await message.reply("Here is your link:", reply_markup=keyboard)
    else:
        keyboard = types.InlineKeyboardMarkup()
        keyboard.add(types.InlineKeyboardButton("Try Again", callback_data=f"try_again:{email}"))
        await message.reply('No link found for this email.', reply_markup=keyboard)

# Callback handler
@dp.callback_query_handler(lambda c: c.data and c.data.startswith('try_again:'))
async def try_again(callback_query: types.CallbackQuery):
    email = callback_query.data.split(":")[1]
    await perform_search(callback_query.message.chat.id, email)

# Error handler
@dp.errors_handler()
async def error_handler(update, error):
    logger.error(f'Update {update} caused error {error}')

# Start the bot
if __name__ == '__main__':
    executor.start_polling(dp, skip_updates=True)
