"""
Universal Data Cleaning Script for All Dataset Types
Handles: blogs, products, support, social, reviews
Features:
- Preserves critical fields (titles, agent_reply)
- Language detection and filtering
- Exact deduplication
- Quality metrics computation
- Proper field mapping per dataset type
"""
import json
import os
from pathlib import Path
from bs4 import BeautifulSoup
from langdetect import detect, LangDetectException
import re
from tqdm import tqdm
from loguru import logger

# Setup logging
logger.add("logs/day4_cleaning.log", rotation="10 MB")

RAW_DIR = Path("data/raw")
CLEANED_DIR = Path("data/cleaned")
REJECTED_DIR = Path("data/rejected")

for d in [CLEANED_DIR, REJECTED_DIR]:
    d.mkdir(parents=True, exist_ok=True)


# ============================================================================
# TEXT CLEANING UTILITIES
# ============================================================================

def clean_text(text: str, preserve_paragraphs: bool = True) -> str:
    """Clean text while optionally preserving paragraph structure"""
    if not text:
        return ""
    
    # Remove HTML tags
    text = BeautifulSoup(text, "html.parser").get_text("\n" if preserve_paragraphs else " ")
    
    # Normalize unicode characters
    replacements = {
        """: "\"", """: "\"", "'": "'", "'": "'",
        "–": "-", "—": "-", "…": "...",
    }
    for bad, good in replacements.items():
        text = text.replace(bad, good)
    
    # Remove URLs and emails
    text = re.sub(r"http\S+|www\S+", "", text)
    text = re.sub(r"\S+@\S+", "", text)
    
    # Remove excessive punctuation patterns
    text = re.sub(r"={2,}", "", text)
    text = re.sub(r"-{3,}", "", text)
    text = re.sub(r"\*{2,}", "", text)
    
    # Fix whitespace
    text = re.sub(r"[ \t]+", " ", text)
    
    if preserve_paragraphs:
        # CNN/DailyMail uses special markers - detect sentence boundaries
        # Create paragraph breaks at sentence endings followed by spaces
        # Look for period/question/exclamation followed by space and capital letter
        text = re.sub(r'([.!?])\s+([A-Z])', r'\1\n\n\2', text)
        
        # Consolidate newlines
        text = re.sub(r"\n{3,}", "\n\n", text)
        
        # Clean individual paragraphs
        paragraphs = []
        for p in text.split("\n\n"):
            p = p.strip()
            # Keep substantial paragraphs (at least 40 chars or 8 words)
            if len(p) >= 40 and len(p.split()) >= 8:
                paragraphs.append(p)
        
        text = "\n\n".join(paragraphs)
    else:
        # Single line
        text = " ".join(text.split())
    
    return text.strip()


def clean_title(title: str) -> str:
    """Clean title/headline text"""
    if not title:
        return ""
    title = BeautifulSoup(title, "html.parser").get_text(" ")
    title = re.sub(r"\s+", " ", title)
    return title.strip()[:200]  # Max 200 chars for titles


def is_english(text: str) -> bool:
    """Check if text is English using langdetect"""
    try:
        if not text or len(text) < 20:
            return False
        # Use first 500 chars for detection
        lang = detect(text[:500])
        return lang == "en"
    except LangDetectException:
        return False


def compute_metadata(text: str, source: str, preserve_paragraphs: bool = True) -> dict:
    """Compute quality metrics for text"""
    words = text.split()
    metadata = {
        "source": source,
        "word_count": len(words),
        "char_length": len(text),
        "has_numbers": any(ch.isdigit() for ch in text),
    }
    
    if preserve_paragraphs:
        metadata["paragraphs"] = len(text.split("\n\n"))
    
    return metadata


# ============================================================================
# DATASET-SPECIFIC PROCESSORS
# ============================================================================

