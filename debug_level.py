import scrapper
import app
import sys

def debug_level():
    username = "Technoblade" if len(sys.argv) < 2 else sys.argv[1]
    print(f"Debugging level extraction for: {username}")
    
    # Step 1: Get raw data from scraper
    scraped_data = scrapper.scrape_bwstats(username)
    print("\nRaw Level from scraper:", repr(scraped_data.get('level')))
    
    # Step 2: Apply the transformation
    transformed_data = app.transform_scraped_data(scraped_data, username)
    print("Level after transform:", repr(transformed_data.get('level')))
    
    # Step 3: Check if level is being properly parsed in clean_and_convert
    if scraped_data.get('level'):
        raw_level = scraped_data.get('level')
        cleaned_level = app.clean_and_convert(raw_level, int)
        print(f"Manual clean_and_convert of '{raw_level}' resulted in: {cleaned_level}")
    
    # Step 4: Try a test with a comma-separated number
    test_with_comma = "1,234✫"
    cleaned_test = app.clean_and_convert(test_with_comma, int)
    print(f"Test with '{test_with_comma}' results in: {cleaned_test}")
    
    # Additional check - what would happen with our scraper fix
    if scraped_data.get('level'):
        raw_level = scraped_data.get('level')
        manually_cleaned = raw_level.replace('✫', '').replace(',', '').strip()
        print(f"Manually cleaning '{raw_level}' with replace: '{manually_cleaned}'")
        try:
            as_int = int(manually_cleaned)
            print(f"Converting to int: {as_int}")
        except ValueError as e:
            print(f"Error converting to int: {e}")

if __name__ == "__main__":
    debug_level() 