from pypdf import PdfReader
from langchain.text_splitter import RecursiveCharacterTextSplitter

reader = PdfReader("Specifications.pdf")

text = ""

for page in reader.pages:
    page_text = page.extract_text()
    
    if page_text:
        text += page_text
        
        splitter = RecursiveCharacterTextSplitter(
        chunk_size=1000,
        chunk_overlap=200
)

chunks = splitter.split_text(text)

print("Total Chunks:", len(chunks))
print("\nFirst Chunk:\n")
print(chunks[0])