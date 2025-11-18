#!/usr/bin/env python3
"""
Email Newsletter Generator with Progress Tracking
Generate compelling email newsletters with enhanced user experience
"""
import sys
import requests
import time
from pathlib import Path

# API configuration
API_BASE_URL = "http://localhost:8000"

def print_email_header():
    print("\n" + "="*70)
    print("📧 EMAIL NEWSLETTER GENERATOR")
    print("="*70)
    print("Generate engaging email newsletters with enhanced experience!")
    print("\nFeatures:")
    print("  • Progress simulation with visual feedback")
    print("  • Real-time status updates")
    print("  • Professional newsletter formatting")
    print("\nCommands:")
    print("  'quit' or 'exit' - Exit the generator")
    print("  'help' - Show this help message") 
    print("  'tones' - Show available tone options")
    print("  'examples' - Show newsletter examples")
    print("="*70 + "\n")

def show_tone_options():
    print("\n🎨 AVAILABLE TONES:")
    print("  1. Professional - Formal, business-focused, authoritative")
    print("  2. Casual - Conversational, friendly, relaxed") 
    print("  3. Friendly - Warm, approachable, personal")
    print("  4. Persuasive - Compelling, action-oriented, sales-focused")
    print("  5. Educational - Informative, helpful, value-driven")
    print("  6. Urgent - Time-sensitive, important, immediate action")
    print("  7. Newsletter - Engaging, update-focused, community-oriented")

def show_newsletter_examples():
    print("\n💡 NEWSLETTER EXAMPLES:")
    print("  • Monthly Product Updates and New Features")
    print("  • Weekly Industry News Roundup")
    print("  • Company Announcements and Events")
    print("  • Educational Content and How-To Guides")
    print("  • Seasonal Promotions and Special Offers")
    print("  • Customer Success Stories and Case Studies")
    print("  • Team Updates and Behind-the-Scenes")
    print("  • Product Tips and Best Practices")

def get_tone_choice():
    """Get tone selection from user"""
    show_tone_options()
    while True:
        tone_key = input("\nSelect tone (1-7, default 7): ").strip()
        tone_map = {
            "1": "professional",
            "2": "casual", 
            "3": "friendly",
            "4": "persuasive",
            "5": "educational",
            "6": "urgent",
            "7": "newsletter"
        }
        
        if not tone_key:
            return "newsletter"
        elif tone_key in tone_map:
            return tone_map[tone_key]
        else:
            print("❌ Invalid selection. Please choose 1-7.")

def get_newsletter_details():
    """Get comprehensive newsletter information from user"""
    print("\n📧 NEWSLETTER DETAILS")
    print("-" * 40)
    
    # Newsletter topic (required)
    while True:
        topic = input("Newsletter topic: ").strip()
        if topic:
            break
        print("❌ Newsletter topic is required")
    
    # Newsletter type
    print("\n📋 NEWSLETTER TYPE")
    print("1. Product Updates")
    print("2. Company News")
    print("3. Educational Content")
    print("4. Promotional Offer")
    print("5. Event Announcement")
    print("6. Industry News")
    print("7. General Newsletter")
    
    type_choice = input("Select type (1-7, optional): ").strip()
    type_map = {
        "1": "product updates",
        "2": "company news",
        "3": "educational content",
        "4": "promotional offer",
        "5": "event announcement",
        "6": "industry news",
        "7": "general newsletter"
    }
    newsletter_type = type_map.get(type_choice, "general newsletter")
    
    # Target audience
    print("\n👥 TARGET AUDIENCE")
    audience = input("Who is this newsletter for? (press Enter for 'subscribers'): ").strip() or "subscribers"
    
    # Key points to cover
    print("\n📝 KEY POINTS TO COVER")
    print("Enter main points one by one (press Enter twice when done):")
    key_points = []
    while True:
        point = input("Point: ").strip()
        if point:
            key_points.append(point)
        elif key_points:
            break
        else:
            print("❌ Please enter at least one key point")
    
    # Call-to-action
    print("\n🎯 CALL-TO-ACTION")
    cta = input("What should readers do? (e.g., 'Learn more', 'Sign up', 'Shop now', optional): ").strip()
    
    # Word count
    try:
        word_input = input("Newsletter length in words (default 400): ").strip()
        word_count = int(word_input) if word_input else 400
        word_count = max(200, min(800, word_count))
    except ValueError:
        print("⚠️  Invalid number, using 400 words")
        word_count = 400
    
    # Build context object
    context = {
        "newsletter_info": {
            "type": newsletter_type,
            "key_points": key_points,
            "call_to_action": cta,
        },
        "target_audience": audience,
    }
    
    return topic, context, word_count

