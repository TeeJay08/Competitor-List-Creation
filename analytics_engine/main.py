from typing import List
from analytics_engine.models import (
    XRayRawRow, CerebroRawRow, MagnetRawRow, DifferentiationInput, OutputResult
)
from analytics_engine.cleaning import clean_xray_data, clean_cerebro_data, clean_magnet_data
from analytics_engine.evaluator import (
    evaluate_demand_blockers, evaluate_keyword_blockers,
    evaluate_entry_blockers, evaluate_differentiation_blocker
)
from analytics_engine.scoring import calculate_scores, orchestrate_scoring
from analytics_engine.dashboard_exporter import create_7_sheet_dashboard

def run_analytics_pipeline(
    xray_raw: List[XRayRawRow],
    cerebro_raw: List[CerebroRawRow],
    magnet_raw: List[MagnetRawRow],
    diff_input: DifferentiationInput,
    output_filename: str = "Validation_Dashboard.xlsx"
) -> str:
    # 1. Cleaning
    xray_clean = clean_xray_data(xray_raw)
    cerebro_clean = clean_cerebro_data(cerebro_raw)
    magnet_clean = clean_magnet_data(magnet_raw)
    
    # Initialize Tracking
    result = OutputResult(
        xray_clean=xray_clean,
        cerebro_clean=cerebro_clean,
        magnet_clean=magnet_clean,
        differentiation=diff_input
    )
    
    # 2. Blockers & Metrics Evaluation
    # Sheet 1 Demand
    demand_blockers, demand_metrics = evaluate_demand_blockers(xray_clean)
    
    # Sheet 2 Keywords
    kw_blockers, kw_metrics = evaluate_keyword_blockers(cerebro_clean)
    
    # Sheet 4 Entry
    entry_blockers, entry_metrics = evaluate_entry_blockers(xray_clean)
    
    # Sheet 5 Differentiation
    diff_blockers = evaluate_differentiation_blocker(diff_input)
    
    # Assemble ALL blockers
    all_blockers = demand_blockers + kw_blockers + entry_blockers + diff_blockers
    result.blockers = all_blockers
    
    # 3. Scoring
    scores_map = calculate_scores(demand_metrics, kw_metrics, entry_metrics)
    
    # Orchestrate final score & decision
    result = orchestrate_scoring(result, scores_map, diff_input.score)
    
    # 4. Generate Dashboard
    final_file = create_7_sheet_dashboard(result, output_filename)
    
    return final_file
