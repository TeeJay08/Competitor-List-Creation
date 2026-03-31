import os
import json
import requests
import pandas as pd
import datetime
from dotenv import load_dotenv

def filter_xray_with_llm(file_path: str, product_details_prompt: str, folder_keyword: str = "custom") -> str:
    load_dotenv(override=True)
    OPENAI_API_KEY = os.getenv("OPENAI_API_KEY", "")
    
    def log_debug(msg):
        with open("llm_debug.txt", "a") as f:
            f.write(msg + "\n")
            
    # Reset log
    with open("llm_debug.txt", "w") as f:
        f.write(f"Starting LLM filter for file: {file_path}\n")
        f.write(f"OPENAI_API_KEY present: {bool(OPENAI_API_KEY)}\n")
        
    # 1. Load Data
    df = None
    try:
        if file_path.endswith('.csv'):
            df = pd.read_csv(file_path)
        else:
            df = pd.read_excel(file_path)
    except Exception as e:
        log_debug(f"Error reading file: {e}")
        return file_path
         
    asin_col = next((c for c in df.columns if 'asin' in str(c).lower()), None)
    title_col = next((c for c in df.columns if 'title' in str(c).lower() or 'product' in str(c).lower()), None)
    brand_col = next((c for c in df.columns if 'brand' in str(c).lower()), None)
    
    # Revenue deduplication parsing
    child_rev_col = next((c for c in df.columns if 'asin revenue' in str(c).lower()), None)
    parent_rev_col = next((c for c in df.columns if 'parent level revenue' in str(c).lower()), None)
    if not parent_rev_col:
        parent_rev_col = next((c for c in df.columns if 'revenue' in str(c).lower() and 'asin' not in str(c).lower()), None)

    log_debug(f"Columns mapped - ASIN: {asin_col}, Title: {title_col}, Brand: {brand_col}")

    if not asin_col or not OPENAI_API_KEY or not product_details_prompt.strip():
        log_debug("Early abort condition triggered (Missing ASIN col, key, or prompt).")
        return file_path
        
    # Drop rows without ASIN
    df = df.dropna(subset=[asin_col])
    
    # Pre-process numeric strings handling commas and $
    def clean_numeric(series):
        if series is None: return None
        return pd.to_numeric(series.astype(str).replace(r'[$,]', '', regex=True), errors='coerce').fillna(0)

    # 1. Deduplicate repeated ASINs entirely (keep the first)
    df = df.drop_duplicates(subset=[asin_col], keep='first')

    # 2. If parent level revenue exists, deduplicate leaving only the one with the highest child revenue
    if parent_rev_col:
        df['__parent_revenue'] = clean_numeric(df[parent_rev_col])
        df['__child_revenue'] = clean_numeric(df[child_rev_col]) if child_rev_col else df['__parent_revenue']
        
        # We sort by child revenue descending, then drop duplicates by parent revenue.
        # This guarantees that out of variants sharing a parent revenue, the highest child seller is kept.
        df = df.sort_values(by='__child_revenue', ascending=False)
        df = df.drop_duplicates(subset=['__parent_revenue'], keep='first')
    
    # 2. Extract slim representation for LLM
    items = []
    for _, row in df.iterrows():
        a = str(row[asin_col]).strip()
        if not a or a.lower() == 'nan': continue
        t = str(row[title_col]).strip() if title_col else ""
        b = str(row[brand_col]).strip() if brand_col else ""
        items.append({"ASIN": a, "Title": t, "Brand": b})
        
    # 3. Request LLM Filter
    system_prompt = (
        "You are an expert, highly cautious Amazon product auditor. "
        "Your task is to review a list of products against a User Intent rule, and strictly output a JSON object with a single key 'valid_asins' containing an array of ASINs. "
        "CRITICAL RULE: Erring on the side of caution is mandatory. If a product title seems even SLIGHTLY relevant, or if you are ambiguous/unsure about it, you MUST INCLUDE IT. "
        "Only remove a product if it is 100% definitively violating the user's explicit exclusion instructions."
    )
    user_prompt = f"User Intent/Criteria: '{product_details_prompt}'\n\nProducts Data: {json.dumps(items)}\n\nOutput strictly JSON: {{\"valid_asins\": [\"ASIN1\", \"ASIN2\"]}}"
    
    headers = {"Content-Type": "application/json", "Authorization": f"Bearer {OPENAI_API_KEY}"}
    payload = {
        "model": "gpt-4o",
        "messages": [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_prompt}
        ],
        "temperature": 0.0,
        "response_format": {"type": "json_object"}
    }
    
    try:
        response = requests.post("https://api.openai.com/v1/chat/completions", headers=headers, json=payload, timeout=30)
        res_data = response.json()
        
        if "error" in res_data:
            log_debug(f"OpenAI API Error returned: {res_data['error']}")
            return file_path
            
        cont = res_data["choices"][0]["message"]["content"]
        parsed = json.loads(cont)
        valid_asins = set(parsed.get("valid_asins", []))
        
        log_debug(f"LLM returned {len(valid_asins)} valid ASINs.")
        
        # 4. Apply Filter mask
        filtered_df = df[df[asin_col].astype(str).str.strip().isin(valid_asins)]
        
        # 5. Save back to a new file in a dedicated folder
        folder_path = "filtered_xray"
        os.makedirs(folder_path, exist_ok=True)
        timestamp = datetime.datetime.now().strftime("%Y-%m-%d_%H-%M-%S")
        safe_kw = folder_keyword.replace(" ", "_")
        new_path = os.path.join(folder_path, f"filtered_{safe_kw}_{timestamp}.xlsx")
        
        # Clean up temporary injected columns before saving
        if '__parent_revenue' in filtered_df.columns:
            filtered_df = filtered_df.drop(columns=['__parent_revenue'])
        if '__child_revenue' in filtered_df.columns:
            filtered_df = filtered_df.drop(columns=['__child_revenue'])
            
        filtered_df.to_excel(new_path, index=False)
        
        log_debug(f"Saved successfully to {new_path}")
        return new_path
        
    except Exception as e:
        log_debug(f"LLM Error during execution: {e}")
        return file_path
