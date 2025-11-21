"""
Visual Demo: Day 9 Feedback Learning System
Shows how the feedback loop works with actual data
"""

import sys
sys.path.insert(0, "D:\\Malind Tech\\AI_Models_Ata")

from backend.feedback_analyzer import FeedbackAnalyzer
import json
import pandas as pd
from colorama import init, Fore, Style

init(autoreset=True)

print(f"""
{Fore.CYAN}╔══════════════════════════════════════════════════════════════════════════════╗
║                    DAY 9 FEEDBACK LEARNING SYSTEM                            ║
║                         Visual Walkthrough                                   ║
╚══════════════════════════════════════════════════════════════════════════════╝{Style.RESET_ALL}

{Fore.YELLOW}┌─ THE FEEDBACK LOOP ────────────────────────────────────────────────────────┐{Style.RESET_ALL}
│                                                                              │
│  1. USER INTERACTION          2. CONTENT GENERATION       3. HUMAN REVIEW   │
│     ┌─────────┐                  ┌──────────┐               ┌─────────┐    │
│     │ Query   │──────────────────>│  Agent   │──────────────>│ Review  │    │
│     │ "blog"  │                  │ +Prompts │               │  App    │    │
│     └─────────┘                  └──────────┘               └─────────┘    │
│                                       │                          │          │
│                                       │                          ▼          │
│                                       │                   ┌─────────────┐   │
│  6. IMPROVED OUTPUT          5. UPDATE PROMPTS           │  Approved?  │   │
│     ┌─────────┐                  ┌──────────┐           │  Rejected?  │   │
│     │ Better  │<─────────────────│  Apply   │<──────────│  Edited?    │   │
│     │ Content │                  │ Changes  │           └─────────────┘   │
│     └─────────┘                  └──────────┘                   │          │
│                                       ▲                          │          │
│                                       │                          ▼          │
│                                       │                   ┌─────────────┐   │
│                                  4. ANALYZE              │   Save to   │   │
│                                  ┌──────────┐            │   CSV File  │   │
│                                  │ Identify │<───────────│  feedback/  │   │
│                                  │ Patterns │            └─────────────┘   │
│                                  └──────────┘                               │
│                                                                              │
{Fore.YELLOW}└──────────────────────────────────────────────────────────────────────────────┘{Style.RESET_ALL}

""")

# Initialize analyzer
analyzer = FeedbackAnalyzer()

# ============================================================================
print(f"\n{Fore.CYAN}{'='*80}")
print("STEP 1: LOAD FEEDBACK DATA FROM CSV FILES")
print(f"{'='*80}{Style.RESET_ALL}\n")

content_df = analyzer.load_content_feedback()
support_df = analyzer.load_support_feedback()

print(f"{Fore.WHITE}Content Feedback:{Style.RESET_ALL}")
print(f"  📁 File: data/human_feedback.csv")
print(f"  📊 Records: {len(content_df)}")
print(f"  📅 Date Range: {content_df['timestamp'].min()} to {content_df['timestamp'].max()}\n")

print(f"{Fore.WHITE}Support Feedback:{Style.RESET_ALL}")
print(f"  📁 File: data/support_feedback.csv")
print(f"  📊 Records: {len(support_df)}")
if not support_df.empty:
    print(f"  📅 Date Range: {support_df['timestamp'].min()} to {support_df['timestamp'].max()}\n")

# ============================================================================
print(f"\n{Fore.CYAN}{'='*80}")
print("STEP 2: EXAMINE ACTUAL FEEDBACK SAMPLES")
print(f"{'='*80}{Style.RESET_ALL}\n")

