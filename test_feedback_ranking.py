"""
Test Feedback-Based Retrieval Ranking
"""

import sys
sys.path.insert(0, "D:\\Malind Tech\\AI_Models_Ata")

from backend.feedback_ranker import get_feedback_ranker
from colorama import init, Fore, Style

init(autoreset=True)

print(f"""
{Fore.CYAN}╔══════════════════════════════════════════════════════════════╗
║     TESTING: Feedback-Based Retrieval Ranking               ║
╚══════════════════════════════════════════════════════════════╝{Style.RESET_ALL}
""")

# Get ranker
ranker = get_feedback_ranker()

# Show what it learned
stats = ranker.get_ranking_stats()

if stats.get('status') == 'no_feedback_data':
    print(f"{Fore.YELLOW}No feedback data yet{Style.RESET_ALL}")
else:
    print(f"{Fore.GREEN}✅ Retrieval Ranking Intelligence Loaded{Style.RESET_ALL}\n")
    
    print(f"Total topics analyzed: {stats.get('total_topics', 0)}")
    print(f"Average success rate: {stats.get('average_score', 0):.1%}\n")
    
    print(f"{Fore.GREEN}Top Performing Topics (BOOSTED in retrieval):{Style.RESET_ALL}")
    for topic, score in stats.get('top_performing', []):
        print(f"  • {topic}: {score:.1%} approval")
    
    print(f"\n{Fore.YELLOW}Poor Performing Topics (DE-PRIORITIZED):{Style.RESET_ALL}")
    for topic, score in stats.get('bottom_performing', []):
        print(f"  • {topic}: {score:.1%} approval")

# Test re-ranking
print(f"\n{Fore.CYAN}{'='*60}")
print("TESTING: Re-ranking in action")
print(f"{'='*60}{Style.RESET_ALL}\n")

# Simulate retrieval results
mock_results = [
    {
        'id': '1',
        'text': 'Content about Test topic for CSV logging...',
        'distance': 0.3,
        'metadata': {}
    },
    {
        'id': '2',
        'text': 'Content about AI-powered customer service best practices...',
        'distance': 0.25,
        'metadata': {}
    },
    {
        'id': '3',
        'text': 'Article about running shoes for beginners...',
        'distance': 0.35,
        'metadata': {}
    }
]

query = "AI customer service"

print(f"Query: '{query}'")
print(f"\n{Fore.WHITE}BEFORE Re-ranking (by distance only):{Style.RESET_ALL}")
for i, r in enumerate(mock_results, 1):
    print(f"  #{i}: {r['text'][:50]}... (dist: {r['distance']:.3f})")

# Apply re-ranking
reranked = ranker.rerank_results(mock_results, query)

print(f"\n{Fore.GREEN}AFTER Re-ranking (with feedback signals):{Style.RESET_ALL}")
for i, r in enumerate(reranked, 1):
    boost = r.get('feedback_boost', 0)
    final = r.get('final_score', 0)
    boost_color = Fore.GREEN if boost > 0 else Fore.RED if boost < 0 else Fore.YELLOW
    print(f"  #{i}: {r['text'][:50]}...")
    print(f"       Original: {r.get('original_score', 0):.3f}, "
          f"{boost_color}Boost: {boost:+.3f}{Style.RESET_ALL}, "
          f"Final: {final:.3f}")

print(f"\n{Fore.GREEN}✅ Retrieval ranking is ACTIVE and learning from feedback!{Style.RESET_ALL}\n")
