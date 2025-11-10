#!/usr/bin/env python3
"""
Interactive Customer Support Agent Chat
Talk to the AI agent and see detected intent + contextual replies
"""
import sys
from pathlib import Path

# Add project root to path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from fastapi.testclient import TestClient
from backend.main import app

client = TestClient(app)

def print_header():
    print("\n" + "="*70)
    print("🤖 CUSTOMER SUPPORT AGENT - Interactive Chat")
    print("="*70)
    print("Type your message and get an AI-powered support response!")
    print("The agent will detect your intent and provide a contextual reply.")
    print("\nCommands:")
    print("  'quit' or 'exit' - Exit the chat")
    print("  'help' - Show this help message")
    print("="*70 + "\n")

def chat_with_agent(message):
    """Send message to agent and display intent + reply"""
    print(f"\n{'─'*70}")
    print(f"💬 YOU: {message}")
    print(f"{'─'*70}\n")
    
    try:
        # Call the Reply Agent endpoint
        response = client.post(
            "/v1/generate/reply",
            json={"message": message}
        )
        
        if response.status_code != 200:
            print(f"❌ Error: {response.json()}")
            return
        
        data = response.json()
        
        # Display detected intent
        intent_emoji = {
            "complaint": "😟",
            "inquiry": "❓",
            "request": "🙋"
        }
        emoji = intent_emoji.get(data['detected_intent'], "💭")
        
        print(f"{emoji} DETECTED INTENT: {data['detected_intent'].upper()}")
        print(f"⏱️  Classification time: {data['classification_latency_s']:.2f}s\n")
        
        # Display reply
        print(f"🤖 AGENT REPLY:")
        print(f"\n{data['reply']}\n")
        
        # Display next steps if available
        if data.get('next_steps') and data['next_steps'].strip():
            print(f"📋 NEXT STEPS:")
            print(f"{data['next_steps']}\n")
        
        # Display timing info
        print(f"{'─'*70}")
        print(f"⏱️  Generation time: {data['generation_latency_s']:.2f}s")
        print(f"⏱️  Total time: {data['total_latency_s']:.2f}s")
        print(f"{'─'*70}\n")
        
    except Exception as e:
        print(f"❌ Error: {e}")
        import traceback
        traceback.print_exc()

def main():
    """Main interactive chat loop"""
    print_header()
    
    # Show some example messages
    print("💡 Try these example messages:")
    print("   • My order hasn't arrived yet")
    print("   • What are your business hours?")
    print("   • Can you send me a replacement?")
    print("   • I'm very disappointed with this product")
    print("   • How do I track my shipment?\n")
    
    conversation_count = 0
    
    while True:
        try:
            # Get user input
            user_input = input("💬 Your message > ").strip()
            
            # Handle commands
            if not user_input:
                continue
                
            if user_input.lower() in ['quit', 'exit', 'q']:
                print("\n👋 Thanks for chatting with the Customer Support Agent!")
                print(f"📊 Total conversations: {conversation_count}\n")
                break
                
            if user_input.lower() == 'help':
                print_header()
                continue
            
            # Chat with agent
            chat_with_agent(user_input)
            conversation_count += 1
            
        except KeyboardInterrupt:
            print("\n\n👋 Chat interrupted. Goodbye!\n")
            break
        except EOFError:
            print("\n\n👋 End of input. Goodbye!\n")
            break

if __name__ == "__main__":
    main()
