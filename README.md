# Lava Stat Checker

A Flask web application to check and compare Hypixel Bedwars player statistics. This application fetches data from the official Hypixel API and uses a web scraper for `bwstats.shivam.pro` as a fallback.

## Features

- View detailed Bedwars stats for a single player.
- Compare Bedwars stats between two players.
- Provides a JSON API for player stats and comparisons.
- Caches scraped data to reduce load times and minimize requests.

## Project Structure

```
.
├── app.py              # Main Flask application
├── hypixel_api.py      # Logic for Hypixel API interaction
├── scrapper.py         # Web scraper for bwstats.shivam.pro
├── config.py           # Configuration for API keys
├── requirements.txt    # Python dependencies
├── templates/          # HTML templates for the web interface
│   ├── index.html
│   ├── stats.html
│   └── compare.html
├── static/             # Static assets (CSS, JS)
│   ├── css/
│   └── js/
├── cache/              # Directory for cached scraper data
└── Procfile            # For deployment on services like Heroku
```

## Setup and Installation

1.  **Clone the repository:**
    ```bash
    git clone https://github.com/your-username/Lava_Stat_Checker.git
    cd Lava_Stat_Checker
    ```

2.  **Create a virtual environment and activate it:**
    ```bash
    python -m venv venv
    # On Windows
    venv\Scripts\activate
    # On macOS/Linux
    source venv/bin/activate
    ```

3.  **Install the required dependencies:**
    ```bash
    pip install -r requirements.txt
    ```

4.  **Create a `.env` file** in the root of the project and add your Hypixel API key:
    ```
    HYPIXEL_API_KEY="your_api_key_here"
    ```

5.  **Run the application:**
    ```bash
    flask run
    ```
    The application will be available at `http://127.0.0.1:5000`.

## API Endpoints

-   **Get Player Stats:**
    -   **URL:** `/api/player/<username>`
    -   **Method:** `GET`
    -   **Success Response:**
        ```json
        {
          "username": "PlayerName",
          "level": 100,
          "overall": { ... },
          "modes": { ... }
        }
        ```
    -   **Error Response:**
        ```json
        {
          "error": "Player not found"
        }
        ```

-   **Compare Player Stats:**
    -   **URL:** `/api/compare?users=<user1>,<user2>`
    -   **Method:** `GET`
    -   **Success Response:**
        ```json
        {
          "user1": { ... stats for user1 ... },
          "user2": { ... stats for user2 ... }
        }
        ```
