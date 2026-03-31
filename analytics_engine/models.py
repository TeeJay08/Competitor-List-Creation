from pydantic import BaseModel
from typing import List, Optional
from enum import Enum

class BlockerCode(str, Enum):
    RC_01 = "RC-01"
    RC_02 = "RC-02"
    RC_03 = "RC-03"
    RC_04 = "RC-04"
    RC_05 = "RC-05"
    RC_06 = "RC-06"

def get_blocker_message(code: str, custom_msg: str) -> str:
    return f"{code}: {custom_msg}"

# --- XRAY (Demand) ---
class XRayRawRow(BaseModel):
    asin: str
    product_title: Optional[str] = ""
    brand: Optional[str] = ""
    price_raw: Optional[str] = ""
    revenue_raw: Optional[str] = ""
    sales: float = 0
    reviews: float = 0
    rating: float = 0
    category: Optional[str] = ""
    bsr: float = 0
    variations: Optional[str] = ""

class XRayCleanRow(BaseModel):
    asin: str
    product_title: str
    brand: str
    price_clean: float
    revenue_clean: float
    sales: float
    reviews: float
    rating: float
    valid_row: str = "KEEP"

# --- CEREBRO (Keywords) ---
class CerebroRawRow(BaseModel):
    keyword: str
    search_volume: float = 0
    competing_products: float = 0
    ranking_asin_count: float = 0
    relevance_tag: Optional[str] = "Manual"

class CerebroCleanRow(BaseModel):
    keyword: str
    search_volume: float
    competing_products: float
    ranking_asin_count: float
    relevance_tag: str
    valid_keyword: str = "KEEP"

# --- MAGNET (Long Tail) ---
class MagnetRawRow(BaseModel):
    keyword: str
    search_volume: float = 0
    match_type: Optional[str] = ""

class MagnetCleanRow(BaseModel):
    keyword: str
    search_volume: float
    match_type: str
    valid: str = "KEEP"

# --- DIFFERENTIATION ---
class DifferentiationInput(BaseModel):
    top_asins: str = ""
    reviews_summary: str = ""
    features_summary: str = ""
    common_complaints: str = ""
    feature_gaps: str = ""
    unmet_needs: str = ""
    bundling_opportunities: str = ""
    listing_weakness: str = ""
    feasibility: str = "NONE" # HIGH / MEDIUM / LOW / NONE
    score: float = 0.0

class OutputResult(BaseModel):
    xray_clean: List[XRayCleanRow] = []
    cerebro_clean: List[CerebroCleanRow] = []
    magnet_clean: List[MagnetCleanRow] = []
    differentiation: DifferentiationInput = DifferentiationInput()
    
    # Blockers tracking
    blockers: List[str] = []
    
    # Overarching Scores
    demand_score: float = 0
    keyword_score: float = 0
    entry_score: float = 0
    differentiation_score: float = 0
    base_score: float = 0
    final_score: float = 0
    decision: str = "REJECT"
