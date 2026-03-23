import os
import pandas as pd
from fetch_and_save_json import process_and_save_all, BASE_JSON_DIR

def run_manual_mode():
    kw = input("Enter the Keyword (folder name for JSON data): ").strip()
    if not kw:
        print("Keyword is required. Exiting.")
        return
        
    current_keyword = kw.replace(" ", "_")
    
    asins_input = input("Enter the list of ASINs to fetch and save (comma separated): ").strip()
    if not asins_input:
        print("No ASINs provided. Exiting.")
        return
        
    asins = [a.strip() for a in asins_input.split(",") if a.strip()]
    
    force_sec_input = input("Force re-download of variations and related items as well? (y/n): ").strip().lower()
    force_secondary = force_sec_input in ['y', 'yes']
    
    execute_fetch_pipeline(current_keyword, asins, force_secondary)

def extract_asins_from_xray(file_path):
    print(f"Reading X-Ray file from: {file_path}")
    try:
        if file_path.endswith('.csv'):
             df = pd.read_csv(file_path)
        elif file_path.endswith('.xlsx'):
             df = pd.read_excel(file_path)
        else:
             print("Unsupported file format. Please provide a .csv or .xlsx file.")
             return []
    except Exception as e:
        print(f"Error reading file {file_path}: {e}")
        return []

    # Try to find necessary columns
    asin_col = next((c for c in df.columns if 'asin' in str(c).lower()), None)
    
    # Prioritize 'ASIN Revenue' explicitly
    rev_col = next((c for c in df.columns if 'asin revenue' in str(c).lower()), None)
    if not rev_col:
        rev_col = next((c for c in df.columns if 'revenue' in str(c).lower()), None)
        
    reviews_col = next((c for c in df.columns if 'review count' in str(c).lower() or 'reviews' in str(c).lower()), None)
    rating_col = next((c for c in df.columns if 'rating' in str(c).lower() and 'review' in str(c).lower()), None)
    if not rating_col:
        rating_col = next((c for c in df.columns if 'rating' in str(c).lower()), None)
        
    brand_col = next((c for c in df.columns if 'brand' in str(c).lower()), None)

    if not asin_col:
         print("Could not find an 'ASIN' column in the file. Please ensure the file has one.")
         return []

    df = df.dropna(subset=[asin_col])
    
    # Pre-process numeric columns
    def clean_numeric(series):
        if series is None: return None
        return pd.to_numeric(series.astype(str).replace(r'[$,]', '', regex=True), errors='coerce').fillna(0)
        
    if rev_col: df['__revenue'] = clean_numeric(df[rev_col])
    else: df['__revenue'] = 0
    
    if reviews_col: df['__reviews'] = clean_numeric(df[reviews_col])
    else: df['__reviews'] = 0
    
    if rating_col: df['__rating'] = clean_numeric(df[rating_col])
    else: df['__rating'] = 0

    filtered_out = []
    shortlisted = []
    seen_asins = set()

    for index, row in df.iterrows():
        asin = str(row[asin_col]).strip()
        if not asin or asin.lower() == 'nan':
            continue
            
        if asin in seen_asins:
            continue
        seen_asins.add(asin)
            
        rev = row['__revenue']
        revs = row['__reviews']
        rating = row['__rating']
        
        # Hard Filters
        if rev < 3000:
            filtered_out.append((asin, "Revenue < $3,000"))
            continue
        if revs > 1000:
            filtered_out.append((asin, "Reviews > 1,000"))
            continue
        if rating > 4.7 or rating < 3.8:
            filtered_out.append((asin, f"Rating {rating} outside acceptable bounds (3.8 - 4.7)"))
            continue
            
        # Optional: New Listings Check? Helium 10 has a creation date column sometimes, 
        # but rule states "low reviews + unstable data". We can use < 10 reviews as proxy for very new.
        if revs < 10:
            filtered_out.append((asin, "Very new/low reviews (<10)"))
            continue

        # If it passed hard filters, evaluate Sweet Spot Criteria
        reason = "Passed Hard Filters"
        is_sweet_spot = False
        if (5000 <= rev <= 25000) and (50 <= revs <= 300) and (4.0 <= rating <= 4.4):
            reason = "Matches Ideal Sweet Spot Criteria"
            is_sweet_spot = True
            
        shortlisted.append({
            "asin": asin,
            "revenue": rev,
            "reviews": revs,
            "rating": rating,
            "brand": str(row[brand_col]).strip() if brand_col else None,
            "reason": reason,
            "is_sweet_spot": is_sweet_spot
        })
        
    # Niche health check / sorting
    # We want to prioritize sweet spot matches, then just by revenue
    shortlisted.sort(key=lambda x: (x['is_sweet_spot'], x['revenue']), reverse=True)
    
    # Brand Deduplication Logic
    # Keep only the highest revenue ASIN per brand
    brand_filtered_shortlisted = []
    seen_brands = set()
    
    for s in shortlisted:
        brand = s.get('brand')
        # If no brand info exists, just keep it. If it exists, check if we've seen it.
        if brand and brand.lower() != 'nan':
            # normalize brand name loosely for tracking
            b_norm = brand.strip().lower()
            if b_norm in seen_brands:
                filtered_out.append((s['asin'], f"Duplicate Brand ({brand}). Lower revenue than representative."))
                continue
            seen_brands.add(b_norm)
            
        brand_filtered_shortlisted.append(s)
        
    # Take top 5-8 ASINs (we'll just take top 8 max)
    final_selection = brand_filtered_shortlisted[:8]
    
    print("\n### Section A — Filtered Out ASINs ###")
    for asin, reason in filtered_out:
        print(f"* {asin} | {reason}")
        
    print("\n### Section B — Shortlisted ASINs ###")
    print("* ASIN | Revenue | Reviews | Rating | Brand | Reason Selected")
    for s in final_selection:
        print(f"* {s['asin']} | ${s['revenue']:,.2f} | {s['reviews']} | {s['rating']} | {s.get('brand','N/A')} | {s['reason']}")
        
    # Write to text file
    txt_path = "shortlisted_asins.txt"
    try:
        with open(txt_path, "w", encoding="utf-8") as f:
            f.write("ASIN | Revenue | Reviews | Rating | Brand | Reason Selected\n")
            for s in final_selection:
                f.write(f"{s['asin']} | ${s['revenue']:,.2f} | {s['reviews']} | {s['rating']} | {s.get('brand','N/A')} | {s['reason']}\n")
        print(f"\n[Created File: {txt_path}]")
    except Exception as e:
        print(f"Could not write to {txt_path}: {e}")

    return [s['asin'] for s in final_selection]

