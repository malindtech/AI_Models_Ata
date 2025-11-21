"""
Day 9 Auto-Learning Script
Run this manually to analyze feedback and auto-update the system

Usage: python day9_auto_learn.py
"""

import sys
sys.path.insert(0, "D:\\Malind Tech\\AI_Models_Ata")

from backend.feedback_analyzer import FeedbackAnalyzer
from backend.prompt_manager import PromptManager
from pathlib import Path
import json
from datetime import datetime
from colorama import init, Fore, Style
import yaml

init(autoreset=True)

def print_header(title):
    print(f"\n{Fore.CYAN}{'='*80}")
    print(f"{title}")
    print(f"{'='*80}{Style.RESET_ALL}\n")

def print_section(title):
    print(f"\n{Fore.YELLOW}▶ {title}{Style.RESET_ALL}")

def print_success(msg):
    print(f"{Fore.GREEN}✅ {msg}{Style.RESET_ALL}")

def print_warning(msg):
    print(f"{Fore.YELLOW}⚠️  {msg}{Style.RESET_ALL}")

def print_error(msg):
    print(f"{Fore.RED}❌ {msg}{Style.RESET_ALL}")

def print_info(msg):
    print(f"{Fore.WHITE}{msg}{Style.RESET_ALL}")

# ============================================================================
# STEP 1: ANALYZE FEEDBACK
# ============================================================================
def analyze_feedback():
    """Collect and analyze all feedback"""
    print_header("STEP 1: ANALYZING FEEDBACK")
    
    analyzer = FeedbackAnalyzer()
    
    # Load feedback
    content_df = analyzer.load_content_feedback()
    support_df = analyzer.load_support_feedback()
    
    print_info(f"  📊 Content feedback: {len(content_df)} entries")
    print_info(f"  📊 Support feedback: {len(support_df)} entries")
    
    if len(content_df) == 0 and len(support_df) == 0:
        print_error("No feedback data found. Generate content and collect reviews first.")
        return None
    
    # Generate analysis
    report = analyzer.generate_full_report()
    
    # Calculate metrics
    content_metrics = report.get('content_generation_agent', {}).get('metrics', {})
    support_metrics = report.get('customer_support_agent', {}).get('metrics', {})
    
    approval_rate = content_metrics.get('approval_rate', 0)
    validation_rate = support_metrics.get('validation_rate', 0)
    
    print_section("Performance Metrics")
    
    if approval_rate > 0:
        color = Fore.GREEN if approval_rate >= 0.7 else Fore.YELLOW if approval_rate >= 0.5 else Fore.RED
        print(f"  Content Approval Rate: {color}{approval_rate:.1%}{Style.RESET_ALL}")
    
    if validation_rate > 0:
        color = Fore.GREEN if validation_rate >= 0.8 else Fore.YELLOW if validation_rate >= 0.6 else Fore.RED
        print(f"  Support Validation Rate: {color}{validation_rate:.1%}{Style.RESET_ALL}")
    
    # Show issues
    suggestions = report.get('improvement_suggestions', {})
    if suggestions:
        print_section("Issues Identified")
        issue_count = 0
        for template, items in suggestions.items():
            for item in items:
                issue_count += 1
                print(f"  {issue_count}. {item}")
    else:
        print_success("No critical issues found!")
    
    return report

# ============================================================================
# STEP 2: GENERATE CHANGES PREVIEW
# ============================================================================
def generate_changes_preview(report):
    """Show what will be changed"""
    print_header("STEP 2: PROPOSED CHANGES")
    
    suggestions = report.get('improvement_suggestions', {})
    
    if not suggestions:
        print_success("System is performing well - no changes needed!")
        return []
    
    changes = []
    
    # Analyze each suggestion and propose concrete changes
    for template_name, suggestion_list in suggestions.items():
        for suggestion in suggestion_list:
            change = parse_suggestion_to_change(suggestion, template_name, report)
            if change:
                changes.append(change)
    
    # Display changes
    if not changes:
        print_info("No actionable changes generated from suggestions.")
        return []
    
    print_section("Prompt Updates")
    for i, change in enumerate(changes, 1):
        print(f"\n{Fore.CYAN}Change #{i}:{Style.RESET_ALL}")
        print(f"  File: {change['file']}")
        print(f"  Action: {change['action']}")
        print(f"  Reason: {change['reason']}")
        if 'preview' in change:
            print(f"  Preview: {change['preview'][:100]}...")
    
    return changes

def parse_suggestion_to_change(suggestion, template_name, report):
    """Convert suggestion text to actionable change"""
    
    # Example: "Address validation issue: Content too short"
    if "too short" in suggestion.lower() or "missing body" in suggestion.lower():
        return {
            'file': 'prompts/blog_generator.yaml',
            'action': 'Add length requirements',
            'reason': suggestion,
            'type': 'add_validation',
            'content': """
REQUIREMENTS:
- Write at least 300 words
- Include both headline and body
- Ensure content is complete and well-structured
"""
        }
    
    # Example: "Low quality scores for intent X"
    if "low quality" in suggestion.lower():
        return {
            'file': 'prompts/reply_generator.yaml',
            'action': 'Improve response quality',
            'reason': suggestion,
            'type': 'add_examples',
            'content': None  # Will add successful examples
        }
    
    # Generic improvement
    return {
        'file': f'prompts/{template_name}.yaml',
        'action': 'General improvement',
        'reason': suggestion,
        'type': 'generic'
    }

