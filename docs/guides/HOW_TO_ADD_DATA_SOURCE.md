# How to Add a New Data Source
**Step-by-Step Tutorial for Extending the RAG System**

**Difficulty**: Intermediate  
**Time Required**: 30-60 minutes  
**Prerequisites**: Python 3.11+, basic understanding of the system

---

## 📋 Overview

This guide walks through adding a **new data source** (e.g., FAQs, documentation, customer reviews) to the RAG system. You'll learn how to:

1. Generate or collect raw data
2. Clean and prepare data
3. Add a new ChromaDB collection
4. Update API endpoints
5. Test the new data source

---

## 🎯 Example: Adding FAQ Data

We'll add a **FAQ collection** for common customer questions.

---

## Step 1: Create Data Generation Script

**File**: `Datasets/data_faqs.py`

```python
"""
Generate FAQ dataset for customer service
"""
from datasets import load_dataset
import pandas as pd
import json

def generate_faq_data():
    """Generate FAQ data from multiple sources"""
    
    # Option 1: Use Hugging Face dataset
    # Example: Customer support FAQ dataset
    dataset = load_dataset("squad", split="train[:500]")  # Use Q&A dataset
    
    faqs = []
    for item in dataset:
        faq = {
            "question": item["question"],
            "answer": item["context"][:300],  # Truncate long answers
            "category": "general",  # Add categories as needed
            "metadata": {
                "source": "squad",
                "confidence": "high"
            }
        }
        faqs.append(faq)
    
    # Option 2: Manual FAQ data
    manual_faqs = [
        {
            "question": "What is your return policy?",
            "answer": "We offer 30-day returns on all products. Items must be unused and in original packaging.",
            "category": "returns",
            "metadata": {"source": "manual", "priority": "high"}
        },
        {
            "question": "How long does shipping take?",
            "answer": "Standard shipping takes 5-7 business days. Express shipping is 2-3 business days.",
            "category": "shipping",
            "metadata": {"source": "manual", "priority": "high"}
        }
    ]
    
    faqs.extend(manual_faqs)
    
    # Save raw data
    df = pd.DataFrame(faqs)
    df.to_csv("data/raw/faqs_raw.csv", index=False)
    print(f"✅ Generated {len(faqs)} FAQ entries")
    print(f"   Saved to: data/raw/faqs_raw.csv")
    
    return faqs

if __name__ == "__main__":
    generate_faq_data()
```

**Run the script**:

```powershell
python Datasets/data_faqs.py
```

**Expected Output**:
```
✅ Generated 502 FAQ entries
   Saved to: data/raw/faqs_raw.csv
```

---

## Step 2: Clean and Prepare Data

**Extend**: `Datasets/clean_data_universal.py`

Add a new cleaning function:

```python
def clean_faqs(input_path: str, output_path: str):
    """Clean FAQ data"""
    
    df = pd.read_csv(input_path)
    
    # Remove duplicates
    df = df.drop_duplicates(subset=['question', 'answer'])
    
    # Remove empty entries
    df = df.dropna(subset=['question', 'answer'])
    
    # Standardize text
    df['question'] = df['question'].str.strip()
    df['answer'] = df['answer'].str.strip()
    
    # Filter out very short answers (< 20 chars)
    df = df[df['answer'].str.len() >= 20]
    
    # Add unique ID
    df['id'] = ['faq_' + str(i).zfill(4) for i in range(len(df))]
    
    # Save cleaned data
    df.to_csv(output_path, index=False)
    print(f"✅ Cleaned {len(df)} FAQ entries")
    print(f"   Saved to: {output_path}")
    
    return df

# Add to main() function
def main():
    # ... existing cleaning code ...
    
    # Add FAQ cleaning
    clean_faqs(
        input_path="data/raw/faqs_raw.csv",
        output_path="data/cleaned/faqs_cleaned.csv"
    )
```

**Run the cleaner**:

```powershell
python Datasets/clean_data_universal.py
```

**Expected Output**:
```
✅ Cleaned 498 FAQ entries
   Saved to: data/cleaned/faqs_cleaned.csv
```

---

## Step 3: Update Vector Database Ingestion

**File**: `scripts/initialize_vectordb.py`