def process_blogs(raw_file: Path) -> tuple[list, list]:
    """Process blog articles - require longer content with paragraphs"""
    with open(raw_file, "r", encoding="utf-8") as f:
        items = json.load(f)
    
    cleaned = []
    rejected = []
    seen_texts = set()  # For deduplication
    
    for item in tqdm(items, desc=f"Cleaning {raw_file.name}"):
        text = item.get("text", "").strip()
        title = item.get("title", "").strip()
        
        if not text:
            rejected.append({"id": item.get("id"), "reason": "empty_text"})
            continue
        
        # Clean text and title
        cleaned_text = clean_text(text, preserve_paragraphs=True)
        cleaned_title = clean_title(title)
        
        # Quality checks for blogs
        word_count = len(cleaned_text.split())
        
        if word_count < 100:  # Blogs should be substantial
            rejected.append({"id": item.get("id"), "reason": "too_short", "word_count": word_count})
            continue
        
        if word_count > 10000:
            rejected.append({"id": item.get("id"), "reason": "too_long", "word_count": word_count})
            continue
        
        # Language check
        if not is_english(cleaned_text):
            rejected.append({"id": item.get("id"), "reason": "not_english"})
            continue
        
        # Deduplication
        text_hash = cleaned_text[:200]  # Use first 200 chars as fingerprint
        if text_hash in seen_texts:
            rejected.append({"id": item.get("id"), "reason": "duplicate"})
            continue
        seen_texts.add(text_hash)
        
        # Store cleaned item
        cleaned.append({
            "id": item.get("id", f"blog_{len(cleaned)}"),
            "title": cleaned_title,
            "text": cleaned_text,
            "metadata": compute_metadata(cleaned_text, item.get("source", "blogs"), preserve_paragraphs=True)
        })
    
    return cleaned, rejected


def process_products(raw_file: Path) -> tuple[list, list]:
    """Process product reviews - preserve titles!"""
    with open(raw_file, "r", encoding="utf-8") as f:
        items = json.load(f)
    
    cleaned = []
    rejected = []
    seen_texts = set()
    
    for item in tqdm(items, desc=f"Cleaning {raw_file.name}"):
        text = item.get("text", "").strip()
        title = item.get("title", "").strip()
        
        # Products MUST have title
        if not title:
            rejected.append({"id": item.get("id"), "reason": "missing_title"})
            continue
        
        if not text:
            rejected.append({"id": item.get("id"), "reason": "empty_text"})
            continue
        
        # Clean text (no paragraph preservation for reviews)
        cleaned_text = clean_text(text, preserve_paragraphs=False)
        cleaned_title = clean_title(title)
        
        # Quality checks
        word_count = len(cleaned_text.split())
        
        if word_count < 20:  # Reviews should have some substance
            rejected.append({"id": item.get("id"), "reason": "too_short", "word_count": word_count})
            continue
        
        if word_count > 5000:
            rejected.append({"id": item.get("id"), "reason": "too_long", "word_count": word_count})
            continue
        
        # Language check
        if not is_english(cleaned_text):
            rejected.append({"id": item.get("id"), "reason": "not_english"})
            continue
        
        # Deduplication
        text_hash = cleaned_text[:200]
        if text_hash in seen_texts:
            rejected.append({"id": item.get("id"), "reason": "duplicate"})
            continue
        seen_texts.add(text_hash)
        
        # Store cleaned item
        cleaned.append({
            "id": item.get("id", f"prod_{len(cleaned)}"),
            "title": cleaned_title,  # Title preserved!
            "text": cleaned_text,
            "metadata": {
                **compute_metadata(cleaned_text, "products", preserve_paragraphs=False),
                **item.get("metadata", {})  # Preserve original metadata (rating, etc)
            }
        })
    
    return cleaned, rejected


def process_support(raw_file: Path) -> tuple[list, list]:
    """Process customer support - preserve agent_reply field!"""
    with open(raw_file, "r", encoding="utf-8") as f:
        items = json.load(f)
    
    cleaned = []
    rejected = []
    seen_texts = set()
    
    for item in tqdm(items, desc=f"Cleaning {raw_file.name}"):
        text = item.get("text", "").strip()  # Customer query
        agent_reply = item.get("agent_reply", "").strip()  # Agent response
        
        if not text:
            rejected.append({"id": item.get("id"), "reason": "empty_query"})
            continue
        
        # Support tickets should ideally have agent replies
        # But we'll accept entries without them (can be generated later)
        
        # Clean text
        cleaned_text = clean_text(text, preserve_paragraphs=False)
        cleaned_reply = clean_text(agent_reply, preserve_paragraphs=False) if agent_reply else ""
        
        # Quality checks
        word_count = len(cleaned_text.split())
        
        if word_count < 5:  # Queries should be meaningful
            rejected.append({"id": item.get("id"), "reason": "too_short", "word_count": word_count})
            continue
        
        if word_count > 1000:
            rejected.append({"id": item.get("id"), "reason": "too_long", "word_count": word_count})
            continue
        
        # Language check
        if not is_english(cleaned_text):
            rejected.append({"id": item.get("id"), "reason": "not_english"})
            continue
        
        # Deduplication
        text_hash = cleaned_text[:150]
        if text_hash in seen_texts:
            rejected.append({"id": item.get("id"), "reason": "duplicate"})
            continue
        seen_texts.add(text_hash)
        
        # Store cleaned item
        entry = {
            "id": item.get("id", f"support_{len(cleaned)}"),
            "title": "",  # Support entries don't need titles
            "text": cleaned_text,
            "metadata": compute_metadata(cleaned_text, "support", preserve_paragraphs=False)
        }
        
        # Preserve agent_reply if present
        if cleaned_reply:
            entry["agent_reply"] = cleaned_reply
            entry["metadata"]["has_agent_reply"] = True
            entry["metadata"]["reply_word_count"] = len(cleaned_reply.split())
        else:
            entry["metadata"]["has_agent_reply"] = False
        
        # Preserve intent/category if present
        if "metadata" in item:
            if "intent" in item["metadata"]:
                entry["metadata"]["intent"] = item["metadata"]["intent"]
            if "category" in item["metadata"]:
                entry["metadata"]["category"] = item["metadata"]["category"]
        
        cleaned.append(entry)
    
    return cleaned, rejected


