import requests
from bs4 import BeautifulSoup
import re

def scrape_bwstats(user: str) -> dict:
    url = f"https://bwstats.shivam.pro/user/{user}"
    headers = {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'
    }
    scraped_data = {
        'username': user,
        'level': None,
        'coins': None,
        'fkdr_summary': None,
        'bblr_summary': None,
        'main_stats': None,
        'other_modes_stats': None,
        'completed_challenges': None,
        'summary_text': None,
        'last_updated': None,
        'error': None
    }

    try:
        response = requests.get(url, headers=headers, timeout=10)
        response.raise_for_status()

    except requests.exceptions.RequestException as e:
        scraped_data['error'] = f"Network or HTTP error: {e}"
        return scraped_data
    except Exception as e:
        scraped_data['error'] = f"An unexpected error occurred during request: {e}"
        return scraped_data

    try:
        soup = BeautifulSoup(response.text, 'html.parser')

        main_content_div = soup.find('div', style="width:100%;flex:6")
        if not main_content_div:
            main_container = soup.find('div', class_='stats-container')
            if main_container:
                main_content_div = main_container.find('div', style=lambda s: s and 'width:100%' in s)
            if not main_content_div:
                scraped_data['error'] = "Could not find the main content div. Page structure might have changed."
                title_tag = soup.find('title')
                if title_tag and "'s Bedwars Stats" in title_tag.text:
                    scraped_data['username'] = title_tag.text.split("'s Bedwars Stats")[0]
                return scraped_data

        h1_tag = soup.find('h1', class_='text-center')
        if h1_tag:
            username_text = h1_tag.text.strip()
            if "'s Bedwars Stats" in username_text:
                scraped_data['username'] = username_text.split("'s Bedwars Stats")[0]

        p_tags = main_content_div.find_all('p', recursive=False)
        for p in p_tags:
            text = p.text.strip()
            if text.startswith("Level:"):
                scraped_data['level'] = text.split(': ')[1].replace('✫', '').strip()
            elif text.startswith("Coins:"):
                scraped_data['coins'] = text.split(': ')[1].replace(',', '').strip()
            elif text.startswith("Final Kills/Deaths Ratio (FKDR):"):
                scraped_data['fkdr_summary'] = text.split(': ')[1].strip()
            elif text.startswith("Beds Broken/Lost Ratio (BBLR):"):
                scraped_data['bblr_summary'] = text.split(': ')[1].strip()

        def parse_stats_table(table_element):
            if not table_element:
                return None, "Table element not found"
            try:
                headers = [th.text.strip() for th in table_element.find('thead').find_all('th')[1:]]
                stats_dict = {}
                tbody = table_element.find('tbody')
                if not tbody:
                    return None, "Table body not found"

                for row in tbody.find_all('tr'):
                    cells = row.find_all('td')
                    if not cells or cells[0].get('class') == ['divider']:
                        continue
                    stat_name = cells[0].text.strip()
                    if not stat_name:
                        continue

                    values = [cell.text.strip().replace(',', '') for cell in cells[1:]]
                    if len(values) == len(headers):
                        stats_dict[stat_name] = dict(zip(headers, values))
                    else:
                        stats_dict[stat_name] = {"error": "Header/value count mismatch", "raw_values": values}

                return stats_dict, None
            except Exception as e:
                return None, f"Error parsing table: {e}"

        main_table_container = main_content_div.find('div', class_='stats-table-container')
        main_table = main_table_container.find('table', class_='stats-table') if main_table_container else None
        main_stats_data, main_stats_error = parse_stats_table(main_table)
        scraped_data['main_stats'] = main_stats_data
        if main_stats_error and not scraped_data['error']:
            scraped_data['error'] = f"Main stats: {main_stats_error}"

        other_modes_acc = soup.find('div', id='other-modes-acc')
        other_modes_table = None
        if other_modes_acc:
            other_modes_container = other_modes_acc.find('div', class_='stats-table-container')
            if other_modes_container:
                other_modes_table = other_modes_container.find('table', class_='stats-table')

        other_stats_data, other_stats_error = parse_stats_table(other_modes_table)
        scraped_data['other_modes_stats'] = other_stats_data
        if other_stats_error and not scraped_data['error']:
            scraped_data['error'] = f"Other modes: {other_stats_error}"

        challenges_acc = soup.find('div', id='challenges-acc')
        challenges_list = []
        if challenges_acc:
            try:
                challenges_parent_div = challenges_acc.find('div', class_='challenges-list')
                if challenges_parent_div:
                    completed_div = challenges_parent_div.find('div', recursive=False)
                    if completed_div and completed_div.find('h3', string='Completed'):
                        completed_challenges_tags = completed_div.find_all('p', class_='challenge')
                        for chall_tag in completed_challenges_tags:
                            name = re.sub(r"^\d+\.\s*", "", chall_tag.text.strip())
                            challenges_list.append({
                                "name": name,
                                "details_html": chall_tag.get('data-bs-original-title', '').strip()
                            })
                scraped_data['completed_challenges'] = challenges_list if challenges_list else None
            except Exception as e:
                if not scraped_data['error']:
                    scraped_data['error'] = f"Error parsing challenges: {e}"
                scraped_data['completed_challenges'] = None
        else:
            scraped_data['completed_challenges'] = None

        summary_acc = soup.find('div', id='summary-acc')
        if summary_acc:
            try:
                summary_p = summary_acc.find('p')
                scraped_data['summary_text'] = summary_p.text.strip().replace('\n', ' ').replace('  ', ' ') if summary_p else None
            except Exception as e:
                if not scraped_data['error']:
                    scraped_data['error'] = f"Error parsing summary: {e}"
                scraped_data['summary_text'] = None
        else:
            scraped_data['summary_text'] = None

        time_tag = soup.find('time', class_='change-time')
        if time_tag:
            scraped_data['last_updated'] = time_tag.get('datetime')
        else:
            time_div = soup.find('div', class_='mt-3')
            if time_div and time_div.find('p', class_='text-center'):
                time_tag_fallback = time_div.find('time', class_='change-time')
                if time_tag_fallback:
                    scraped_data['last_updated'] = time_tag_fallback.get('datetime')

    except AttributeError as e:
        if not scraped_data['error']:
            scraped_data['error'] = f"AttributeError: Likely missing HTML element during parsing. Check page structure. Details: {e}"
    except Exception as e:
        if not scraped_data['error']:
            scraped_data['error'] = f"An unexpected error occurred during parsing: {e}"

    return scraped_data

