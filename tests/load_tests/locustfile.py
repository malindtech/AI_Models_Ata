"""
Day 9: Load Testing with Locust
Tests both Content Generation and Customer Support agents
Simulates 10-20 concurrent users per agent (20-40 total)
Validates performance under load and cache effectiveness
"""

from locust import HttpUser, task, between, events
import json
import random
from datetime import datetime
import logging

logger = logging.getLogger(__name__)

# Test data pools
CONTENT_TOPICS = [
    "sustainable living tips",
    "home office productivity",
    "healthy breakfast recipes",
    "budget travel destinations",
    "beginner yoga poses",
    "time management strategies",
    "indoor plant care",
    "minimalist lifestyle",
    "meditation techniques",
    "eco-friendly products"
]

CONTENT_TYPES = ["blog", "product_description", "ad_copy", "email_newsletter", "social_media"]
TONES = ["professional", "casual", "friendly", "formal", "empathetic"]

SUPPORT_MESSAGES = [
    "Where is my order #ORD-12345? It's been 2 weeks!",
    "I received a damaged product. Can I get a refund?",
    "How do I track my shipment?",
    "What is your return policy?",
    "My package says delivered but I never received it.",
    "Can I change my shipping address for order #ORD-67890?",
    "I was charged twice for my order, please help!",
    "How long does shipping usually take?",
    "Do you offer international shipping?",
    "I need to cancel my order immediately."
]

RAG_QUERIES = [
    "shipping policy",
    "return process",
    "order tracking",
    "refund policy",
    "product warranty",
    "delivery time",
    "payment methods",
    "customer service contact",
    "product recommendations",
    "order status"
]


class ContentGenerationUser(HttpUser):
    """
    Simulates users generating content
    Tests content generation agent performance
    """
    wait_time = between(1, 3)  # Wait 1-3 seconds between requests
    
    @task(4)  # 40% of requests
    def generate_blog(self):
        """Generate blog post"""
        payload = {
            "content_type": "blog",
            "topic": random.choice(CONTENT_TOPICS),
            "tone": random.choice(TONES),
            "enable_expansion": random.choice([True, False])
        }
        
        with self.client.post(
            "/v1/generate/content",
            json=payload,
            catch_response=True,
            name="Generate Blog"
        ) as response:
            if response.status_code == 200:
                data = response.json()
                latency = data.get("latency_s", 0)
                body_length = len(data.get("body", ""))
                
                if latency > 5.0:
                    response.failure(f"Slow response: {latency:.2f}s")
                elif body_length < 200:
                    response.failure(f"Content too short: {body_length} chars")
                else:
                    response.success()
            else:
                response.failure(f"HTTP {response.status_code}")
    
    @task(3)  # 30% of requests
    def generate_product_description(self):
        """Generate product description"""
        payload = {
            "content_type": "product_description",
            "topic": random.choice(["wireless headphones", "coffee maker", "running shoes", 
                                   "laptop backpack", "yoga mat"]),
            "tone": "professional",
            "enable_expansion": True
        }
        
        with self.client.post(
            "/v1/generate/content",
            json=payload,
            catch_response=True,
            name="Generate Product Description"
        ) as response:
            if response.status_code == 200:
                data = response.json()
                if data.get("latency_s", 0) > 3.0:
                    response.failure(f"Slow response: {data['latency_s']:.2f}s")
                else:
                    response.success()
            else:
                response.failure(f"HTTP {response.status_code}")
    
    @task(2)  # 20% of requests
    def generate_ad_copy(self):
        """Generate advertisement copy"""
        payload = {
            "content_type": "ad_copy",
            "topic": random.choice(["summer sale", "new product launch", "limited offer", 
                                   "holiday special", "flash discount"]),
            "tone": "friendly"
        }
        
        with self.client.post(
            "/v1/generate/content",
            json=payload,
            catch_response=True,
            name="Generate Ad Copy"
        ) as response:
            if response.status_code == 200:
                response.success()
            else:
                response.failure(f"HTTP {response.status_code}")
    
    @task(1)  # 10% of requests
    def retrieve_documents(self):
        """Test RAG retrieval"""
        payload = {
            "query": random.choice(RAG_QUERIES),
            "collection": random.choice(["blogs", "products", "social"]),
            "top_k": 5,
            "enable_hybrid": random.choice([True, False])
        }
        
        with self.client.post(
            "/v1/retrieve",
            json=payload,
            catch_response=True,
            name="RAG Retrieval"
        ) as response:
            if response.status_code == 200:
                data = response.json()
                latency = data.get("latency_ms", 0)
                num_results = data.get("num_results", 0)
                
                if latency > 100:  # >100ms for retrieval is slow
                    response.failure(f"Slow retrieval: {latency:.2f}ms")
                elif num_results == 0:
                    response.failure("No results returned")
                else:
                    response.success()
            else:
                response.failure(f"HTTP {response.status_code}")


