"""
Day 9: Prompt Management System
Handles prompt template versioning, A/B testing, and performance tracking
"""

import yaml
import json
from pathlib import Path
from typing import Dict, Optional, List, Tuple
from datetime import datetime
from loguru import logger
import pandas as pd
from collections import defaultdict


class PromptManager:
    """
    Manages prompt templates with versioning and performance tracking
    
    Features:
    - Load prompts with version metadata
    - Track performance metrics per template/version
    - A/B testing with traffic splitting
    - Rollback capability
    - Automated prompt improvement suggestions
    """
    
    def __init__(
        self, 
        prompts_dir: str = "prompts",
        metrics_file: str = "data/prompt_metrics.csv"
    ):
        self.prompts_dir = Path(prompts_dir)
        self.metrics_file = Path(metrics_file)
        self._loaded_prompts = {}
        self._metrics_cache = None
    
    def load_prompt(
        self, 
        template_name: str, 
        version: str = "latest"
    ) -> Optional[Dict]:
        """
        Load prompt template with version support
        
        Args:
            template_name: Template name (e.g., "reply_generator")
            version: Version string or "latest" for current version
        
        Returns:
            Prompt template dict with metadata
        """
        # Build file path
        template_path = self.prompts_dir / f"{template_name}.yaml"
        
        if not template_path.exists():
            logger.error(f"Prompt template not found: {template_path}")
            return None
        
        try:
            with open(template_path, 'r', encoding='utf-8') as f:
                prompt_data = yaml.safe_load(f)
            
            # Add metadata if missing
            if 'version' not in prompt_data:
                prompt_data['version'] = '1.0.0'
            
            if 'last_updated' not in prompt_data:
                prompt_data['last_updated'] = datetime.now().isoformat()
            
            # Cache loaded prompt
            cache_key = f"{template_name}:{prompt_data['version']}"
            self._loaded_prompts[cache_key] = prompt_data
            
            logger.info(f"✅ Loaded prompt: {template_name} v{prompt_data['version']}")
            
            return prompt_data
            
        except Exception as e:
            logger.error(f"Error loading prompt {template_name}: {e}")
            return None
    
    def save_prompt_version(
        self, 
        template_name: str, 
        prompt_data: Dict, 
        version: str,
        changelog: Optional[str] = None
    ) -> bool:
        """
        Save new version of prompt template
        
        Args:
            template_name: Template name
            prompt_data: Prompt content dict
            version: Version string (e.g., "1.1.0")
            changelog: Description of changes
        
        Returns:
            True if successful
        """
        template_path = self.prompts_dir / f"{template_name}.yaml"
        
        # Create backup of current version
        if template_path.exists():
            backup_dir = self.prompts_dir / "versions" / template_name
            backup_dir.mkdir(parents=True, exist_ok=True)
            
            # Load current version
            with open(template_path, 'r') as f:
                current = yaml.safe_load(f)
            
            current_version = current.get('version', '1.0.0')
            backup_path = backup_dir / f"v{current_version}.yaml"
            
            with open(backup_path, 'w', encoding='utf-8') as f:
                yaml.dump(current, f, sort_keys=False, allow_unicode=True)
            
            logger.info(f"📦 Backed up {template_name} v{current_version}")
        
        # Update metadata
        prompt_data['version'] = version
        prompt_data['last_updated'] = datetime.now().isoformat()
        
        if changelog:
            if 'changelog' not in prompt_data:
                prompt_data['changelog'] = []
            prompt_data['changelog'].append({
                "version": version,
                "date": datetime.now().isoformat(),
                "changes": changelog
            })
        
        # Save new version
        try:
            with open(template_path, 'w', encoding='utf-8') as f:
                yaml.dump(prompt_data, f, sort_keys=False, allow_unicode=True)
            
            logger.info(f"✅ Saved {template_name} v{version}")
            return True
            
        except Exception as e:
            logger.error(f"Error saving prompt version: {e}")
            return False
    
    def load_metrics(self) -> pd.DataFrame:
        """Load prompt performance metrics"""
        if not self.metrics_file.exists():
            # Create empty metrics file
            df = pd.DataFrame(columns=[
                'timestamp', 'template_name', 'version', 'content_type',
                'total_uses', 'approved_count', 'rejected_count', 'edited_count',
                'avg_quality_score', 'avg_latency_s', 'approval_rate'
            ])
            self.metrics_file.parent.mkdir(parents=True, exist_ok=True)
            df.to_csv(self.metrics_file, index=False)
            return df
        
        try:
            df = pd.read_csv(self.metrics_file)
            self._metrics_cache = df
            return df
        except Exception as e:
            logger.error(f"Error loading metrics: {e}")
            return pd.DataFrame()
    
    def log_prompt_usage(
        self,
        template_name: str,
        version: str,
        content_type: Optional[str] = None,
        outcome: str = "unknown",  # approved/rejected/edited
        quality_score: float = 0.0,
        latency_s: float = 0.0
    ):
        """
        Log prompt template usage for performance tracking
        
        Args:
            template_name: Template name
            version: Version string
            content_type: Content type (blog, support_reply, etc.)
            outcome: approved/rejected/edited
            quality_score: Quality score (0-1)
            latency_s: Generation latency
        """
        # Load existing metrics
        df = self.load_metrics()
        
        # Create new entry
        new_entry = pd.DataFrame([{
            'timestamp': datetime.now().isoformat(),
            'template_name': template_name,
            'version': version,
            'content_type': content_type or 'unknown',
            'outcome': outcome,
            'quality_score': quality_score,
            'latency_s': latency_s
        }])
        
        # Append and save
        df = pd.concat([df, new_entry], ignore_index=True)
        df.to_csv(self.metrics_file, index=False)
    
    def get_template_metrics(
        self, 
        template_name: str, 
        version: Optional[str] = None,
        days: int = 30
    ) -> Dict:
        """
        Get performance metrics for a template
        
        Args:
            template_name: Template name
            version: Specific version or None for all versions
            days: Number of days to analyze
        
        Returns:
            Metrics dict with approval rates, latency, etc.
        """
        df = self.load_metrics()
        
        if df.empty:
            return {"error": "No metrics available"}
        
        # Filter by template
        mask = df['template_name'] == template_name
        if version:
            mask &= df['version'] == version
        
        # Filter by date
        if 'timestamp' in df.columns:
            df['timestamp'] = pd.to_datetime(df['timestamp'])
            cutoff = pd.Timestamp.now() - pd.Timedelta(days=days)
            mask &= df['timestamp'] >= cutoff
        
        filtered = df[mask]
        
        if filtered.empty:
            return {"error": f"No data for {template_name}"}
        
        # Calculate metrics
        if 'outcome' in filtered.columns:
            outcomes = filtered['outcome'].value_counts().to_dict()
            total = len(filtered)
            approval_rate = (
                outcomes.get('approved', 0) + outcomes.get('edited', 0)
            ) / total if total > 0 else 0.0
        else:
            outcomes = {}
            approval_rate = 0.0
        
        metrics = {
            "template_name": template_name,
            "version": version or "all",
            "period_days": days,
            "total_uses": len(filtered),
            "outcomes": outcomes,
            "approval_rate": round(approval_rate, 3),
            "avg_quality_score": round(filtered['quality_score'].mean(), 3) if 'quality_score' in filtered.columns else 0.0,
            "avg_latency_s": round(filtered['latency_s'].mean(), 3) if 'latency_s' in filtered.columns else 0.0
        }
        
        # By content type breakdown
        if 'content_type' in filtered.columns:
            by_type = {}
            for ctype in filtered['content_type'].unique():
                subset = filtered[filtered['content_type'] == ctype]
                type_outcomes = subset['outcome'].value_counts().to_dict() if 'outcome' in subset.columns else {}
                by_type[ctype] = {
                    "total": len(subset),
                    "outcomes": type_outcomes,
                    "avg_quality": round(subset['quality_score'].mean(), 3) if 'quality_score' in subset.columns else 0.0
                }
            metrics["by_content_type"] = by_type
        
        return metrics
    
    def compare_versions(
        self, 
        template_name: str, 
        version1: str, 
        version2: str,
        days: int = 30
    ) -> Dict:
        """
        Compare performance between two versions
        
        Returns:
            Comparison dict with metrics for both versions
        """
        v1_metrics = self.get_template_metrics(template_name, version1, days)
        v2_metrics = self.get_template_metrics(template_name, version2, days)
        
        comparison = {
            "template_name": template_name,
            "version1": {
                "version": version1,
                "metrics": v1_metrics
            },
            "version2": {
                "version": version2,
                "metrics": v2_metrics
            }
        }
        
        # Calculate deltas
        if "approval_rate" in v1_metrics and "approval_rate" in v2_metrics:
            comparison["approval_rate_delta"] = round(
                v2_metrics["approval_rate"] - v1_metrics["approval_rate"], 3
            )
        
        if "avg_latency_s" in v1_metrics and "avg_latency_s" in v2_metrics:
            comparison["latency_delta_s"] = round(
                v2_metrics["avg_latency_s"] - v1_metrics["avg_latency_s"], 3
            )
        
        return comparison
    
    def get_all_templates(self) -> List[Dict]:
        """
        Get list of all available prompt templates with metadata
        
        Returns:
            List of template info dicts
        """
        templates = []
        
        if not self.prompts_dir.exists():
            return templates
        
        for yaml_file in self.prompts_dir.glob("*.yaml"):
            if yaml_file.stem == "intent_classifier":  # Skip non-generation prompts
                continue
            
            try:
                with open(yaml_file, 'r', encoding='utf-8') as f:
                    data = yaml.safe_load(f)
                
                templates.append({
                    "name": yaml_file.stem,
                    "version": data.get('version', '1.0.0'),
                    "last_updated": data.get('last_updated', 'unknown'),
                    "description": data.get('description', 'No description')
                })
            except Exception as e:
                logger.warning(f"Could not load template {yaml_file}: {e}")
        
        return templates
    
    def apply_improvement_suggestions(
        self,
        template_name: str,
        suggestions: List[str],
        auto_apply: bool = False
    ) -> Dict:
        """
        Apply improvement suggestions to a prompt template
        
        Args:
            template_name: Template to improve
            suggestions: List of improvement suggestions
            auto_apply: If True, automatically save changes (use with caution!)
        
        Returns:
            Dict with proposed changes
        """
        current_prompt = self.load_prompt(template_name)
        
        if not current_prompt:
            return {"error": f"Template {template_name} not found"}
        
        # Build improvement plan
        improvements = {
            "template": template_name,
            "current_version": current_prompt.get('version', '1.0.0'),
            "suggestions": suggestions,
            "proposed_changes": []
        }
        
        # Analyze suggestions and propose specific changes
        system_instructions = current_prompt.get('system_instructions', '')
        
        for suggestion in suggestions:
            suggestion_lower = suggestion.lower()
            
            # Pattern: Add minimum length requirement
            if 'minimum length' in suggestion_lower or 'short content' in suggestion_lower:
                improvements["proposed_changes"].append({
                    "type": "add_instruction",
                    "location": "system_instructions",
                    "change": "Add explicit length requirement: 'Generate at least 300 words of detailed content.'"
                })
            
            # Pattern: Address validation issues
            if 'validation issue' in suggestion_lower or 'validation failure' in suggestion_lower:
                improvements["proposed_changes"].append({
                    "type": "add_validation_check",
                    "location": "system_instructions",
                    "change": f"Add validation guidance: {suggestion}"
                })
            
            # Pattern: Improve tone/style
            if 'tone' in suggestion_lower or 'voice' in suggestion_lower:
                improvements["proposed_changes"].append({
                    "type": "enhance_tone_guidance",
                    "location": "system_instructions",
                    "change": "Add specific tone examples and voice guidelines"
                })
            
            # Pattern: Intent-specific improvements
            if 'intent' in suggestion_lower:
                improvements["proposed_changes"].append({
                    "type": "improve_intent_handling",
                    "location": "intent_guidelines or prompt_pattern",
                    "change": suggestion
                })
        
        # If auto_apply enabled, create new version
        if auto_apply and improvements["proposed_changes"]:
            logger.warning(f"⚠️ Auto-applying improvements to {template_name} (use with caution!)")
            
            # Increment version
            current_version = current_prompt.get('version', '1.0.0')
            major, minor, patch = map(int, current_version.split('.'))
            new_version = f"{major}.{minor + 1}.0"
            
            # Create changelog
            changelog = f"Auto-applied {len(improvements['proposed_changes'])} improvements from feedback analysis"
            
            # Note: Actual prompt modification would require more sophisticated logic
            # For safety, we just log the intent here
            logger.info(f"Would create version {new_version} with {len(improvements['proposed_changes'])} changes")
            improvements["new_version"] = new_version
            improvements["auto_applied"] = False  # Set to True when actually implemented
        
        return improvements
    
    def rollback_to_version(
        self, 
        template_name: str, 
        target_version: str
    ) -> bool:
        """
        Rollback template to a previous version
        
        Args:
            template_name: Template name
            target_version: Version to rollback to
        
        Returns:
            True if successful
        """
        backup_path = self.prompts_dir / "versions" / template_name / f"v{target_version}.yaml"
        
        if not backup_path.exists():
            logger.error(f"Backup version not found: {backup_path}")
            return False
        
        try:
            # Load backup version
            with open(backup_path, 'r', encoding='utf-8') as f:
                backup_data = yaml.safe_load(f)
            
            # Save current version as backup first
            current_path = self.prompts_dir / f"{template_name}.yaml"
            if current_path.exists():
                with open(current_path, 'r', encoding='utf-8') as f:
                    current_data = yaml.safe_load(f)
                
                current_version = current_data.get('version', '1.0.0')
                rollback_backup = self.prompts_dir / "versions" / template_name / f"v{current_version}_pre_rollback.yaml"
                
                with open(rollback_backup, 'w', encoding='utf-8') as f:
                    yaml.dump(current_data, f, sort_keys=False, allow_unicode=True)
            
            # Restore backup
            with open(current_path, 'w', encoding='utf-8') as f:
                yaml.dump(backup_data, f, sort_keys=False, allow_unicode=True)
            
            logger.info(f"✅ Rolled back {template_name} to version {target_version}")
            return True
            
        except Exception as e:
            logger.error(f"Rollback failed: {e}")
            return False


