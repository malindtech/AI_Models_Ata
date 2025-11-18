#!/usr/bin/env python3
"""
Social Media Post Generator Chat
Generate engaging social media posts through interactive chat
"""
import sys
import requests
from pathlib import Path

# API configuration
API_BASE_URL = "http://localhost:8000"

def print_social_header():
    print("\n" + "="*70)
    print("📱 AI SOCIAL MEDIA POST GENERATOR")
    print("="*70)
    print("Generate engaging social media posts for all platforms!")
    print("\nCommands:")
    print("  'quit' or 'exit' - Exit the generator")
    print("  'help' - Show this help message") 
    print("  'tones' - Show available tone options")
    print("  'platforms' - Show platform options")
    print("  'examples' - Show post examples")
    print("="*70 + "\n")

def show_tone_options():
    print("\n🎨 AVAILABLE TONES:")
    print("  1. Professional - Formal, business-focused, authoritative")
    print("  2. Casual - Conversational, friendly, relaxed") 
    print("  3. Friendly - Warm, approachable, personal")
    print("  4. Persuasive - Compelling, action-oriented, sales-focused")
    print("  5. Humorous - Funny, witty, entertaining")
    print("  6. Inspirational - Motivational, uplifting, positive")
    print("  7. Urgent - Time-sensitive, important, immediate action")
    print("  8. Educational - Informative, helpful, value-driven")

def show_platform_options():
    print("\n📱 SOCIAL MEDIA PLATFORMS:")
    print("  1. Twitter/X - Short, concise, trending topics")
    print("  2. Instagram - Visual, engaging, story-focused")
    print("  3. Facebook - Conversational, community-oriented")
    print("  4. LinkedIn - Professional, industry-focused")
    print("  5. TikTok - Trendy, creative, viral content")
    print("  6. Pinterest - Inspirational, visual, DIY-focused")
    print("  7. All Platforms - General social media post")

def show_post_examples():
    print("\n💡 POST EXAMPLES:")
    print("  • Product Launch Announcement")
    print("  • Company News and Updates")
    print("  • Behind-the-Scenes Content")
    print("  • Customer Testimonials")
    print("  • Industry Tips and Insights")
    print("  • Event Promotions")
    print("  • Limited Time Offers")
    print("  • Educational Content")

def get_tone_choice():
    """Get tone selection from user"""
    show_tone_options()
    while True:
        tone_key = input("\nSelect tone (1-8, default 3): ").strip()
        tone_map = {
            "1": "professional",
            "2": "casual", 
            "3": "friendly",
            "4": "persuasive",
            "5": "humorous",
            "6": "inspirational",
            "7": "urgent",
            "8": "educational"
        }
        
        if not tone_key:
            return "friendly"  # Default for social media
        elif tone_key in tone_map:
            return tone_map[tone_key]
        else:
            print("❌ Invalid selection. Please choose 1-8.")

def get_platform_choice():
    """Get platform selection from user"""
    show_platform_options()
    while True:
        platform_key = input("\nSelect platform (1-7, default 7): ").strip()
        platform_map = {
            "1": "twitter",
            "2": "instagram", 
            "3": "facebook",
            "4": "linkedin",
            "5": "tiktok",
            "6": "pinterest",
            "7": "all_platforms"
        }
        
        if not platform_key:
            return "all_platforms"  # Default for all platforms
        elif platform_key in platform_map:
            return platform_map[platform_key]
        else:
            print("❌ Invalid selection. Please choose 1-7.")