print(f"{Fore.YELLOW}📝 Content Feedback Sample:{Style.RESET_ALL}\n")
for idx, row in content_df.tail(2).iterrows():
    decision_color = Fore.GREEN if row['decision'] == 'approved' else Fore.RED
    print(f"{Fore.WHITE}Entry {idx + 1}:{Style.RESET_ALL}")
    print(f"  📅 Date: {row['timestamp']}")
    print(f"  📂 Type: {row['content_type']}")
    print(f"  💭 Topic: {row['topic']}")
    print(f"  📝 Headline: \"{row['generated_headline'][:70]}\"")
    
    body = str(row['generated_body']) if pd.notna(row['generated_body']) else "(empty)"
    print(f"  📄 Body: \"{body[:70]}...\"")
    
    decision = str(row['decision']) if pd.notna(row['decision']) else "unknown"
    print(f"  {decision_color}✓ Decision: {decision.upper()}{Style.RESET_ALL}")
    
    if pd.notna(row['validation_issues']) and str(row['validation_issues']).strip():
        print(f"  {Fore.RED}⚠️  Issues: {row['validation_issues']}{Style.RESET_ALL}")
    
    if pd.notna(row['reviewer_notes']) and str(row['reviewer_notes']).strip():
        print(f"  💬 Notes: {row['reviewer_notes']}")
    
    print(f"  ⏱️  Latency: {row['latency_s']:.2f}s\n")

if not support_df.empty:
    print(f"{Fore.YELLOW}🎧 Support Feedback Sample:{Style.RESET_ALL}\n")
    for idx, row in support_df.tail(1).iterrows():
        valid_color = Fore.GREEN if row['is_valid'] else Fore.RED
        print(f"{Fore.WHITE}Entry {idx + 1}:{Style.RESET_ALL}")
        print(f"  📅 Date: {row['timestamp']}")
        print(f"  🎯 Intent: {row['intent']}")
        print(f"  💬 Message: \"{row['message'][:60]}\"")
        print(f"  🤖 Reply: \"{row['reply'][:70]}...\"")
        print(f"  {valid_color}✓ Valid: {row['is_valid']}{Style.RESET_ALL}")
        print(f"  ⭐ Quality: {row['quality_score']:.2f}/1.0")
        print(f"  ⏱️  Latency: {row['latency_s']:.2f}s\n")

# ============================================================================
print(f"\n{Fore.CYAN}{'='*80}")
print("STEP 3: CALCULATE PERFORMANCE METRICS")
print(f"{'='*80}{Style.RESET_ALL}\n")

content_metrics = analyzer.calculate_content_metrics(content_df)
support_metrics = analyzer.calculate_support_metrics(support_df)

print(f"{Fore.YELLOW}📊 Content Generation Performance:{Style.RESET_ALL}\n")
print(f"  Total Reviews: {content_metrics.get('total_reviews', 0)}")
print(f"  ✅ Approved: {content_metrics.get('approved', 0)}")
print(f"  ❌ Rejected: {content_metrics.get('rejected', 0)}")
print(f"  ✏️  Edited: {content_metrics.get('edited', 0)}\n")

approval_rate = content_metrics.get('approval_rate', 0)
if approval_rate >= 0.7:
    color = Fore.GREEN
    emoji = "🎉"
elif approval_rate >= 0.5:
    color = Fore.YELLOW
    emoji = "⚠️ "
else:
    color = Fore.RED
    emoji = "❌"

print(f"  {color}{emoji} Overall Approval Rate: {approval_rate:.1%}{Style.RESET_ALL}\n")

if 'by_content_type' in content_metrics:
    print(f"  {Fore.WHITE}Breakdown by Content Type:{Style.RESET_ALL}")
    for ctype, stats in content_metrics['by_content_type'].items():
        rate = stats.get('approval_rate', 0)
        rate_color = Fore.GREEN if rate >= 0.7 else Fore.YELLOW if rate >= 0.5 else Fore.RED
        print(f"    • {ctype}: {rate_color}{rate:.1%}{Style.RESET_ALL} ({stats['total']} samples)")