def update_prompt_with_feedback(template_name: str, feedback_report: Dict) -> Dict:
    """
    Utility function to update a prompt based on feedback analysis
    
    Args:
        template_name: Template to update
        feedback_report: Feedback analysis report from FeedbackAnalyzer
    
    Returns:
        Update result dict
    """
    manager = PromptManager()
    
    # Extract suggestions for this template
    suggestions = feedback_report.get('improvement_suggestions', {}).get(template_name, [])
    
    if not suggestions:
        return {"status": "no_suggestions", "template": template_name}
    
    # Apply improvements (manual review recommended)
    result = manager.apply_improvement_suggestions(
        template_name,
        suggestions,
        auto_apply=False  # Set to True for automatic updates (risky!)
    )
    
    return result


if __name__ == "__main__":
    print("\n=== Testing Prompt Manager ===\n")
    
    manager = PromptManager()
    
    # List all templates
    print("1. Available templates:")
    templates = manager.get_all_templates()
    for tmpl in templates:
        print(f"   - {tmpl['name']} (v{tmpl['version']})")
    
    # Load a template
    print("\n2. Loading reply_generator template...")
    prompt = manager.load_prompt("reply_generator")
    if prompt:
        print(f"   Version: {prompt.get('version', 'unknown')}")
        print(f"   Last updated: {prompt.get('last_updated', 'unknown')}")
    
    # Get metrics
    print("\n3. Getting template metrics...")
    metrics = manager.get_template_metrics("reply_generator", days=30)
    if "error" not in metrics:
        print(f"   Total uses: {metrics.get('total_uses', 0)}")
        print(f"   Approval rate: {metrics.get('approval_rate', 0):.1%}")
    else:
        print(f"   {metrics['error']}")
    
    print("\n✅ Prompt manager tests complete!\n")
