#!/usr/bin/env python3
"""
Product Description Generator Chat
Generate compelling product descriptions through interactive chat
"""
import sys
import requests
from pathlib import Path

# API configuration
API_BASE_URL = "http://localhost:8000"

def print_product_header():
    print("\n" + "="*70)
    print("🛍️ AI PRODUCT DESCRIPTION GENERATOR")
    print("="*70)
    print("Generate compelling, conversion-focused product descriptions!")
    print("\nCommands:")
    print("  'quit' or 'exit' - Exit the generator")
    print("  'help' - Show this help message") 
    print("  'tones' - Show available tone options")
    print("  'examples' - Show product examples")
    print("="*70 + "\n")

def show_tone_options():
    print("\n🎨 AVAILABLE TONES:")
    print("  1. Professional - Formal, authoritative, business-focused")
    print("  2. Casual - Conversational, friendly, relatable") 
    print("  3. Friendly - Warm, approachable, customer-focused")
    print("  4. Persuasive - Compelling, benefit-focused, action-oriented")
    print("  5. Technical - Detailed, precise, feature-focused")
    print("  6. Luxurious - Premium, exclusive, high-end")
    print("  7. Urgent - Time-sensitive, limited availability")
    print("  8. Empathetic - Understanding, solution-focused")

def show_product_examples():
    print("\n💡 PRODUCT EXAMPLES:")
    print("  • Wireless Bluetooth Headphones with Noise Cancellation")
    print("  • Organic Skincare Set for Sensitive Skin")
    print("  • Smart Home Security Camera System")
    print("  • Ergonomic Office Chair with Lumbar Support")
    print("  • Portable Espresso Maker for Travel")
    print("  • Sustainable Bamboo Toothbrush Set")
    print("  • AI-Powered Fitness Tracker Watch")
    print("  • Vegan Leather Crossbody Bag")

def get_tone_choice():
    """Get tone selection from user"""
    show_tone_options()
    while True:
        tone_key = input("\nSelect tone (1-8, default 4): ").strip()
        tone_map = {
            "1": "professional",
            "2": "casual", 
            "3": "friendly",
            "4": "persuasive",
            "5": "technical",
            "6": "luxurious",
            "7": "urgent",
            "8": "empathetic"
        }
        
        if not tone_key:
            return "persuasive"  # Default for product descriptions
        elif tone_key in tone_map:
            return tone_map[tone_key]
        else:
            print("❌ Invalid selection. Please choose 1-8.")

def get_product_details():
    """Get comprehensive product information from user"""
    print("\n🛍️ PRODUCT DETAILS")
    print("-" * 40)
    
    # Product name (required)
    while True:
        product_name = input("Product name: ").strip()
        if product_name:
            break
        print("❌ Product name is required")
    
    # Product category
    category = input("Product category (optional): ").strip()
    
    # Key features
    print("\n📋 KEY FEATURES")
    print("Enter key features one by one (press Enter twice when done):")
    features = []
    while True:
        feature = input("Feature: ").strip()
        if feature:
            features.append(feature)
        elif features:  # Allow empty to finish if we have at least one feature
            break
        else:
            print("❌ Please enter at least one key feature")
    
    # Key benefits
    print("\n🌟 KEY BENEFITS")
    print("How do these features benefit the customer?")
    benefits = []
    while True:
        benefit = input("Benefit: ").strip()
        if benefit:
            benefits.append(benefit)
        elif benefits:  # Allow empty to finish if we have at least one benefit
            break
        else:
            print("❌ Please enter at least one key benefit")
    
    # Target audience
    print("\n👥 TARGET AUDIENCE")
    audience = input("Who is this product for? (press Enter for 'general'): ").strip() or "general"
    
    # Price point context
    print("\n💰 PRICE CONTEXT")
    print("1. Budget-friendly")
    print("2. Mid-range")
    print("3. Premium")
    print("4. Luxury")
    price_choice = input("Price range (1-4, optional): ").strip()
    price_map = {
        "1": "budget-friendly",
        "2": "mid-range", 
        "3": "premium",
        "4": "luxury"
    }
    price_context = price_map.get(price_choice, "")
    
    # Keywords for SEO
    keywords_input = input("SEO keywords (comma-separated, optional): ").strip()
    keywords = [k.strip() for k in keywords_input.split(",") if k.strip()]
    
    # Word count
    try:
        word_input = input("Description length in words (default 250): ").strip()
        word_count = int(word_input) if word_input else 250
        word_count = max(100, min(500, word_count))  # Limit to reasonable range
    except ValueError:
        print("⚠️  Invalid number, using 250 words")
        word_count = 250
    
    # Build context object
    context = {
        "product_info": {
            "name": product_name,
            "category": category,
            "features": features,
            "benefits": benefits,
            "price_context": price_context
        },
        "target_audience": audience,
        "keywords": keywords
    }
    
    return product_name, context, word_count

