import os
import json
import glob

BASE_JSON_DIR = "json_data"
current_keyword_dir = ""

def load_local_json(asin):
    if not asin or not current_keyword_dir:
        return None
        
    search_path = os.path.join(current_keyword_dir, f"{asin}_v*.json")
    files = glob.glob(search_path)
    if not files:
        return None
    
    def get_version(f):
        try:
            filename = os.path.basename(f)
            v_part = filename.split('_v')[1]
            v_num = int(v_part.split('_')[0])
            return v_num
        except:
            return 0

    latest_file = max(files, key=get_version)
    try:
        with open(latest_file, "r", encoding="utf-8") as f:
            return json.load(f)
    except json.JSONDecodeError:
        return None

def process_product_from_json(target_asin):
    product = load_local_json(target_asin)
    if not product:
        print(f"Warning: Main JSON for {target_asin} not found in {current_keyword_dir}/")
        return None

    asin = product.get("asin", target_asin)

    # Variations loop
    variations_data = []
    for variation in product.get("variation", []):
        var_asin = variation.get("asin")
        if var_asin == asin:
            var_price = product.get("price")
        else:
            var_product = load_local_json(var_asin)
            var_price = var_product.get("price") if var_product else None
        
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
            item_product = load_local_json(item_asin)
            
            # Use data from the local JSON if we fetched it, otherwise fallback to whatever is in the main JSON
            if item_product:
                item_title = item_product.get("title") or item_product.get("product_name") or item.get("title")
                item_link = item_product.get("url") or f"https://www.amazon.com/dp/{item_asin}"
            else:
                item_title = item.get("title", f"Unknown (JSON missing)")
                item_link = f"https://www.amazon.com/dp/{item_asin}"
                
            buy_it_with_data.append({
                "asin": item_asin,
                "title": item_title,
                "amazon_link": item_link
            })
    
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
            item_product = load_local_json(item_asin)
            if item_product:
                item_title = item_product.get("title") or item_product.get("product_name") or item.get("title")
                item_link = item_product.get("url") or f"https://www.amazon.com/dp/{item_asin}"
            else:
                item_title = item.get("title", f"Unknown (JSON missing)")
                item_link = f"https://www.amazon.com/dp/{item_asin}"
                
            fbt_data.append({
                "asin": item_asin,
                "title": item_title,
                "amazon_link": item_link
            })

    data = {
        "amazon_link": product.get("url") or f"https://www.amazon.com/dp/{asin}",
        "asin": asin,
        "brand_name": product.get("brand"),
        "main_image": product.get("images", [None])[0] if product.get("images") else None,
        "sales": product.get("sales_volume"),
        "rating": product.get("rating"),
        "number_of_reviews": product.get("reviews_count"),
        "launch_date": product.get("product_details", {}).get("date_first_available"),
        "selling_price": product.get("price"),
        "variations": variations_data,
        "buy_it_with": buy_it_with_data,
        "frequently_bought_together": fbt_data,
        "sales_ranks": [
            {
                "rank": r.get("rank"),
                "category": " > ".join([c.get("name") for c in r.get("ladder", [])])
            }
            for r in product.get("sales_rank", [])
        ]
    }

    return data

if __name__ == "__main__":
    kw = input("Enter the Keyword used previously (folder name): ").strip()
    if not kw:
        print("Keyword is required. Exiting.")
        exit()
        
    current_keyword_dir = os.path.join(BASE_JSON_DIR, kw.replace(" ", "_"))
    
    if not os.path.exists(current_keyword_dir):
        print(f"Directory {current_keyword_dir} does not exist. Exiting.")
        exit()

    asins_input = input(f"Enter the list of ASINs to generate Excel for (comma separated, or leave blank to auto-load ASINs previously fetched in '{kw}'): ").strip()
    
    if asins_input:
        asins = [a.strip() for a in asins_input.split(",") if a.strip()]
    else:
        main_asins_file = os.path.join(current_keyword_dir, "main_asins.txt")
        if os.path.exists(main_asins_file):
            with open(main_asins_file, "r", encoding="utf-8") as f:
                content = f.read().strip()
                asins = [a.strip() for a in content.split(",") if a.strip()]
            print(f"Auto-loaded {len(asins)} main ASINs from previous fetch.")
        else:
            print("Could not find auto-saved ASINs. Please provide the main ASINs to process.")
            asins_input = input("Main ASINs: ").strip()
            asins = [a.strip() for a in asins_input.split(",") if a.strip()]

    if not asins:
        print("No ASINs to process. Exiting.")
        exit()

    excel_title = input("Enter the Keyword for the Excel heading (can be same as folder name): ").strip()

    xray_metadata = {}
    meta_file = os.path.join(current_keyword_dir, "xray_metadata.json")
    if os.path.exists(meta_file):
        with open(meta_file, "r", encoding="utf-8") as f:
            try:
                x_list = json.load(f)
                for item in x_list:
                    xray_metadata[item.get("asin")] = item
            except json.JSONDecodeError:
                pass

    all_data = []
    for idx, target_asin in enumerate(asins):
        print(f"[{idx+1}/{len(asins)}] Parsing JSON for ASIN: {target_asin}")
        product_data = process_product_from_json(target_asin)
        if product_data:
            if target_asin in xray_metadata:
                x_data = xray_metadata[target_asin]
                product_data["parent_revenue"] = x_data.get("parent_revenue", 0)
                product_data["child_revenue"] = x_data.get("child_revenue", 0)
            all_data.append(product_data)
            
    if all_data:
        try:
            from export_to_excel import export_products_to_excel
            filename = f"{excel_title.replace(' ', '_')}_competitors.xlsx" if excel_title else "competitors.xlsx"
            export_products_to_excel(all_data, excel_title, filename)
        except ImportError:
            print("Could not find export_to_excel.py script!")
        except Exception as e:
            print(f"Error creating Excel file: {e}")
    else:
        print("No valid product data found to export.")
