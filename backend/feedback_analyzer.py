"""
Day 9: Feedback Learning & Analysis System
Analyzes human feedback for both Content Generation and Customer Support agents
Identifies failure patterns and suggests prompt improvements
"""

import pandas as pd
import numpy as np
from pathlib import Path
from typing import Dict, List, Optional, Tuple
from collections import defaultdict, Counter
import json
from datetime import datetime, timedelta
from loguru import logger
import re


class FeedbackAnalyzer:
    """
    Unified feedback analyzer for both Content Generation and Support Reply agents
    
    Analyzes:
    - Content feedback from data/human_feedback.csv (Streamlit review app)
    - Support feedback from data/support_feedback.csv (validator results)
    
    Generates:
    - Approval rate metrics by content type and prompt template
    - Common failure patterns and validation issues
    - Successful content patterns for few-shot examples
    - Actionable prompt improvement suggestions
    """
    
    def __init__(
        self, 
        content_feedback_path: str = "data/human_feedback.csv",
        support_feedback_path: str = "data/support_feedback.csv"
    ):
        self.content_feedback_path = Path(content_feedback_path)
        self.support_feedback_path = Path(support_feedback_path)
        
    def load_content_feedback(self) -> pd.DataFrame:
        """Load content generation feedback from Streamlit review app"""
        if not self.content_feedback_path.exists():
            logger.warning(f"Content feedback not found: {self.content_feedback_path}")
            return pd.DataFrame()
        
        try:
            df = pd.read_csv(self.content_feedback_path)
            logger.info(f"✅ Loaded {len(df)} content feedback entries")
            return df
        except Exception as e:
            logger.error(f"Error loading content feedback: {e}")
            return pd.DataFrame()
    
    def load_support_feedback(self) -> pd.DataFrame:
        """Load support reply feedback from validator results"""
        if not self.support_feedback_path.exists():
            logger.warning(f"Support feedback not found: {self.support_feedback_path}")
            return pd.DataFrame()
        
        try:
            df = pd.read_csv(self.support_feedback_path)
            logger.info(f"✅ Loaded {len(df)} support feedback entries")
            return df
        except Exception as e:
            logger.error(f"Error loading support feedback: {e}")
            return pd.DataFrame()
    
    def calculate_content_metrics(self, df: pd.DataFrame) -> Dict:
        """
        Calculate approval metrics for content generation
        
        Returns:
            Dict with approval rates, edit distances, latency stats
        """
        if df.empty:
            return {"error": "No content feedback data available"}
        
        total = len(df)
        
        # Decision breakdown
        decision_counts = df['decision'].value_counts().to_dict() if 'decision' in df.columns else {}
        approved = decision_counts.get('approved', 0)
        rejected = decision_counts.get('rejected', 0)
        edited = decision_counts.get('edited', 0)
        
        # Calculate approval rate (approved + edited are considered successful)
        approval_rate = (approved + edited) / total if total > 0 else 0.0
        rejection_rate = rejected / total if total > 0 else 0.0
        
        # Metrics by content type
        by_content_type = {}
        if 'content_type' in df.columns:
            for content_type in df['content_type'].unique():
                subset = df[df['content_type'] == content_type]
                decisions = subset['decision'].value_counts().to_dict()
                by_content_type[content_type] = {
                    "total": len(subset),
                    "approved": decisions.get('approved', 0),
                    "rejected": decisions.get('rejected', 0),
                    "edited": decisions.get('edited', 0),
                    "approval_rate": (decisions.get('approved', 0) + decisions.get('edited', 0)) / len(subset)
                }
        
        # Latency statistics
        latency_stats = {}
        if 'latency_s' in df.columns:
            latency_stats = {
                "mean": float(df['latency_s'].mean()),
                "median": float(df['latency_s'].median()),
                "p95": float(df['latency_s'].quantile(0.95)),
                "min": float(df['latency_s'].min()),
                "max": float(df['latency_s'].max())
            }
        
        return {
            "total_reviews": total,
            "approved": approved,
            "rejected": rejected,
            "edited": edited,
            "approval_rate": round(approval_rate, 3),
            "rejection_rate": round(rejection_rate, 3),
            "by_content_type": by_content_type,
            "latency_stats": latency_stats,
            "analysis_timestamp": datetime.now().isoformat()
        }
    
    def calculate_support_metrics(self, df: pd.DataFrame) -> Dict:
        """
        Calculate quality metrics for support replies
        
        Returns:
            Dict with validation pass rates, quality scores
        """
        if df.empty:
            return {"error": "No support feedback data available"}
        
        total = len(df)
        
        # Validation status
        valid_count = df['is_valid'].sum() if 'is_valid' in df.columns else 0
        validation_rate = valid_count / total if total > 0 else 0.0
        
        # Quality score statistics
        quality_stats = {}
        if 'quality_score' in df.columns:
            quality_stats = {
                "mean": float(df['quality_score'].mean()),
                "median": float(df['quality_score'].median()),
                "min": float(df['quality_score'].min()),
                "max": float(df['quality_score'].max()),
                "std": float(df['quality_score'].std())
            }
        
        # Metrics by intent
        by_intent = {}
        if 'intent' in df.columns:
            for intent in df['intent'].unique():
                subset = df[df['intent'] == intent]
                by_intent[intent] = {
                    "total": len(subset),
                    "valid_count": int(subset['is_valid'].sum()) if 'is_valid' in subset.columns else 0,
                    "validation_rate": float(subset['is_valid'].mean()) if 'is_valid' in subset.columns else 0.0,
                    "avg_quality_score": float(subset['quality_score'].mean()) if 'quality_score' in subset.columns else 0.0
                }
        
        # Latency statistics
        latency_stats = {}
        if 'latency_s' in df.columns:
            latency_stats = {
                "mean": float(df['latency_s'].mean()),
                "median": float(df['latency_s'].median()),
                "p95": float(df['latency_s'].quantile(0.95))
            }
        
        return {
            "total_replies": total,
            "valid_count": int(valid_count),
            "validation_rate": round(validation_rate, 3),
            "quality_stats": quality_stats,
            "by_intent": by_intent,
            "latency_stats": latency_stats,
            "analysis_timestamp": datetime.now().isoformat()
        }
    
    def identify_content_failure_patterns(self, df: pd.DataFrame) -> List[Dict]:
        """
        Analyze rejected/edited content to find common issues
        
        Returns:
            List of failure patterns with frequency and examples
        """
        if df.empty or 'decision' not in df.columns:
            return []
        
        # Focus on rejected and edited content
        problematic = df[df['decision'].isin(['rejected', 'edited'])]
        
        if problematic.empty:
            return []
        
        patterns = []
        
        # Pattern 1: Validation issues
        if 'validation_issues' in problematic.columns:
            issues = problematic['validation_issues'].dropna()
            if not issues.empty:
                # Parse validation issues (may be JSON or text)
                issue_counts = Counter()
                for issue in issues:
                    if isinstance(issue, str) and issue.strip():
                        # Try to parse as JSON list
                        try:
                            issue_list = json.loads(issue)
                            if isinstance(issue_list, list):
                                issue_counts.update(issue_list)
                            else:
                                issue_counts[str(issue)] += 1
                        except:
                            issue_counts[issue] += 1
                
                if issue_counts:
                    patterns.append({
                        "pattern_type": "validation_failures",
                        "description": "Common validation issues in rejected content",
                        "top_issues": [{"issue": k, "count": v} for k, v in issue_counts.most_common(5)],
                        "total_affected": len(issues)
                    })
        
        # Pattern 2: Reviewer notes analysis
        if 'reviewer_notes' in problematic.columns:
            notes = problematic['reviewer_notes'].dropna()
            if not notes.empty:
                # Extract common keywords/phrases
                note_words = Counter()
                for note in notes:
                    if isinstance(note, str):
                        # Simple keyword extraction
                        words = re.findall(r'\b[a-z]{4,}\b', note.lower())
                        note_words.update(words)
                
                # Filter out common words
                stop_words = {'that', 'this', 'with', 'from', 'have', 'been', 'were', 'their', 'would', 'could', 'should'}
                filtered = {k: v for k, v in note_words.items() if k not in stop_words and v > 1}
                
                if filtered:
                    patterns.append({
                        "pattern_type": "reviewer_concerns",
                        "description": "Common themes in reviewer feedback",
                        "top_keywords": [{"word": k, "frequency": v} for k, v in Counter(filtered).most_common(10)],
                        "total_notes": len(notes)
                    })
        
        # Pattern 3: Content type specific issues
        if 'content_type' in problematic.columns:
            by_type = problematic.groupby('content_type').size().to_dict()
            patterns.append({
                "pattern_type": "content_type_failures",
                "description": "Rejection/edit counts by content type",
                "breakdown": [{"content_type": k, "count": v} for k, v in sorted(by_type.items(), key=lambda x: x[1], reverse=True)],
                "total_types": len(by_type)
            })
        
        # Pattern 4: Short content (likely incomplete generation)
        if 'generated_body' in problematic.columns:
            short_content = problematic[problematic['generated_body'].str.len() < 200]
            if not short_content.empty:
                patterns.append({
                    "pattern_type": "insufficient_content",
                    "description": "Generated content too short (< 200 chars)",
                    "count": len(short_content),
                    "percentage": round(len(short_content) / len(problematic) * 100, 1),
                    "avg_length": int(short_content['generated_body'].str.len().mean())
                })
        
        return patterns
    
    def identify_support_failure_patterns(self, df: pd.DataFrame) -> List[Dict]:
        """
        Analyze low-quality support replies to find common issues
        
        Returns:
            List of failure patterns with frequency and examples
        """
        if df.empty:
            return []
        
        patterns = []
        
        # Pattern 1: Low quality scores
        if 'quality_score' in df.columns:
            low_quality = df[df['quality_score'] < 0.7]
            if not low_quality.empty:
                patterns.append({
                    "pattern_type": "low_quality_responses",
                    "description": "Replies with quality score < 0.7",
                    "count": len(low_quality),
                    "percentage": round(len(low_quality) / len(df) * 100, 1),
                    "avg_score": round(low_quality['quality_score'].mean(), 3)
                })
        
        # Pattern 2: Validation failures by issue type
        if 'issues' in df.columns:
            invalid = df[df['is_valid'] == False] if 'is_valid' in df.columns else df
            if not invalid.empty:
                issue_counts = Counter()
                for issues in invalid['issues'].dropna():
                    if isinstance(issues, str):
                        try:
                            issue_list = json.loads(issues)
                            if isinstance(issue_list, list):
                                issue_counts.update(issue_list)
                        except:
                            pass
                
                if issue_counts:
                    patterns.append({
                        "pattern_type": "validation_issues",
                        "description": "Common validation failures",
                        "top_issues": [{"issue": k, "count": v} for k, v in issue_counts.most_common(5)]
                    })
        
        # Pattern 3: Intent-specific problems
        if 'intent' in df.columns and 'is_valid' in df.columns:
            by_intent = df.groupby('intent')['is_valid'].agg(['sum', 'count']).to_dict('index')
            problematic_intents = []
            for intent, stats in by_intent.items():
                validation_rate = stats['sum'] / stats['count']
                if validation_rate < 0.8:  # Less than 80% validation rate
                    problematic_intents.append({
                        "intent": intent,
                        "validation_rate": round(validation_rate, 3),
                        "failed_count": int(stats['count'] - stats['sum'])
                    })
            
            if problematic_intents:
                patterns.append({
                    "pattern_type": "intent_specific_issues",
                    "description": "Intents with <80% validation rate",
                    "problematic_intents": sorted(problematic_intents, key=lambda x: x['validation_rate'])
                })
        
        return patterns
    
    def extract_successful_patterns(self, df: pd.DataFrame, agent_type: str = "content") -> List[Dict]:
        """
        Extract examples from highly-rated content for few-shot prompting
        
        Args:
            df: Feedback dataframe
            agent_type: "content" or "support"
        
        Returns:
            List of successful examples with context
        """
        if df.empty:
            return []
        
        successful_examples = []
        
        if agent_type == "content":
            # Get approved content
            if 'decision' in df.columns:
                approved = df[df['decision'] == 'approved']
                
                if not approved.empty:
                    # Sample top examples by content type
                    if 'content_type' in approved.columns:
                        for content_type in approved['content_type'].unique():
                            subset = approved[approved['content_type'] == content_type]
                            
                            # Get up to 3 examples per type
                            samples = subset.head(3)
                            
                            for _, row in samples.iterrows():
                                example = {
                                    "content_type": content_type,
                                    "topic": row.get('topic', 'N/A'),
                                    "tone": row.get('tone', 'neutral'),
                                    "headline": row.get('generated_headline', '')[:100],
                                    "body_preview": row.get('generated_body', '')[:200],
                                    "latency_s": row.get('latency_s', 0.0)
                                }
                                successful_examples.append(example)
        
        elif agent_type == "support":
            # Get high-quality replies
            if 'quality_score' in df.columns:
                high_quality = df[df['quality_score'] >= 0.85]
                
                if not high_quality.empty:
                    # Sample by intent
                    if 'intent' in high_quality.columns:
                        for intent in high_quality['intent'].unique():
                            subset = high_quality[high_quality['intent'] == intent]
                            
                            # Get up to 3 examples per intent
                            samples = subset.nlargest(3, 'quality_score')
                            
                            for _, row in samples.iterrows():
                                example = {
                                    "intent": intent,
                                    "message_preview": row.get('message', '')[:100],
                                    "reply_preview": row.get('reply', '')[:200],
                                    "quality_score": row.get('quality_score', 0.0)
                                }
                                successful_examples.append(example)
        
        return successful_examples
    
    def suggest_prompt_improvements(
        self, 
        content_patterns: List[Dict], 
        support_patterns: List[Dict]
    ) -> Dict[str, List[str]]:
        """
        Generate actionable suggestions for prompt template improvements
        
        Args:
            content_patterns: Failure patterns from content generation
            support_patterns: Failure patterns from support replies
        
        Returns:
            Dict mapping template names to improvement suggestions
        """
        suggestions = defaultdict(list)
        
        # Content generation improvements
        for pattern in content_patterns:
            if pattern['pattern_type'] == 'insufficient_content':
                suggestions['blog_generator'].append(
                    f"Add explicit minimum length requirement (currently {pattern['count']} cases of short content)"
                )
                suggestions['product_description'].append(
                    "Emphasize detailed descriptions with specific examples"
                )
            
            elif pattern['pattern_type'] == 'validation_failures':
                for issue in pattern['top_issues'][:3]:
                    suggestions['all_content_templates'].append(
                        f"Address validation issue: {issue['issue']} (occurred {issue['count']} times)"
                    )
            
            elif pattern['pattern_type'] == 'reviewer_concerns':
                # Extract actionable keywords
                keywords = [kw['word'] for kw in pattern['top_keywords'][:5]]
                if any(word in keywords for word in ['generic', 'vague', 'unclear']):
                    suggestions['all_content_templates'].append(
                        "Add instruction for specific, concrete examples rather than generic statements"
                    )
                if any(word in keywords for word in ['tone', 'voice', 'style']):
                    suggestions['all_content_templates'].append(
                        "Strengthen tone guidance with explicit examples of desired voice"
                    )
        
        # Support reply improvements
        for pattern in support_patterns:
            if pattern['pattern_type'] == 'intent_specific_issues':
                for intent_issue in pattern['problematic_intents']:
                    suggestions['reply_generator'].append(
                        f"Improve '{intent_issue['intent']}' intent handling (validation rate: {intent_issue['validation_rate']:.1%})"
                    )
            
            elif pattern['pattern_type'] == 'validation_issues':
                for issue in pattern['top_issues'][:3]:
                    suggestions['reply_generator'].append(
                        f"Add guidance to prevent: {issue['issue']}"
                    )
            
            elif pattern['pattern_type'] == 'low_quality_responses':
                suggestions['reply_generator'].append(
                    f"Review response quality - {pattern['count']} low-scored replies ({pattern['percentage']:.1f}%)"
                )
        
        # Convert defaultdict to regular dict
        return dict(suggestions)
    
    def generate_full_report(self) -> Dict:
        """
        Generate comprehensive analysis report for both agents
        
        Returns:
            Dict with complete analysis including metrics, patterns, and suggestions
        """
        logger.info("🔍 Generating comprehensive feedback analysis report...")
        
        # Load feedback data
        content_df = self.load_content_feedback()
        support_df = self.load_support_feedback()
        
        # Calculate metrics
        content_metrics = self.calculate_content_metrics(content_df)
        support_metrics = self.calculate_support_metrics(support_df)
        
        # Identify failure patterns
        content_failures = self.identify_content_failure_patterns(content_df)
        support_failures = self.identify_support_failure_patterns(support_df)
        
        # Extract successful examples
        content_successes = self.extract_successful_patterns(content_df, agent_type="content")
        support_successes = self.extract_successful_patterns(support_df, agent_type="support")
        
        # Generate improvement suggestions
        improvement_suggestions = self.suggest_prompt_improvements(content_failures, support_failures)
        
        # Build comprehensive report
        report = {
            "report_metadata": {
                "generated_at": datetime.now().isoformat(),
                "content_feedback_entries": len(content_df),
                "support_feedback_entries": len(support_df),
                "analysis_version": "1.0.0"
            },
            "content_generation_agent": {
                "metrics": content_metrics,
                "failure_patterns": content_failures,
                "successful_examples": content_successes[:10]  # Limit to 10
            },
            "customer_support_agent": {
                "metrics": support_metrics,
                "failure_patterns": support_failures,
                "successful_examples": support_successes[:10]
            },
            "improvement_suggestions": improvement_suggestions,
            "summary": {
                "content_approval_rate": content_metrics.get('approval_rate', 0.0),
                "support_validation_rate": support_metrics.get('validation_rate', 0.0),
                "total_patterns_identified": len(content_failures) + len(support_failures),
                "total_suggestions": sum(len(v) for v in improvement_suggestions.values())
            }
        }
        
        logger.info(f"✅ Analysis complete - {report['summary']['total_suggestions']} improvement suggestions generated")
        
        return report
    
    def save_report(self, report: Dict, output_path: str = "logs/feedback_analysis_report.json"):
        """Save analysis report to file"""
        output_file = Path(output_path)
        output_file.parent.mkdir(parents=True, exist_ok=True)
        
        with open(output_file, 'w', encoding='utf-8') as f:
            json.dump(report, f, indent=2, ensure_ascii=False)
        
        logger.info(f"📄 Report saved to: {output_file}")
        return output_file


