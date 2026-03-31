from typing import List, Tuple, Dict
from collections import defaultdict
import statistics

from analytics_engine.models import (
    XRayCleanRow, CerebroCleanRow, DifferentiationInput,
    BlockerCode, get_blocker_message, OutputResult
)

# Helpers to calculate blockers

def evaluate_demand_blockers(xray_data: List[XRayCleanRow]) -> Tuple[List[str], Dict[str, float]]:
    blockers = []
    if not xray_data:
        return [get_blocker_message(BlockerCode.RC_01, "No valid XRay data")], {}
        
    revenues = sorted([r.revenue_clean for r in xray_data], reverse=True)
    reviews = [r.reviews for r in xray_data]
    
    total_rev = sum(revenues)
    median_rev = statistics.median(revenues) if revenues else 0
    top3_share = sum(revenues[:3]) / total_rev if total_rev > 0 else 0
    
    review_barrier = statistics.median(reviews) if reviews else 0
    asin_count_3k = sum(1 for r in revenues if r >= 3000)
    
    # Blockers
    if median_rev < 5000:
        blockers.append(get_blocker_message(BlockerCode.RC_01, "Low demand"))
    if top3_share > 0.6:
        blockers.append(get_blocker_message(BlockerCode.RC_04, "Revenue concentration"))
    if review_barrier > 300:
        blockers.append(get_blocker_message(BlockerCode.RC_02, "High competition"))
    if asin_count_3k < 5:
        blockers.append(get_blocker_message(BlockerCode.RC_01, "Low demand depth"))
        
    metrics = {
        "Median_Revenue": median_rev,
        "Top3_Revenue_Share": top3_share,
        "Review_Barrier": review_barrier,
        "ASIN_Count_3K": asin_count_3k
    }
    return blockers, metrics

def evaluate_keyword_blockers(cerebro_data: List[CerebroCleanRow]) -> Tuple[List[str], Dict[str, float]]:
    blockers = []
    if not cerebro_data:
        return [get_blocker_message(BlockerCode.RC_03, "No Keyword data")], {}
        
    volumes = [r.search_volume for r in cerebro_data]
    max_sv = max(volumes) if volumes else 0
    
    relevant_count = sum(1 for r in cerebro_data if "irrelevant" not in r.relevance_tag.lower())
    relevance_pct = relevant_count / len(cerebro_data) if cerebro_data else 0
    
    kw_count_3000 = sum(1 for v in volumes if v >= 3000)
    
    if max_sv < 3000:
        blockers.append(get_blocker_message(BlockerCode.RC_03, "Weak keyword demand"))
    if relevance_pct < 0.6:
        blockers.append(get_blocker_message(BlockerCode.RC_03, "Irrelevant keywords"))
    if kw_count_3000 < 3:
        blockers.append(get_blocker_message(BlockerCode.RC_03, "Poor keyword spread"))
        
    metrics = {
        "Max_Search_Volume": max_sv,
        "Keyword_Count_3000+": kw_count_3000,
        "Relevance_Percentage": relevance_pct
    }
    return blockers, metrics

def evaluate_entry_blockers(xray_data: List[XRayCleanRow]) -> Tuple[List[str], Dict[str, float]]:
    blockers = []
    if not xray_data:
        return [], {}
        
    # Brand dominance
    brand_revs = defaultdict(float)
    total_rev = 0
    for r in xray_data:
        brand_revs[r.brand] += r.revenue_clean
        total_rev += r.revenue_clean
        
    top_brand_share = max(brand_revs.values()) / total_rev if total_rev > 0 else 0
    brand_dominance = "HIGH" if top_brand_share > 0.50 else "LOW"
    
    prices = [r.price_clean for r in xray_data if r.price_clean > 0]
    avg_price = sum(prices)/len(prices) if prices else 0
    price_ceiling = max(prices) if prices else 0
    threshold = 15.0 # Example arbitrary threshold
    
    if brand_dominance == "HIGH":
        blockers.append(get_blocker_message(BlockerCode.RC_02, "Brand dominance"))
    if price_ceiling < threshold:
        blockers.append(get_blocker_message(BlockerCode.RC_06, "Low pricing power"))
        
    return blockers, {
        "Avg_Price": avg_price,
        "Price_Ceiling": price_ceiling,
        "Brand_Dominance": brand_dominance
    }

def evaluate_differentiation_blocker(diff_input: DifferentiationInput) -> List[str]:
    if diff_input.feasibility.upper() == "NONE":
        return [get_blocker_message(BlockerCode.RC_05, "No differentiation")]
    return []
