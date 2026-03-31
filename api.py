import os
import io
import json
from fastapi import FastAPI, UploadFile, File, Form, BackgroundTasks, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse
from pydantic import BaseModel
from typing import List, Dict, Optional

# Import our existing logic
import main as main_cli
import json_to_excel
import export_to_excel
from fetch_and_save_json import BASE_JSON_DIR
try:
    from llm_filter import filter_xray_with_llm
except ImportError:
    filter_xray_with_llm = lambda p, t: p # Fallback


# Import Analytics Engine logic
from analytics_engine.models import XRayRawRow, CerebroRawRow, MagnetRawRow, DifferentiationInput
from analytics_engine.main import run_analytics_pipeline

app = FastAPI(title="Competitor List API")

# Allow React app to talk to FastAPI
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"], 
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# In-memory store for task statuses processing
# Format: {"keyword": {"status": "fetching"|"building_excel"|"done"|"error", "total": int, "current": int, "message": str}}
task_status = {}

class ManualFetchRequest(BaseModel):
    keyword: str
    asins: List[str]
    force_secondary: bool

class XrayFetchRequest(BaseModel):
    keyword: str
    asins: List[str]
    force_secondary: bool
    xray_metadata: List[Dict]

def run_fetch_task(keyword: str, asins: List[str], force_secondary: bool, xray_metadata: Optional[List[Dict]] = None):
    try:
        task_status[keyword] = {"status": "fetching", "total": len(asins), "current": 0, "message": "Starting fetch..."}
        
        # We need to simulate progress by tracking which ASIN is being fetched.
        # Since process_and_save_all blocks, we can just update status before each one.
        import fetch_and_save_json
        fetch_and_save_json.current_keyword = keyword
        keyword_dir = os.path.join(BASE_JSON_DIR, keyword)
        os.makedirs(keyword_dir, exist_ok=True)
        
        main_asins_filepath = os.path.join(keyword_dir, "main_asins.txt")
        with open(main_asins_filepath, "w", encoding="utf-8") as f:
            f.write(",".join(asins))
            
        if xray_metadata:
            meta_filepath = os.path.join(keyword_dir, "xray_metadata.json")
            with open(meta_filepath, "w", encoding="utf-8") as f:
                json.dump(xray_metadata, f, indent=4)

        for idx, target_asin in enumerate(asins):
            task_status[keyword]["current"] = idx + 1
            task_status[keyword]["message"] = f"Fetching ASIN {idx+1}/{len(asins)}: {target_asin}"
            fetch_and_save_json.process_and_save_all(target_asin, force_secondary=force_secondary)
            
        task_status[keyword] = {"status": "done", "total": len(asins), "current": len(asins), "message": "Fetching complete! Ready to build Excel."}
    except Exception as e:
        task_status[keyword] = {"status": "error", "message": str(e)}

@app.get("/")
def read_root():
    return {"status": "API is running"}

@app.post("/api/manual-fetch")
def start_manual_fetch(req: ManualFetchRequest, background_tasks: BackgroundTasks):
    current_keyword = req.keyword.replace(" ", "_")
    background_tasks.add_task(run_fetch_task, current_keyword, req.asins, req.force_secondary)
    return {"message": "Task started", "keyword": current_keyword}

@app.post("/api/upload-xray")
async def upload_xray(file: UploadFile = File(...), product_details: Optional[str] = Form(None), keyword: Optional[str] = Form(None)):
    # Save the file temporarily
    temp_path = f"temp_{file.filename}"
    with open(temp_path, "wb") as f:
        content = await file.read()
        f.write(content)
        
    # AI Filtering: if the user provided product details, run the LLM filter
    filtered_path = temp_path
    if product_details and str(product_details).strip():
        kw_val = str(keyword).strip() if keyword else "unnamed_folder"
        filtered_path = filter_xray_with_llm(temp_path, str(product_details), kw_val)
        
    # Extract ASINs using existing logic
    all_shortlisted = main_cli.extract_asins_from_xray(filtered_path)
    
    # Cleanup
    if os.path.exists(temp_path):
        os.remove(temp_path)
        
    if not all_shortlisted:
        raise HTTPException(status_code=400, detail="Could not extract ASINs. Make sure rules match and file is valid.")
        
    return {"shortlisted": all_shortlisted}