Add FAQ preparation function:

```python
def prepare_faq_documents():
    """Prepare FAQ documents for ingestion"""
    
    df = pd.read_csv("data/cleaned/faqs_cleaned.csv")
    
    documents = []
    metadatas = []
    ids = []
    
    for _, row in df.iterrows():
        # Combine question and answer for embedding
        text = f"Q: {row['question']}\nA: {row['answer']}"
        
        documents.append(text)
        metadatas.append({
            "id": row['id'],
            "question": row['question'],
            "category": row.get('category', 'general'),
            "source": "faq",
            "confidence": row.get('metadata', {}).get('confidence', 'medium')
        })
        ids.append(row['id'])
    
    return documents, metadatas, ids

# Add to main initialization
def initialize_all_collections():
    """Initialize all collections including FAQs"""
    
    # ... existing collections ...
    
    # Add FAQ collection
    print("\n5. Initializing FAQ collection...")
    faq_docs, faq_meta, faq_ids = prepare_faq_documents()
    
    faq_collection = chroma_client.get_or_create_collection(
        name="faqs",
        embedding_function=embedding_function
    )
    
    # Add in batches (ChromaDB limit: 5000 per batch)
    batch_size = 500
    for i in range(0, len(faq_docs), batch_size):
        batch_docs = faq_docs[i:i+batch_size]
        batch_meta = faq_meta[i:i+batch_size]
        batch_ids = faq_ids[i:i+batch_size]
        
        faq_collection.add(
            documents=batch_docs,
            metadatas=batch_meta,
            ids=batch_ids
        )
    
    print(f"✅ Added {len(faq_docs)} FAQ documents to 'faqs' collection")
```

**Run the initialization**:

```powershell
python scripts/initialize_vectordb.py
```

**Expected Output**:
```
5. Initializing FAQ collection...
✅ Added 498 FAQ documents to 'faqs' collection
```

---

## Step 4: Update API Endpoints

**File**: `backend/main.py`

### 4.1 Add FAQ to Collection List

```python
# Update VALID_COLLECTIONS
VALID_COLLECTIONS = ["blogs", "products", "support", "social", "reviews", "faqs"]  # ADD 'faqs'
```

### 4.2 Update Retrieval Endpoint

```python
# The /v1/retrieve endpoint already supports dynamic collections
# No changes needed - it will automatically work with 'faqs'

# Test it works:
@app.get("/v1/stats")
async def get_stats():
    """Get system statistics"""
    stats = {
        "collections": {
            "blogs": count_documents("blogs"),
            "products": count_documents("products"),
            "support": count_documents("support"),
            "social": count_documents("social"),
            "reviews": count_documents("reviews"),
            "faqs": count_documents("faqs")  # ADD THIS
        }
    }
    return stats
```

### 4.3 (Optional) Create Dedicated FAQ Endpoint

```python
@app.post("/v1/support/faq-search")
async def search_faqs(request: FAQSearchRequest):
    """Search FAQs for similar questions"""
    
    results = retrieve_similar(
        query=request.query,
        collection_name="faqs",
        top_k=request.top_k or 5
    )
    
    # Format FAQ-specific response
    formatted = []
    for result in results:
        formatted.append({
            "question": result["metadata"]["question"],
            "answer": result["text"].split("A: ")[1],  # Extract answer
            "category": result["metadata"]["category"],
            "similarity": result["similarity"]
        })
    
    return {"query": request.query, "faqs": formatted}
```

---

## Step 5: Test the New Data Source

### 5.1 Verify Collection Exists

```python
# Test script: scripts/test_faq_collection.py

import chromadb
from chromadb.utils import embedding_functions

# Connect to ChromaDB
client = chromadb.PersistentClient(path="data/chroma_db")
embedding_fn = embedding_functions.SentenceTransformerEmbeddingFunction(
    model_name="all-MiniLM-L6-v2"
)

# Get FAQ collection
faq_collection = client.get_collection(name="faqs", embedding_function=embedding_fn)

# Check count
count = faq_collection.count()
print(f"✅ FAQ collection has {count} documents")

# Sample query
results = faq_collection.query(
    query_texts=["How do I return a product?"],
    n_results=3
)

print("\n📋 Sample results:")
for i, doc in enumerate(results["documents"][0]):
    print(f"{i+1}. {doc[:100]}...")
```

