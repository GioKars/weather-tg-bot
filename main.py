import sqlite3
import requests
import asyncio
import os
from dotenv import load_dotenv
from datetime import datetime, time as dt_time, timedelta
from telegram import Update
from telegram.ext import Application, CommandHandler, ContextTypes, ConversationHandler, MessageHandler, filters

# Load environment variables from the .env file
print("Loading environment variables...")
load_dotenv()

# Access the environment variables
OWM_API_KEY = os.getenv('API_KEY')
TG_KEY = os.getenv('TG_KEY')

print(f"OWM_API_KEY: {OWM_API_KEY}")
print(f"TG_KEY: {TG_KEY}")

# Database setup
print("Setting up database...")
conn = sqlite3.connect('user_data.db', check_same_thread=False)
c = conn.cursor()
c.execute('''
    CREATE TABLE IF NOT EXISTS users (
        user_id INTEGER PRIMARY KEY,
        city TEXT,
        time TEXT DEFAULT '08:00'
    )
''')
c.execute('''
    CREATE TABLE IF NOT EXISTS time_changes (
        user_id INTEGER,
        change_time TEXT,
        PRIMARY KEY (user_id, change_time),
        FOREIGN KEY(user_id) REFERENCES users(user_id)
    )
''')
conn.commit()

# Define states for the conversation handler
CITY = 1
WEATHER = 2
TIME = 3


def weather_icon(description):
    icons = {
        'clear sky': '☀️',
        'few clouds': '🌤️',
        'scattered clouds': '🌥️',
        'broken clouds': '☁️',
        'overcast clouds': '🌥️',
        'shower rain': '🌧️',
        'rain': '🌧️',
        'thunderstorm': '⛈️',
        'snow': '❄️',
        'mist': '🌫️',
        'drizzle': '🌦️',
        'light rain': '🌦️',
        'heavy rain': '🌧️',
        'light snow': '🌨️',
        'heavy snow': '❄️',
        'fog': '🌁'
    }
    # Default to Earth emoji if description not found
    return icons.get(description, '🌍')


def get_24_hour_forecast(city):
    print(f"Fetching 24-hour forecast for city: {city}")
    url = f"http://api.openweathermap.org/data/2.5/forecast?q={city}&appid={OWM_API_KEY}&units=metric"
    response = requests.get(url)
    if response.status_code == 200:
        data = response.json()
        forecast_list = data['list']
        now = datetime.now()
        forecast_24_hours = []

        # Collect data for the next 24 hours
        for forecast in forecast_list:
            forecast_time = datetime.fromtimestamp(forecast['dt'])
            if forecast_time <= now + timedelta(hours=24):
                weather_desc = forecast['weather'][0]['description']
                weather = weather_icon(weather_desc)
                temp = forecast['main']['temp']
                forecast_24_hours.append(
                    f"{forecast_time:%H:%M} - {weather} {weather_desc.capitalize()}: {temp:.1f}°C")
            else:
                break

        if forecast_24_hours:
            formatted_forecast = f"24-Hour Forecast: {datetime.today().strftime('%d-%m-%Y')}\n" + "\n".join(
                forecast_24_hours)

        else:
            formatted_forecast = "No forecast data available for the next 24 hours."

        return formatted_forecast
    else:
        print("City not found!")
        return "City not found!"


# Command to start the bot


