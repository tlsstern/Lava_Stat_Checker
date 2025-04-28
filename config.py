import os
from dotenv import load_dotenv

load_dotenv()

API_KEY = os.getenv("HYPIXEL_API_KEY")

if not API_KEY:
    raise ValueError("Kein HYPIXEL_API_KEY in der .env Datei gefunden!")