class SupportReplyUser(HttpUser):
    """
    Simulates users requesting support replies
    Tests customer support agent performance
    """
    wait_time = between(1, 3)
    
    @task(5)  # 50% of requests
    def generate_support_reply(self):
        """Generate support reply (synchronous)"""
        payload = {
            "message": random.choice(SUPPORT_MESSAGES)
        }
        
        with self.client.post(
            "/v1/generate/reply?async_mode=false",
            json=payload,
            catch_response=True,
            name="Generate Support Reply"
        ) as response:
            if response.status_code == 200:
                data = response.json()
                total_latency = data.get("total_latency_s", 0)
                detected_intent = data.get("detected_intent", "")
                reply = data.get("reply", "")
                
                if total_latency > 5.0:
                    response.failure(f"Slow response: {total_latency:.2f}s")
                elif len(reply) < 50:
                    response.failure(f"Reply too short: {len(reply)} chars")
                elif not detected_intent:
                    response.failure("No intent detected")
                else:
                    response.success()
            elif response.status_code == 429:
                response.failure("Rate limited")
            else:
                response.failure(f"HTTP {response.status_code}")
    
    @task(3)  # 30% of requests
    def classify_intent(self):
        """Test intent classification (cached heavily)"""
        payload = {
            "message": random.choice(SUPPORT_MESSAGES)
        }
        
        with self.client.post(
            "/v1/classify/intent",
            json=payload,
            catch_response=True,
            name="Classify Intent"
        ) as response:
            if response.status_code == 200:
                data = response.json()
                latency = data.get("latency_s", 0)
                intent = data.get("intent", "")
                
                if latency > 1.0:
                    response.failure(f"Slow classification: {latency:.2f}s")
                elif intent not in ["complaint", "inquiry", "request"]:
                    response.failure(f"Invalid intent: {intent}")
                else:
                    response.success()
            else:
                response.failure(f"HTTP {response.status_code}")
    
    @task(2)  # 20% of requests
    def retrieve_support_context(self):
        """Test RAG retrieval for support context"""
        payload = {
            "query": random.choice(SUPPORT_MESSAGES[:5]),  # Use subset for caching
            "collection": "support",
            "top_k": 3
        }
        
        with self.client.post(
            "/v1/retrieve",
            json=payload,
            catch_response=True,
            name="Support RAG Retrieval"
        ) as response:
            if response.status_code == 200:
                data = response.json()
                latency = data.get("latency_ms", 0)
                
                if latency > 50:  # Should be fast with caching
                    response.failure(f"Slow retrieval: {latency:.2f}ms")
                else:
                    response.success()
            else:
                response.failure(f"HTTP {response.status_code}")


class MixedWorkloadUser(HttpUser):
    """
    Simulates mixed workload - both content generation and support
    More realistic production scenario
    """
    wait_time = between(2, 5)
    
    @task(3)
    def generate_content(self):
        """Generate content"""
        payload = {
            "content_type": random.choice(CONTENT_TYPES),
            "topic": random.choice(CONTENT_TOPICS),
            "tone": random.choice(TONES)
        }
        
        with self.client.post(
            "/v1/generate/content",
            json=payload,
            catch_response=True,
            name="Mixed: Generate Content"
        ) as response:
            if response.status_code == 200:
                response.success()
            else:
                response.failure(f"HTTP {response.status_code}")
    
    @task(2)
    def support_reply(self):
        """Generate support reply"""
        payload = {
            "message": random.choice(SUPPORT_MESSAGES)
        }
        
        with self.client.post(
            "/v1/generate/reply?async_mode=false",
            json=payload,
            catch_response=True,
            name="Mixed: Support Reply"
        ) as response:
            if response.status_code == 200:
                response.success()
            elif response.status_code == 429:
                response.failure("Rate limited")
            else:
                response.failure(f"HTTP {response.status_code}")
    
    @task(1)
    def health_check(self):
        """Health check"""
        with self.client.get("/health", name="Health Check") as response:
            if response.status_code == 200:
                response.success()
            else:
                response.failure(f"HTTP {response.status_code}")


# Event handlers for statistics
@events.test_start.add_listener
def on_test_start(environment, **kwargs):
    """Print test start info"""
    print("\n" + "="*80)
    print("DAY 9: LOAD TEST STARTING")
    print("="*80)
    print(f"Host: {environment.host}")
    print(f"Time: {datetime.now().isoformat()}")
    print("="*80 + "\n")


@events.test_stop.add_listener
def on_test_stop(environment, **kwargs):
    """Print test summary"""
    print("\n" + "="*80)
    print("DAY 9: LOAD TEST COMPLETE")
    print("="*80)
    print(f"Time: {datetime.now().isoformat()}")
    
    stats = environment.stats
    print(f"\nTotal Requests: {stats.total.num_requests}")
    print(f"Failed Requests: {stats.total.num_failures}")
    print(f"Success Rate: {(1 - stats.total.fail_ratio) * 100:.2f}%")
    print(f"Median Response Time: {stats.total.median_response_time}ms")
    print(f"95th Percentile: {stats.total.get_response_time_percentile(0.95)}ms")
    print(f"Requests/sec: {stats.total.total_rps:.2f}")
    
    print("\n" + "="*80 + "\n")
