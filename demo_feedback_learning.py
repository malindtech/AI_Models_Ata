"""
Interactive Demo: Day 9 Feedback Learning System
This script demonstrates how feedback learning works step-by-step
"""

import sys
sys.path.insert(0, "D:\\Malind Tech\\AI_Models_Ata")

from backend.feedback_analyzer import FeedbackAnalyzer
import json
import pandas as pd
from colorama import init, Fore, Style

init(autoreset=True)

def print_header(title):
    print(f"\n{Fore.CYAN}{'='*80}")
    print(f"{title}")
    print(f"{'='*80}{Style.RESET_ALL}\n")

def print_section(title):
    print(f"\n{Fore.YELLOW}--- {title} ---{Style.RESET_ALL}")

def print_success(msg):
    print(f"{Fore.GREEN}✅ {msg}{Style.RESET_ALL}")

def print_info(msg):
    print(f"{Fore.WHITE}{msg}{Style.RESET_ALL}")

print_header("DAY 9 FEEDBACK LEARNING: INTERACTIVE DEMO")

print(f"""{Fore.MAGENTA}
📚 HOW IT WORKS:

1. FEEDBACK COLLECTION (2 sources):
   - Content Agent: Streamlit review app saves to data/human_feedback.csv
   - Support Agent: Validator saves to data/support_feedback.csv

2. FEEDBACK ANALYSIS:
   - Loads feedback from CSV files
   - Calculates approval/validation rates
   - Identifies common failure patterns
   - Extracts successful examples

3. LEARNING LOOP:
   - Generates improvement suggestions for prompts
   - Tracks metrics over time
   - A/B tests prompt versions
   - Applies best-performing changes

Let's see it in action!
{Style.RESET_ALL}""")

input(f"\n{Fore.CYAN}Press ENTER to continue...{Style.RESET_ALL}")

# ============================================================================
# STEP 1: Load Feedback Data
# ============================================================================
print_header("STEP 1: LOAD FEEDBACK DATA")

analyzer = FeedbackAnalyzer()

print_section("Loading Content Generation Feedback")
content_df = analyzer.load_content_feedback()
print_info(f"  Rows loaded: {len(content_df)}")
print_info(f"  Columns: {list(content_df.columns)}")
print_info(f"  Date range: {content_df['timestamp'].min()} to {content_df['timestamp'].max()}")

print_section("Loading Support Reply Feedback")
support_df = analyzer.load_support_feedback()
print_info(f"  Rows loaded: {len(support_df)}")
if not support_df.empty:
    print_info(f"  Columns: {list(support_df.columns)}")

input(f"\n{Fore.CYAN}Press ENTER to see the actual data...{Style.RESET_ALL}")

# ============================================================================
# STEP 2: Show Raw Feedback Samples
# ============================================================================
print_header("STEP 2: EXAMINE FEEDBACK SAMPLES")

print_section("Sample Content Feedback (Last 3 entries)")
for idx, row in content_df.tail(3).iterrows():
    print(f"\n{Fore.WHITE}Entry #{idx + 1}:")
    print(f"  Timestamp: {row['timestamp']}")
    print(f"  Content Type: {row['content_type']}")
    print(f"  Topic: {row['topic']}")
    print(f"  Decision: {Fore.GREEN if row['decision'] == 'approved' else Fore.RED}{row['decision']}{Style.RESET_ALL}")
    print(f"  Headline: {row['generated_headline'][:60]}...")
    print(f"  Body: {row['generated_body'][:80] if pd.notna(row['generated_body']) else '(empty)'}...")
    if pd.notna(row['validation_issues']) and row['validation_issues']:
        print(f"  {Fore.RED}Issues: {row['validation_issues']}{Style.RESET_ALL}")
    if pd.notna(row['reviewer_notes']) and row['reviewer_notes']:
        print(f"  Notes: {row['reviewer_notes']}")

