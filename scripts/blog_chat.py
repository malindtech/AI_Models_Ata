#!/usr/bin/env python3
"""
Interactive Blog Generator Chat
Generate blog posts by providing topics and preferences via terminal
"""
import sys
import json
import requests
from pathlib import Path

# API configuration
API_BASE_URL = "http://localhost:8000"

def print_blog_header():
    print("\n" + "="*70)
    print("📝 AI BLOG GENERATOR - Interactive Writer")
    print("="*70)
    print("Generate complete blog posts by providing a topic and preferences!")
    print("\nCommands:")
    print("  'quit' or 'exit' - Exit the blog generator")
    print("  'help' - Show this help message") 
    print("  'styles' - Show available writing styles")
    print("  'lengths' - Show length options")
    print("  'ideas' - Generate blog topic ideas")
    print("  'detail' - Enter detailed mode for full control")
    print("="*70 + "\n")

def show_writing_styles():
    print("\n📚 AVAILABLE WRITING STYLES:")
    print("  • professional - Formal, authoritative, industry-focused")
    print("  • casual - Conversational, friendly, relatable") 
    print("  • technical - Detailed, precise, expert-oriented")
    print("  • persuasive - Compelling, benefit-focused, action-oriented")
    print("  • educational - Explanatory, step-by-step, beginner-friendly\n")

def show_length_options():
    print("\n📏 BLOG LENGTH OPTIONS:")
    print("  • short - Brief (2-3 paragraphs, ~300 words)")
    print("  • medium - Standard (4-6 paragraphs, ~500 words)")
    print("  • long - Comprehensive (7+ paragraphs, ~800 words)\n")

