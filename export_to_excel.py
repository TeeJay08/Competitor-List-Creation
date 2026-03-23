import openpyxl
from openpyxl.utils import get_column_letter
from openpyxl.styles import Alignment, Border, Side, Font

def apply_solid_border(cell):
    thin = Side(border_style="thin", color="000000")
    cell.border = Border(top=thin, left=thin, right=thin, bottom=thin)

def make_hyperlink(cell, link_str):
    if link_str and str(link_str).startswith("http"):
        cell.hyperlink = link_str
        cell.font = Font(name="Arial", size=10, color="0563C1", underline="single")
        
def export_products_to_excel(products_data, keyword="BATTEL ROPES", filename="competitors_output.xlsx"):
    wb = openpyxl.Workbook()
    ws = wb.active
    ws.title = "Competitors"
    
    title_str = f"{keyword.upper()} COMPETITORS" if keyword else "COMPETITORS"
    ws["B1"] = title_str
    ws["B1"].font = Font(name="Lora", bold=True, size=14)
    
    for idx, product in enumerate(products_data):
        block_idx = idx // 3
        col_idx = idx % 3
        
        start_col = 2 + (col_idx * 4)
        label_col = get_column_letter(start_col)
        data_col = get_column_letter(start_col + 1)
        
        row_offset = block_idx * 16 # Provide spacing between blocks
        
        # Helper to set label styling
        def set_label(base_row, text):
            r = base_row + row_offset
            c = ws[f"{label_col}{r}"]
            c.value = str(text).upper()
            c.font = Font(name="Lora", size=10, bold=True)
            c.alignment = Alignment(vertical='center', horizontal='left')
            return c
            
        # Helper to set data styling
        def set_data(base_row, val, wrap=False):
            r = base_row + row_offset
            c = ws[f"{data_col}{r}"]
            c.value = val
            c.font = Font(name="Arial", size=10)
            c.alignment = Alignment(horizontal='center', vertical='center', wrapText=wrap)
            return c

        rows_used = []

        # Row 4: AMAZON LINK
        l_cell = set_label(4, "AMAZON LINK")
        d_cell = set_data(4, product.get("amazon_link", ""))
        make_hyperlink(d_cell, product.get("amazon_link", ""))
        rows_used.append(4 + row_offset)
        
        # Row 5: ASIN
        set_label(5, "ASIN ")
        set_data(5, product.get("asin", ""))
        rows_used.append(5 + row_offset)
        
        # Row 6: Brand Name
        set_label(6, "Brand Name")
        set_data(6, product.get("brand_name", ""))
        rows_used.append(6 + row_offset)
        
        # Row 7: MAIN IMAGE
        set_label(7, "MAIN IMAGE")
        img_url = product.get("main_image", "")
        img_cell = set_data(7, "")
        if img_url:
            try:
                import requests
                from openpyxl.drawing.image import Image
                import io
                response = requests.get(img_url, timeout=10)
                if response.status_code == 200:
                    image_stream = io.BytesIO(response.content)
                    img = Image(image_stream)
                    ratio = min(90 / img.width, 90 / img.height)
                    img.width = int(img.width * ratio)
                    img.height = int(img.height * ratio)
                    ws.add_image(img, f"{data_col}{7 + row_offset}")
                    ws.row_dimensions[7 + row_offset].height = 80
                else:
                    img_cell.value = "Image fetch failed"
            except ImportError:
                img_cell.value = "Missing Pillow library"
            except Exception as e:
                img_cell.value = f"Error: {e}"
        else:
            img_cell.value = "No Image"
        rows_used.append(7 + row_offset)
        
        # Row 8: SALES
        set_label(8, "SALES")
        set_data(8, product.get("sales", ""))
        rows_used.append(8 + row_offset)
        
        # Row 9: RATING
        set_label(9, "RATING")
        rating = product.get("rating", "")
        if rating: rating = f"{str(rating).replace('⭐', '').strip()}⭐"
        set_data(9, rating)
        rows_used.append(9 + row_offset)
        
        # Row 10: REVIEWS
        set_label(10, "REVIEWS")
        set_data(10, product.get("number_of_reviews", ""))
        rows_used.append(10 + row_offset)
        
        # Row 11: LAUNCH DATE
        set_label(11, "LAUNCH DATE")
        set_data(11, product.get("launch_date", ""))
        rows_used.append(11 + row_offset)
        
        # Row 12: SELLING PRICE
        set_label(12, "SELLING PRICE")
        sp = product.get("selling_price", 0)
        try: sp = float(sp) if sp else 0.0
        except ValueError: sp = 0.0
        set_data(12, sp)
        rows_used.append(12 + row_offset)
        
        # Row 13: VARIATIONS
        set_label(13, "VARIATIONS")
        vars_list = product.get("variations", [])
        if vars_list:
            var_texts = []
            for v in vars_list:
                asin = v.get("asin", "")
                price = v.get("price", "")
                dim_dict = v.get("dimensions") or {}
                dim_str = ", ".join([f"{k.capitalize()}: {val}" for k, val in dim_dict.items()]) if dim_dict else "N/A"
                var_texts.append(f"ASIN: {asin}\nPrice: {price}\nVariation: {dim_str}")
            set_data(13, "\n\n".join(var_texts), wrap=True)
        else:
            set_data(13, "")
        rows_used.append(13 + row_offset)
        
        # Row 14: BUY IT WITH
        set_label(14, "BUY IT WITH")
        biw = product.get("buy_it_with", [])
        biw_str = "\n\n".join([f"ASIN: {i.get('asin', '')}\nTitle: {i.get('title', '')}\nAmazon Link: {i.get('amazon_link', '')}" for i in biw]) if biw else ""
        set_data(14, biw_str, wrap=True)
        rows_used.append(14 + row_offset)
        
        # Row 15: FREQUENTLY BOUGHT TOGETHER
        set_label(15, "FREQUENTLY BOUGHT TOGETHER")
        fbt = product.get("frequently_bought_together", [])
        fbt_str = "\n\n".join([f"ASIN: {i.get('asin', '')}\nTitle: {i.get('title', '')}\nAmazon Link: {i.get('amazon_link', '')}" for i in fbt]) if fbt else ""
        set_data(15, fbt_str, wrap=True)
        rows_used.append(15 + row_offset)
        
        # Row 16: SALES RANKS
        set_label(16, "SALES RANKS")
        ranks = product.get("sales_ranks", [])
        r_str = "\n\n".join([f"#{r.get('rank', '')} in {r.get('category', '')}" for r in ranks]) if ranks else ""
        set_data(16, r_str, wrap=True)
        rows_used.append(16 + row_offset)
        
        # Apply solid borders
        for r in rows_used:
            apply_solid_border(ws[f"{label_col}{r}"])
            apply_solid_border(ws[f"{data_col}{r}"])
            
        ws.column_dimensions[label_col].width = 30
        ws.column_dimensions[data_col].width = 45

    wb.save(filename)
    print(f"Exported to {filename} successfully.")

if __name__ == "__main__":
    p_example = {
        "brand_name": "KINEOZ",
        "amazon_link": "https://www.amazon.com/dp/B0FHJLX7YP",
        "asin": "B0FHJLX7YP",
        "main_image": "https://m.media-amazon.com/images/I/71u7mHveaML._AC_SL1500_.jpg",
        "sales": "300+",
        "rating": "4.6",
        "number_of_reviews": 29,
        "launch_date": "2025-07-15",
        "selling_price": 69.99,
        "variations": [{"asin": "B123", "price": 10, "dimensions": {"size": "Large"}}],
        "buy_it_with": [{"asin": "C456", "title": "Gloves", "amazon_link": "https://amazon.com/dp/C456"}],
        "frequently_bought_together": [{"asin": "D789", "title": "Mat", "amazon_link": "https://amazon.com/dp/D789"}],
    }
    
    # Test with 5 items to verify wrapping logic
    test_products = [p_example]*5 
    export_products_to_excel(test_products, "TEST KEYWORD", "competitors_output_test.xlsx")
