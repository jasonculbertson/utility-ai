from fpdf import FPDF
import os

def create_test_pdf():
    # Create a PDF with the test bill content
    pdf = FPDF()
    pdf.add_page()
    pdf.set_font("Arial", size=12)
    
    # Read the text file
    with open('test_bill.txt', 'r') as f:
        content = f.read()
    
    # Split by lines and add to PDF
    lines = content.split('\n')
    for line in lines:
        pdf.cell(200, 10, txt=line, ln=True)
    
    # Create directory if it doesn't exist
    if not os.path.exists('bills_to_process'):
        os.makedirs('bills_to_process')
    
    # Save the PDF
    output_file = 'bills_to_process/test_bill.pdf'
    pdf.output(output_file)
    print(f"Created test PDF at {output_file}")

if __name__ == "__main__":
    create_test_pdf()