**Run the test**:

```powershell
python scripts/test_faq_collection.py
```

**Expected Output**:
```
✅ FAQ collection has 498 documents

📋 Sample results:
1. Q: What is your return policy?
   A: We offer 30-day returns on all products...
2. Q: How do I start a return?
   A: Log in to your account, go to Orders...
3. Q: Are returns free?
   A: Yes, we provide free return shipping labels...
```

### 5.2 Test API Endpoint

```python
# Test via API
import requests

response = requests.post("http://localhost:8000/v1/retrieve", json={
    "query": "return policy",
    "collections": ["faqs"],
    "top_k": 3
})

print(response.json())
```

**Expected Response**:
```json
{
  "query": "return policy",
  "results": [
    {
      "id": "faq_0042",
      "text": "Q: What is your return policy?\nA: We offer 30-day returns...",
      "metadata": {
        "question": "What is your return policy?",
        "category": "returns",
        "source": "faq"
      },
      "similarity": 0.91
    }
  ]
}
```

### 5.3 Test with Content Generation

```python
# Use FAQ data in support reply generation
response = requests.post("http://localhost:8000/v1/support/reply", json={
    "message": "How do I return a broken item?",
    "intent": "inquiry"
})

print(response.json()["reply"])
```

**Expected**: Reply should reference FAQ data and provide accurate return policy info.

---

## 🎯 Quick Reference Checklist

- [x] **Step 1**: Create `Datasets/data_faqs.py` → Generate raw data
- [x] **Step 2**: Update `Datasets/clean_data_universal.py` → Add cleaning function
- [x] **Step 3**: Update `scripts/initialize_vectordb.py` → Add preparation function
- [x] **Step 4**: Update `backend/main.py` → Add to VALID_COLLECTIONS
- [x] **Step 5**: Test collection, API, and generation

---

## 📚 Common Data Source Types

### **1. Documentation Pages**

```python
# Scrape documentation
from bs4 import BeautifulSoup
import requests

def scrape_docs(url: str):
    response = requests.get(url)
    soup = BeautifulSoup(response.content, 'html.parser')
    
    # Extract text from documentation
    docs = []
    for section in soup.find_all('section'):
        docs.append({
            "title": section.find('h2').text,
            "content": section.get_text(strip=True),
            "url": url
        })
    
    return docs
```

### **2. Customer Reviews**

```python
# Already implemented in data_reviews.py
# Can extend with more sources (Trustpilot, G2, etc.)
```

### **3. Internal Knowledge Base**

```python
# Load from existing databases
import sqlite3

def load_from_database():
    conn = sqlite3.connect("knowledge_base.db")
    df = pd.read_sql_query("SELECT * FROM articles", conn)
    return df
```

### **4. PDF Documents**

```python
# Extract text from PDFs
import PyPDF2

def extract_pdf_text(pdf_path: str):
    with open(pdf_path, 'rb') as file:
        reader = PyPDF2.PdfReader(file)
        text = ""
        for page in reader.pages:
            text += page.extract_text()
    return text
```

---

## 🔧 Troubleshooting

### **Issue**: Collection not found

```python
# Error: Collection 'faqs' does not exist
# Solution: Run initialize_vectordb.py
python scripts/initialize_vectordb.py
```

### **Issue**: Duplicate IDs

```python
# Error: IDs must be unique
# Solution: Ensure unique IDs in cleaning step
df['id'] = ['faq_' + str(i).zfill(4) for i in range(len(df))]
```

### **Issue**: Poor retrieval quality

```python
# Solution: Improve text representation
# Combine multiple fields for better context
text = f"Category: {category}\nQ: {question}\nA: {answer}"
```

---

## 📖 Related Documentation

- **Data Management Guide**: `docs/guides/DATA_MANAGEMENT_GUIDE.md`
- **Architecture Overview**: `docs/architecture/AGENT_ARCHITECTURE.md`
- **API Reference**: `docs/api/API_REFERENCE.md`

---

**Last Updated**: November 19, 2025  
**Version**: 1.0  
**Status**: ✅ Complete