if __name__ == "__main__":
    username_to_scrape = "Lava999"
    
    print(f"Scraping stats for: {username_to_scrape}")
    stats = scrape_bwstats(username_to_scrape)

    if stats.get('error'):
        print(f"\nError: {stats['error']}")
    else:
        print("\n--- Scraped Data ---")
        print(f"Username: {stats.get('username')}")
        print(f"Level: {stats.get('level')}")
        print(f"Coins: {stats.get('coins')}")
        print(f"FKDR (Summary): {stats.get('fkdr_summary')}")
        print(f"BBLR (Summary): {stats.get('bblr_summary')}")
        print(f"Last Updated: {stats.get('last_updated')}")

        print("\nMain Stats:")
        if stats.get('main_stats'):
            for stat, values in stats['main_stats'].items():
                print(f"  {stat}: {values}")
        else:
            print("  (Not found or error parsing)")

        print("\nOther Mode Stats:")
        if stats.get('other_modes_stats'):
            for stat, values in stats['other_modes_stats'].items():
                print(f"  {stat}: {{k: v for i, (k, v) in enumerate(values.items()) if i < 5}} ...")
        else:
            print("  (Not found or error parsing)")

        print("\nCompleted Challenges:")
        if stats.get('completed_challenges'):
            print(f"  Count: {len(stats['completed_challenges'])}")
            for i, challenge in enumerate(stats['completed_challenges']):
                if i < 3:
                    print(f"  - {challenge['name']}")
                elif i == 3:
                    print("  ...")
                    break
        else:
            print("  (Not found or error parsing)")

        print("\nSummary Text:")
        if stats.get('summary_text'):
            print(f"  {stats['summary_text'][:150]}...")
        else:
            print("  (Not found or error parsing)")

    print("\n--- End of Scrape ---")