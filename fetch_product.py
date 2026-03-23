import requests
import time

USERNAME = "amz_scrape_yAlYS"
PASSWORD = "Amz_scrape420"

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
            return result.json()

        # Direct response
        return data["results"][0]["content"]

    except Exception as e:
        print("Error:", e)
        return None


def process_product(target_asin):
    product = fetch_product(target_asin)
    if not product:
        return None

    asin = product.get("asin")

    # Variations loop
    variations_data = []
    for variation in product.get("variation", []):
        var_asin = variation.get("asin")
        # Avoid fetching the same ASIN to save time/requests
        if var_asin == asin:
            var_price = product.get("price")
        else:
            print(f"Fetching variation ASIN: {var_asin} ...")
            var_product = fetch_product(var_asin)
            var_price = var_product.get("price") if var_product else None
            time.sleep(1) # Sleep to avoid rate limits
        
        variations_data.append({
            "asin": var_asin,
            "dimensions": variation.get("dimensions", {}),
            "price": var_price
        })

    # Buy it with loop
    buy_it_with_data = []
    for item in product.get("buy_it_with", []):
        item_asin = item.get("asin")
        if item_asin:
            print(f"Fetching Buy It With ASIN: {item_asin} ...")
            item_product = fetch_product(item_asin)
            if item_product:
                item_title = item_product.get("title") or item_product.get("product_name")
                item_link = item_product.get("url") or f"https://www.amazon.com/dp/{item_asin}"
                buy_it_with_data.append({
                    "asin": item_asin,
                    "title": item_title,
                    "amazon_link": item_link
                })
            time.sleep(1)
    
    # Frequently bought together loop
    fbt_data = []
    for item in product.get("frequently_bought_together", []):
        item_asin = item.get("asin")
        if item_asin == asin:
            # Main product
            main_title = product.get("title") or product.get("product_name")
            main_link = product.get("url") or f"https://www.amazon.com/dp/{asin}"
            fbt_data.append({
                "asin": item_asin,
                "title": main_title,
                "amazon_link": main_link
            })
        elif item_asin:
            print(f"Fetching FBT ASIN: {item_asin} ...")
            item_product = fetch_product(item_asin)
            if item_product:
                item_title = item_product.get("title") or item_product.get("product_name")
                item_link = item_product.get("url") or f"https://www.amazon.com/dp/{item_asin}"
                fbt_data.append({
                    "asin": item_asin,
                    "title": item_title,
                    "amazon_link": item_link
                })
            time.sleep(1)

    data = {
        "amazon_link": product.get("url") or f"https://www.amazon.com/dp/{asin}",
        "asin": asin,
        "brand_name": product.get("brand"),

        "main_image": product.get("images", [None])[0],  # ✅ MAIN IMAGE

        # Sales (approx from sales_volume like "4K+ bought")
        "sales": product.get("sales_volume"),

        "rating": product.get("rating"),
        "number_of_reviews": product.get("reviews_count"),

        # Launch date
        "launch_date": product.get("product_details", {}).get("date_first_available"),

        "selling_price": product.get("price"),
        "variations": variations_data,

        # Buy it with
        "buy_it_with": buy_it_with_data,

        # Frequently bought together
        "frequently_bought_together": fbt_data,

        # Sales ranks
        "sales_ranks": [
            {
                "rank": r.get("rank"),
                "category": " > ".join([c.get("name") for c in r.get("ladder", [])])
            }
            for r in product.get("sales_rank", [])
        ]
    }

    # Print nicely
    for key, value in data.items():
        if key not in ("variations", "buy_it_with", "frequently_bought_together", "sales_ranks"):
            print(f"{key}: {value}")
            
    return data


if __name__ == "__main__":
    keyword = input("Enter the Keyword for the Excel heading: ").strip()
    asins_input = input("Enter the list of ASINs (comma separated): ").strip()
    
    if not asins_input:
        print("No ASINs provided. Exiting.")
        exit()
        
    asins = [a.strip() for a in asins_input.split(",") if a.strip()]
    
    all_data = []
    for idx, target_asin in enumerate(asins):
        print(f"\n[{idx+1}/{len(asins)}] Processing ASIN: {target_asin}")
        product_data = process_product(target_asin)
        if product_data:
            all_data.append(product_data)
            
    if all_data:
        create_excel = input(f"\nDo you want to create an Excel sheet for these {len(all_data)} products? (y/n): ")
        if create_excel.lower() in ('y', 'yes'):
            try:
                from export_to_excel import export_products_to_excel
                filename = f"{keyword.replace(' ', '_')}_competitors.xlsx" if keyword else "competitors.xlsx"
                export_products_to_excel(all_data, keyword, filename)
            except ImportError:
                print("Could not find export_to_excel.py script!")
            except PermissionError:
                print(f"\n[!] Permission denied: Could not save '{filename}'. Please make sure the Excel file is closed and try again.")
            except Exception as e:
                print(f"Error creating Excel file: {e}")