def simulate_progress(duration=8):
    """Simulate progress with visual feedback"""
    steps = [
        "📝 Analyzing your topic and requirements...",
        "🎯 Structuring newsletter sections...",
        "✍️  Writing compelling content...",
        "🔍 Optimizing for engagement...",
        "✨ Adding final touches...",
        "✅ Finalizing newsletter..."
    ]
    
    for i, step in enumerate(steps):
        print(f"🔄 {step}")
        time.sleep(duration / len(steps))
        
        # Show progress bar
        progress = (i + 1) / len(steps) * 100
        bar_length = 30
        filled = int(bar_length * (i + 1) / len(steps))
        bar = "█" * filled + "░" * (bar_length - filled)
        print(f"   [{bar}] {progress:.0f}%")
    
    print("🎉 Newsletter generated successfully!")

def generate_email_newsletter(topic, tone, context, word_count):
    """Generate email newsletter using the correct endpoints"""
    print(f"\n{'─'*70}")
    print(f"📧 GENERATING EMAIL NEWSLETTER...")
    print(f"📝 Topic: {topic}")
    print(f"🎨 Tone: {tone}")
    print(f"📊 Target Words: {word_count}")
    print(f"{'─'*70}\n")
    
    payload = {
        "content_type": "email_newsletter",
        "topic": topic,
        "tone": tone,
        "word_count": word_count,
        "context": context
    }
    
    try:
        # Show progress simulation
        simulate_progress(10)
        
        # Make the actual API call to the CORRECT newsletter endpoint
        response = requests.post(
            f"{API_BASE_URL}/v2/generate/content",
            json=payload,
            timeout=120
        )
        
        if response.status_code != 200:
            print(f"❌ API Error: {response.status_code}")
            try:
                error_detail = response.json()
                print(f"   Detail: {error_detail}")
            except:
                print(f"   Response: {response.text}")
            return None
        
        data = response.json()
        
        # Display the newsletter in a professional format
        print(f"\n{'═'*70}")
        print(f"📧 EMAIL NEWSLETTER: {topic.upper()}")
        print(f"{'═'*70}\n")
        print(f"{data['content']}\n")
        print(f"{'═'*70}")
        
        # Show metadata
        metadata = data.get('metadata', {})
        print(f"📊 Stats: {metadata.get('estimated_words', 0)} words | "
              f"Tone: {metadata.get('tone', 'N/A')}")
        print(f"⏱️  Generated in: {data['latency_s']:.2f}s")
        print(f"{'═'*70}\n")
        
        return data
        
    except requests.exceptions.ConnectionError:
        print(f"❌ Cannot connect to API server at {API_BASE_URL}")
        print("   Please make sure the server is running:")
        print("   uvicorn backend.main:app --reload --host 0.0.0.0 --port 8000")
        return None
    except requests.exceptions.Timeout:
        print("❌ Request timeout - the generation took too long")
        return None
    except Exception as e:
        print(f"❌ Unexpected error: {e}")
        return None

def save_newsletter(newsletter_data, context, topic):
    """Save generated newsletter to a text file"""
    if not newsletter_data:
        print("❌ No newsletter data to save")
        return False
        
    filename = f"newsletter_{topic.replace(' ', '_').lower()[:30]}.txt"
    
    try:
        with open(filename, 'w', encoding='utf-8') as f:
            f.write(f"EMAIL NEWSLETTER\n")
            f.write("=" * 50 + "\n\n")
            f.write(f"Topic: {topic}\n")
            f.write(f"Type: {context['newsletter_info'].get('type', 'general newsletter')}\n")
            f.write(f"Target Audience: {context['target_audience']}\n")
            f.write(f"Tone: {newsletter_data.get('metadata', {}).get('tone', 'N/A')}\n")
            f.write(f"Word Count: {newsletter_data.get('metadata', {}).get('estimated_words', 0)}\n")
            f.write(f"Generation Time: {newsletter_data['latency_s']:.2f}s\n")
            
            # Write key points
            if context["newsletter_info"].get("key_points"):
                f.write(f"\nKEY POINTS COVERED:\n")
                for point in context["newsletter_info"]["key_points"]:
                    f.write(f"• {point}\n")
            
            if context["newsletter_info"].get("call_to_action"):
                f.write(f"Call-to-Action: {context['newsletter_info']['call_to_action']}\n")
            
            f.write("\n" + "=" * 50 + "\n\n")
            f.write(f"{newsletter_data['content']}\n")
        
        print(f"✅ Newsletter saved as: {filename}")
        return True
    except Exception as e:
        print(f"❌ Error saving file: {e}")
        return False

