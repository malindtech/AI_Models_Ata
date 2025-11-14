#!/usr/bin/env python3
"""
Async Blog Generator Chat
Generate blog posts asynchronously with Celery task tracking and terminal display
"""
import sys
import requests
import time
import json
from pathlib import Path

# API configuration
API_BASE_URL = "http://localhost:8000"

def print_async_header():
    print("\n" + "="*70)
    print("⚡ ASYNC BLOG GENERATOR (Celery + Redis)")
    print("="*70)
    print("Generate blog posts asynchronously with real-time progress tracking!")
    print("\nFeatures:")
    print("  • Non-blocking API calls")
    print("  • Real-time task status updates") 
    print("  • Full blog display in terminal")
    print("  • Monitor progress in Flower: http://localhost:5555")
    print("  • Continue generating while tasks run in background")
    print("\nCommands:")
    print("  'quit' or 'exit' - Exit the generator")
    print("  'status' - Check all active tasks")
    print("  'flower' - Open Flower monitoring")
    print("  'detail' - Enter detailed mode for full control")
    print("="*70 + "\n")

def display_blog_result(blog_data):
    """Display the complete blog post in terminal"""
    blog = blog_data['blog']
    
    print(f"\n{'═'*70}")
    print(f"📖 {blog['title']}")
    print(f"{'═'*70}\n")
    
    print(f"📍 INTRODUCTION:")
    print(f"{blog['introduction']}\n")
    
    print(f"📝 BODY:")
    print(f"{blog['body']}\n")
    
    print(f"🎯 CONCLUSION:")
    print(f"{blog['conclusion']}\n")
    
    print(f"🏷️  TAGS: {', '.join(blog['tags'])}")
    
    print(f"\n{'─'*70}")
    print(f"⏱️  Generation time: {blog_data['latency_s']:.2f}s")
    print(f"{'─'*70}\n")

def start_async_blog_generation(topic, style="professional", audience="general", length="medium"):
    """Start async blog generation and track progress"""
    print(f"\n{'─'*70}")
    print(f"⚡ STARTING ASYNC BLOG GENERATION...")
    print(f"📝 Topic: {topic}")
    print(f"🎨 Style: {style}")
    print(f"👥 Audience: {audience}")
    print(f"📏 Length: {length}")
    print(f"{'─'*70}\n")
    
    try:
        # Use the ASYNC endpoint
        response = requests.post(
            f"{API_BASE_URL}/v1/async/generate/blog",
            json={
                "topic": topic,
                "style": style,
                "audience": audience,
                "length": length
            },
            timeout=10
        )
        
        if response.status_code != 200:
            print(f"❌ Failed to start async task: {response.text}")
            return None
        
        task_data = response.json()
        task_id = task_data["task_id"]
        
        print(f"✅ Async task started!")
        print(f"📋 Task ID: {task_id}")
        print(f"🔄 Status: {task_data['status']}")
        print(f"💡 Check progress: http://localhost:5555")
        print(f"🔍 API: curl http://localhost:8000/v1/tasks/{task_id}")
        
        return task_id
        
    except Exception as e:
        print(f"❌ Error starting async task: {e}")
        return None

def track_task_progress(task_id, max_checks=60, show_progress=True):
    """Track the progress of a specific task and display final blog"""
    if show_progress:
        print(f"\n📊 Tracking task: {task_id}")
        print("-" * 50)
    
    last_progress = ""
    
    for check in range(max_checks):
        try:
            response = requests.get(f"{API_BASE_URL}/v1/tasks/{task_id}")
            
            if response.status_code != 200:
                print(f"❌ Error checking task: {response.text}")
                break
            
            status_data = response.json()
            current_status = status_data["status"]
            
            # Show progress with emojis
            if current_status == "SUCCESS":
                if show_progress:
                    print(f"🎉 TASK COMPLETED SUCCESSFULLY!")
                
                result = status_data["result"]
                if result and "blog" in result:
                    display_blog_result(result)
                    return result
                else:
                    print("❌ Task completed but no blog data received")
                    return None
                
            elif current_status == "FAILURE":
                error_msg = status_data.get('error', 'Unknown error')
                print(f"❌ TASK FAILED: {error_msg}")
                return None
                
            elif current_status == "PROGRESS":
                progress = status_data.get('progress', {})
                current = progress.get('current', 0)
                total = progress.get('total', 100)
                status_msg = progress.get('status', 'Processing...')
                
                if show_progress and status_msg != last_progress:
                    if total > 0:
                        percent = (current / total) * 100
                        print(f"🔄 [{check+1}/{max_checks}] {status_msg} ({percent:.1f}%)")
                    else:
                        print(f"🔄 [{check+1}/{max_checks}] {status_msg}")
                    last_progress = status_msg
                
            elif current_status == "PENDING":
                if show_progress:
                    print(f"⏳ [{check+1}/{max_checks}] Task queued and waiting...")
            
            # Wait before next check
            time.sleep(2)
            
        except requests.exceptions.ConnectionError:
            print(f"❌ Cannot connect to API server")
            break
        except Exception as e:
            print(f"❌ Error tracking task: {e}")
            break
    
    else:
        print(f"⏰ Task taking too long. Check later with: curl http://localhost:8000/v1/tasks/{task_id}")
    
    return None

def check_all_tasks():
    """Check status of all tasks"""
    print("\n📋 Checking all tasks...")
    try:
        response = requests.get(f"{API_BASE_URL}/v1/tasks")
        if response.status_code == 200:
            tasks = response.json()
            print(f"\n📊 Found {len(tasks)} tasks:")
            print("-" * 50)
            for task_id, task_info in tasks.items():
                status = task_info.get('status', 'UNKNOWN')
                result = task_info.get('result', {})
                if result and 'blog' in result:
                    topic = result.get('topic', 'Unknown')
                    print(f"📝 {task_id}: {status} - {topic}")
                else:
                    print(f"📝 {task_id}: {status}")
        else:
            print("❌ Could not fetch tasks list")
    except Exception as e:
        print(f"❌ Error checking tasks: {e}")

