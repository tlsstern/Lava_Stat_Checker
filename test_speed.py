import time
import scrapper
import json

# Test single user scraping speed
print("Testing optimized scraper speed...")
print("-" * 50)

# Test with a single user
username = "Technoblade"  # Example username

# Clear cache for fair testing
import os
cache_path = scrapper.get_cache_path()
if os.path.exists(cache_path):
    os.remove(cache_path)
    print("Cache cleared for testing")

# Test new optimized version
start_time = time.time()
result = scrapper.scrape_bwstats(username)
end_time = time.time()

print(f"\nOptimized scraper results for {username}:")
print(f"Time taken: {end_time - start_time:.2f} seconds")
print(f"Data fetched: {'Success' if 'error' not in result else result.get('error')}")
if 'modes' in result:
    print(f"Modes found: {list(result['modes'].keys())}")

# Test batch scraping
print("\n" + "-" * 50)
print("Testing batch scraping (3 users)...")
usernames = ["Technoblade", "Dream", "Hypixel"]

start_time = time.time()
results = scrapper.scrape_multiple_bwstats(usernames)
end_time = time.time()

print(f"Batch scraping results:")
print(f"Time taken for {len(usernames)} users: {end_time - start_time:.2f} seconds")
print(f"Average time per user: {(end_time - start_time) / len(usernames):.2f} seconds")

for username in usernames:
    if username in results:
        result = results[username]
        status = 'Success' if 'error' not in result else f"Error: {result.get('error')}"
        print(f"  - {username}: {status}")

# Cleanup
scrapper.cleanup_drivers()
print("\nDriver pool cleaned up")