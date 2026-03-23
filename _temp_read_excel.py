import zipfile
import xml.etree.ElementTree as ET
import json
import re

def col2num(col):
    num = 0
    for c in col:
        if c in 'ABCDEFGHIJKLMNOPQRSTUVWXYZ':
            num = num * 26 + (ord(c.upper()) - ord('A')) + 1
    return num

def read_xlsx_headers(filepath):
    try:
        with zipfile.ZipFile(filepath, 'r') as z:
            shared_strings = []
            if 'xl/sharedStrings.xml' in z.namelist():
                with z.open('xl/sharedStrings.xml') as f:
                    tree = ET.parse(f)
                    root = tree.getroot()
                    ns = {'ns': root.tag.split('}')[0].strip('{')} if '}' in root.tag else {}
                    for si in root.findall('.//ns:si', ns) if ns else root.findall('.//si'):
                        t = si.find('.//ns:t', ns) if ns else si.find('.//t')
                        shared_strings.append(t.text if t is not None else "")
            
            sheet_name = 'xl/worksheets/sheet1.xml'
            with z.open(sheet_name) as f:
                tree = ET.parse(f)
                root = tree.getroot()
                ns = {'ns': root.tag.split('}')[0].strip('{')} if '}' in root.tag else {}
                
                rows_data = []
                for row in root.findall('.//ns:row', ns) if ns else root.findall('.//row'):
                    row_idx = int(row.attrib.get('r'))
                    # Pad rows if some were skipped
                    while len(rows_data) < row_idx - 1:
                        rows_data.append([])
                    
                    row_vals = []
                    last_col_num = 0
                    for c in row.findall('.//ns:c', ns) if ns else row.findall('.//c'):
                        ref = c.attrib.get('r')
                        col_str = re.match(r"([A-Z]+)", ref).group(1)
                        col_num = col2num(col_str)
                        
                        while last_col_num < col_num - 1:
                            row_vals.append("")
                            last_col_num += 1
                            
                        v = c.find('ns:v', ns) if ns else c.find('v')
                        val = ""
                        if v is not None:
                            val = v.text
                            if c.attrib.get('t') == 's': # shared string
                                val = shared_strings[int(val)]
                        row_vals.append(val)
                        last_col_num += 1
                        
                    rows_data.append(row_vals)
                    if len(rows_data) >= 15: # first 15 rows
                        break
                return rows_data
    except Exception as e:
        return str(e)

with open('_temp_excel_dump.json', 'w', encoding='utf-8') as f:
    json.dump(read_xlsx_headers('specimen_format.xlsx'), f, indent=2)
