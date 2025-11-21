# Data Management Guide
**Managing, Updating, and Expanding Your Vector Database**

**Date**: November 19, 2025  
**Version**: 1.0  
**Audience**: Developers, Data Engineers

---

## 📋 Table of Contents

1. [Current Data Structure](#current-data-structure)
2. [Adding Documents to Existing Collections](#adding-documents-to-existing-collections)
3. [Updating Existing Documents](#updating-existing-documents)
4. [Deleting Documents](#deleting-documents)
5. [Adding a NEW Data Source](#adding-a-new-data-source)
6. [Data Versioning Strategy](#data-versioning-strategy)
7. [Backup and Recovery](#backup-and-recovery)
8. [Performance Optimization](#performance-optimization)
9. [Limitations and Constraints](#limitations-and-constraints)

---

## 📊 Current Data Structure

### **Overview**

Your system currently contains **1,085 documents** across **5 collections** in ChromaDB:

| Collection | Documents | Source | Purpose |
|------------|-----------|--------|---------|
| **blogs** | 243 | CNN/DailyMail | Long-form content generation |
| **products** | 197 | Amazon Polarity | Product descriptions, reviews |
| **support** | 272 | Bitext Customer Support | Customer service replies |
| **social** | 177 | GoEmotions | Social media posts |
| **reviews** | 196 | Yelp | Restaurant reviews |
| **TOTAL** | **1,085** | - | - |

### **Storage Location**

```
data/
├── chroma_db/                  # Vector database (persistent)
│   ├── chroma.sqlite3          # Metadata storage
│   └── [embedding files]       # Vector embeddings
├── cleaned/                    # Processed JSON files
│   ├── blogs.json
│   ├── products.json
│   ├── support.json
│   ├── social.json
│   └── reviews.json
├── raw/                        # Original downloaded data
│   ├── blogs/
│   ├── products/
│   └── support/
└── rejected/                   # Quality-filtered rejects
```

### **Document Schema**

Each document follows this structure:

```json
{
  "id": "blog_cnn_001",
  "title": "Article headline or product title",
  "text": "Full content/description/message",
  "metadata": {
    "source": "cnn_dailymail",
    "word_count": 582,
    "char_length": 3421,
    "paragraphs": 12,
    "has_numbers": true
  }
}
```

---

## ➕ Adding Documents to Existing Collections

### **Method 1: Using Python API**

Add documents programmatically to an existing collection:

```python
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent))

from backend.vector_store import (
    initialize_chroma_client,
    create_or_get_collection,
    add_documents
)

# Step 1: Initialize ChromaDB
client = initialize_chroma_client()

# Step 2: Get existing collection
collection = create_or_get_collection("blogs", client)

# Step 3: Prepare new documents
new_docs = [
    {
        "id": "blog_custom_001",
        "text": "This is a new blog post about AI automation in customer service...",
        "metadata": {
            "title": "AI Automation in Customer Service",
            "source": "custom",
            "word_count": 450,
            "date_added": "2025-11-19"
        }
    },
    {
        "id": "blog_custom_002",
        "text": "Another blog post about chatbots and their impact...",
        "metadata": {
            "title": "The Rise of Chatbots",
            "source": "custom",
            "word_count": 380,
            "date_added": "2025-11-19"
        }
    }
]

# Step 4: Add documents (embeddings generated automatically)
add_documents(collection, new_docs, batch_size=50)

print(f"✅ Added {len(new_docs)} documents to 'blogs' collection")

# Step 5: Verify
stats = collection.count()
print(f"📊 Total documents in 'blogs': {stats}")
```

### **Method 2: Bulk Import from JSON File**

Add many documents from a JSON file:

```python
import json
from pathlib import Path
from backend.vector_store import initialize_chroma_client, create_or_get_collection, add_documents

# Load JSON file
with open("data/custom/new_blogs.json", "r", encoding="utf-8") as f:
    new_blogs = json.load(f)

# Prepare documents for ChromaDB
documents = []
for blog in new_blogs:
    documents.append({
        "id": blog["id"],
        "text": blog["text"],
        "metadata": {
            "title": blog.get("title", ""),
            "source": blog["metadata"]["source"],
            "word_count": blog["metadata"]["word_count"]
        }
    })

# Add to collection
client = initialize_chroma_client()
collection = create_or_get_collection("blogs", client)
add_documents(collection, documents, batch_size=100)

print(f"✅ Imported {len(documents)} documents from JSON")
```

### **Method 3: Using initialize_vectordb.py Script**

Extend the existing initialization script:

```python
# In scripts/initialize_vectordb.py, add this function:

def add_custom_data(collection_name: str, json_file: Path):
    """Add custom data to existing collection"""
    print(f"\n📥 Adding custom data to '{collection_name}'...")
    
    # Load data
    with open(json_file, "r", encoding="utf-8") as f:
        data = json.load(f)
    
    # Prepare documents based on collection type
    if collection_name == "blogs":
        documents = prepare_blog_documents(data)
    elif collection_name == "products":
        documents = prepare_product_documents(data)
    # ... add other types
    
    # Get collection
    client = initialize_chroma_client()
    collection = create_or_get_collection(collection_name, client)
    
    # Add documents
    add_documents(collection, documents, batch_size=50)
    
    print(f"✅ Added {len(documents)} documents")
    return len(documents)

# Usage:
# python -c "from scripts.initialize_vectordb import add_custom_data; add_custom_data('blogs', Path('data/custom/blogs.json'))"
```

### **Best Practices for Adding Documents**

1. **Use unique IDs**: Prevent collisions with existing docs
   ```python
   id = f"{collection}_{source}_{timestamp}_{index}"
   # Example: "blogs_custom_20251119_001"
   ```

2. **Batch processing**: Add in batches of 50-100 for performance
   ```python
   add_documents(collection, docs, batch_size=50)
   ```

3. **Metadata consistency**: Include all standard metadata fields
   ```python
   metadata = {
       "source": "custom",
       "word_count": len(text.split()),
       "date_added": datetime.now().isoformat(),
       "version": "1.0"
   }
   ```

4. **Validate before adding**: Check text length, language, etc.
   ```python
   assert len(text) >= 50, "Text too short"
   assert len(text) <= 100000, "Text too long"
   ```

5. **Progress tracking**: Use tqdm for large batches
   ```python
   from tqdm import tqdm
   for i in tqdm(range(0, len(docs), batch_size), desc="Adding docs"):
       batch = docs[i:i+batch_size]
       add_documents(collection, batch)
   ```

---

## 🔄 Updating Existing Documents

ChromaDB doesn't support direct updates. Use **delete + add** pattern:

### **Update Single Document**

```python
from backend.vector_store import initialize_chroma_client, create_or_get_collection

client = initialize_chroma_client()
collection = create_or_get_collection("blogs", client)

# Step 1: Delete old document
document_id = "blog_cnn_001"
collection.delete(ids=[document_id])

# Step 2: Add updated version
updated_doc = {
    "id": document_id,  # Same ID
    "text": "Updated blog content with new information...",
    "metadata": {
        "title": "Updated Title",
        "source": "cnn_dailymail",
        "word_count": 650,
        "updated_at": "2025-11-19T16:30:00",
        "version": "2.0"
    }
}

collection.add(
    ids=[updated_doc["id"]],
    documents=[updated_doc["text"]],
    metadatas=[updated_doc["metadata"]]
)

print(f"✅ Updated document {document_id}")
```

### **Update Multiple Documents**

```python
def update_documents(collection, updates: list[dict]):
    """Update multiple documents efficiently"""
    
    # Step 1: Delete old versions
    old_ids = [doc["id"] for doc in updates]
    collection.delete(ids=old_ids)
    
    # Step 2: Add updated versions
    new_ids = [doc["id"] for doc in updates]
    new_texts = [doc["text"] for doc in updates]
    new_metadata = [doc["metadata"] for doc in updates]
    
    collection.add(
        ids=new_ids,
        documents=new_texts,
        metadatas=new_metadata
    )
    
    print(f"✅ Updated {len(updates)} documents")

# Usage:
updates = [
    {"id": "blog_001", "text": "New content 1...", "metadata": {...}},
    {"id": "blog_002", "text": "New content 2...", "metadata": {...}}
]
update_documents(collection, updates)
```

### **Update Metadata Only**

If only metadata changes (no text change):

```python
# ChromaDB doesn't support metadata-only updates
# Must still use delete + add pattern

document_id = "blog_cnn_001"

# Step 1: Retrieve current document
results = collection.get(ids=[document_id], include=["documents", "metadatas"])
current_text = results["documents"][0]
current_metadata = results["metadatas"][0]

# Step 2: Update metadata
current_metadata["category"] = "AI & Technology"
current_metadata["updated_at"] = "2025-11-19"

# Step 3: Delete + Re-add
collection.delete(ids=[document_id])
collection.add(
    ids=[document_id],
    documents=[current_text],
    metadatas=[current_metadata]
)
```

---

## 🗑️ Deleting Documents

### **Delete by ID**

```python
from backend.vector_store import initialize_chroma_client, create_or_get_collection

client = initialize_chroma_client()
collection = create_or_get_collection("blogs", client)

# Single document
collection.delete(ids=["blog_cnn_001"])

# Multiple documents
collection.delete(ids=["blog_cnn_001", "blog_cnn_002", "blog_cnn_003"])

print("✅ Documents deleted")
```

### **Delete by Metadata Filter**

```python
# Delete all documents from specific source
collection.delete(where={"source": "custom"})

# Delete documents older than specific date
collection.delete(where={"date_added": {"$lt": "2025-01-01"}})

# Delete short documents
collection.delete(where={"word_count": {"$lt": 100}})

print("✅ Filtered documents deleted")
```

### **Delete Entire Collection**

```python
client = initialize_chroma_client()
client.delete_collection(name="blogs")
print("✅ Collection 'blogs' deleted completely")

# Recreate empty collection if needed
collection = client.create_collection(
    name="blogs",
    embedding_function=get_embedding_function()
)
```

### **Safe Deletion with Backup**

```python
import json
from datetime import datetime

def safe_delete(collection, ids: list[str], backup_dir="data/backups"):
    """Delete documents with automatic backup"""
    
    # Step 1: Retrieve documents before deletion
    results = collection.get(ids=ids, include=["documents", "metadatas"])
    
    # Step 2: Save backup
    backup_file = f"{backup_dir}/deleted_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
    backup_data = {
        "ids": results["ids"],
        "documents": results["documents"],
        "metadatas": results["metadatas"]
    }
    
    Path(backup_dir).mkdir(parents=True, exist_ok=True)
    with open(backup_file, "w", encoding="utf-8") as f:
        json.dump(backup_data, f, indent=2)
    
    # Step 3: Delete
    collection.delete(ids=ids)
    
    print(f"✅ Deleted {len(ids)} documents")
    print(f"💾 Backup saved: {backup_file}")

# Usage:
safe_delete(collection, ["blog_001", "blog_002"])
```

---

## 🆕 Adding a NEW Data Source

### **Overview**

To add a completely new data source (e.g., "FAQs", "Emails", "Documentation"):

**Steps**:
1. Create data generation script (download/create data)
2. Add processor to cleaning pipeline
3. Create prepare function for ChromaDB
4. Update API endpoints to query new collection
5. Test retrieval

### **Step 1: Create Data Generation Script**

**File**: `Datasets/data_faqs.py`

```python
"""
Download or generate FAQ data
Dataset: Custom FAQs from JSON/CSV or external API
"""
import json
import os
from pathlib import Path

# Create output directory
Path("data/raw/faqs").mkdir(parents=True, exist_ok=True)

print("Generating FAQ dataset...")

# Option A: Load from JSON file
# with open("external_sources/faqs.json", "r") as f:
#     faqs = json.load(f)

# Option B: Generate synthetic FAQs
faqs = []
faq_data = [
    {
        "question": "What is your return policy?",
        "answer": "We offer a 30-day money-back guarantee on all products. Simply contact support@example.com to initiate a return.",
        "category": "Returns & Refunds"
    },
    {
        "question": "How long does shipping take?",
        "answer": "Standard shipping takes 5-7 business days. Express shipping (2-3 days) is available for an additional fee.",
        "category": "Shipping"
    },
    # Add more FAQs...
]

for i, faq in enumerate(faq_data):
    faqs.append({
        "id": f"faq_{i:03}",
        "title": faq["question"],  # Question as title
        "text": faq["answer"],     # Answer as text
        "metadata": {
            "source": "custom_faqs",
            "category": faq["category"],
            "type": "faq"
        }
    })

print(f"Total FAQs generated: {len(faqs)}")
print(f"Sample FAQ: {faqs[0]['title'][:80]}...")

# Save to raw directory
with open("data/raw/faqs/raw_faqs.json", "w", encoding="utf-8") as f:
    json.dump(faqs, f, indent=2)

print("✓ Saved to data/raw/faqs/raw_faqs.json")
```

**Run**:
```bash
python Datasets/data_faqs.py
```

### **Step 2: Add Processor to Cleaning Pipeline**

**File**: `Datasets/clean_data_universal.py`

Add FAQ processor function:

```python
def process_faqs(raw_file: Path) -> tuple[list, list]:
    """Process FAQ data - keep questions and answers"""
    with open(raw_file, "r", encoding="utf-8") as f:
        items = json.load(f)
    
    cleaned = []
    rejected = []
    seen_texts = set()
    
    for item in tqdm(items, desc=f"Cleaning {raw_file.name}"):
        question = item.get("title", "").strip()  # Question
        answer = item.get("text", "").strip()     # Answer
        
        if not question or not answer:
            rejected.append({"id": item.get("id"), "reason": "missing_data"})
            continue
        
        # Clean text
        cleaned_question = clean_title(question)
        cleaned_answer = clean_text(answer, preserve_paragraphs=False)
        
        # Quality checks
        answer_word_count = len(cleaned_answer.split())
        
        if answer_word_count < 10:  # Answers should be substantial
            rejected.append({"id": item.get("id"), "reason": "too_short", "word_count": answer_word_count})
            continue
        
        if answer_word_count > 1000:
            rejected.append({"id": item.get("id"), "reason": "too_long", "word_count": answer_word_count})
            continue
        
        # Language check
        if not is_english(cleaned_answer):
            rejected.append({"id": item.get("id"), "reason": "not_english"})
            continue
        
        # Deduplication
        text_hash = cleaned_answer[:100]
        if text_hash in seen_texts:
            rejected.append({"id": item.get("id"), "reason": "duplicate"})
            continue
        seen_texts.add(text_hash)
        
        # Store cleaned item
        cleaned.append({
            "id": item.get("id", f"faq_{len(cleaned)}"),
            "title": cleaned_question,  # Question
            "text": cleaned_answer,     # Answer
            "metadata": {
                **item.get("metadata", {}),
                "word_count": answer_word_count,
                "char_length": len(cleaned_answer),
                "has_numbers": bool(re.search(r'\d', cleaned_answer))
            }
        })
    
    return cleaned, rejected
```

Add to PROCESSORS dict:

```python
PROCESSORS = {
    "blogs": process_blogs,
    "products": process_products,
    "support": process_support,
    "social": process_social,
    "reviews": process_reviews,
    "faqs": process_faqs,  # ADD THIS
}
```

Update main() function:

```python
def main():
    """Main cleaning pipeline - process all datasets"""
    # ... existing code ...
    
    # Process FAQs (ADD THIS)
    faq_files = list((RAW_DIR / "faqs").glob("*.json")) if (RAW_DIR / "faqs").exists() else []
    for faq_file in faq_files:
        process_dataset("faqs", faq_file)
        datasets_processed += 1
```

**Run**:
```bash
python Datasets/clean_data_universal.py
```

### **Step 3: Create Prepare Function for ChromaDB**

**File**: `scripts/initialize_vectordb.py`

Add FAQ prepare function:

```python
def prepare_faq_documents(data: List[Dict]) -> List[Dict[str, Any]]:
    """Prepare FAQ documents for ChromaDB"""
    documents = []
    
    for item in data:
        # Combine question + answer for better retrieval
        combined_text = f"Question: {item['title']}\nAnswer: {item['text']}"
        
        documents.append({
            "id": item["id"],
            "text": combined_text,  # Question + Answer
            "metadata": {
                "question": item["title"],
                "answer": item["text"],
                "category": item["metadata"].get("category", "general"),
                "source": item["metadata"]["source"],
                "word_count": item["metadata"]["word_count"]
            }
        })
    
    return documents
```

Update main() function:

```python
def main():
    """Main initialization workflow"""
    # ... existing code ...
    
    datasets = {
        'blogs': load_dataset('blogs'),
        'products': load_dataset('products'),
        'support': load_dataset('support'),
        'social': load_dataset('social'),
        'reviews': load_dataset('reviews'),
        'faqs': load_dataset('faqs')  # ADD THIS
    }
    
    # ... existing initialization code ...
    
    # Initialize FAQs collection (ADD THIS)
    if datasets['faqs']:
        count = initialize_collection(
            client,
            'faqs',
            datasets['faqs'],
            prepare_faq_documents
        )
        total_embedded += count
        print(f"✓ FAQs: {count} documents embedded")
```

**Run**:
```bash
python scripts/initialize_vectordb.py
```

### **Step 4: Update API Endpoints**

**File**: `backend/main.py`

Update content generation to use FAQ collection:

```python
# In generate_content() function, update RAG retrieval:

# OLD:
collections_to_search = ["blogs", "products", "support"]

# NEW:
collections_to_search = ["blogs", "products", "support", "faqs"]
```

Update stats endpoint:

```python
@app.get("/v1/stats")
def get_statistics():
    """Production monitoring endpoint"""
    stats = {
        "status": "operational",
        "model": "llama3",
        "collections": {
            "blogs": get_collection_stats("blogs") if CHROMA_CLIENT else 0,
            "products": get_collection_stats("products") if CHROMA_CLIENT else 0,
            "support": get_collection_stats("support") if CHROMA_CLIENT else 0,
            "social": get_collection_stats("social") if CHROMA_CLIENT else 0,
            "reviews": get_collection_stats("reviews") if CHROMA_CLIENT else 0,
            "faqs": get_collection_stats("faqs") if CHROMA_CLIENT else 0  # ADD THIS
        },
        # ... rest of stats
    }
```

### **Step 5: Test New Collection**

```python
# Test script: scripts/test_faq_collection.py

import requests

# Test retrieval
response = requests.post("http://localhost:8000/v1/retrieve", json={
    "query": "What is your return policy?",
    "collections": ["faqs"],
    "top_k": 3
})

print("FAQ Retrieval Test:")
print(response.json())

# Test content generation
response = requests.post("http://localhost:8000/v1/generate/content", json={
    "content_type": "support_reply",
    "topic": "return policy question",
    "tone": "friendly"
})

print("\nContent Generation with FAQ Context:")
print(response.json())
```

---

## 📦 Data Versioning Strategy

### **Version Tracking in Metadata**

Add version info to all documents:

```python
metadata = {
    "version": "1.0",
    "created_at": "2025-11-19T10:00:00",
    "updated_at": "2025-11-19T10:00:00",
    "data_source_version": "cnn_dailymail_v3.0"
}
```

### **Collection Snapshots**

Create versioned collections:

```python
from datetime import datetime

def create_collection_snapshot(source_collection_name: str):
    """Create timestamped snapshot of collection"""
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    snapshot_name = f"{source_collection_name}_snapshot_{timestamp}"
    
    client = initialize_chroma_client()
    
    # Get all documents from source
    source = client.get_collection(source_collection_name)
    all_docs = source.get(include=["documents", "metadatas"])
    
    # Create new snapshot collection
    snapshot = client.create_collection(name=snapshot_name)
    snapshot.add(
        ids=all_docs["ids"],
        documents=all_docs["documents"],
        metadatas=all_docs["metadatas"]
    )
    
    print(f"✅ Created snapshot: {snapshot_name}")
    return snapshot_name
```

### **Backup Before Major Updates**

```python
import shutil
from pathlib import Path
from datetime import datetime

def backup_chromadb():
    """Backup entire ChromaDB directory"""
    source = Path("data/chroma_db")
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    backup = Path(f"data/chroma_db_backup_{timestamp}")
    
    shutil.copytree(source, backup)
    print(f"✅ Backup created: {backup}")
    return backup

# Before major update:
backup_path = backup_chromadb()
# ... perform updates ...
# If issues, restore from backup_path
```

---

## 💾 Backup and Recovery

### **Automated Backup Script**

```python
# scripts/backup_vectordb.py

import shutil
from pathlib import Path
from datetime import datetime
import json

def backup_vector_database(backup_dir="backups"):
    """Create full backup of vector database"""
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    
    # Create backup directory
    backup_path = Path(backup_dir) / f"backup_{timestamp}"
    backup_path.mkdir(parents=True, exist_ok=True)
    
    # Backup ChromaDB directory
    chroma_source = Path("data/chroma_db")
    chroma_backup = backup_path / "chroma_db"
    shutil.copytree(chroma_source, chroma_backup)
    
    # Backup cleaned JSON files
    cleaned_source = Path("data/cleaned")
    cleaned_backup = backup_path / "cleaned"
    shutil.copytree(cleaned_source, cleaned_backup)
    
    # Create manifest
    manifest = {
        "timestamp": timestamp,
        "backup_path": str(backup_path),
        "collections": [],
        "total_size_mb": 0
    }
    
    # Get collection stats
    from backend.vector_store import initialize_chroma_client, get_collection_stats
    client = initialize_chroma_client()
    for collection_name in ["blogs", "products", "support", "social", "reviews"]:
        count = get_collection_stats(collection_name)
        manifest["collections"].append({
            "name": collection_name,
            "document_count": count
        })
    
    # Calculate size
    total_size = sum(f.stat().st_size for f in backup_path.rglob('*') if f.is_file())
    manifest["total_size_mb"] = round(total_size / (1024 * 1024), 2)
    
    # Save manifest
    with open(backup_path / "manifest.json", "w") as f:
        json.dump(manifest, f, indent=2)
    
    print(f"✅ Backup complete: {backup_path}")
    print(f"📊 Total size: {manifest['total_size_mb']} MB")
    return backup_path

if __name__ == "__main__":
    backup_vector_database()
```

### **Restore from Backup**

```python
# scripts/restore_vectordb.py

import shutil
from pathlib import Path
import json

def restore_vector_database(backup_path: Path):
    """Restore vector database from backup"""
    
    # Verify backup exists
    if not backup_path.exists():
        raise FileNotFoundError(f"Backup not found: {backup_path}")
    
    manifest_file = backup_path / "manifest.json"
    if not manifest_file.exists():
        raise FileNotFoundError("Backup manifest not found")
    
    # Load manifest
    with open(manifest_file, "r") as f:
        manifest = json.load(f)
    
    print(f"Restoring backup from: {manifest['timestamp']}")
    
    # Backup current data first
    print("Creating safety backup of current data...")
    current_backup = Path("data") / f"current_backup_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
    if Path("data/chroma_db").exists():
        shutil.copytree("data/chroma_db", current_backup)
    
    # Restore ChromaDB
    print("Restoring ChromaDB...")
    if Path("data/chroma_db").exists():
        shutil.rmtree("data/chroma_db")
    shutil.copytree(backup_path / "chroma_db", "data/chroma_db")
    
    # Restore cleaned files
    print("Restoring cleaned files...")
    if Path("data/cleaned").exists():
        shutil.rmtree("data/cleaned")
    shutil.copytree(backup_path / "cleaned", "data/cleaned")
    
    print(f"✅ Restore complete!")
    print(f"📊 Restored {len(manifest['collections'])} collections")
    print(f"💾 Safety backup saved: {current_backup}")

if __name__ == "__main__":
    import sys
    if len(sys.argv) < 2:
        print("Usage: python scripts/restore_vectordb.py <backup_path>")
        sys.exit(1)
    
    backup_path = Path(sys.argv[1])
    restore_vector_database(backup_path)
```

---

## ⚡ Performance Optimization

### **Batch Processing**

Process large datasets in batches:

```python
def add_documents_optimized(collection, documents: list, batch_size=100):
    """Add documents with optimized batch size"""
    from tqdm import tqdm
    
    for i in tqdm(range(0, len(documents), batch_size), desc="Adding docs"):
        batch = documents[i:i+batch_size]
        
        ids = [doc["id"] for doc in batch]
        texts = [doc["text"] for doc in batch]
        metadatas = [doc["metadata"] for doc in batch]
        
        collection.add(
            ids=ids,
            documents=texts,
            metadatas=metadatas
        )
    
    print(f"✅ Added {len(documents)} documents")
```

### **Embedding Cache**

Cache embeddings for frequently used queries:

```python
from functools import lru_cache

@lru_cache(maxsize=1000)
def get_cached_embedding(text: str):
    """Cache embeddings for frequently queried texts"""
    from backend.vector_store import get_embedding_function
    embedding_fn = get_embedding_function()
    return embedding_fn([text])[0]
```

### **Parallel Processing**

Process multiple collections in parallel:

```python
from concurrent.futures import ThreadPoolExecutor, as_completed

def initialize_all_collections_parallel():
    """Initialize all collections in parallel"""
    
    collections_data = {
        'blogs': ('data/cleaned/blogs.json', prepare_blog_documents),
        'products': ('data/cleaned/products.json', prepare_product_documents),
        'support': ('data/cleaned/support.json', prepare_support_documents),
        # ... more collections
    }
    
    def init_collection(name, data_file, prepare_fn):
        with open(data_file, 'r') as f:
            data = json.load(f)
        docs = prepare_fn(data)
        
        client = initialize_chroma_client()
        collection = create_or_get_collection(name, client)
        add_documents(collection, docs)
        
        return name, len(docs)
    
    # Process in parallel
    with ThreadPoolExecutor(max_workers=3) as executor:
        futures = {
            executor.submit(init_collection, name, file, fn): name
            for name, (file, fn) in collections_data.items()
        }
        
        for future in as_completed(futures):
            name, count = future.result()
            print(f"✅ {name}: {count} documents")
```

---

## ⚠️ Limitations and Constraints

### **Current Limitations**

1. **No Continuous Learning**
   - System uses static RAG (retrieval only)
   - Does NOT fine-tune or update LLM weights
   - New data helps retrieval but doesn't "teach" the model

2. **Manual Updates Required**
   - No automated data refresh
   - Must manually run scripts to add new data
   - No scheduled ingestion pipelines

3. **Storage Constraints**
   - Current: ~50MB for 1,085 docs
   - Projected: ~1.6GB for 35,000 docs
   - Disk space grows linearly with document count

4. **No Real-Time Updates**
   - ChromaDB reads from disk
   - New documents not immediately available
   - Need to reinitialize client for changes

5. **Limited Query Complexity**
   - Basic semantic search only
   - No complex boolean queries
   - No date range filters in RAG

6. **Embedding Model Fixed**
   - all-MiniLM-L6-v2 (384 dim)
   - Cannot easily switch models
   - Re-embedding required for model change

### **Workarounds**

1. **For Near Real-Time Updates**:
   ```python
   # Reload collection after adding docs
   client = initialize_chroma_client()
   collection = client.get_collection("blogs")  # Gets latest data
   ```

2. **For Automated Updates**:
   ```python
   # Use cron job or scheduled task
   # 0 */6 * * * cd /path/to/project && python scripts/update_data.py
   ```

3. **For Storage Optimization**:
   ```python
   # Compress old embeddings
   # Delete unused collections
   # Use external storage (S3) for raw data
   ```

---

## 📚 Related Documentation

- **Architecture**: `docs/architecture/AGENT_ARCHITECTURE.md`
- **API Reference**: `docs/api/API_REFERENCE.md`
- **How-To Guides**: `docs/guides/HOW_TO_ADD_DATA_SOURCE.md`
- **Optimization**: `docs/guides/OPTIMIZATION_GUIDE.md`

---

**Last Updated**: November 19, 2025  
**Version**: 1.0  
**Status**: ✅ Complete
