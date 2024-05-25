import os
import psycopg2
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import Application, CommandHandler, MessageHandler, CallbackQueryHandler, filters, CallbackContext
import asyncio
import time
import logging

# Enable logging
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)
logger = logging.getLogger(__name__)

# Retrieve database credentials from environment variables
DB_HOST = os.environ.get('DB_HOST')
DB_PORT = os.environ.get('DB_PORT')
DB_USER = os.environ.get('DB_USER')
DB_PASSWORD = os.environ.get('DB_PASSWORD')
DB_NAME = os.environ.get('DB_NAME')

# Telegram bot token from environment variable
BOT_TOKEN = os.environ.get('BOT_TOKEN')

# Function to connect to the database
def get_db_connection():
    connection = psycopg2.connect(
        host=DB_HOST,
        port=DB_PORT,
        user=DB_USER,
        password=DB_PASSWORD,
        database=DB_NAME
    )
    return connection

# Function to handle the /start command
async def start(update: Update, context: CallbackContext):
    await update.message.reply_text('Hello! Send an email to search for the corresponding link in the database.')

# Function to perform the search
async def perform_search(context: CallbackContext, chat_id: int, email: str, message_id: int = None):
    connection = get_db_connection()
    cursor = connection.cursor()

    try:
        # Send a loading message if not provided
        if message_id is None:
            loading_message = await context.bot.send_message(chat_id=chat_id, text="Searching for the link...")
        else:
            loading_message = await context.bot.edit_message_text(chat_id=chat_id, message_id=message_id, text="Searching for the link...")

        link_found = False  # Flag to track if the link has been found
        start_time = time.time()  # Get the current time

        # Real-time search until the link is found or 15second has passed
        while not link_found:
            # Check if 1 minute has passed
            if time.time() - start_time > 15:
                break

            # Query to get the link from the MESSAGE column where EMAIL matches
            query = "SELECT MESSAGE FROM temp_code WHERE EMAIL = %s"
            cursor.execute(query, (email,))
            result = cursor.fetchone()

            if result:
                link = result[0]
                keyboard = [[InlineKeyboardButton("Link", url=link)]]
                reply_markup = InlineKeyboardMarkup(keyboard)
                await loading_message.delete()  # Delete the loading message
                await context.bot.send_message(chat_id=chat_id, text="Here is your link:", reply_markup=reply_markup)
                
                # Delete the row after retrieving the link
                delete_query = "DELETE FROM temp_code WHERE EMAIL = %s"
                cursor.execute(delete_query, (email,))
                connection.commit()
                link_found = True  # Set flag to True when link is found
            else:
                # Wait for a short period before the next query
                await asyncio.sleep(1)

        if not link_found:
            await loading_message.delete()  # Delete the loading message
            keyboard = [[InlineKeyboardButton("Try Again", callback_data=f"try_again:{email}")]]
            reply_markup = InlineKeyboardMarkup(keyboard)
            await context.bot.send_message(chat_id=chat_id, text='No link found for this email.', reply_markup=reply_markup)
    except psycopg2.Error as err:
        logger.error(f"Database error: {err}")
        await context.bot.send_message(chat_id=chat_id, text=f"Error: {err}")
    finally:
        cursor.close()
        connection.close()

# Function to handle user messages (email searches)
async def search_email(update: Update, context: CallbackContext):
    email = update.message.text
    await perform_search(context, update.message.chat_id, email)

# Function to handle try again button clicks
async def try_again(update: Update, context: CallbackContext):
    query = update.callback_query
    await query.answer()
    email = query.data.split(":")[1]
    await perform_search(context, query.message.chat_id, email, query.message.message_id)

def main():
    application = Application.builder().token(BOT_TOKEN).read_timeout(20).write_timeout(20).connect_timeout(10).pool_timeout(10).build()

    application.add_handler(CommandHandler('start', start))
    application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, search_email))
    application.add_handler(CallbackQueryHandler(try_again, pattern=r"try_again:"))

    logger.info("Starting bot")
    application.run_polling(workers=10)  # Increase concurrency by setting the number of worker threads

if __name__ == '__main__':
    main()