def generate_blog_post(topic, style="professional", audience="general", length="medium"):
    """Generate blog post and display formatted result"""
    print(f"\n{'─'*70}")
    print(f"🎯 GENERATING BLOG POST...")
    print(f"📝 Topic: {topic}")
    print(f"🎨 Style: {style}")
    print(f"👥 Audience: {audience}")
    print(f"📏 Length: {length}")
    print(f"{'─'*70}\n")
    
    try:
        # Call the Blog Generation endpoint
        response = requests.post(
            f"{API_BASE_URL}/v1/generate/blog",
            json={
                "topic": topic,
                "style": style,
                "audience": audience,
                "length": length
            },
            timeout=180
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
        blog = data['blog']
        
        # Display the generated blog post
        print(f"📖 {blog['title']}")
        print(f"{'─'*50}\n")
        
        print(f"📍 INTRODUCTION:")
        print(f"{blog['introduction']}\n")
        
        print(f"📝 BODY:")
        print(f"{blog['body']}\n")
        
        print(f"🎯 CONCLUSION:")
        print(f"{blog['conclusion']}\n")
        
        print(f"🏷️  TAGS: {', '.join(blog['tags'])}")
        
        print(f"\n{'─'*70}")
        print(f"⏱️  Generation time: {data['latency_s']:.2f}s")
        print(f"{'─'*70}\n")
        
        return data
        
    except requests.exceptions.ConnectionError:
        print(f"❌ Cannot connect to API server at {API_BASE_URL}")
        print("   Please make sure the server is running:")
        print("   uvicorn backend.main:app --reload --host 0.0.0.0 --port 8000")
        return None
    except requests.exceptions.Timeout:
        print("❌ Request timeout - the blog generation took too long")
        return None
    except Exception as e:
        print(f"❌ Unexpected error: {e}")
        return None

def generate_blog_ideas(category, count=5):
    """Generate blog topic ideas"""
    print(f"\n💡 Generating {count} blog ideas about: {category}")
    
    try:
        response = requests.post(
            f"{API_BASE_URL}/v1/generate/blog-ideas",
            json={
                "category": category,
                "count": count
            },
            timeout=180
        )
        
        if response.status_code != 200:
            print(f"❌ API Error: {response.status_code}")
            return []
        
        data = response.json()
        print(f"\n🎯 BLOG IDEAS FOR '{category}':")
        print("-" * 50)
        for i, idea in enumerate(data['ideas'], 1):
            print(f"{i}. {idea}")
        print("-" * 50)
        print(f"⏱️  Generated in {data['latency_s']:.2f}s\n")
        
        return data['ideas']
        
    except requests.exceptions.ConnectionError:
        print(f"❌ Cannot connect to API server at {API_BASE_URL}")
        return []
    except Exception as e:
        print(f"❌ Error: {e}")
        return []

def get_blog_preferences():
    """Get detailed blog preferences from user"""
    print("\n📝 Please provide blog details:")
    
    topic = input("🎯 Blog topic > ").strip()
    if not topic:
        print("❌ Topic cannot be empty")
        return None
    
    print("\n🎨 Writing style (press Enter for 'professional'):")
    style = input("Style > ").strip().lower()
    if not style:
        style = "professional"
    elif style not in ['professional', 'casual', 'technical', 'persuasive', 'educational']:
        print(f"⚠️  Unknown style '{style}', using 'professional'")
        style = "professional"
    
    audience = input("👥 Target audience (press Enter for 'general') > ").strip()
    if not audience:
        audience = "general"
    
    print("\n📏 Length (short/medium/long, press Enter for 'medium'):")
    length = input("Length > ").strip().lower()
    if not length:
        length = "medium"
    elif length not in ['short', 'medium', 'long']:
        print(f"⚠️  Unknown length '{length}', using 'medium'")
        length = "medium"
    
    return {
        "topic": topic,
        "style": style,
        "audience": audience,
        "length": length
    }

def save_blog_to_file(blog_data, filename=None):
    """Save generated blog to a text file"""
    if not filename:
        # Create filename from topic
        topic = blog_data['topic']
        filename = f"blog_{topic.replace(' ', '_').lower()[:30]}.txt"
    
    try:
        with open(filename, 'w', encoding='utf-8') as f:
            f.write(f"Title: {blog_data['blog']['title']}\n")
            f.write(f"Topic: {blog_data['topic']}\n")
            f.write(f"Style: {blog_data['style']}\n")
            f.write(f"Audience: {blog_data['audience']}\n")
            f.write(f"Length: {blog_data['length']}\n")
            f.write(f"Tags: {', '.join(blog_data['blog']['tags'])}\n")
            f.write(f"Generation Time: {blog_data['latency_s']:.2f}s\n")
            f.write("\n" + "="*60 + "\n\n")
            f.write(f"INTRODUCTION:\n{blog_data['blog']['introduction']}\n\n")
            f.write(f"BODY:\n{blog_data['blog']['body']}\n\n")
            f.write(f"CONCLUSION:\n{blog_data['blog']['conclusion']}\n")
        
        print(f"✅ Blog saved as: {filename}")
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
    """Main interactive blog generation loop"""
    print_blog_header()
    
    # Test connection first
    print("🔍 Checking API connection...")
    if not check_api_health():
        print("\n❌ Cannot connect to Blog Generator API.")
        print("   Please make sure the server is running:")
        print("   uvicorn backend.main:app --reload --host 0.0.0.0 --port 8000")
        print("\n   Also ensure Ollama is running:")
        print("   ollama serve")
        return
    
    # Show some example topics
    print("\n💡 Try these example topics:")
    print("   • The Future of Artificial Intelligence")
    print("   • How to Improve Your Productivity")
    print("   • Sustainable Living Tips for Urban Dwellers")
    print("   • Introduction to Machine Learning")
    print("   • The Benefits of Remote Work\n")
    
    blog_count = 0
    
    while True:
        try:
            # Get user command
            user_input = input("\n📝 Enter topic or command > ").strip()
            
            # Handle commands
            if not user_input:
                continue
                
            if user_input.lower() in ['quit', 'exit', 'q']:
                print(f"\n👋 Thanks for using the Blog Generator!")
                print(f"📊 Total blogs generated: {blog_count}\n")
                break
                
            if user_input.lower() == 'help':
                print_blog_header()
                continue
                
            if user_input.lower() == 'styles':
                show_writing_styles()
                continue
                
            if user_input.lower() == 'lengths':
                show_length_options()
                continue
                
            if user_input.lower() == 'ideas':
                category = input("Enter category for ideas > ").strip()
                if category:
                    count_input = input("How many ideas? (1-15, default 5) > ").strip()
                    count = 5
                    if count_input:
                        try:
                            count = max(1, min(15, int(count_input)))
                        except ValueError:
                            print("⚠️  Invalid number, using 5")
                    
                    ideas = generate_blog_ideas(category, count)
                    if ideas:
                        # Ask if user wants to use any idea
                        use_idea = input("\nUse one of these ideas? (y/N) > ").strip().lower()
                        if use_idea == 'y':
                            try:
                                idea_num = int(input("Which idea number? > ").strip())
                                if 1 <= idea_num <= len(ideas):
                                    user_input = ideas[idea_num - 1]
                                    print(f"🎯 Using idea: {user_input}")
                                else:
                                    print("❌ Invalid idea number")
                            except ValueError:
                                print("❌ Please enter a valid number")
                continue
            
            # Check if user wants to provide detailed preferences
            if user_input.lower() == 'detail':
                preferences = get_blog_preferences()
                if not preferences:
                    continue
                topic = preferences["topic"]
                style = preferences["style"]
                audience = preferences["audience"]
                length = preferences["length"]
            else:
                # Use defaults for quick generation
                topic = user_input
                style = "professional"
                audience = "general"
                length = "medium"
            
            # Generate blog post
            result = generate_blog_post(topic, style, audience, length)
            if result:
                blog_count += 1
                
                # Ask if user wants to save
                save = input("\n💾 Save this blog to file? (y/N) > ").strip().lower()
                if save == 'y':
                    custom_name = input("Filename (press Enter for auto-generate) > ").strip()
                    if not custom_name:
                        custom_name = None
                    save_blog_to_file(result, custom_name)
            
        except KeyboardInterrupt:
            print("\n\n👋 Blog generation interrupted. Goodbye!\n")
            break
        except EOFError:
            print("\n\n👋 End of input. Goodbye!\n")
            break

if __name__ == "__main__":
    main()