if not support_df.empty:
    print_section("Sample Support Feedback")
    for idx, row in support_df.tail(2).iterrows():
        print(f"\n{Fore.WHITE}Entry #{idx + 1}:")
        print(f"  Timestamp: {row['timestamp']}")
        print(f"  Intent: {row['intent']}")
        print(f"  Valid: {Fore.GREEN if row['is_valid'] else Fore.RED}{row['is_valid']}{Style.RESET_ALL}")
        print(f"  Quality Score: {row['quality_score']:.2f}")
        print(f"  Message: {row['message'][:60]}...")
        print(f"  Reply: {row['reply'][:80]}...")

input(f"\n{Fore.CYAN}Press ENTER to analyze metrics...{Style.RESET_ALL}")

# ============================================================================
# STEP 3: Calculate Metrics
# ============================================================================
print_header("STEP 3: CALCULATE PERFORMANCE METRICS")

print_section("Content Generation Metrics")
content_metrics = analyzer.calculate_content_metrics(content_df)

print_info(f"  Total Reviews: {content_metrics.get('total_reviews', 0)}")
print_info(f"  Approved: {content_metrics.get('approved', 0)}")
print_info(f"  Rejected: {content_metrics.get('rejected', 0)}")
print_info(f"  Edited: {content_metrics.get('edited', 0)}")

approval_rate = content_metrics.get('approval_rate', 0)
color = Fore.GREEN if approval_rate > 0.7 else Fore.YELLOW if approval_rate > 0.5 else Fore.RED
print(f"\n  {color}Approval Rate: {approval_rate:.1%}{Style.RESET_ALL}")

if 'by_content_type' in content_metrics:
    print(f"\n  By Content Type:")
    for ctype, stats in content_metrics['by_content_type'].items():
        rate = stats.get('approval_rate', 0)
        print(f"    {ctype}: {rate:.1%} ({stats['total']} samples)")

print_section("Support Reply Metrics")
support_metrics = analyzer.calculate_support_metrics(support_df)

if 'error' not in support_metrics:
    print_info(f"  Total Reviews: {support_metrics.get('total_reviews', 0)}")
    print_info(f"  Valid Replies: {support_metrics.get('valid_replies', 0)}")
    print_info(f"  Invalid Replies: {support_metrics.get('invalid_replies', 0)}")
    
    validation_rate = support_metrics.get('validation_rate', 0)
    avg_quality = support_metrics.get('avg_quality_score', 0)
    
    color = Fore.GREEN if validation_rate > 0.8 else Fore.YELLOW if validation_rate > 0.6 else Fore.RED
    print(f"\n  {color}Validation Rate: {validation_rate:.1%}{Style.RESET_ALL}")
    print(f"  Average Quality Score: {avg_quality:.2f}/1.0")
else:
    print_info(f"  {support_metrics['error']}")

input(f"\n{Fore.CYAN}Press ENTER to identify failure patterns...{Style.RESET_ALL}")

# ============================================================================
# STEP 4: Identify Failure Patterns
# ============================================================================
print_header("STEP 4: IDENTIFY FAILURE PATTERNS")

print_section("Content Generation Failures")
content_failures = analyzer.identify_content_failure_patterns(content_df)

if 'validation_failures' in content_failures:
    print(f"\n  {Fore.RED}Validation Failures:{Style.RESET_ALL}")
    for issue, count in content_failures['validation_failures'].items():
        print(f"    • {issue}: {count} occurrences")

if 'content_type_failures' in content_failures:
    print(f"\n  {Fore.YELLOW}Failures by Content Type:{Style.RESET_ALL}")
    for ctype, counts in content_failures['content_type_failures'].items():
        print(f"    {ctype}: {counts['rejected']} rejected, {counts['edited']} edited")

if 'reviewer_concerns' in content_failures:
    print(f"\n  {Fore.YELLOW}Reviewer Concerns:{Style.RESET_ALL}")
    for concern, count in list(content_failures['reviewer_concerns'].items())[:5]:
        print(f"    • {concern}: {count} mentions")

print_section("Support Reply Failures")
support_failures = analyzer.identify_support_failure_patterns(support_df)