# ============================================================================
# STEP 3: APPLY CHANGES
# ============================================================================
def apply_changes(changes):
    """Apply approved changes to prompt files"""
    print_header("STEP 3: APPLYING CHANGES")
    
    if not changes:
        print_info("No changes to apply.")
        return
    
    manager = PromptManager()
    applied_count = 0
    
    for change in changes:
        try:
            file_path = Path(change['file'])
            
            if not file_path.exists():
                print_warning(f"File not found: {file_path}")
                continue
            
            # Load existing prompt
            with open(file_path, 'r', encoding='utf-8') as f:
                prompt_data = yaml.safe_load(f)
            
            # Backup original
            backup_path = file_path.parent / f"{file_path.stem}_backup_{datetime.now().strftime('%Y%m%d_%H%M%S')}.yaml"
            with open(backup_path, 'w', encoding='utf-8') as f:
                yaml.dump(prompt_data, f)
            
            # Apply change
            if change['type'] == 'add_validation':
                # Add requirements to system prompt
                system_prompt = prompt_data.get('system', '')
                
                # Check if this exact change was already applied
                change_signature = change['content'].strip()
                if change_signature in system_prompt:
                    print_info(f"✓ Already applied: {file_path.name} (no changes needed)")
                    continue
                
                # Check for any validation requirements (prevent duplicates)
                if 'REQUIREMENTS:' in system_prompt and 'Write at least' in system_prompt:
                    print_info(f"✓ Similar changes exist: {file_path.name} (skipping to avoid duplicates)")
                    continue
                
                # Safe to apply - this is a new change
                prompt_data['system'] = system_prompt + "\n" + change['content']
                
                # Save updated prompt
                with open(file_path, 'w', encoding='utf-8') as f:
                    yaml.dump(prompt_data, f, default_flow_style=False)
                
                print_success(f"Updated: {file_path.name}")
                print_info(f"  Backup: {backup_path.name}")
                applied_count += 1
            
            elif change['type'] == 'add_examples':
                # Add successful examples
                print_info(f"Manual review needed for: {file_path.name}")
                print_info(f"  Add successful examples from feedback data")
            
            else:
                print_info(f"Manual review needed for: {file_path.name}")
        
        except Exception as e:
            print_error(f"Failed to update {change['file']}: {e}")
    
    print(f"\n{Fore.GREEN}Applied {applied_count}/{len(changes)} changes{Style.RESET_ALL}")

# ============================================================================
# STEP 4: UPDATE RETRIEVAL RANKING
# ============================================================================
def update_retrieval_ranking(report):
    """Update retrieval based on feedback patterns"""
    print_header("STEP 4: UPDATING RETRIEVAL RANKING")
    
    try:
        from backend.feedback_ranker import get_feedback_ranker
        
        ranker = get_feedback_ranker()
        stats = ranker.get_ranking_stats()
        
        if stats.get('status') == 'no_feedback_data':
            print_info("No feedback data yet for retrieval ranking")
            return
        
        print_section("Ranking Intelligence Learned")
        print_info(f"  Topics analyzed: {stats.get('total_topics', 0)}")
        print_info(f"  Average success rate: {stats.get('average_score', 0):.1%}")
        
        # Show top performing topics (boost these in retrieval)
        top = stats.get('top_performing', [])
        if top:
            print(f"\n  {Fore.GREEN}✓ Boosting these topics in retrieval:{Style.RESET_ALL}")
            for topic, score in top[:3]:
                print(f"    • {topic}: {score:.1%} approval")
        
        # Show poor performing topics (de-prioritize these)
        bottom = stats.get('bottom_performing', [])
        if bottom:
            print(f"\n  {Fore.YELLOW}⚠ De-prioritizing these topics:{Style.RESET_ALL}")
            for topic, score in bottom[:3]:
                print(f"    • {topic}: {score:.1%} approval")
        
        print_success("\nRetrieval ranking updated based on feedback!")
        print_info("Next retrieval will use learned preferences")
        
    except Exception as e:
        print_error(f"Error updating retrieval ranking: {e}")

