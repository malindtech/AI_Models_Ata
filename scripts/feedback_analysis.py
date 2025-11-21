"""
Day 9: Feedback Analysis CLI Tool
Command-line interface for analyzing feedback and generating improvement reports
"""

import argparse
import json
from pathlib import Path
from backend.feedback_analyzer import FeedbackAnalyzer
from backend.prompt_manager import PromptManager
from loguru import logger
import sys


def print_section(title: str, char: str = "="):
    """Print formatted section header"""
    print(f"\n{char * 80}")
    print(f"{title}")
    print(f"{char * 80}\n")


def analyze_feedback(output_format: str = "text", save_report: bool = True):
    """Run comprehensive feedback analysis"""
    print_section("DAY 9: FEEDBACK LEARNING & ANALYSIS")
    
    analyzer = FeedbackAnalyzer()
    
    print("📊 Analyzing feedback from both agents...\n")
    report = analyzer.generate_full_report()
    
    if output_format == "json":
        # JSON output
        print(json.dumps(report, indent=2))
        return report
    
    # Text output
    print_section("SUMMARY", "-")
    summary = report.get('summary', {})
    print(f"Content Generation Approval Rate: {summary.get('content_approval_rate', 0):.1%}")
    print(f"Support Reply Validation Rate: {summary.get('support_validation_rate', 0):.1%}")
    print(f"Total Patterns Identified: {summary.get('total_patterns_identified', 0)}")
    print(f"Total Improvement Suggestions: {summary.get('total_suggestions', 0)}")
    
    # Content Generation Analysis
    content_data = report.get('content_generation_agent', {})
    content_metrics = content_data.get('metrics', {})
    
    if not content_metrics.get('error'):
        print_section("CONTENT GENERATION AGENT", "-")
        print(f"Total Reviews: {content_metrics.get('total_reviews', 0)}")
        print(f"Approved: {content_metrics.get('approved', 0)}")
        print(f"Rejected: {content_metrics.get('rejected', 0)}")
        print(f"Edited: {content_metrics.get('edited', 0)}")
        print(f"Approval Rate: {content_metrics.get('approval_rate', 0):.1%}")
        
        # By content type
        by_type = content_metrics.get('by_content_type', {})
        if by_type:
            print("\nBy Content Type:")
            for ctype, stats in sorted(by_type.items(), key=lambda x: x[1]['approval_rate'], reverse=True):
                print(f"  {ctype:20s}: {stats['approval_rate']:.1%} ({stats['total']} samples)")
        
        # Failure patterns
        failures = content_data.get('failure_patterns', [])
        if failures:
            print("\nFailure Patterns:")
            for pattern in failures:
                print(f"  • {pattern['pattern_type']}: {pattern['description']}")
    
    # Customer Support Analysis
    support_data = report.get('customer_support_agent', {})
    support_metrics = support_data.get('metrics', {})
    
    if not support_metrics.get('error'):
        print_section("CUSTOMER SUPPORT AGENT", "-")
        print(f"Total Replies: {support_metrics.get('total_replies', 0)}")
        print(f"Valid: {support_metrics.get('valid_count', 0)}")
        print(f"Validation Rate: {support_metrics.get('validation_rate', 0):.1%}")
        
        # Quality stats
        quality = support_metrics.get('quality_stats', {})
        if quality:
            print(f"\nQuality Scores:")
            print(f"  Mean: {quality.get('mean', 0):.3f}")
            print(f"  Median: {quality.get('median', 0):.3f}")
            print(f"  Min: {quality.get('min', 0):.3f}")
            print(f"  Max: {quality.get('max', 0):.3f}")
        
        # By intent
        by_intent = support_metrics.get('by_intent', {})
        if by_intent:
            print("\nBy Intent:")
            for intent, stats in sorted(by_intent.items(), key=lambda x: x[1]['validation_rate'], reverse=True):
                print(f"  {intent:15s}: {stats['validation_rate']:.1%} validation ({stats['total']} samples)")
        
        # Failure patterns
        failures = support_data.get('failure_patterns', [])
        if failures:
            print("\nFailure Patterns:")
            for pattern in failures:
                print(f"  • {pattern['pattern_type']}: {pattern.get('description', 'No description')}")
    
    # Improvement Suggestions
    suggestions = report.get('improvement_suggestions', {})
    if suggestions:
        print_section("IMPROVEMENT SUGGESTIONS", "-")
        for template, suggestion_list in suggestions.items():
            print(f"\n{template}:")
            for i, suggestion in enumerate(suggestion_list, 1):
                print(f"  {i}. {suggestion}")
    
    # Save report
    if save_report:
        output_path = analyzer.save_report(report)
        print(f"\n✅ Full report saved to: {output_path}")
    
    return report


def list_prompts():
    """List all prompt templates with versions"""
    print_section("PROMPT TEMPLATES")
    
    manager = PromptManager()
    templates = manager.get_all_templates()
    
    if not templates:
        print("No templates found.")
        return
    
    print(f"{'Template':<25} {'Version':<10} {'Last Updated':<20}")
    print("-" * 60)
    
    for tmpl in templates:
        print(f"{tmpl['name']:<25} {tmpl['version']:<10} {tmpl.get('last_updated', 'unknown')[:19]:<20}")
    
    print(f"\nTotal templates: {len(templates)}")


