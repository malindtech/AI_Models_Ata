# Data Pipeline Documentation

## Datasets Used

### 1. Blogs - `cnn_dailymail` (3.0.0)
**Source**: HuggingFace CNN/DailyMail dataset  
**Fields**:
- `id`: Unique identifier (e.g., `blog_cnn_001`)
- `title`: Article headline/first highlight
- `text`: Full article content with paragraphs
- `metadata`: `{source, word_count, char_length, paragraphs, has_numbers}`

**Statistics**: 243 articles, median 582 words, avg 22.3 paragraphs

### 2. Products - `amazon_polarity`
**Source**: HuggingFace Amazon product reviews  
**Fields**:
- `id`: Unique identifier (e.g., `prod_001`)
- `title`: Product review title (100% preserved)
- `text`: Review content
- `metadata`: `{source, word_count, char_length, has_numbers, rating}`

**Statistics**: 197 products, 100% with titles

### 3. Support - `bitext/Bitext-customer-support-llm-chatbot-training-dataset`
**Source**: HuggingFace Bitext customer support dataset  
**Fields**:
- `id`: Unique identifier (e.g., `support_001`)
- `title`: Empty (not applicable)
- `text`: Customer query/message
- `agent_reply`: Agent's response (100% coverage)
- `metadata`: `{source, word_count, has_agent_reply, reply_word_count, intent, category}`

**Statistics**: 214 conversations, all with agent replies

### 4. Social - `go_emotions`
**Source**: HuggingFace GoEmotions dataset  
**Fields**:
- `id`: Unique identifier (e.g., `social_001`)
- `title`: Empty (not applicable)
- `text`: Social media post content
- `metadata`: `{source, word_count, char_length, has_numbers, length_category}`

**Statistics**: 176 posts, 83.5% short, 16.5% medium

### 5. Reviews - `yelp_review_full`
**Source**: HuggingFace Yelp reviews dataset  
**Fields**:
- `id`: Unique identifier (e.g., `review_001`)
- `title`: Empty (not applicable)
- `text`: Review content
- `metadata`: `{source, word_count, char_length, has_numbers, rating}`

**Statistics**: 196 reviews

---

## Data Cleaning Approach

### Pipeline: `clean_data_universal.py`

#### 1. Text Cleaning
- **HTML removal**: Strip all HTML tags using BeautifulSoup
- **Unicode normalization**: Convert smart quotes, dashes, ellipsis to ASCII
- **URL/Email removal**: Remove web links and email addresses
- **Whitespace normalization**: Fix excessive spaces and tabs

#### 2. Paragraph Detection (Blogs Only)
- **Sentence boundary detection**: Regex pattern `([.!?])\s+([A-Z])` creates paragraph breaks
- **Paragraph filtering**: Keep paragraphs with ≥40 chars and ≥8 words
- **Result**: Average 22.3 paragraphs per blog article

#### 3. Language Filtering
- **Method**: `langdetect` library on first 500 characters
- **Criterion**: English only (lang == "en")
- **Result**: 100% English purity across all datasets

#### 4. Deduplication
- **Method**: Exact text matching using first 150-200 chars as fingerprint
- **Storage**: Set-based tracking during processing
- **Result**: 0% duplicate ratio across all datasets

#### 5. Quality Thresholds
| Dataset | Min Words | Max Words | Special Requirements |
|---------|-----------|-----------|---------------------|
| Blogs | 100 | 10,000 | Paragraph structure preserved |
| Products | 20 | 5,000 | **Title must be present** |
| Support | 5 | 1,000 | agent_reply preserved if available |
| Social | 3 | 500 | Length categorization (short/medium/long) |
| Reviews | 10 | 5,000 | Rating field preserved |

#### 6. Field Preservation
- **Products**: Title field explicitly preserved (not lost during cleaning)
- **Support**: `agent_reply` field maintained separately
- **Reviews**: Rating metadata preserved from source
- **All datasets**: Source metadata tracked

---

## Data Validation for Quality Checking

### Validation Script: `scripts/day4_validation.py`

#### Metrics Computed

**1. Content Quality Metrics**
- Median word count (blogs: ≥300 required)
- Average paragraphs per article (blogs: ≥2 required)
- Title preservation rate (products: >80% required)
- Agent reply coverage (support: ≥200 entries required)

**2. Distribution Metrics**
- Length categorization (short <20, medium 20-100, long >100 words)
- Mixture validation (social: both short and medium >10%)

**3. Data Quality Metrics**
- **Noise rate**: rejected / (cleaned + rejected) for each dataset
  - Requirement: <30% for core datasets (blogs, products, support)
  - Results: blogs 2.8%, products 1.5%, support 28.7%

- **Language purity**: English content detection
  - Method: ASCII ratio check on sample (>80% ASCII = English)
  - Requirement: >90% purity
  - Results: 100% across all datasets

- **Duplicate ratio**: Fingerprint-based duplicate detection
  - Method: First 150 chars as unique identifier
  - Requirement: <5% duplicates
  - Results: 0% across all datasets

---

## Cleaned Data Files

### Output Directory: `data/cleaned/`

**All files in JSON format with consistent structure**:

1. **`blogs.json`** - 243 articles
   - CNN/DailyMail long-form content
   - Median: 582 words, Avg: 22.3 paragraphs

2. **`products.json`** - 197 products
   - Amazon reviews with preserved titles
   - 100% title coverage

3. **`support.json`** - 214 conversations
   - Customer queries + agent responses
   - 100% agent_reply coverage

4. **`social.json`** - 176 posts
   - Short-form social media content
   - Mix of short (83.5%) and medium (16.5%) posts

5. **`reviews.json`** - 196 reviews
   - Yelp restaurant reviews with ratings

### Rejected Data: `data/rejected/`
- `blogs_rejected.json` - 7 entries (2.8%)
- `products_rejected.json` - 3 entries (1.5%)
- `support_rejected.json` - 86 entries (28.7%)
- `social_rejected.json` - 24 entries (12.0%)
- `reviews_rejected.json` - 4 entries (2.0%)

**Total Cleaned Records**: 1,026 high-quality entries

---

## Validation Results

**File**: `logs/day4_validation_results.json`

**Status**: ✅ ALL 7 ACCEPTANCE CRITERIA PASSED

| Criterion | Status | Details |
|-----------|--------|---------|
| Blogs quality | ✓ PASS | median_wc: 582, avg_para: 22.29 |
| Product titles | ✓ PASS | 100% preservation (197/197) |
| Support replies | ✓ PASS | 100% coverage (214/214) |
| Social mixture | ✓ PASS | 83.5% short + 16.5% medium |
| Noise rate | ✓ PASS | All <30% (2.8%, 1.5%, 28.7%) |
| Language purity | ✓ PASS | 100% English |
| Duplicate ratio | ✓ PASS | 0% duplicates |

---

## Quick Access

**Run validation**: `python scripts/day4_validation.py`  
**View cleaned data**: Files in `data/cleaned/*.json`  
**Check logs**: `logs/day4_cleaning.log` and `logs/day4_validation_results.json`