# ============================================================================
# STEP 5: GENERATE MEETING SUMMARY
# ============================================================================
def generate_meeting_summary(report, changes):
    """Create executive summary for meetings"""
    print_header("STEP 5: MEETING SUMMARY")
    
    summary_data = {
        'date': datetime.now().strftime('%Y-%m-%d'),
        'metrics': {},
        'issues_fixed': [],
        'changes_applied': [],
        'performance_trends': {}
    }
    
    # Extract metrics
    content_metrics = report.get('content_generation_agent', {}).get('metrics', {})
    support_metrics = report.get('customer_support_agent', {}).get('metrics', {})
    
    summary_data['metrics'] = {
        'content_approval_rate': f"{content_metrics.get('approval_rate', 0):.1%}",
        'content_total_reviews': content_metrics.get('total_reviews', 0),
        'support_validation_rate': f"{support_metrics.get('validation_rate', 0):.1%}",
        'support_avg_quality': f"{support_metrics.get('quality_stats', {}).get('mean', 0):.2f}/1.0"
    }
    
    # Issues fixed
    suggestions = report.get('improvement_suggestions', {})
    for template, items in suggestions.items():
        summary_data['issues_fixed'].extend(items)
    
    # Changes applied
    summary_data['changes_applied'] = [
        f"{change['file']}: {change['action']}" for change in changes
    ]
    
    # Save summary
    summary_file = Path('logs/meeting_summary.json')
    summary_file.parent.mkdir(exist_ok=True)
    
    with open(summary_file, 'w') as f:
        json.dump(summary_data, f, indent=2)
    
    # Display summary
    print_section("Executive Summary")
    print(f"\n{Fore.WHITE}Performance Metrics:{Style.RESET_ALL}")
    print(f"  • Content Approval Rate: {summary_data['metrics']['content_approval_rate']}")
    print(f"  • Reviews Analyzed: {summary_data['metrics']['content_total_reviews']}")
    print(f"  • Support Validation: {summary_data['metrics']['support_validation_rate']}")
    print(f"  • Support Quality: {summary_data['metrics']['support_avg_quality']}")
    
    if summary_data['issues_fixed']:
        print(f"\n{Fore.WHITE}Issues Identified & Fixed:{Style.RESET_ALL}")
        for i, issue in enumerate(summary_data['issues_fixed'][:3], 1):
            print(f"  {i}. {issue[:80]}...")
    
    if summary_data['changes_applied']:
        print(f"\n{Fore.WHITE}Prompts Updated:{Style.RESET_ALL}")
        for change in summary_data['changes_applied']:
            print(f"  • {change}")
    
    print_success(f"\nFull summary saved: {summary_file}")
    
    return summary_data

# ============================================================================
# MAIN WORKFLOW
# ============================================================================
def main():
    print(f"""
{Fore.MAGENTA}╔══════════════════════════════════════════════════════════════════════════════╗
║                    DAY 9 AUTO-LEARNING SYSTEM                                ║
║                   Feedback → Analysis → Auto-Update                          ║
╚══════════════════════════════════════════════════════════════════════════════╝{Style.RESET_ALL}

This script will:
  1. Analyze all collected feedback
  2. Identify issues and patterns
  3. Propose changes to prompts
  4. Show preview before applying
  5. Update retrieval ranking
  6. Generate meeting summary

{Fore.YELLOW}Press ENTER to start...{Style.RESET_ALL}
""")
    input()
    
    # Step 1: Analyze
    report = analyze_feedback()
    if not report:
        return
    
    # Step 2: Preview changes
    changes = generate_changes_preview(report)
    
    # Ask for confirmation
    if changes:
        print(f"\n{Fore.YELLOW}{'='*80}")
        print(f"READY TO APPLY {len(changes)} CHANGES")
        print(f"{'='*80}{Style.RESET_ALL}\n")
        
        try:
            response = input(f"{Fore.CYAN}Apply these changes? (yes/no): {Style.RESET_ALL}").strip().lower()
        except (EOFError, KeyboardInterrupt):
            print_info("\nNo input received. Changes cancelled.")
            changes = []
            response = 'no'
        
        if response in ['yes', 'y']:
            # Step 3: Apply changes
            apply_changes(changes)
        else:
            print_info("Changes cancelled. No files modified.")
            changes = []
    
    # Step 4: Update retrieval (always runs, independent of prompt changes)
    update_retrieval_ranking(report)
    
    # Step 5: Generate summary (always)
    summary = generate_meeting_summary(report, changes if changes else [])
    
    # Final message
    print(f"\n{Fore.GREEN}╔══════════════════════════════════════════════════════════════════════════════╗")
    print(f"║  ✅ AUTO-LEARNING COMPLETE                                                   ║")
    print(f"╚══════════════════════════════════════════════════════════════════════════════╝{Style.RESET_ALL}\n")
    
    print(f"{Fore.CYAN}Next Steps:{Style.RESET_ALL}")
    print("  1. Review updated prompts in prompts/ folder")
    print("  2. Test content generation to verify improvements")
    print("  3. Continue collecting feedback in Streamlit")
    print("  4. Run this script again next week")
    print(f"\n{Fore.WHITE}Meeting Summary: logs/meeting_summary.json{Style.RESET_ALL}")
    print(f"{Fore.WHITE}Full Report: logs/feedback_analysis_report.json{Style.RESET_ALL}\n")

if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print(f"\n{Fore.YELLOW}Process interrupted by user{Style.RESET_ALL}")
    except Exception as e:
        print(f"\n{Fore.RED}Error: {e}{Style.RESET_ALL}")
        import traceback
        traceback.print_exc()