print(f"\n{Fore.YELLOW}🎧 Support Reply Performance:{Style.RESET_ALL}\n")
if 'error' not in support_metrics:
    print(f"  Total Reviews: {support_metrics.get('total_reviews', 0)}")
    print(f"  ✅ Valid: {support_metrics.get('valid_replies', 0)}")
    print(f"  ❌ Invalid: {support_metrics.get('invalid_replies', 0)}\n")
    
    validation_rate = support_metrics.get('validation_rate', 0)
    avg_quality = support_metrics.get('avg_quality_score', 0)
    
    if validation_rate >= 0.8:
        color = Fore.GREEN
        emoji = "🎉"
    elif validation_rate >= 0.6:
        color = Fore.YELLOW
        emoji = "⚠️ "
    else:
        color = Fore.RED
        emoji = "❌"
    
    print(f"  {color}{emoji} Validation Rate: {validation_rate:.1%}{Style.RESET_ALL}")
    print(f"  ⭐ Average Quality: {avg_quality:.2f}/1.0\n")
else:
    print(f"  {Fore.YELLOW}No support feedback available yet{Style.RESET_ALL}\n")

# ============================================================================
print(f"\n{Fore.CYAN}{'='*80}")
print("STEP 4: IDENTIFY FAILURE PATTERNS")
print(f"{'='*80}{Style.RESET_ALL}\n")

content_failures = analyzer.identify_content_failure_patterns(content_df)
support_failures = analyzer.identify_support_failure_patterns(support_df)

print(f"{Fore.YELLOW}🔍 Content Generation Issues:{Style.RESET_ALL}\n")

if 'validation_failures' in content_failures and content_failures['validation_failures']:
    print(f"  {Fore.RED}Validation Failures:{Style.RESET_ALL}")
    for issue, count in list(content_failures['validation_failures'].items())[:5]:
        print(f"    ❌ {issue}: {count} occurrences")
    print()

if 'content_type_failures' in content_failures and content_failures['content_type_failures']:
    print(f"  {Fore.YELLOW}Failures by Content Type:{Style.RESET_ALL}")
    for ctype, counts in content_failures['content_type_failures'].items():
        if counts['rejected'] > 0 or counts['edited'] > 0:
            print(f"    • {ctype}: {counts['rejected']} rejected, {counts['edited']} edited")
    print()

if 'reviewer_concerns' in content_failures and content_failures['reviewer_concerns']:
    print(f"  {Fore.YELLOW}Common Reviewer Concerns:{Style.RESET_ALL}")
    for concern, count in list(content_failures['reviewer_concerns'].items())[:3]:
        print(f"    💭 \"{concern}\": {count} mentions")
    print()

print(f"{Fore.YELLOW}🔍 Support Reply Issues:{Style.RESET_ALL}\n")
if support_failures and 'low_quality_scores' in support_failures:
    low_quality = support_failures['low_quality_scores']
    if low_quality:
        print(f"  {Fore.RED}Low Quality Replies (<0.6):{Style.RESET_ALL}")
        for entry in low_quality[:2]:
            print(f"    ❌ Intent: {entry['intent']}, Score: {entry['quality_score']:.2f}")
            print(f"       Message: \"{entry['message'][:50]}...\"")
        print()
    else:
        print(f"  {Fore.GREEN}✅ No low-quality replies detected{Style.RESET_ALL}\n")

# ============================================================================
print(f"\n{Fore.CYAN}{'='*80}")
print("STEP 5: GENERATE IMPROVEMENT SUGGESTIONS")
print(f"{'='*80}{Style.RESET_ALL}\n")

# Note: suggest_prompt_improvements expects pattern lists, not DataFrames
# For demo, we'll use the generate_full_report method instead
report = analyzer.generate_full_report()
suggestions = report.get('improvement_suggestions', {})

if suggestions:
    print(f"{Fore.GREEN}💡 Found {len(suggestions)} areas for improvement:{Style.RESET_ALL}\n")
    
    for template_name, template_suggestions in suggestions.items():
        print(f"{Fore.YELLOW}📝 Template: {template_name}{Style.RESET_ALL}")
        for i, suggestion in enumerate(template_suggestions, 1):
            print(f"   {i}. {suggestion}")
        print()
else:
    print(f"{Fore.GREEN}✅ No critical issues found - system is performing well!{Style.RESET_ALL}\n")

