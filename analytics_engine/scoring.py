from typing import Dict
from analytics_engine.models import OutputResult

def calculate_scores(
    demand_metrics: Dict[str, float],
    kw_metrics: Dict[str, float],
    entry_metrics: Dict[str, float]
) -> Dict[str, float]:
    
    # 1. Demand Score Component
    # We map arbitrary healthy metrics to a 0-10 scale for the sake of the engine demo
    median_rev = demand_metrics.get("Median_Revenue", 0)
    top3_share = demand_metrics.get("Top3_Revenue_Share", 1.0)
    asin_3k = demand_metrics.get("ASIN_Count_3K", 0)
    
    median_score = min(10, median_rev / 1500)  # Caps at ~15k
    dist_score = 10 if top3_share < 0.4 else max(0, 10 - (top3_share - 0.4)*20)
    consistency_score = 7.0 # placeholder
    depth_score = min(10, asin_3k)

    demand_total = (median_score * 0.15) + (dist_score * 0.10) + (consistency_score * 0.10) + (depth_score * 0.05)
    
    # 2. Keyword Component
    max_sv = kw_metrics.get("Max_Search_Volume", 0)
    kw_3k = kw_metrics.get("Keyword_Count_3000+", 0)
    rel_pct = kw_metrics.get("Relevance_Percentage", 0)
    
    vol_score = min(10, max_sv / 1000)
    rel_score = rel_pct * 10
    spread_score = min(10, kw_3k * 2)
    longtail_score = 5.0 # Placeholder
    
    kw_total = (vol_score * 0.10) + (rel_score * 0.05) + (spread_score * 0.05) + (longtail_score * 0.05)
    
    # 3. Entry Component
    avg_price = entry_metrics.get("Avg_Price", 0)
    dom = entry_metrics.get("Brand_Dominance", "HIGH")
    
    comp_score = 2 if dom == "HIGH" else 8
    price_flex = min(10, max(0, (avg_price - 10) / 2)) # Caps at $30
    
    entry_total = (comp_score * 0.10) + (price_flex * 0.10)
    
    return {
        "demand_total": demand_total, # max 4.0
        "keyword_total": kw_total, # max 2.5
        "entry_total": entry_total # max 2.0
    }

def orchestrate_scoring(result: OutputResult, scores_map: Dict[str, float], diff_score: float) -> OutputResult:
    d_tot = scores_map.get("demand_total", 0)
    k_tot = scores_map.get("keyword_total", 0)
    e_tot = scores_map.get("entry_total", 0)
    
    base_score = d_tot + k_tot + e_tot # Out of 8.5 potential if weighted exactly as percentages, but user specified formulas:
    
    # Actually the user prompt:
    # Demand = (Median*0.15 + ...) -> max 4.0 (implies out of 10, total 0.40)
    # The actual percentages match 0.4, 0.25, 0.2
    
    final_score = base_score + (diff_score * 0.15) # max 10
    
    result.demand_score = d_tot
    result.keyword_score = k_tot
    result.entry_score = e_tot
    result.differentiation_score = diff_score
    result.base_score = base_score
    result.final_score = final_score
    
    # Decision Logic
    bc = len(result.blockers)
    if bc > 2:
        result.decision = "REJECT"
    else:
        if final_score >= 7.5:
            result.decision = "ACCEPT"
        elif final_score >= 6.0:
            result.decision = "CONDITIONAL"
        else:
            result.decision = "REJECT"
            
    return result