def process_social(raw_file: Path) -> tuple[list, list]:
    """Process social media posts - short to medium length"""
    with open(raw_file, "r", encoding="utf-8") as f:
        items = json.load(f)
    
    cleaned = []
    rejected = []
    seen_texts = set()
    
    for item in tqdm(items, desc=f"Cleaning {raw_file.name}"):
        text = item.get("text", "").strip()
        
        if not text:
            rejected.append({"id": item.get("id"), "reason": "empty_text"})
            continue
        
        # Clean text (no paragraph preservation)
        cleaned_text = clean_text(text, preserve_paragraphs=False)
        
        # Quality checks for social posts
        word_count = len(cleaned_text.split())
        
        if word_count < 3:  # Too short even for social
            rejected.append({"id": item.get("id"), "reason": "too_short", "word_count": word_count})
            continue
        
        if word_count > 500:  # Social posts should be concise
            rejected.append({"id": item.get("id"), "reason": "too_long", "word_count": word_count})
            continue
        
        # Language check
        if not is_english(cleaned_text):
            rejected.append({"id": item.get("id"), "reason": "not_english"})
            continue
        
        # Deduplication
        text_hash = cleaned_text[:100]
        if text_hash in seen_texts:
            rejected.append({"id": item.get("id"), "reason": "duplicate"})
            continue
        seen_texts.add(text_hash)
        
        # Store cleaned item
        cleaned.append({
            "id": item.get("id", f"social_{len(cleaned)}"),
            "title": "",
            "text": cleaned_text,
            "metadata": {
                **compute_metadata(cleaned_text, "social", preserve_paragraphs=False),
                "length_category": "short" if word_count < 20 else "medium" if word_count < 100 else "long"
            }
        })
    
    return cleaned, rejected


def process_reviews(raw_file: Path) -> tuple[list, list]:
    """Process product reviews"""
    with open(raw_file, "r", encoding="utf-8") as f:
        items = json.load(f)
    
    cleaned = []
    rejected = []
    seen_texts = set()
    
    for item in tqdm(items, desc=f"Cleaning {raw_file.name}"):
        text = item.get("text", "").strip()
        rating = item.get("rating", 0)
        
        if not text:
            rejected.append({"id": item.get("id"), "reason": "empty_text"})
            continue
        
        # Clean text
        cleaned_text = clean_text(text, preserve_paragraphs=False)
        
        # Quality checks
        word_count = len(cleaned_text.split())
        
        if word_count < 10:
            rejected.append({"id": item.get("id"), "reason": "too_short", "word_count": word_count})
            continue
        
        if word_count > 5000:
            rejected.append({"id": item.get("id"), "reason": "too_long", "word_count": word_count})
            continue
        
        # Language check
        if not is_english(cleaned_text):
            rejected.append({"id": item.get("id"), "reason": "not_english"})
            continue
        
        # Deduplication
        text_hash = cleaned_text[:200]
        if text_hash in seen_texts:
            rejected.append({"id": item.get("id"), "reason": "duplicate"})
            continue
        seen_texts.add(text_hash)
        
        # Store cleaned item
        cleaned.append({
            "id": item.get("id", f"review_{len(cleaned)}"),
            "title": "",
            "text": cleaned_text,
            "metadata": {
                **compute_metadata(cleaned_text, "reviews", preserve_paragraphs=False),
                "rating": rating
            }
        })
    
    return cleaned, rejected


# ============================================================================
# MAIN PROCESSING PIPELINE
# ============================================================================