def generate_product_description(product_name, tone, context, word_count):
    """Generate product description using the multi-agent system"""
    print(f"\n{'─'*70}")
    print(f"🛍️ GENERATING PRODUCT DESCRIPTION...")
    print(f"📦 Product: {product_name}")
    print(f"🎨 Tone: {tone}")
    print(f"📊 Target Words: {word_count}")
    print(f"{'─'*70}\n")
    
    payload = {
        "content_type": "product_description",
        "topic": product_name,
        "tone": tone,
        "word_count": word_count,
        "context": context
    }
    
    try:
        response = requests.post(
            f"{API_BASE_URL}/v2/generate/content",
            json=payload,
            timeout=180  # Same timeout as blog script
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
        
        print(f"🛍️ PRODUCT DESCRIPTION:")
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

def save_product_description(product_data, context):
    """Save generated product description to a text file"""
    product_name = context["product_info"]["name"]
    filename = f"product_{product_name.replace(' ', '_').lower()[:30]}.txt"
    
    try:
        with open(filename, 'w', encoding='utf-8') as f:
            f.write(f"PRODUCT DESCRIPTION\n")
            f.write("=" * 50 + "\n\n")
            f.write(f"Product: {product_name}\n")
            
            if context["product_info"].get("category"):
                f.write(f"Category: {context['product_info']['category']}\n")
            
            f.write(f"Target Audience: {context['target_audience']}\n")
            f.write(f"Tone: {product_data['metadata'].get('tone', 'N/A')}\n")
            f.write(f"Word Count: {product_data['metadata'].get('estimated_words', 0)}\n")
            f.write(f"Generation Time: {product_data['latency_s']:.2f}s\n")
            
            # Write features and benefits
            if context["product_info"].get("features"):
                f.write(f"\nKEY FEATURES:\n")
                for feature in context["product_info"]["features"]:
                    f.write(f"• {feature}\n")
            
            if context["product_info"].get("benefits"):
                f.write(f"\nKEY BENEFITS:\n")
                for benefit in context["product_info"]["benefits"]:
                    f.write(f"• {benefit}\n")
            
            if context["product_info"].get("price_context"):
                f.write(f"Price Context: {context['product_info']['price_context']}\n")
            
            if context.get("keywords"):
                f.write(f"Keywords: {', '.join(context['keywords'])}\n")
            
            f.write("\n" + "=" * 50 + "\n\n")
            f.write(f"{product_data['content']}\n")
        
        print(f"✅ Product description saved as: {filename}")
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
    """Main product description generation loop"""
    print_product_header()
    
    # Check API health
    print("🔍 Checking API connection...")
    if not check_api_health():
        print("\n❌ Cannot connect to Product Description Generator API.")
        print("   Please make sure the server is running:")
        print("   uvicorn backend.main:app --reload --host 0.0.0.0 --port 8000")
        print("\n   Also ensure Ollama is running:")
        print("   ollama serve")
        return
    
    # Show examples
    show_product_examples()
    
    product_count = 0
    
    while True:
        try:
            # Get user command
            user_input = input("\n🛍️ Enter 'start' to begin or command > ").strip().lower()
            
            # Handle commands
            if not user_input:
                continue
                
            if user_input in ['quit', 'exit', 'q']:
                print(f"\n👋 Thanks for using the Product Description Generator!")
                print(f"📊 Total products described: {product_count}\n")
                break
                
            if user_input == 'help':
                print_product_header()
                continue
                
            if user_input == 'tones':
                show_tone_options()
                continue
                
            if user_input == 'examples':
                show_product_examples()
                continue
            
            if user_input == 'start' or user_input == 's':
                # Get product details
                product_name, context, word_count = get_product_details()
                
                # Get tone selection
                tone = get_tone_choice()
                
                # Generate product description
                result = generate_product_description(product_name, tone, context, word_count)
                
                if result:
                    product_count += 1
                    
                    # Ask if user wants to save
                    save = input("\n💾 Save this product description? (y/N) > ").strip().lower()
                    if save == 'y':
                        save_product_description(result, context)
                    
                    # Ask if user wants to generate another
                    another = input("\n🔄 Generate another product description? (y/N) > ").strip().lower()
                    if another != 'y':
                        print(f"\n👋 Thanks for using the Product Description Generator!")
                        print(f"📊 Total products described: {product_count}\n")
                        break
            
            else:
                print("❌ Unknown command. Type 'help' for available commands.")
            
        except KeyboardInterrupt:
            print("\n\n👋 Product description generation interrupted. Goodbye!\n")
            break
        except EOFError:
            print("\n\n👋 End of input. Goodbye!\n")
            break

if __name__ == "__main__":
    main()