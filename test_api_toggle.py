import os
import hypixel_api
from config import API_KEY

print("=" * 60)
print("Testing API Key Toggle Feature")
print("=" * 60)

# Show current API key status
print(f"\nCurrent API_KEY setting: {API_KEY}")
print("-" * 40)

# Test with a sample username
test_username = "Technoblade"

print(f"\nFetching data for: {test_username}")
result = hypixel_api.fetch_player_data(test_username)

print(f"\nData source: {result.get('fetched_by', 'unknown')}")
if 'error' in result:
    print(f"Error: {result['error']}")
else:
    print("Success! Data retrieved.")
    if 'modes' in result:
        print(f"Found modes: {list(result['modes'].keys())[:3]}...")

print("\n" + "=" * 60)
print("To switch between modes:")
print("1. Set HYPIXEL_API_KEY=off in .env file to use scraper only")
print("2. Set HYPIXEL_API_KEY=your-actual-key to use API")
print("=" * 60)