PROCESSORS = {
    "blogs": process_blogs,
    "products": process_products,
    "support": process_support,
    "social": process_social,
    "reviews": process_reviews,
}


def process_dataset(dataset_type: str, raw_file: Path):
    """Process a single dataset file"""
    print(f"\n{'='*70}")
    print(f"Processing: {dataset_type.upper()} - {raw_file.name}")
    print(f"{'='*70}")
    
    processor = PROCESSORS.get(dataset_type)
    if not processor:
        logger.error(f"Unknown dataset type: {dataset_type}")
        return
    
    try:
        cleaned, rejected = processor(raw_file)
        
        # Save cleaned data
        output_file = CLEANED_DIR / f"{dataset_type}.json"
        with open(output_file, "w", encoding="utf-8") as f:
            json.dump(cleaned, f, indent=2, ensure_ascii=False)
        
        # Save rejected data
        if rejected:
            rejected_file = REJECTED_DIR / f"{dataset_type}_rejected.json"
            with open(rejected_file, "w", encoding="utf-8") as f:
                json.dump(rejected, f, indent=2, ensure_ascii=False)
        
        # Log results
        rejection_rate = len(rejected) / (len(cleaned) + len(rejected)) if (len(cleaned) + len(rejected)) > 0 else 0
        
        logger.info(f"{dataset_type}: cleaned={len(cleaned)}, rejected={len(rejected)}, rejection_rate={rejection_rate:.2%}")
        
        print(f"\n✓ Cleaned: {len(cleaned)} entries")
        print(f"✗ Rejected: {len(rejected)} entries")
        print(f"📊 Rejection rate: {rejection_rate:.1%}")
        print(f"💾 Saved to: {output_file}")
        
        # Show quality metrics for specific datasets
        if dataset_type == "products" and cleaned:
            titles_present = sum(1 for item in cleaned if item.get("title"))
            print(f"✓ Products with titles: {titles_present}/{len(cleaned)} ({titles_present/len(cleaned)*100:.1f}%)")
        
        if dataset_type == "support" and cleaned:
            with_replies = sum(1 for item in cleaned if item.get("metadata", {}).get("has_agent_reply"))
            print(f"✓ Support entries with agent_reply: {with_replies}/{len(cleaned)} ({with_replies/len(cleaned)*100:.1f}%)")
        
        if dataset_type == "blogs" and cleaned:
            word_counts = [item["metadata"]["word_count"] for item in cleaned]
            avg_wc = sum(word_counts) / len(word_counts)
            median_wc = sorted(word_counts)[len(word_counts) // 2]
            paragraphs = [item["metadata"].get("paragraphs", 1) for item in cleaned]
            avg_para = sum(paragraphs) / len(paragraphs)
            print(f"📝 Blogs - Median words: {median_wc}, Avg paragraphs: {avg_para:.1f}")
        
    except Exception as e:
        logger.exception(f"Error processing {dataset_type}")
        print(f"\n❌ ERROR: {e}")


def main():
    """Main cleaning pipeline - process all datasets"""
    print("\n" + "="*70)
    print("UNIVERSAL DATA CLEANING PIPELINE")
    print("="*70)
    
    # Find and process all raw data files
    datasets_processed = 0
    
    # Process blogs
    blog_files = list((RAW_DIR / "blogs").glob("*.json")) if (RAW_DIR / "blogs").exists() else []
    for blog_file in blog_files:
        process_dataset("blogs", blog_file)
        datasets_processed += 1
    
    # Process products
    product_files = list((RAW_DIR / "products").glob("*.json")) if (RAW_DIR / "products").exists() else []
    for product_file in product_files:
        process_dataset("products", product_file)
        datasets_processed += 1
    
    # Process support
    support_files = list((RAW_DIR / "support").glob("raw_support.json")) if (RAW_DIR / "support").exists() else []
    for support_file in support_files:
        process_dataset("support", support_file)
        datasets_processed += 1
    
    # Process social
    social_files = list((RAW_DIR / "social").glob("*.json")) if (RAW_DIR / "social").exists() else []
    for social_file in social_files:
        process_dataset("social", social_file)
        datasets_processed += 1
    
    # Process reviews
    review_files = list((RAW_DIR / "reviews").glob("*.json")) if (RAW_DIR / "reviews").exists() else []
    for review_file in review_files:
        process_dataset("reviews", review_file)
        datasets_processed += 1
    
    print(f"\n{'='*70}")
    print(f"CLEANING COMPLETE - {datasets_processed} datasets processed")
    print(f"{'='*70}\n")


if __name__ == "__main__":
    main()
