# scripts/cli_review_tool.py
"""
Day 8: Command-Line Review Tool
Alternative to Streamlit UI for Python 3.13 compatibility issues
"""
import httpx
import csv
import json
from datetime import datetime
from pathlib import Path

BACKEND_URL = "http://localhost:8000"
FEEDBACK_CSV = Path("data/human_feedback.csv")
TIMEOUT = 30

# Ensure CSV exists
FEEDBACK_CSV.parent.mkdir(parents=True, exist_ok=True)
if not FEEDBACK_CSV.exists():
    with open(FEEDBACK_CSV, 'w', newline='', encoding='utf-8') as f:
        writer = csv.writer(f)
        writer.writerow([
            'timestamp', 'session_id', 'content_type', 'topic', 'tone',
            'input_prompt', 'retrieved_context', 'generated_headline', 
            'generated_body', 'decision', 'edited_headline', 'edited_body',
            'reviewer_notes', 'validation_issues', 'latency_s'
        ])

def print_header(text):
    print("\n" + "="*70)
    print(f"  {text}")
    print("="*70 + "\n")

def check_backend():
    """Check if backend is running"""
    try:
        response = httpx.get(f"{BACKEND_URL}/health", timeout=5)
        if response.status_code == 200:
            data = response.json()
            print(f"✅ Backend: Connected")
            print(f"   Vector DB: {'Available' if data.get('vector_db') else 'Unavailable'}")
            return True
        else:
            print(f"❌ Backend returned status {response.status_code}")
            return False
    except Exception as e:
        print(f"❌ Cannot connect to backend: {e}")
        print(f"   Start with: uvicorn backend.main:app --reload")
        return False

def generate_content(content_type, topic, tone):
    """Generate content via API"""
    print(f"\n🔄 Generating {content_type}...")
    try:
        response = httpx.post(
            f"{BACKEND_URL}/v1/generate/content",
            json={"content_type": content_type, "topic": topic, "tone": tone},
            timeout=TIMEOUT
        )
        if response.status_code == 200:
            return response.json()
        else:
            print(f"❌ Generation failed: {response.status_code}")
            print(response.text)
            return None
    except httpx.TimeoutException:
        print("⏱️ Generation timed out (model may be slow, try again)")
        return None
    except Exception as e:
        print(f"❌ Error: {e}")
        return None

def retrieve_context(query, collection=None):
    """Retrieve RAG context"""
    try:
        response = httpx.post(
            f"{BACKEND_URL}/v1/retrieve",
            json={"query": query, "collection": collection, "top_k": 3},
            timeout=10
        )
        if response.status_code == 200:
            return response.json()
        return None
    except:
        return None

def validate_content(headline, body):
    """Run validation checks"""
    issues = []
    
    # Empty check
    if not headline.strip() or not body.strip():
        issues.append("Content is empty")
    
    # Length check
    if len(body.strip()) < 20:
        issues.append(f"Body too short ({len(body)} chars, min 20)")
    
    # Profanity check (simple)
    bad_words = ['damn', 'hell', 'shit', 'fuck', 'bitch', 'stupid', 'idiot']
    text_lower = (headline + " " + body).lower()
    found = [w for w in bad_words if w in text_lower]
    if found:
        issues.append(f"Inappropriate language: {', '.join(found)}")
    
    # Spam patterns
    spam = ['click here', 'free money', 'act now', 'guaranteed', '100% free']
    found_spam = [p for p in spam if p in text_lower]
    if found_spam:
        issues.append(f"Spam patterns: {', '.join(found_spam)}")
    
    return issues

def save_feedback(data):
    """Save review to CSV"""
    try:
        with open(FEEDBACK_CSV, 'a', newline='', encoding='utf-8') as f:
            writer = csv.writer(f)
            writer.writerow([
                data.get('timestamp'),
                data.get('session_id'),
                data.get('content_type'),
                data.get('topic'),
                data.get('tone'),
                data.get('input_prompt'),
                data.get('retrieved_context', ''),
                data.get('generated_headline'),
                data.get('generated_body'),
                data.get('decision'),
                data.get('edited_headline', ''),
                data.get('edited_body', ''),
                data.get('reviewer_notes', ''),
                data.get('validation_issues', ''),
                data.get('latency_s', 0.0)
            ])
        return True
    except Exception as e:
        print(f"❌ Failed to save: {e}")
        return False

