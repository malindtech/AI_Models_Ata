"""
Interactive Agent Testing - Type Your Own Messages
Test both Content Generation Agent and Customer Support Agent with RAG
"""

import requests
import json
from typing import Dict

BASE_URL = "http://localhost:8000"

# Color codes for terminal output
class Colors:
    GREEN = '\033[92m'
    RED = '\033[91m'
    YELLOW = '\033[93m'
    BLUE = '\033[94m'
    CYAN = '\033[96m'
    MAGENTA = '\033[95m'
    BOLD = '\033[1m'
    END = '\033[0m'

def print_banner():
    """Print welcome banner"""
    print(f"\n{Colors.BOLD}{Colors.CYAN}")
    print("╔" + "="*78 + "╗")
    print("║" + " INTERACTIVE AGENT TESTING ".center(78) + "║")
    print("║" + " Type your own messages and see AI responses! ".center(78) + "║")
    print("╚" + "="*78 + "╝")
    print(f"{Colors.END}\n")

def check_system():
    """Check if server and ChromaDB are ready"""
    try:
        response = requests.get(f"{BASE_URL}/health", timeout=5)
        data = response.json()
        
        if data.get("status") == "ok" and data.get("vector_db"):
            print(f"{Colors.GREEN}✅ System Ready: Server & ChromaDB Online{Colors.END}\n")
            return True
        else:
            print(f"{Colors.RED}❌ System Not Ready: Check server or ChromaDB{Colors.END}\n")
            return False
    except Exception as e:
        print(f"{Colors.RED}❌ Cannot connect to server: {e}{Colors.END}\n")
        return False

def test_content_generation():
    """Interactive Content Generation Agent"""
    print(f"\n{Colors.BOLD}{Colors.BLUE}{'='*80}{Colors.END}")
    print(f"{Colors.BOLD}{Colors.BLUE}🤖 CONTENT GENERATION AGENT{Colors.END}")
    print(f"{Colors.BOLD}{Colors.BLUE}{'='*80}{Colors.END}\n")
    
    print(f"{Colors.YELLOW}This agent generates diverse content types with RAG context.{Colors.END}")
    
    # Select content type
    print(f"\n{Colors.CYAN}Select Content Type:{Colors.END}")
    print("  1. Blog Post")
    print("  2. Product Description")
    print("  3. Ad Copy")
    print("  4. Email Newsletter")
    print("  5. Social Media Post")
    print("  6. Customer Support Reply")
    
    type_choice = input(f"{Colors.BOLD}Choose (1-6):{Colors.END} ").strip()
    type_map = {
        "1": ("blog", "Blog Post", "AI in healthcare", "blogs"),
        "2": ("product_description", "Product Description", "wireless headphones", "products"),
        "3": ("ad_copy", "Ad Copy", "summer sale campaign", "products"),
        "4": ("email_newsletter", "Email Newsletter", "weekly tech updates", "blogs"),
        "5": ("social_media", "Social Media Post", "new product launch", "social"),
        "6": ("support_reply", "Support Reply", "refund for late delivery", "support")
    }
    
    if type_choice not in type_map:
        print(f"{Colors.RED}❌ Invalid choice. Using default (Support Reply){Colors.END}")
        type_choice = "6"
    
    content_type, type_name, example, collection = type_map[type_choice]
    
    print(f"\n{Colors.YELLOW}Example topic: '{example}'\n{Colors.END}")
    
    # Get user input
    topic = input(f"{Colors.BOLD}💭 Enter your topic:{Colors.END} ").strip()
    
    if not topic:
        print(f"{Colors.RED}❌ No topic entered. Skipping...{Colors.END}\n")
        return
    
    # Get tone preference
    print(f"\n{Colors.CYAN}Select tone:{Colors.END}")
    print("  1. Empathetic (default)")
    print("  2. Friendly")
    print("  3. Formal")
    print("  4. Neutral")
    
    tone_choice = input(f"{Colors.BOLD}Choose (1-4) or press Enter for default:{Colors.END} ").strip()
    tone_map = {"1": "empathetic", "2": "friendly", "3": "formal", "4": "neutral"}
    tone = tone_map.get(tone_choice, "empathetic")
    
    print(f"\n{Colors.CYAN}🔄 Generating {type_name}...{Colors.END}")
    print(f"{Colors.YELLOW}  → Retrieving RAG context from '{collection}' collection...{Colors.END}")
    print(f"{Colors.YELLOW}  → Injecting context into prompt...{Colors.END}")
    print(f"{Colors.YELLOW}  → Generating with Llama 3...{Colors.END}\n")
    
    # Make request
    try:
        response = requests.post(
            f"{BASE_URL}/v1/generate/content",
            json={
                "content_type": content_type,
                "topic": topic,
                "tone": tone
            },
            timeout=60
        )
        
        if response.status_code == 200:
            data = response.json()
            
            print(f"{Colors.GREEN}{'='*80}{Colors.END}")
            print(f"{Colors.BOLD}{Colors.GREEN}✅ GENERATED {type_name.upper()}{Colors.END}")
            print(f"{Colors.GREEN}{'='*80}{Colors.END}\n")
            
            print(f"{Colors.BOLD}{Colors.CYAN}📌 HEADLINE:{Colors.END}")
            print(f"{Colors.BOLD}{data['headline']}{Colors.END}\n")
            
            print(f"{Colors.BOLD}{Colors.CYAN}📝 BODY:{Colors.END}")
            print(f"{data['body']}\n")
            
            print(f"{Colors.CYAN}⏱️  Generation Time: {data['latency_s']:.2f}s{Colors.END}")
            print(f"{Colors.CYAN}🎯 Tone: {tone}{Colors.END}")
            print(f"{Colors.GREEN}{'='*80}{Colors.END}\n")
            
        else:
            print(f"{Colors.RED}❌ Error: {response.status_code} - {response.text}{Colors.END}\n")
            
    except Exception as e:
        print(f"{Colors.RED}❌ Request failed: {e}{Colors.END}\n")