def get_post_details():
    """Get comprehensive post information from user"""
    print("\n📝 POST DETAILS")
    print("-" * 40)
    
    # Post topic (required)
    while True:
        topic = input("Post topic: ").strip()
        if topic:
            break
        print("❌ Post topic is required")
    
    # Post type
    print("\n📋 POST TYPE")
    print("1. Announcement")
    print("2. Promotion")
    print("3. Educational")
    print("4. Question/Engagement")
    print("5. Story/Behind-the-Scenes")
    print("6. Event")
    print("7. General Update")
    
    type_choice = input("Select type (1-7, optional): ").strip()
    type_map = {
        "1": "announcement",
        "2": "promotion",
        "3": "educational",
        "4": "engagement",
        "5": "story",
        "6": "event",
        "7": "general"
    }
    post_type = type_map.get(type_choice, "general")
    
    # Target audience
    print("\n👥 TARGET AUDIENCE")
    audience = input("Who is this post for? (press Enter for 'followers'): ").strip() or "followers"
    
    # Key message
    print("\n💬 KEY MESSAGE")
    key_message = input("Main message to convey (optional): ").strip()
    
    # Call-to-action
    print("\n🎯 CALL-TO-ACTION")
    print("1. Like/Share")
    print("2. Comment")
    print("3. Click Link")
    print("4. Learn More")
    print("5. Shop Now")
    print("6. Sign Up")
    print("7. No specific CTA")
    
    cta_choice = input("Select CTA (1-7, default 1): ").strip() or "1"
    cta_map = {
        "1": "like and share",
        "2": "comment your thoughts",
        "3": "click the link in bio",
        "4": "learn more on our website",
        "5": "shop now",
        "6": "sign up today",
        "7": ""
    }
    call_to_action = cta_map.get(cta_choice, "like and share")
    
    # Hashtag preferences
    print("\n🏷️  HASHTAGS")
    print("1. Include trending hashtags")
    print("2. Include niche-specific hashtags")
    print("3. Include both trending and niche")
    print("4. Minimal hashtags")
    print("5. No hashtags")
    
    hashtag_choice = input("Hashtag preference (1-5, default 3): ").strip() or "3"
    
    # Custom hashtags
    custom_hashtags_input = input("Custom hashtags (comma-separated, optional): ").strip()
    custom_hashtags = [h.strip() for h in custom_hashtags_input.split(",") if h.strip()]
    
    # Keywords for optimization
    keywords_input = input("Keywords (comma-separated, optional): ").strip()
    keywords = [k.strip() for k in keywords_input.split(",") if k.strip()]
    
    # Build context object
    context = {
        "post_info": {
            "type": post_type,
            "key_message": key_message,
            "call_to_action": call_to_action,
            "hashtag_preference": hashtag_choice,
            "custom_hashtags": custom_hashtags
        },
        "target_audience": audience,
        "keywords": keywords
    }
    
    return topic, context