def review_workflow():
    """Main review workflow"""
    session_id = datetime.now().strftime('%Y%m%d_%H%M%S')
    
    print_header("DAY 8: CLI REVIEW TOOL")
    
    # Check backend
    if not check_backend():
        return
    
    # Configuration
    print("\n📝 Configure Content Generation:")
    
    content_types = ['blog', 'product_description', 'ad_copy', 'email_newsletter', 'social_media', 'support_reply']
    print("\nContent Types:")
    for i, ct in enumerate(content_types, 1):
        print(f"  {i}. {ct}")
    
    try:
        choice = int(input("\nSelect type (1-6): ").strip())
        content_type = content_types[choice - 1]
    except:
        print("Invalid choice, using 'blog'")
        content_type = 'blog'
    
    topic = input("Enter topic: ").strip()
    if not topic:
        topic = "AI-powered automation"
        print(f"Using default: {topic}")
    
    tones = ['neutral', 'empathetic', 'formal', 'friendly', 'professional', 'casual']
    print("\nTones:", ', '.join(tones))
    tone = input("Enter tone (or press Enter for 'professional'): ").strip() or 'professional'
    
    use_rag = input("\nEnable RAG context? (y/n): ").strip().lower() == 'y'
    
    # Generate content
    result = generate_content(content_type, topic, tone)
    if not result:
        print("\n❌ Generation failed. Try again.")
        return
    
    headline = result.get('headline', '')
    body = result.get('body', '')
    latency = result.get('latency_s', 0)
    
    # Retrieve context if enabled
    context_data = None
    if use_rag:
        print("\n🔍 Retrieving RAG context...")
        context_data = retrieve_context(topic)
        if context_data and context_data.get('results'):
            print(f"   Found {len(context_data['results'])} relevant documents")
    
    # Display results
    print_header("GENERATED CONTENT")
    
    print(f"Content Type: {content_type}")
    print(f"Topic: {topic}")
    print(f"Tone: {tone}")
    print(f"Latency: {latency:.2f}s\n")
    
    if context_data and context_data.get('results'):
        print("📚 Retrieved Context:")
        for i, doc in enumerate(context_data['results'][:2], 1):
            print(f"   {i}. {doc['text'][:80]}...")
            print(f"      Collection: {doc['collection']}, Distance: {doc['distance']:.3f}")
        print()
    
    print(f"Headline: {headline}")
    print(f"\nBody:\n{body}\n")
    
    # Validation
    issues = validate_content(headline, body)
    if issues:
        print("⚠️ Validation Issues:")
        for issue in issues:
            print(f"   • {issue}")
        print()
    else:
        print("✅ All validation checks passed\n")
    
    # Review decision
    print_header("REVIEW DECISION")
    print("1. Approve")
    print("2. Reject")
    print("3. Edit")
    print("4. Skip")
    
    decision_choice = input("\nYour choice (1-4): ").strip()
    
    feedback_data = {
        'timestamp': datetime.utcnow().isoformat(),
        'session_id': session_id,
        'content_type': content_type,
        'topic': topic,
        'tone': tone,
        'input_prompt': topic,
        'retrieved_context': json.dumps(context_data) if context_data else '',
        'generated_headline': headline,
        'generated_body': body,
        'latency_s': latency,
        'validation_issues': '; '.join(issues)
    }
    
    if decision_choice == '1':  # Approve
        feedback_data['decision'] = 'approved'
        feedback_data['edited_headline'] = ''
        feedback_data['edited_body'] = ''
        feedback_data['reviewer_notes'] = ''
        
        if save_feedback(feedback_data):
            print("\n✅ Content approved and saved!")
        
    elif decision_choice == '2':  # Reject
        notes = input("\nWhy are you rejecting this content? ").strip()
        feedback_data['decision'] = 'rejected'
        feedback_data['edited_headline'] = ''
        feedback_data['edited_body'] = ''
        feedback_data['reviewer_notes'] = notes
        
        if save_feedback(feedback_data):
            print("\n❌ Content rejected and feedback saved!")
    
    elif decision_choice == '3':  # Edit
        print("\nEdit mode (press Enter to keep original):")
        edited_headline = input(f"\nNew headline [{headline[:50]}...]: ").strip() or headline
        print(f"\nOriginal body:\n{body}\n")
        edited_body = input("New body (or press Enter to keep): ").strip() or body
        notes = input("\nEditor notes: ").strip()
        
        # Validate edited content
        edit_issues = validate_content(edited_headline, edited_body)
        if edit_issues:
            print("\n⚠️ Edited content still has issues:")
            for issue in edit_issues:
                print(f"   • {issue}")
            confirm = input("\nSave anyway? (y/n): ").strip().lower()
            if confirm != 'y':
                print("Edit canceled.")
                return
        
        feedback_data['decision'] = 'edited'
        feedback_data['edited_headline'] = edited_headline
        feedback_data['edited_body'] = edited_body
        feedback_data['reviewer_notes'] = notes
        
        if save_feedback(feedback_data):
            print("\n✏️ Edited content saved!")
    
    else:
        print("\nSkipped (not saved)")
        return
    
    # Show stats
    try:
        with open(FEEDBACK_CSV, 'r', encoding='utf-8') as f:
            reader = csv.DictReader(f)
            rows = list(reader)
            total = len(rows)
            approved = sum(1 for r in rows if r['decision'] == 'approved')
            rejected = sum(1 for r in rows if r['decision'] == 'rejected')
            edited = sum(1 for r in rows if r['decision'] == 'edited')
            
            print(f"\n📊 Review Statistics:")
            print(f"   Total: {total} | Approved: {approved} | Rejected: {rejected} | Edited: {edited}")
            if total > 0:
                print(f"   Approval Rate: {approved/total*100:.1f}%")
    except:
        pass
    
    print(f"\n💾 Feedback saved to: {FEEDBACK_CSV}")

if __name__ == "__main__":
    try:
        while True:
            review_workflow()
            
            again = input("\n\nReview another item? (y/n): ").strip().lower()
            if again != 'y':
                print("\n👋 Thanks for reviewing!")
                break
    except KeyboardInterrupt:
        print("\n\n👋 Review session ended.")
    except Exception as e:
        print(f"\n❌ Error: {e}")
