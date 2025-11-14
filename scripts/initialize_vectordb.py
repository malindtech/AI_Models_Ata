# scripts/initialize_vectordb.py
"""
Initialize ChromaDB Vector Database - Day 5

Loads all cleaned datasets into ChromaDB with embeddings:
- blogs (243 entries)
- products (197 entries)
- support (272 entries)
- social (177 entries)
- reviews (196 entries)

Total: 1,085 documents
"""

import json
import sys
import time
from pathlib import Path
from typing import List, Dict, Any
from tqdm import tqdm

# Add project root to path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from backend.vector_store import (
    initialize_chroma_client,
    create_or_get_collection,
    add_documents,
    get_collection_stats
)

CLEANED_DIR = project_root / "data" / "cleaned"


def load_dataset(dataset_name: str) -> List[Dict]:
    """Load cleaned dataset from JSON"""
    file_path = CLEANED_DIR / f"{dataset_name}.json"
    
    if not file_path.exists():
        print(f"❌ Dataset not found: {file_path}")
        return []
    
    with open(file_path, "r", encoding="utf-8") as f:
        data = json.load(f)
    
    print(f"✓ Loaded {dataset_name}: {len(data)} entries")
    return data


def prepare_blog_documents(data: List[Dict]) -> List[Dict[str, Any]]:
    """
    Prepare blog entries for embedding
    
    Format: title + text combined
    """
    documents = []
    
    for item in data:
        doc_id = item.get('id', f"blog_{len(documents)}")
        title = item.get('title', '')
        text = item.get('text', '')
        
        # Combine title and text
        combined_text = f"{title}\n\n{text}" if title else text
        
        documents.append({
            'id': str(doc_id),
            'text': combined_text,
            'metadata': item.get('metadata', {})
        })
    
    return documents


def prepare_product_documents(data: List[Dict]) -> List[Dict[str, Any]]:
    """
    Prepare product entries for embedding
    
    Format: title + text combined
    """
    documents = []
    
    for item in data:
        doc_id = item.get('id', f"product_{len(documents)}")
        title = item.get('title', '')
        text = item.get('text', '')
        
        # Combine title and text
        combined_text = f"{title}\n\n{text}" if title else text
        
        documents.append({
            'id': str(doc_id),
            'text': combined_text,
            'metadata': item.get('metadata', {})
        })
    
    return documents


def prepare_support_documents(data: List[Dict]) -> List[Dict[str, Any]]:
    """
    Prepare support entries for embedding
    
    Format: title + customer message + agent reply
    """
    documents = []
    
    for item in data:
        doc_id = item.get('id', f"support_{len(documents)}")
        title = item.get('title', '')
        text = item.get('text', '')
        agent_reply = item.get('agent_reply', '')
        
        # Combine all fields
        parts = []
        if title:
            parts.append(title)
        if text:
            parts.append(f"Customer: {text}")
        if agent_reply:
            parts.append(f"Agent Reply: {agent_reply}")
        
        combined_text = "\n\n".join(parts)
        
        documents.append({
            'id': str(doc_id),
            'text': combined_text,
            'metadata': item.get('metadata', {})
        })
    
    return documents


def prepare_social_documents(data: List[Dict]) -> List[Dict[str, Any]]:
    """
    Prepare social media posts for embedding
    
    Format: text only (short posts)
    """
    documents = []
    
    for item in data:
        doc_id = item.get('id', f"social_{len(documents)}")
        text = item.get('text', '')
        
        documents.append({
            'id': str(doc_id),
            'text': text,
            'metadata': item.get('metadata', {})
        })
    
    return documents


def prepare_review_documents(data: List[Dict]) -> List[Dict[str, Any]]:
    """
    Prepare review entries for embedding
    
    Format: text only
    """
    documents = []
    
    for item in data:
        doc_id = item.get('id', f"review_{len(documents)}")
        text = item.get('text', '')
        
        documents.append({
            'id': str(doc_id),
            'text': text,
            'metadata': item.get('metadata', {})
        })
    
    return documents


