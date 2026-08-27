from pypdf import PdfReader

pdf_file = "Specifications.pdf"

reader = PdfReader(pdf_file)

text = ""

for page in reader.pages:
    page_text = page.extract_text()
    
    if page_text:
        text += page_text
        
        print(text[:1000])