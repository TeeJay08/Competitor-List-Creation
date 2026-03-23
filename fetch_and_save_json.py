import os
import json
import time
import requests
import glob
from datetime import datetime

USERNAME = "amz_scrape_yAlYS"
PASSWORD = "Amz_scrape420"
BASE_JSON_DIR = "json_data"

fetched_this_session = {}
current_keyword = ""

def fetch_product(asin):
    payload = {
        "source": "amazon_product",
        "query": asin,
        "parse": True
    }

    headers = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) Chrome/120.0.0.0 Safari/537.36"}

    try:
        response = requests.post(
            "http://realtime.oxylabs.io/v1/queries",
            auth=(USERNAME, PASSWORD),
            json=payload,
            headers=headers,
            proxies={"http": None, "https": None},
            verify=False,
            timeout=60
        )
        data = response.json()

        # Handle async response
        if data.get("status") == "pending":
            results_url = data["_links"][2]["href_list"][0].replace("https://", "http://")
            time.sleep(3)  # wait for scrape
            result = requests.get(
                results_url,
                auth=(USERNAME, PASSWORD),
                proxies={"http": None, "https": None},
                verify=False,
                timeout=60
            )
            return result.json().get("results", [{}])[0].get("content")

        # Direct response
        return data.get("results", [{}])[0].get("content")

    except Exception as e:
        print("Error fetching", asin, ":", e)
        return None

def get_latest_local_json(keyword, asin):
    search_path = os.path.join(BASE_JSON_DIR, keyword, f"{asin}_v*.json")
    files = glob.glob(search_path)
    if not files:
        return None, 0
    
    def get_version(f):
        try:
            filename = os.path.basename(f)
            v_part = filename.split('_v')[1]
            v_num = int(v_part.split('_')[0])
            return v_num
        except:
            return 0

    latest_file = max(files, key=get_version)
    latest_v = get_version(latest_file)
    return latest_file, latest_v

def get_or_fetch_json(asin, force_fetch=False):
    if not asin:
        return None
        
    keyword_dir = os.path.join(BASE_JSON_DIR, current_keyword)
    os.makedirs(keyword_dir, exist_ok=True)
    
    if asin in fetched_this_session:
        return fetched_this_session[asin]

    latest_file, latest_v = get_latest_local_json(current_keyword, asin)
    
    if latest_file and not force_fetch:
        try:
            with open(latest_file, "r", encoding="utf-8") as f:
                data = json.load(f)
                fetched_this_session[asin] = data
                return data
        except json.JSONDecodeError:
            pass # corrupted, re-fetch
            
    print(f"Fetching data for ASIN: {asin} from Oxylabs... (Version: v{latest_v + 1})")
    data = fetch_product(asin)
    if data:
        new_v = latest_v + 1
        now_str = datetime.now().strftime("%Y-%m-%d_%H-%M-%S")
        new_filename = f"{asin}_v{new_v}_{now_str}.json"
        filepath = os.path.join(keyword_dir, new_filename)
        
        with open(filepath, "w", encoding="utf-8") as f:
            json.dump(data, f, indent=4)
            
        print(f"Saved: {filepath}")
        fetched_this_session[asin] = data
        time.sleep(1)
    return data

def process_and_save_all(target_asin, force_secondary=False):
    print(f"\n--- Processing Main ASIN: {target_asin} ---")
    product = get_or_fetch_json(target_asin, force_fetch=True)
    if not product:
        print(f"Failed to fetch main ASIN: {target_asin}")
        return

    # Look for variations
    for variation in product.get("variation", []):
        var_asin = variation.get("asin")
        if var_asin and var_asin != target_asin:
            get_or_fetch_json(var_asin, force_fetch=force_secondary)

    # Look for buy it with
    for item in product.get("buy_it_with", []):
        item_asin = item.get("asin")
        if item_asin and item_asin != target_asin:
            get_or_fetch_json(item_asin, force_fetch=force_secondary)

    # Look for frequently bought together
    for item in product.get("frequently_bought_together", []):
        item_asin = item.get("asin")
        if item_asin and item_asin != target_asin:
            get_or_fetch_json(item_asin, force_fetch=force_secondary)

if __name__ == "__main__":
    kw = input("Enter the Keyword (folder name for JSON data): ").strip()
    if not kw:
        print("Keyword is required. Exiting.")
        exit()
        
    current_keyword = kw.replace(" ", "_")
    
    asins_input = input("Enter the list of ASINs to fetch and save (comma separated): ").strip()
    if not asins_input:
        print("No ASINs provided. Exiting.")
        exit()
        
    asins = [a.strip() for a in asins_input.split(",") if a.strip()]
    
    force_sec_input = input("Force re-download of variations and related items as well? (y/n): ").strip().lower()
    force_secondary = force_sec_input in ['y', 'yes']
    
    # Save the list of main ASINs so json_to_excel knows which ones to process
    main_asins_filepath = os.path.join(BASE_JSON_DIR, current_keyword, "main_asins.txt")
    with open(main_asins_filepath, "w", encoding="utf-8") as f:
        f.write(",".join(asins))

    for idx, target_asin in enumerate(asins):
        print(f"\n[{idx+1}/{len(asins)}] Starting ASIN workflow: {target_asin}")
        process_and_save_all(target_asin, force_secondary=force_secondary)
        
    print(f"\nAll JSON data fetched and saved to the '{BASE_JSON_DIR}/{current_keyword}' directory.")
    print("You can now run 'json_to_excel.py' to generate the Excel sheet.")
