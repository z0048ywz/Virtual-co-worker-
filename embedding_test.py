from sentence_transformers import SentenceTransformer

model = SentenceTransformer(
	"all-MiniLM-L6-v2"
)

texts = [
	"Compressor specification",
	"Maintenance procedure",
	"Risk assessment"
]

embeddings = model.encode(texts)

print(embeddings.shape)