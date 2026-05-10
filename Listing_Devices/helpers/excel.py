import openpyxl
from openpyxl.styles import PatternFill
import re

class ExcelHelper:
    def __init__(self, excel_file):
        self.excel_file = excel_file
        self.data=None

    def write_data_to_excel(self, data):
        wb = openpyxl.Workbook()
        ws = wb.active
        ws.title = "All Devices"
        
        # Header with bold/standard styling
        ws.append(["File Name", "No Case", "Colour Conn", "APPAREIL REP"])
        
        # Define high-readability fills (soft versions of the requested colors)
        red_fill = PatternFill(start_color="FFC7CE", end_color="FFC7CE", fill_type="solid")        
        yellow_fill = PatternFill(start_color="FEF9C3", end_color="FEF9C3", fill_type="solid")  # Light Yellow
        green_fill = PatternFill(start_color="DCFCE7", end_color="DCFCE7", fill_type="solid")   # Light Green
        
        prev_file = None
        color_cycle = [red_fill, yellow_fill, green_fill]
        color_index = -1
        
        for row in data:
            filename = row[0]
            tokens = row[1]
            
            # Change color only when filename changes
            if filename != prev_file:
                color_index = (color_index + 1) % len(color_cycle)
                prev_file = filename
            
            current_fill = color_cycle[color_index]
            
            # Prepare row data
            if isinstance(tokens, list):
                row_data = [filename] + tokens
            else:
                row_data = [filename, tokens]
            
            # Append row
            ws.append(row_data)
            
            # Apply color to the newly added row
            current_row_idx = ws.max_row
            for cell in ws[current_row_idx]:
                cell.fill = current_fill
                
        wb.save(self.excel_file)
    
        