def analyze_feedback_cli():
    """Command-line interface for feedback analysis"""
    print("\n" + "="*80)
    print("DAY 9: FEEDBACK LEARNING & ANALYSIS")
    print("="*80 + "\n")
    
    analyzer = FeedbackAnalyzer()
    
    print("📊 Generating comprehensive feedback analysis report...\n")
    report = analyzer.generate_full_report()
    
    # Print summary
    print("\n" + "-"*80)
    print("SUMMARY")
    print("-"*80)
    print(f"Content Generation Approval Rate: {report['summary']['content_approval_rate']:.1%}")
    print(f"Support Reply Validation Rate: {report['summary']['support_validation_rate']:.1%}")
    print(f"Patterns Identified: {report['summary']['total_patterns_identified']}")
    print(f"Improvement Suggestions: {report['summary']['total_suggestions']}")
    
    # Print top suggestions
    if report['improvement_suggestions']:
        print("\n" + "-"*80)
        print("TOP IMPROVEMENT SUGGESTIONS")
        print("-"*80)
        for template, suggestions in report['improvement_suggestions'].items():
            print(f"\n{template}:")
            for suggestion in suggestions[:3]:  # Top 3 per template
                print(f"  • {suggestion}")
    
    # Save report
    output_path = analyzer.save_report(report)
    print(f"\n✅ Full report saved to: {output_path}\n")
    
    return report


if __name__ == "__main__":
    analyze_feedback_cli()