def get_detailed_preferences():
    """Get detailed blog preferences from user"""
    print("\n📝 Detailed Blog Configuration:")
    
    topic = input("🎯 Blog topic > ").strip()
    if not topic:
        print("❌ Topic cannot be empty")
        return None
    
    print("\n🎨 Writing style (professional/casual/technical/persuasive/educational):")
    style = input("Style (press Enter for 'professional') > ").strip().lower() or "professional"
    
    audience = input("👥 Target audience (press Enter for 'general') > ").strip() or "general"
    
    print("\n📏 Length (short/medium/long):")
    length = input("Length (press Enter for 'medium') > ").strip().lower() or "medium"
    
    return {
        "topic": topic,
        "style": style,
        "audience": audience,
        "length": length
    }

def save_blog_to_file(blog_data, filename=None):
    """Save generated blog to a text file"""
    if not blog_data:
        print("❌ No blog data to save")
        return False
        
    if not filename:
        # Create filename from topic
        topic = blog_data.get('topic', 'blog')
        filename = f"async_blog_{topic.replace(' ', '_').lower()[:30]}_{int(time.time())}.txt"
    
    try:
        with open(filename, 'w', encoding='utf-8') as f:
            blog = blog_data['blog']
            f.write(f"Title: {blog['title']}\n")
            f.write(f"Topic: {blog_data.get('topic', 'Unknown')}\n")
            f.write(f"Style: {blog_data.get('style', 'professional')}\n")
            f.write(f"Audience: {blog_data.get('audience', 'general')}\n")
            f.write(f"Length: {blog_data.get('length', 'medium')}\n")
            f.write(f"Tags: {', '.join(blog['tags'])}\n")
            f.write(f"Generation Time: {blog_data.get('latency_s', 0):.2f}s\n")
            f.write(f"Generated Asynchronously with Celery\n")
            f.write("\n" + "="*60 + "\n\n")
            f.write(f"INTRODUCTION:\n{blog['introduction']}\n\n")
            f.write(f"BODY:\n{blog['body']}\n\n")
            f.write(f"CONCLUSION:\n{blog['conclusion']}\n")
        
        print(f"✅ Blog saved as: {filename}")
        return True
    except Exception as e:
        print(f"❌ Error saving file: {e}")
        return False

def main():
    """Main async blog generation loop"""
    print_async_header()
    
    # Check if async endpoints are available
    try:
        response = requests.get(f"{API_BASE_URL}/health", timeout=5)
        if response.status_code == 200:
            print("✅ API Server: Healthy")
        else:
            print("❌ API Server: Not healthy")
            return
    except requests.exceptions.ConnectionError:
        print("❌ Cannot connect to API server")
        print("   Make sure the server is running:")
        print("   uvicorn backend.main:app --reload --host 0.0.0.0 --port 8000")
        return
    except Exception as e:
        print(f"❌ Error checking API: {e}")
        return
    
    print("💡 Try these quick topics:")
    print("   • The Future of Artificial Intelligence")
    print("   • Sustainable Living in Modern Cities")
    print("   • Introduction to Machine Learning")
    
    active_tasks = []
    
    while True:
        try:
            user_input = input("\n⚡ Enter topic or command > ").strip()
            
            if not user_input:
                continue
                
            if user_input.lower() in ['quit', 'exit', 'q']:
                print(f"\n👋 Thanks for using Async Blog Generator!")
                if active_tasks:
                    print(f"💡 Active tasks still running: {len(active_tasks)}")
                    for task_id in active_tasks:
                        print(f"   - {task_id}")
                break
                
            if user_input.lower() == 'status':
                check_all_tasks()
                continue
                
            if user_input.lower() == 'flower':
                print("🌐 Opening Flower monitoring: http://localhost:5555")
                print("   (Make sure Flower is running: celery -A backend.celery_app flower)")
                continue
            
            if user_input.lower() == 'detail':
                preferences = get_detailed_preferences()
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
            
            # Start async generation
            task_id = start_async_blog_generation(topic, style, audience, length)
            
            if task_id:
                active_tasks.append(task_id)
                
                # Ask if user wants to track this task
                track = input("\n🔍 Track this task live? (Y/n) > ").strip().lower()
                if track != 'n':
                    result = track_task_progress(task_id)
                    if result:
                        active_tasks.remove(task_id)  # Task completed
                        
                        # Ask if user wants to save
                        save = input("\n💾 Save this blog to file? (y/N) > ").strip().lower()
                        if save == 'y':
                            custom_name = input("Filename (press Enter for auto-generate) > ").strip()
                            if not custom_name:
                                custom_name = None
                            save_blog_to_file(result, custom_name)
                else:
                    print(f"💡 Task {task_id} running in background")
                    print(f"   Check status later with: curl http://localhost:8000/v1/tasks/{task_id}")
                
                # Ask if user wants to start another task
                another = input("\n🔄 Start another async task? (Y/n) > ").strip().lower()
                if another == 'n':
                    if active_tasks:
                        print(f"\n📋 Active tasks still running:")
                        for task_id in active_tasks:
                            print(f"   • {task_id}")
                    break
            
        except KeyboardInterrupt:
            print(f"\n\n👋 Async generation interrupted.")
            if active_tasks:
                print(f"💡 Tasks still running: {len(active_tasks)}")
            break
        except Exception as e:
            print(f"\n❌ Error: {e}")

if __name__ == "__main__":
    main()