# ============================================================================
print(f"\n{Fore.CYAN}{'='*80}")
print("STEP 6: COMPREHENSIVE REPORT SUMMARY")
print(f"{'='*80}{Style.RESET_ALL}\n")

# Report was already generated in Step 5

summary = report.get('summary', {})
print(f"{Fore.WHITE}📊 Analysis Summary:{Style.RESET_ALL}")
print(f"  📅 Date: {summary.get('analysis_date', 'N/A')}")
print(f"  📈 Total Feedback: {summary.get('total_feedback_entries', 0)} entries")
print(f"  🔍 Patterns Found: {summary.get('total_patterns', 0)}")
print(f"  💡 Suggestions: {summary.get('total_suggestions', 0)}\n")

agents = report.get('agents', {})
for agent_name, agent_data in agents.items():
    print(f"{Fore.YELLOW}{agent_name.replace('_', ' ').title()}:{Style.RESET_ALL}")
    metrics = agent_data.get('metrics', {})
    
    if 'approval_rate' in metrics:
        rate = metrics['approval_rate']
        color = Fore.GREEN if rate > 0.7 else Fore.YELLOW if rate > 0.5 else Fore.RED
        print(f"  {color}Approval Rate: {rate:.1%}{Style.RESET_ALL}")
    
    if 'validation_rate' in metrics:
        rate = metrics['validation_rate']
        color = Fore.GREEN if rate > 0.8 else Fore.YELLOW if rate > 0.6 else Fore.RED
        print(f"  {color}Validation Rate: {rate:.1%}{Style.RESET_ALL}")
    
    if 'avg_quality_score' in metrics:
        print(f"  Quality: {metrics['avg_quality_score']:.2f}/1.0")
    print()

print(f"{Fore.GREEN}✅ Full report saved to: logs/feedback_analysis_report.json{Style.RESET_ALL}\n")

# ============================================================================
print(f"\n{Fore.CYAN}{'='*80}")
print("HOW TO USE THIS FOR CONTINUOUS IMPROVEMENT")
print(f"{'='*80}{Style.RESET_ALL}\n")

print(f"""{Fore.WHITE}
🔄 THE CONTINUOUS LEARNING CYCLE:

1️⃣  COLLECT FEEDBACK
   • Use Streamlit review app: streamlit run ui/review_app.py
   • Review generated content and approve/reject/edit
   • Feedback automatically saved to data/human_feedback.csv

2️⃣  ANALYZE PATTERNS (Weekly)
   • Run: python scripts/feedback_analysis.py analyze
   • Review improvement suggestions in logs/feedback_analysis_report.json

3️⃣  UPDATE PROMPTS
   • Edit prompt files in prompts/ directory
   • Add examples from successful content
   • Address common failure patterns

4️⃣  TEST IMPROVEMENTS
   • Generate new content with updated prompts
   • Compare quality with previous versions

5️⃣  MEASURE IMPACT
   • Run: python scripts/feedback_analysis.py compare-prompts <template> <old_v> <new_v>
   • Check if approval rates improved
   • Keep changes if metrics are better

6️⃣  REPEAT
   • Continue collecting feedback
   • System learns and improves over time
{Style.RESET_ALL}""")

print(f"\n{Fore.CYAN}{'='*80}")
print("QUICK COMMANDS")
print(f"{'='*80}{Style.RESET_ALL}\n")

print(f"""{Fore.YELLOW}
# Run full analysis
python scripts/feedback_analysis.py analyze

# View specific template metrics
python scripts/feedback_analysis.py prompt-metrics blog_generator --days 30

# Compare two versions
python scripts/feedback_analysis.py compare-prompts blog_generator 1.0.0 1.1.0

# List all templates
python scripts/feedback_analysis.py list-prompts
{Style.RESET_ALL}""")

print(f"\n{Fore.GREEN}╔══════════════════════════════════════════════════════════════════════════════╗")
print(f"║  ✅ DEMO COMPLETE - Day 9 feedback learning system is operational!           ║")
print(f"╚══════════════════════════════════════════════════════════════════════════════╝{Style.RESET_ALL}\n")