async def start(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    user_id = update.message.chat_id
    print(f"User {user_id} started the bot.")
    c.execute("INSERT OR IGNORE INTO users (user_id) VALUES (?)", (user_id,))
    conn.commit()
    await update.message.reply_text('Welcome! Please set your city using /setcity command.')

# Command to set the city for daily weather updates


async def set_city(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    user_id = update.message.chat_id
    print(f"User {user_id} initiated setting city.")
    await update.message.reply_text('Please provide the city name for daily weather updates:')
    return CITY

# Handling the city name provided by the user for setting city


async def handle_city(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    user_id = update.message.chat_id
    city = update.message.text
    if city:
        print(f"Setting city for user {user_id} to {city}.")
        c.execute("UPDATE users SET city = ? WHERE user_id = ?", (city, user_id))
        conn.commit()
        forecast_info = get_24_hour_forecast(city)
        await update.message.reply_text(f'Your city has been set to {city}.\n{forecast_info}')
        return ConversationHandler.END
    else:
        await update.message.reply_text('Please provide a valid city name.')
        return CITY


async def set_time(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    user_id = update.message.chat_id
    await update.message.reply_text('Please provide the time in HH:MM format (24-hour) for daily weather updates:')
    return TIME


async def handle_time(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    user_id = update.message.chat_id
    time_input = update.message.text

    # Check the number of changes in the current day
    now = datetime.now()
    today = now.date()
    change_count = c.execute('''
        SELECT COUNT(*) FROM time_changes
        WHERE user_id = ? AND DATE(change_time) = ?
    ''', (user_id, today)).fetchone()[0]

    # Allow up to 3 changes per day
    if change_count >= 3:
        await update.message.reply_text('You have reached the limit of 3 time changes per day.')
        return ConversationHandler.END

    try:
        # Validate time format
        valid_time = datetime.strptime(time_input, '%H:%M').time()
        c.execute("UPDATE users SET time = ? WHERE user_id = ?",
                  (time_input, user_id))
        conn.commit()

        # Record the time change
        c.execute("INSERT INTO time_changes (user_id, change_time) VALUES (?, ?)",
                  (user_id, now.isoformat()))
        conn.commit()

        await update.message.reply_text(f'Your daily weather update time has been set to {time_input}.')

        # Schedule the next update immediately
        asyncio.create_task(schedule_next_update(user_id, valid_time))

        return ConversationHandler.END
    except ValueError:
        await update.message.reply_text('Invalid time format. Please provide time in HH:MM format.')
        return TIME


# Command to get weather for any city


async def weather(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    city = ' '.join(context.args)
    if city:
        print(f"User requested weather for city: {city}")
        forecast_info = get_24_hour_forecast(city)
        await update.message.reply_text(forecast_info)
        return ConversationHandler.END
    else:
        print(
            f"User {update.message.chat_id} did not provide a city with /weather command.")
        await update.message.reply_text('Please provide the city name to get the weather. You can type it after this command:')
        return WEATHER

# Handling the city name provided by the user for weather command


async def handle_weather(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    city = update.message.text
    if city:
        print(f"User requested weather for city: {city}")
        forecast_info = get_24_hour_forecast(city)
        await update.message.reply_text(forecast_info)
        return ConversationHandler.END
    else:
        await update.message.reply_text('Please provide a valid city name.')
        return WEATHER

# Command to change the city


async def change_city(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    print(f"User {update.message.chat_id} is changing city.")
    await set_city(update, context)

# Command to show help information


async def help_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    print(f"User {update.message.chat_id} requested help.")
    help_text = (
        "/start - Initializes the bot and welcomes you.\n"
        "/setcity - Set your city for daily weather updates (then provide the city name).\n"
        "/weather [city name] - Get the 24-hour weather forecast for any city (or provide the city name after the command).\n"
        "/changecity [city name] - Change your default city for daily updates.\n"
        "/settime - Set the time for daily weather updates (then provide the time in HH:MM format).\n"
        "/help - Show this help message."
    )
    await update.message.reply_text(help_text)

# Async function to send daily weather at 8:00 AM


async def send_daily_weather():
    print("Sending daily weather...")
    users = c.execute(
        "SELECT user_id, city FROM users WHERE city IS NOT NULL").fetchall()
    print(f"Retrieved users from database: {users}")
    for user_id, city in users:
        print(f"Sending weather to user {user_id} for city {city}.")
        forecast_info = get_24_hour_forecast(city)
        await application.bot.send_message(chat_id=user_id, text=forecast_info)

# Function to run the daily weather scheduler


async def schedule_next_update(user_id: int, new_time: datetime.time):
    now = datetime.now()
    user_target_time = datetime.combine(now.date(), new_time)

    if now > user_target_time:
        # Time has passed today, schedule for tomorrow
        user_target_time += timedelta(days=1)

    delay = (user_target_time - now).total_seconds()

    print(f"User {user_id}: Scheduling next update in {delay} seconds.")

    await asyncio.sleep(delay)

    # Fetch updated city and send weather update
    city = c.execute("SELECT city FROM users WHERE user_id = ?",
                     (user_id,)).fetchone()[0]
    forecast_info = get_24_hour_forecast(city)
    await application.bot.send_message(chat_id=user_id, text=forecast_info)

    # Immediately reschedule the next update for the following day
    asyncio.create_task(schedule_next_update(user_id, new_time))


async def daily_weather_scheduler():
    print("Starting daily weather scheduler...")
    while True:
        now = datetime.now()
        print(f"Current time: {now}")

        # Retrieve users with their current scheduling
        users = c.execute(
            "SELECT user_id, time FROM users WHERE city IS NOT NULL AND time IS NOT NULL").fetchall()
        print(f"Retrieved users from database: {users}")

        # Create tasks for all users
        tasks = []
        for user_id, user_time in users:
            valid_time = datetime.strptime(user_time, '%H:%M').time()
            tasks.append(schedule_next_update(user_id, valid_time))

        # Wait for all tasks to complete (they will handle their own scheduling)
        await asyncio.gather(*tasks)

        # Sleep for a short duration before checking again
        await asyncio.sleep(60)


# Main function to handle incoming updates


async def main():
    global application
    print("Building application...")
    application = Application.builder().token(TG_KEY).build()

    # Initialize the application
    print("Initializing application...")
    await application.initialize()

    # Adding command handlers and conversation handler
    print("Adding command handlers...")
    conversation_handler = ConversationHandler(
        entry_points=[
            CommandHandler("setcity", set_city),
            CommandHandler("weather", weather),
            CommandHandler("settime", set_time)  # Entry point for setting time
        ],
        states={
            CITY: [MessageHandler(filters.TEXT & ~filters.COMMAND, handle_city)],
            WEATHER: [MessageHandler(filters.TEXT & ~filters.COMMAND, handle_weather)],
            # Handling the time input
            TIME: [MessageHandler(
                filters.TEXT & ~filters.COMMAND, handle_time)]
        },
        fallbacks=[]
    )
    application.add_handler(conversation_handler)
    application.add_handler(CommandHandler("start", start))
    application.add_handler(CommandHandler("settime", set_time))
    application.add_handler(CommandHandler("changecity", change_city))
    application.add_handler(CommandHandler("help", help_command))

    # Start the bot
    print("Starting bot...")
    await application.start()
    await application.updater.start_polling()

    # Run the daily weather scheduler
    print("Running daily weather scheduler...")
    asyncio.create_task(daily_weather_scheduler())

    # Keep the application running
    print("Bot is running...")
    try:
        while True:
            # Sleep for an hour to keep the bot running
            await asyncio.sleep(3600)
    except KeyboardInterrupt:
        print("Shutting down bot...")

if __name__ == '__main__':
    print("Starting asyncio loop...")
    asyncio.run(main())