def test_customer_support():
    """Interactive Customer Support Agent"""
    print(f"\n{Colors.BOLD}{Colors.MAGENTA}{'='*80}{Colors.END}")
    print(f"{Colors.BOLD}{Colors.MAGENTA}🎧 CUSTOMER SUPPORT AGENT{Colors.END}")
    print(f"{Colors.BOLD}{Colors.MAGENTA}{'='*80}{Colors.END}\n")
    
    print(f"{Colors.YELLOW}This agent classifies intent and generates contextual replies with RAG.{Colors.END}")
    print(f"{Colors.YELLOW}Examples: 'My order is late', 'Need refund', 'How to track order'\n{Colors.END}")
    
    # Get user input
    message = input(f"{Colors.BOLD}💬 Enter customer message:{Colors.END} ").strip()
    
    if not message:
        print(f"{Colors.RED}❌ No message entered. Skipping...{Colors.END}\n")
        return
    
    print(f"\n{Colors.CYAN}🔄 Processing message...{Colors.END}")
    print(f"{Colors.YELLOW}  → Classifying intent...{Colors.END}")
    print(f"{Colors.YELLOW}  → Retrieving RAG context from ChromaDB...{Colors.END}")
    print(f"{Colors.YELLOW}  → Generating reply with Llama 3...{Colors.END}")
    print(f"{Colors.YELLOW}  → Validating response...{Colors.END}\n")
    
    # Make request (synchronous mode for immediate results)
    try:
        response = requests.post(
            f"{BASE_URL}/v1/generate/reply?async_mode=false",
            json={"message": message},
            timeout=60
        )
        
        if response.status_code == 200:
            data = response.json()
            
            print(f"{Colors.GREEN}{'='*80}{Colors.END}")
            print(f"{Colors.BOLD}{Colors.GREEN}✅ CUSTOMER SUPPORT RESPONSE{Colors.END}")
            print(f"{Colors.GREEN}{'='*80}{Colors.END}\n")
            
            print(f"{Colors.BOLD}{Colors.CYAN}🎯 DETECTED INTENT:{Colors.END} {Colors.BOLD}{data['detected_intent'].upper()}{Colors.END}")
            print(f"{Colors.CYAN}⏱️  Classification Time: {data.get('classification_latency_s', 0):.2f}s{Colors.END}\n")
            
            print(f"{Colors.BOLD}{Colors.CYAN}💬 REPLY:{Colors.END}")
            print(f"{data['reply']}\n")
            
            if data.get('next_steps'):
                print(f"{Colors.BOLD}{Colors.CYAN}📋 NEXT STEPS:{Colors.END}")
                print(f"{data['next_steps']}\n")
            
            print(f"{Colors.CYAN}⏱️  Reply Generation Time: {data.get('generation_latency_s', 0):.2f}s{Colors.END}")
            print(f"{Colors.CYAN}⏱️  Total Time: {data.get('total_latency_s', 0):.2f}s{Colors.END}")
            print(f"{Colors.GREEN}{'='*80}{Colors.END}\n")
            
        else:
            print(f"{Colors.RED}❌ Error: {response.status_code} - {response.text}{Colors.END}\n")
            
    except Exception as e:
        print(f"{Colors.RED}❌ Request failed: {e}{Colors.END}\n")

def show_menu():
    """Display main menu"""
    print(f"{Colors.BOLD}{Colors.CYAN}Choose an agent to test:{Colors.END}")
    print(f"  {Colors.BOLD}1.{Colors.END} 🤖 Content Generation Agent (generates support content)")
    print(f"  {Colors.BOLD}2.{Colors.END} 🎧 Customer Support Agent (replies to customer messages)")
    print(f"  {Colors.BOLD}3.{Colors.END} 🧪 Test Both Agents")
    print(f"  {Colors.BOLD}4.{Colors.END} 🚪 Exit")
    print()

def main():
    """Main interactive loop"""
    print_banner()
    
    # Check system status
    if not check_system():
        print(f"{Colors.RED}Please start the server and ensure ChromaDB is initialized.{Colors.END}")
        print(f"{Colors.YELLOW}Run: uvicorn backend.main:app --reload{Colors.END}\n")
        return
    
    while True:
        show_menu()
        choice = input(f"{Colors.BOLD}Enter your choice (1-4):{Colors.END} ").strip()
        
        if choice == "1":
            test_content_generation()
            
        elif choice == "2":
            test_customer_support()
            
        elif choice == "3":
            test_content_generation()
            test_customer_support()
            
        elif choice == "4":
            print(f"\n{Colors.CYAN}👋 Thanks for testing! Goodbye!{Colors.END}\n")
            break
            
        else:
            print(f"{Colors.RED}❌ Invalid choice. Please enter 1-4.{Colors.END}\n")
        
        # Ask to continue
        continue_choice = input(f"\n{Colors.BOLD}Press Enter to continue or 'q' to quit:{Colors.END} ").strip().lower()
        if continue_choice == 'q':
            print(f"\n{Colors.CYAN}👋 Thanks for testing! Goodbye!{Colors.END}\n")
            break
        print("\n" + "="*80 + "\n")

if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print(f"\n\n{Colors.YELLOW}⚠️  Interrupted by user. Goodbye!{Colors.END}\n")
    except Exception as e:
        print(f"\n{Colors.RED}❌ Unexpected error: {e}{Colors.END}\n")