def check_api_health():
    """Check if the API server is running and newsletter endpoints work"""
    try:
        response = requests.get(f"{API_BASE_URL}/health", timeout=5)
        
        if response.status_code == 200:
            health_data = response.json()
            print(f"✅ API Server: {health_data.get('status', 'ok')}")
            
            # Test the actual newsletter endpoint
            test_payload = {
                "content_type": "email_newsletter",
                "topic": "test connection",
                "tone": "professional",
                "word_count": 100,
                "context": {"target_audience": "test"}
            }
            
            test_response = requests.post(
                f"{API_BASE_URL}/v2/generate/content",
                json=test_payload,
                timeout=180
                
            )
            
            if test_response.status_code == 200:
                print("✅ Newsletter Endpoint: Working correctly")
                return True
            else:
                print(f"❌ Newsletter Endpoint: Failed with status {test_response.status_code}")
                return False
        else:
            print("❌ API Server: Not responding")
            return False
            
    except requests.exceptions.ConnectionError:
        print(f"❌ Cannot connect to {API_BASE_URL}")
        return False
    except Exception as e:
        print(f"❌ Error checking API: {e}")
        return False

def main():
    """Main email newsletter generation loop"""
    print_email_header()
    
    # Check API health
    print("🔍 Checking API connection...")
    if not check_api_health():
        print("\n❌ Cannot connect to Email Newsletter Generator API.")
        print("   Please make sure:")
        print("   1. Server is running: uvicorn backend.main:app --reload --host 0.0.0.0 --port 8000")
        print("   2. The /v2/generate/content endpoint exists for email_newsletter")
        print("   3. Ollama is running: ollama serve")
        return
    
    # Show examples
    show_newsletter_examples()
    
    newsletter_count = 0
    
    while True:
        try:
            user_input = input("\n📧 Enter 'start' to begin or command > ").strip().lower()
            
            if not user_input:
                continue
                
            if user_input in ['quit', 'exit', 'q']:
                print(f"\n👋 Thanks for using the Email Newsletter Generator!")
                print(f"📊 Total newsletters generated: {newsletter_count}\n")
                break
                
            if user_input == 'help':
                print_email_header()
                continue
                
            if user_input == 'tones':
                show_tone_options()
                continue
                
            if user_input == 'examples':
                show_newsletter_examples()
                continue
            
            if user_input == 'start' or user_input == 's':
                # Get newsletter details
                topic, context, word_count = get_newsletter_details()
                tone = get_tone_choice()
                
                # Generate newsletter using the CORRECT endpoint
                result = generate_email_newsletter(topic, tone, context, word_count)
                
                if result:
                    newsletter_count += 1
                    
                    # Ask if user wants to save
                    save = input("\n💾 Save this newsletter? (y/N) > ").strip().lower()
                    if save == 'y':
                        save_newsletter(result, context, topic)
                    
                    # Ask if user wants to generate another
                    another = input("\n🔄 Generate another newsletter? (y/N) > ").strip().lower()
                    if another != 'y':
                        print(f"\n👋 Thanks for using the Email Newsletter Generator!")
                        print(f"📊 Total newsletters generated: {newsletter_count}\n")
                        break
            
            else:
                print("❌ Unknown command. Type 'help' for available commands.")
            
        except KeyboardInterrupt:
            print("\n\n👋 Newsletter generation interrupted. Goodbye!\n")
            break
        except Exception as e:
            print(f"\n❌ Error: {e}")

if __name__ == "__main__":
    main()