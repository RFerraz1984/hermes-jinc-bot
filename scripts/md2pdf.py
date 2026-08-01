#!/usr/bin/env python3
"""Convert markdown to accessible PDF using fpdf2 + markdown2."""
import sys
import markdown2
from fpdf import FPDF
from pathlib import Path

class AccessiblePDF(FPDF):
    def __init__(self):
        super().__init__()
        self.set_auto_page_break(auto=True, margin=25)
        # Add Unicode font (DejaVu Sans - should be available)
        self.add_font("DejaVu", "", "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf", uni=True)
        self.add_font("DejaVu", "B", "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf", uni=True)
        self.add_font("DejaVu", "I", "/usr/share/fonts/truetype/dejavu/DejaVuSans-Oblique.ttf", uni=True)
        self.add_font("DejaVu", "BI", "/usr/share/fonts/truetype/dejavu/DejaVuSans-BoldOblique.ttf", uni=True)
        
    def header(self):
        if self.page_no() > 1:
            self.set_font("DejaVu", "I", 8)
            self.set_text_color(100, 100, 100)
            self.cell(0, 5, "Jornalista Inclusivo - Consultoria em Acessibilidade", align="C")
            self.ln(8)
    
    def footer(self):
        self.set_y(-20)
        self.set_font("DejaVu", "I", 8)
        self.set_text_color(100, 100, 100)
        self.cell(0, 10, f"Página {self.page_no()}/{{nb}}", align="C")

def md_to_pdf(md_path, pdf_path):
    # Read markdown
    with open(md_path, 'r', encoding='utf-8') as f:
        md_content = f.read()
    
    # Convert to HTML
    html = markdown2.markdown(md_content, extras=['tables', 'fenced-code-blocks', 'header-ids'])
    
    # Create PDF
    pdf = AccessiblePDF()
    pdf.alias_nb_pages()
    pdf.add_page()
    
    # Simple HTML to PDF rendering (basic)
    pdf.set_font("DejaVu", "", 11)
    pdf.set_text_color(30, 30, 30)
    
    # For simplicity, render as plain text with basic formatting
    lines = md_content.split('\n')
    for line in lines:
        line = line.strip()
        if not line:
            pdf.ln(4)
            continue
            
        # Headers
        if line.startswith('# '):
            pdf.set_font("DejaVu", "B", 18)
            pdf.set_text_color(44, 95, 138)  # #2c5f8a
            pdf.multi_cell(0, 10, line[2:])
            pdf.ln(4)
        elif line.startswith('## '):
            pdf.set_font("DejaVu", "B", 14)
            pdf.set_text_color(44, 95, 138)
            pdf.multi_cell(0, 8, line[3:])
            pdf.ln(3)
        elif line.startswith('### '):
            pdf.set_font("DejaVu", "B", 12)
            pdf.set_text_color(51, 51, 51)
            pdf.multi_cell(0, 7, line[4:])
            pdf.ln(2)
        # Bold/italic inline (simple)
        elif line.startswith('- ') or line.startswith('* '):
            pdf.set_font("DejaVu", "", 11)
            pdf.set_text_color(30, 30, 30)
            pdf.cell(10)
            pdf.multi_cell(0, 6, "• " + line[2:])
        elif line.startswith('|') and '|' in line[1:]:  # Table row
            pdf.set_font("DejaVu", "", 9)
            pdf.set_text_color(30, 30, 30)
            cells = [c.strip() for c in line.split('|')[1:-1]]
            col_w = 190 / max(len(cells), 1)
            for c in cells:
                pdf.cell(col_w, 6, c[:int(col_w/2)], border=1)
            pdf.ln()
        else:
            pdf.set_font("DejaVu", "", 11)
            pdf.set_text_color(30, 30, 30)
            pdf.multi_cell(0, 6, line)
            pdf.ln(1)
    
    # Save
    pdf.output(pdf_path)
    print(f"PDF gerado: {pdf_path}")

if __name__ == "__main__":
    if len(sys.argv) != 3:
        print("Uso: python3 md2pdf.py <input.md> <output.pdf>")
        sys.exit(1)
    md_to_pdf(sys.argv[1], sys.argv[2])