def generate_social_media_post(topic, tone, platform, context):
    """Generate social media post using the multi-agent system"""
    print(f"\n{'─'*70}")
    print(f"📱 GENERATING SOCIAL MEDIA POST...")
    print(f"📝 Topic: {topic}")
    print(f"🎨 Tone: {tone}")
    print(f"📲 Platform: {platform.replace('_', ' ').title()}")
    print(f"{'─'*70}\n")
    
    # Add platform to context
    context["platform"] = platform
    
    payload = {
        "content_type": "social_media_post",
        "topic": topic,
        "tone": tone,
        "word_count": 150,  # Optimal for social media
        "context": context
    }
    
    try:
        response = requests.post(
            f"{API_BASE_URL}/v2/generate/content",
            json=payload,
            timeout=180  # Same timeout as other scripts
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
        
        print(f"📱 SOCIAL MEDIA POST:")
        print(f"{'─'*70}\n")
        print(f"{data['content']}\n")
        print(f"{'─'*70}")
        
        # Show metadata
        metadata = data.get('metadata', {})
        print(f"📊 Stats: {metadata.get('estimated_words', 0)} words | "
              f"Tone: {metadata.get('tone', 'N/A')}")
        print(f"⏱️  Generated in: {data['latency_s']:.2f}s")
        print(f"{'─'*70}\n")
        
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

def save_social_post(post_data, context, topic, platform):
    """Save generated social media post to a text file"""
    filename = f"social_post_{topic.replace(' ', '_').lower()[:25]}.txt"
    
    try:
        with open(filename, 'w', encoding='utf-8') as f:
            f.write(f"SOCIAL MEDIA POST\n")
            f.write("=" * 50 + "\n\n")
            f.write(f"Topic: {topic}\n")
            f.write(f"Platform: {platform.replace('_', ' ').title()}\n")
            f.write(f"Post Type: {context['post_info'].get('type', 'general').title()}\n")
            f.write(f"Target Audience: {context['target_audience']}\n")
            f.write(f"Tone: {post_data['metadata'].get('tone', 'N/A')}\n")
            f.write(f"Word Count: {post_data['metadata'].get('estimated_words', 0)}\n")
            f.write(f"Generation Time: {post_data['latency_s']:.2f}s\n")
            
            # Write post details
            if context["post_info"].get("key_message"):
                f.write(f"Key Message: {context['post_info']['key_message']}\n")
            
            if context["post_info"].get("call_to_action"):
                f.write(f"Call-to-Action: {context['post_info']['call_to_action']}\n")
            
            if context["post_info"].get("custom_hashtags"):
                f.write(f"Custom Hashtags: {', '.join(context['post_info']['custom_hashtags'])}\n")
            
            if context.get("keywords"):
                f.write(f"Keywords: {', '.join(context['keywords'])}\n")
            
            f.write("\n" + "=" * 50 + "\n\n")
            f.write(f"{post_data['content']}\n")
        
        print(f"✅ Social media post saved as: {filename}")
        return True
    except Exception as e:
        print(f"❌ Error saving file: {e}")
        return False

def check_api_health():
    """Check if the API server is running"""
    try:
        response = requests.get(f"{API_BASE_URL}/health", timeout=5)
        ready_response = requests.get(f"{API_BASE_URL}/ready", timeout=10)
        
        if response.status_code == 200:
            health_data = response.json()
            print(f"✅ API Server: {health_data.get('status', 'ok')}")
            
            if ready_response.status_code == 200:
                ready_data = ready_response.json()
                if ready_data.get("model_ok"):
                    print("✅ LLaMA Model: Ready and responsive")
                    return True
                else:
                    print("❌ LLaMA Model: Not responding properly")
                    return False
            else:
                print("❌ LLaMA Model: Readiness check failed")
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
    """Main social media post generation loop"""
    print_social_header()
    
    # Check API health
    print("🔍 Checking API connection...")
    if not check_api_health():
        print("\n❌ Cannot connect to Social Media Post Generator API.")
        print("   Please make sure the server is running:")
        print("   uvicorn backend.main:app --reload --host 0.0.0.0 --port 8000")
        print("\n   Also ensure Ollama is running:")
        print("   ollama serve")
        return
    
    # Show examples
    show_post_examples()
    
    post_count = 0
    
    while True:
        try:
            # Get user command
            user_input = input("\n📱 Enter 'start' to begin or command > ").strip().lower()
            
            # Handle commands
            if not user_input:
                continue
                
            if user_input in ['quit', 'exit', 'q']:
                print(f"\n👋 Thanks for using the Social Media Post Generator!")
                print(f"📊 Total posts generated: {post_count}\n")
                break
                
            if user_input == 'help':
                print_social_header()
                continue
                
            if user_input == 'tones':
                show_tone_options()
                continue
                
            if user_input == 'platforms':
                show_platform_options()
                continue
                
            if user_input == 'examples':
                show_post_examples()
                continue
            
            if user_input == 'start' or user_input == 's':
                # Get post details
                topic, context = get_post_details()
                
                # Get tone selection
                tone = get_tone_choice()
                
                # Get platform selection
                platform = get_platform_choice()
                
                # Generate social media post
                result = generate_social_media_post(topic, tone, platform, context)
                
                if result:
                    post_count += 1
                    
                    # Ask if user wants to save
                    save = input("\n💾 Save this social media post? (y/N) > ").strip().lower()
                    if save == 'y':
                        save_social_post(result, context, topic, platform)
                    
                    # Ask if user wants to generate another
                    another = input("\n🔄 Generate another social media post? (y/N) > ").strip().lower()
                    if another != 'y':
                        print(f"\n👋 Thanks for using the Social Media Post Generator!")
                        print(f"📊 Total posts generated: {post_count}\n")
                        break
            
            else:
                print("❌ Unknown command. Type 'help' for available commands.")
            
        except KeyboardInterrupt:
            print("\n\n👋 Social media post generation interrupted. Goodbye!\n")
            break
        except EOFError:
            print("\n\n👋 End of input. Goodbye!\n")
            break

if __name__ == "__main__":
    main()