if support_failures and 'low_quality_scores' in support_failures:
    low_quality = support_failures['low_quality_scores']
    if low_quality:
        print(f"\n  {Fore.RED}Low Quality Replies (<0.6):{Style.RESET_ALL}")
        for entry in low_quality[:3]:
            print(f"    • Intent: {entry['intent']}, Score: {entry['quality_score']:.2f}")
            print(f"      Message: {entry['message'][:60]}...")

input(f"\n{Fore.CYAN}Press ENTER to generate improvement suggestions...{Style.RESET_ALL}")

# ============================================================================
# STEP 5: Generate Improvement Suggestions
# ============================================================================
print_header("STEP 5: GENERATE IMPROVEMENT SUGGESTIONS")

suggestions = analyzer.suggest_prompt_improvements(
    content_df, 
    support_df, 
    content_failures, 
    support_failures
)

if suggestions:
    print(f"{Fore.GREEN}Found {len(suggestions)} templates with improvement suggestions:{Style.RESET_ALL}\n")
    
    for template_name, template_suggestions in suggestions.items():
        print(f"{Fore.YELLOW}Template: {template_name}{Style.RESET_ALL}")
        for i, suggestion in enumerate(template_suggestions, 1):
            print(f"  {i}. {suggestion}")
        print()
else:
    print_info("No improvement suggestions generated (high quality across all templates)")

input(f"\n{Fore.CYAN}Press ENTER to see the complete analysis report...{Style.RESET_ALL}")

# ============================================================================
# STEP 6: Generate Full Report
# ============================================================================
print_header("STEP 6: COMPREHENSIVE ANALYSIS REPORT")

report = analyzer.generate_full_report()

print_section("Report Summary")
summary = report.get('summary', {})
print_info(f"  Analysis Date: {summary.get('analysis_date', 'N/A')}")
print_info(f"  Total Feedback Entries: {summary.get('total_feedback_entries', 0)}")
print_info(f"  Patterns Identified: {summary.get('total_patterns', 0)}")
print_info(f"  Improvement Suggestions: {summary.get('total_suggestions', 0)}")

print_section("Agent Performance")
agents = report.get('agents', {})

for agent_name, agent_data in agents.items():
    print(f"\n{Fore.CYAN}{agent_name.replace('_', ' ').title()}{Style.RESET_ALL}")
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
        print(f"  Quality Score: {metrics['avg_quality_score']:.2f}/1.0")

print_section("Report Saved")
print_success(f"Full report saved to: logs/feedback_analysis_report.json")

# ============================================================================
# STEP 7: How to Apply Improvements
# ============================================================================
print_header("STEP 7: HOW TO APPLY IMPROVEMENTS")

print(f"""{Fore.MAGENTA}
📝 APPLYING IMPROVEMENTS TO PROMPTS:

1. Review Suggestions:
   {Fore.WHITE}python scripts/feedback_analysis.py analyze{Fore.MAGENTA}

2. Update Prompt Templates:
   Edit files in prompts/ folder based on suggestions
   Example: prompts/blog_generator.yaml
   
3. Test New Version:
   Generate content with updated prompt
   Collect feedback via Streamlit review app
   
4. Compare Performance:
   {Fore.WHITE}python scripts/feedback_analysis.py compare-prompts blog_generator 1.0.0 1.1.0{Fore.MAGENTA}

5. Apply Best Version:
   If metrics improve, keep new version
   If not, rollback using prompt manager
{Style.RESET_ALL}""")

print_header("DEMO COMPLETE!")

print(f"""{Fore.GREEN}
✅ You've seen how Day 9 feedback learning works:

1. ✅ Collected feedback from both agents (CSV files)
2. ✅ Calculated performance metrics (approval/validation rates)
3. ✅ Identified failure patterns (validation issues, low quality)
4. ✅ Generated improvement suggestions (actionable prompts)
5. ✅ Created comprehensive report (JSON export)

The system continuously learns from human feedback to improve both agents!
{Style.RESET_ALL}""")

print(f"\n{Fore.CYAN}Next Steps:{Style.RESET_ALL}")
print("  1. Generate more content and collect feedback")
print("  2. Run periodic analysis to track trends")
print("  3. Update prompts based on suggestions")
print("  4. Monitor metrics to validate improvements\n")
