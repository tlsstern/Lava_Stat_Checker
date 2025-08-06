import os
from dotenv import load_dotenv

load_dotenv()

API_KEY = os.getenv("HYPIXEL_API_KEY", "off")

# If API_KEY is not set, default to "off" mode (scraper only)
if not API_KEY:
    API_KEY = "off"
    print("No HYPIXEL_API_KEY found, using scraper-only mode")
elif API_KEY.lower() == "off":
    print("HYPIXEL_API_KEY set to 'off', using scraper-only mode")
else:
    print(f"Using Hypixel API with key: {API_KEY[:8]}...")