def get_prompt_metrics(template_name: str, version: str = None, days: int = 30):
    """Get performance metrics for a prompt template"""
    print_section(f"METRICS: {template_name}" + (f" v{version}" if version else ""))
    
    manager = PromptManager()
    metrics = manager.get_template_metrics(template_name, version, days)
    
    if "error" in metrics:
        print(f"❌ {metrics['error']}")
        return
    
    print(f"Template: {metrics['template_name']}")
    print(f"Version: {metrics['version']}")
    print(f"Period: Last {metrics['period_days']} days")
    print(f"Total Uses: {metrics['total_uses']}")
    print(f"Approval Rate: {metrics.get('approval_rate', 0):.1%}")
    print(f"Avg Quality Score: {metrics.get('avg_quality_score', 0):.3f}")
    print(f"Avg Latency: {metrics.get('avg_latency_s', 0):.3f}s")
    
    # Outcomes
    outcomes = metrics.get('outcomes', {})
    if outcomes:
        print("\nOutcomes:")
        for outcome, count in outcomes.items():
            print(f"  {outcome}: {count}")
    
    # By content type
    by_type = metrics.get('by_content_type', {})
    if by_type:
        print("\nBy Content Type:")
        for ctype, stats in by_type.items():
            print(f"  {ctype}: {stats['total']} uses, {stats['avg_quality']:.3f} avg quality")


def compare_prompts(template_name: str, version1: str, version2: str, days: int = 30):
    """Compare two versions of a prompt template"""
    print_section(f"COMPARING: {template_name} v{version1} vs v{version2}")
    
    manager = PromptManager()
    comparison = manager.compare_versions(template_name, version1, version2, days)
    
    print(f"Template: {comparison['template_name']}")
    print(f"Period: Last {days} days\n")
    
    v1 = comparison['version1']['metrics']
    v2 = comparison['version2']['metrics']
    
    print(f"{'Metric':<25} {'v' + version1:<15} {'v' + version2:<15} {'Delta':<15}")
    print("-" * 70)
    
    # Total uses
    if 'total_uses' in v1 and 'total_uses' in v2:
        print(f"{'Total Uses':<25} {v1['total_uses']:<15} {v2['total_uses']:<15} {v2['total_uses'] - v1['total_uses']:<15}")
    
    # Approval rate
    if 'approval_rate' in v1 and 'approval_rate' in v2:
        delta = comparison.get('approval_rate_delta', 0)
        delta_str = f"{delta:+.1%}"
        print(f"{'Approval Rate':<25} {v1['approval_rate']:.1%:<15} {v2['approval_rate']:.1%:<15} {delta_str:<15}")
    
    # Latency
    if 'avg_latency_s' in v1 and 'avg_latency_s' in v2:
        delta = comparison.get('latency_delta_s', 0)
        delta_str = f"{delta:+.3f}s"
        print(f"{'Avg Latency':<25} {v1['avg_latency_s']:.3f}s {v2['avg_latency_s']:.3f}s {delta_str:<15}")
    
    # Quality score
    if 'avg_quality_score' in v1 and 'avg_quality_score' in v2:
        delta = v2.get('avg_quality_score', 0) - v1.get('avg_quality_score', 0)
        delta_str = f"{delta:+.3f}"
        print(f"{'Avg Quality Score':<25} {v1.get('avg_quality_score', 0):.3f} {v2.get('avg_quality_score', 0):.3f} {delta_str:<15}")


def main():
    parser = argparse.ArgumentParser(
        description="Day 9: Feedback Analysis & Prompt Management CLI",
        formatter_class=argparse.RawDescriptionHelpFormatter
    )
    
    subparsers = parser.add_subparsers(dest='command', help='Available commands')
    
    # analyze command
    analyze_parser = subparsers.add_parser('analyze', help='Run feedback analysis')
    analyze_parser.add_argument('--format', choices=['text', 'json'], default='text',
                                help='Output format (default: text)')
    analyze_parser.add_argument('--no-save', action='store_true',
                                help='Do not save report to file')
    
    # list-prompts command
    subparsers.add_parser('list-prompts', help='List all prompt templates')
    
    # prompt-metrics command
    metrics_parser = subparsers.add_parser('prompt-metrics', help='Get prompt performance metrics')
    metrics_parser.add_argument('template', help='Template name (e.g., reply_generator)')
    metrics_parser.add_argument('--version', help='Specific version (optional)')
    metrics_parser.add_argument('--days', type=int, default=30,
                                help='Number of days to analyze (default: 30)')
    
    # compare-prompts command
    compare_parser = subparsers.add_parser('compare-prompts', help='Compare two prompt versions')
    compare_parser.add_argument('template', help='Template name')
    compare_parser.add_argument('version1', help='First version to compare')
    compare_parser.add_argument('version2', help='Second version to compare')
    compare_parser.add_argument('--days', type=int, default=30,
                                help='Number of days to analyze (default: 30)')
    
    args = parser.parse_args()
    
    if not args.command:
        parser.print_help()
        return
    
    try:
        if args.command == 'analyze':
            analyze_feedback(
                output_format=args.format,
                save_report=not args.no_save
            )
        elif args.command == 'list-prompts':
            list_prompts()
        elif args.command == 'prompt-metrics':
            get_prompt_metrics(args.template, args.version, args.days)
        elif args.command == 'compare-prompts':
            compare_prompts(args.template, args.version1, args.version2, args.days)
    
    except Exception as e:
        logger.error(f"Command failed: {e}")
        print(f"\n❌ Error: {e}", file=sys.stderr)
        sys.exit(1)


if __name__ == "__main__":
    main()