def initialize_collection(
    client,
    collection_name: str,
    data: List[Dict],
    prepare_func
):
    """
    Initialize a single collection with data
    
    Args:
        client: ChromaDB client
        collection_name: Name of collection
        data: Raw data from JSON
        prepare_func: Function to prepare documents
    """
    print(f"\n{'='*60}")
    print(f"Processing: {collection_name}")
    print(f"{'='*60}")
    
    # Prepare documents
    print("Preparing documents...")
    documents = prepare_func(data)
    print(f"✓ Prepared {len(documents)} documents")
    
    # Create or get collection
    print(f"Creating collection '{collection_name}'...")
    collection = create_or_get_collection(collection_name, client)
    print(f"✓ Collection ready")
    
    # Add documents with progress bar
    print("Embedding and adding documents...")
    batch_size = 50
    
    with tqdm(total=len(documents), desc=f"Embedding {collection_name}", unit="docs") as pbar:
        for i in range(0, len(documents), batch_size):
            batch = documents[i:i + batch_size]
            
            ids = [doc['id'] for doc in batch]
            texts = [doc['text'] for doc in batch]
            metadatas = [doc['metadata'] for doc in batch]
            
            collection.add(
                ids=ids,
                documents=texts,
                metadatas=metadatas
            )
            
            pbar.update(len(batch))
    
    print(f"✓ Added {len(documents)} documents to '{collection_name}'")
    
    return len(documents)


def main():
    """Main initialization workflow"""
    print("\n" + "="*60)
    print("  CHROMADB INITIALIZATION - DAY 5")
    print("="*60)
    
    start_time = time.time()
    
    # Step 1: Load all datasets
    print("\n📥 Loading datasets from data/cleaned/...")
    print("-" * 60)
    
    datasets = {
        'blogs': load_dataset('blogs'),
        'products': load_dataset('products'),
        'support': load_dataset('support'),
        'social': load_dataset('social'),
        'reviews': load_dataset('reviews')
    }
    
    total_docs = sum(len(data) for data in datasets.values())
    print(f"\n✓ Total entries loaded: {total_docs}")
    
    # Step 2: Initialize ChromaDB
    print("\n🗄️  Initializing ChromaDB...")
    print("-" * 60)
    
    try:
        client = initialize_chroma_client()
        print(f"✓ ChromaDB client initialized")
        print(f"  Location: {project_root / 'data' / 'chroma_db'}")
    except Exception as e:
        print(f"❌ Failed to initialize ChromaDB: {e}")
        print("\nMake sure you have installed the dependencies:")
        print("  pip install chromadb sentence-transformers")
        sys.exit(1)
    
    # Step 3: Process each dataset
    print("\n📊 Creating collections and embedding documents...")
    print("-" * 60)
    
    preparation_funcs = {
        'blogs': prepare_blog_documents,
        'products': prepare_product_documents,
        'support': prepare_support_documents,
        'social': prepare_social_documents,
        'reviews': prepare_review_documents
    }
    
    embedded_counts = {}
    
    for name, data in datasets.items():
        if not data:
            print(f"\n⚠️  Skipping {name} (no data)")
            continue
        
        try:
            count = initialize_collection(
                client,
                name,
                data,
                preparation_funcs[name]
            )
            embedded_counts[name] = count
        except Exception as e:
            print(f"❌ Failed to initialize {name}: {e}")
            import traceback
            traceback.print_exc()
    
    # Step 4: Validation
    print("\n✅ Validating collections...")
    print("-" * 60)
    
    stats = get_collection_stats(client)
    
    for name, count in stats.items():
        expected = embedded_counts.get(name, 0)
        status = "✓" if count == expected else "⚠️"
        print(f"{status} Collection '{name}': {count} documents (expected: {expected})")
    
    # Final summary
    elapsed = time.time() - start_time
    total_embedded = sum(stats.values())
    avg_time_per_doc = elapsed / total_embedded if total_embedded > 0 else 0
    
    print("\n" + "="*60)
    print("  INITIALIZATION COMPLETE")
    print("="*60)
    print(f"\n📊 Statistics:")
    print(f"  Total documents embedded: {total_embedded}")
    print(f"  Total collections: {len(stats)}")
    print(f"  Total time: {elapsed:.1f} seconds")
    print(f"  Average time per document: {avg_time_per_doc:.3f}s")
    print(f"  Embedding model: all-MiniLM-L6-v2")
    print(f"  Storage location: {project_root / 'data' / 'chroma_db'}")
    
    print("\n✅ Vector database is ready for use!")
    print("\nNext steps:")
    print("  1. Start FastAPI: uvicorn backend.main:app --reload")
    print("  2. Test retrieval: python scripts/test_rag_retrieval.py")
    print("  3. Use RAG endpoints: POST /v1/retrieve")
    print()


if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print("\n\n⚠️  Initialization cancelled by user")
        sys.exit(1)
    except Exception as e:
        print(f"\n\n❌ Fatal error: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