@app.post("/api/xray-fetch")
def start_xray_fetch(req: XrayFetchRequest, background_tasks: BackgroundTasks):
    current_keyword = req.keyword.replace(" ", "_")
    background_tasks.add_task(run_fetch_task, current_keyword, req.asins, req.force_secondary, req.xray_metadata)
    return {"message": "Task started", "keyword": current_keyword}

@app.get("/api/status/{keyword}")
def get_status(keyword: str):
    return task_status.get(keyword.replace(" ", "_"), {"status": "unknown", "message": "No active task found for this keyword."})

@app.post("/api/build-excel")
def build_excel(keyword: str = Form(...), excel_title: str = Form(...)):
    current_keyword_dir = os.path.join(BASE_JSON_DIR, keyword.replace(" ", "_"))
    
    if not os.path.exists(current_keyword_dir):
        raise HTTPException(status_code=404, detail="JSON directory not found. Have you fetched data yet?")
        
    # Load metadata
    xray_metadata = {}
    meta_file = os.path.join(current_keyword_dir, "xray_metadata.json")
    if os.path.exists(meta_file):
        with open(meta_file, "r", encoding="utf-8") as f:
            try:
                x_list = json.load(f)
                for item in x_list:
                    xray_metadata[item.get("asin")] = item
            except:
                pass

    # Read ASINs list
    main_asins_file = os.path.join(current_keyword_dir, "main_asins.txt")
    if not os.path.exists(main_asins_file):
         raise HTTPException(status_code=404, detail="main_asins.txt not found. Cannot determine sequence.")
         
    with open(main_asins_file, "r", encoding="utf-8") as f:
        asins = [a.strip() for a in f.read().strip().split(",") if a.strip()]
        
    # Build data
    json_to_excel.current_keyword_dir = current_keyword_dir
    all_data = []
    
    for target_asin in asins:
        p_data = json_to_excel.process_product_from_json(target_asin)
        if p_data:
            if target_asin in xray_metadata:
                p_data["parent_revenue"] = xray_metadata[target_asin].get("parent_revenue", 0)
                p_data["child_revenue"] = xray_metadata[target_asin].get("child_revenue", 0)
            all_data.append(p_data)
            
    if not all_data:
        raise HTTPException(status_code=400, detail="No valid product JSONs found to export.")
        
    filename = f"{excel_title.replace(' ', '_')}_competitors.xlsx" if excel_title else "competitors.xlsx"
    export_to_excel.export_products_to_excel(all_data, excel_title, filename)
    
    return {"message": "Excel Built Successfully", "download_url": f"/api/download/{filename}"}

@app.get("/api/download/{filename}")
def download_excel(filename: str):
    if not os.path.exists(filename):
         raise HTTPException(status_code=404, detail="Excel file not found.")
    return FileResponse(path=filename, filename=filename, media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet")

class ValidateNicheRequest(BaseModel):
    xray_data: List[XRayRawRow]
    cerebro_data: List[CerebroRawRow]
    magnet_data: List[MagnetRawRow]
    differentiation: DifferentiationInput

@app.post("/api/validate-niche")
def validate_niche_endpoint(req: ValidateNicheRequest):
    try:
        output_file = run_analytics_pipeline(
            xray_raw=req.xray_data,
            cerebro_raw=req.cerebro_data,
            magnet_raw=req.magnet_data,
            diff_input=req.differentiation,
            output_filename="Validation_Dashboard.xlsx"
        )
        return {"message": "Validation Complete", "download_url": f"/api/download/{output_file}"}
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))
