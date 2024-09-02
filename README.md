# Weather Telegram Bot

A Python-based Telegram bot that provides users with daily weather updates and 24-hour forecasts. The bot interacts with the OpenWeatherMap API to fetch weather data and sends scheduled updates based on user preferences.

## Features

- **City-based Weather Forecasts**: Set your preferred city and receive a daily weather update at your chosen time.
- **Customizable Update Time**: Users can set the time when they wish to receive their daily weather updates.
- **On-Demand Forecast**: Request a 24-hour weather forecast for any city.
- **Limit on Time Updates**: Prevents abuse by limiting the number of times a user can change the update time in a single day.
- **User-Friendly**: Simple commands to set city, time, and retrieve weather forecasts.

## Commands

- `/start` - Initializes the bot and welcomes you.
- `/setcity` - Set your city for daily weather updates.
- `/settime` - Set the time for daily weather updates.
- `/weather [city name]` - Get the 24-hour weather forecast for any city.
- `/changecity` - Change your default city for daily updates.
- `/help` - Show help information.

## Installation

1. **Clone the Repository:**

   First, clone the repository to your local machine using the following command:

   ```bash
   git clone https://github.com/YourUsername/weather-tg-bot.git
   cd weather-tg-bot
   ```

2. **Install Dependencies:**

   Ensure you have Python 3.x installed on your machine. Then, install the required Python packages using pip:

   ```bash
   pip install -r requirements.txt
   ```

3. **Set Up Environment Variables**

   Create a .env file in the root of the project directory to store your API keys securely. Add your Telegram bot token and OpenWeatherMap API key to this file:

   ```bash
    TG_KEY=your_telegram_bot_token
    OWM_API_KEY=your_openweathermap_api_key
   ```

4. **Run the Bot**
   First, clone the repository to your local machine using the following command:

   ```bash
    python main.py

   ```

## Usage

Once the bot is running, you can interact with it via Telegram using the commands listed above. Set your city and preferred time for daily weather updates, and the bot will handle the rest.

## License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.