def run_xray_mode():
    kw = input("Enter the Keyword (folder name for JSON data): ").strip()
    if not kw:
        print("Keyword is required. Exiting.")
        return
        
    current_keyword = kw.replace(" ", "_")

    file_path = input("Enter the path to your Helium 10 X-Ray export (.csv or .xlsx): ").strip()
    # Handle quotes in path
    file_path = file_path.strip('"').strip("'")
    
    if not os.path.exists(file_path):
        print("File does not exist. Exiting.")
        return

    all_asins = extract_asins_from_xray(file_path)
    if not all_asins:
        print("No valid ASINs extracted.")
        return

    top_n_str = input(f"Found {len(all_asins)} available ASINs. How many top ASINs to process? (default: 10): ").strip()
    top_n = int(top_n_str) if top_n_str.isdigit() else 10
    
    asins = all_asins[:top_n]
    print(f"\nShortlisted ASINs: {', '.join(asins)}\n")

    force_sec_input = input("Force re-download of variations and related items as well? (y/n): ").strip().lower()
    force_secondary = force_sec_input in ['y', 'yes']

    execute_fetch_pipeline(current_keyword, asins, force_secondary)

def execute_fetch_pipeline(current_keyword, asins, force_secondary):
    # This must set the global current_keyword in fetch_and_save_json
    import fetch_and_save_json
    fetch_and_save_json.current_keyword = current_keyword

    keyword_dir = os.path.join(BASE_JSON_DIR, current_keyword)
    os.makedirs(keyword_dir, exist_ok=True)
    
    # Save the list of main ASINs so json_to_excel knows which ones to process
    main_asins_filepath = os.path.join(keyword_dir, "main_asins.txt")
    with open(main_asins_filepath, "w", encoding="utf-8") as f:
        f.write(",".join(asins))

    for idx, target_asin in enumerate(asins):
        print(f"\n[{idx+1}/{len(asins)}] Starting ASIN workflow: {target_asin}")
        process_and_save_all(target_asin, force_secondary=force_secondary)
        
    print(f"\nAll JSON data fetched and saved to the '{BASE_JSON_DIR}/{current_keyword}' directory.")
    print("You can now run 'json_to_excel.py' to generate the Excel sheet.")


if __name__ == "__main__":
    print("====================================")
    print("  COMPETITOR LIST CREATION SYSTEM")
    print("====================================")
    print("1. Enter ASINs manually")
    print("2. Upload X-Ray data (.csv or .xlsx)")
    
    choice = input("Select a mode (1 or 2): ").strip()
    
    if choice == "1":
        run_manual_mode()
    elif choice == "2":
        run_xray_mode()
    else:
        print("Invalid choice. Exiting.")
