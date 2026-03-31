import re
from typing import List, Dict
import pandas as pd
from analytics_engine.models import (
    XRayRawRow, XRayCleanRow,
    CerebroRawRow, CerebroCleanRow,
    MagnetRawRow, MagnetCleanRow
)

def clean_currency(val: str) -> float:
    if not val:
        return 0.0
    # Remove $, commas and other non-numeric chars except dot
    clean_str = re.sub(r'[^\d.]', '', str(val))
    try:
        return float(clean_str) if clean_str else 0.0
    except ValueError:
        return 0.0

def clean_xray_data(raw_data: List[XRayRawRow]) -> List[XRayCleanRow]:
    cleaned = []
    seen_asins = set()
    
    for row in raw_data:
        # Rule 2: Remove duplicate ASINs
        asin = row.asin.strip()
        if not asin or asin in seen_asins:
            continue
        seen_asins.add(asin)
        
        # Rule 3: Normalize currency
        price_clean = clean_currency(row.price_raw)
        revenue_clean = clean_currency(row.revenue_raw)
        
        # Rule 1: Remove empty revenue rows
        if revenue_clean <= 0:
            continue
            
        cleaned.append(XRayCleanRow(
            asin=asin,
            product_title=row.product_title or "",
            brand=row.brand or "UNKNOWN",
            price_clean=price_clean,
            revenue_clean=revenue_clean,
            sales=row.sales,
            reviews=row.reviews,
            rating=row.rating,
            valid_row="KEEP"
        ))
        
    return cleaned

def clean_cerebro_data(raw_data: List[CerebroRawRow]) -> List[CerebroCleanRow]:
    cleaned = []
    
    for row in raw_data:
        kw = row.keyword.strip()
        if not kw: continue
        
        # Rule 4: Filter keyword noise (< 100 volume)
        if row.search_volume < 100:
            continue
            
        # Rule 5: Remove irrelevant keywords (simulated by manual tag for now)
        if "irrelevant" in (row.relevance_tag or "").lower():
            continue
            
        cleaned.append(CerebroCleanRow(
            keyword=kw,
            search_volume=row.search_volume,
            competing_products=row.competing_products,
            ranking_asin_count=row.ranking_asin_count,
            relevance_tag=row.relevance_tag or "Manual",
            valid_keyword="KEEP"
        ))
        
    return cleaned

def clean_magnet_data(raw_data: List[MagnetRawRow]) -> List[MagnetCleanRow]:
    cleaned = []
    
    for row in raw_data:
        kw = row.keyword.strip()
        if not kw: continue
        
        # Validation
        if row.search_volume < 100:
            continue
            
        cleaned.append(MagnetCleanRow(
            keyword=kw,
            search_volume=row.search_volume,
            match_type=row.match_type or "",
            valid="KEEP"
        ))
        
    return cleaned
