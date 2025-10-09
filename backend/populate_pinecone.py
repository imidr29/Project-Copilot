from database import Database
from langchain_openai import OpenAIEmbeddings
from pinecone import Pinecone
import os
from dotenv import load_dotenv

load_dotenv()

db = Database()
embeddings = OpenAIEmbeddings(api_key=os.getenv("OPENAI_API_KEY"))
pc = Pinecone(api_key=os.getenv("PINECONE_API_KEY"))
index = pc.Index("oee-semantic")

# Fetch data to embed (e.g., from Factory_Equipment_Logs)
results = db.execute_query("SELECT id, reason, issue FROM Factory_Equipment_Logs WHERE reason IS NOT NULL OR issue IS NOT NULL LIMIT 100")
vectors = []
for row in results:
    text = f"Reason: {row.get('reason', '')} Issue: {row.get('issue', '')}".strip()
    if text:
        vector = embeddings.embed_query(text)
        vectors.append({"id": str(row['id']), "values": vector, "metadata": {"text": text, "type": "downtime"}})

# Upsert to Pinecone
if vectors:
    index.upsert(vectors=vectors)
print(f"Upserted {len(vectors)} vectors to Pinecone")