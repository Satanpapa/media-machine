"""
Judge Agent - Final editorial decision maker.
Makes the final approve/reject decision and selects the best variant.
"""

from typing import List, Dict, Optional
from datetime import datetime

from config.settings import config
from utils.database import Database
from utils.llm_client import get_llm_client


class Judge:
    """
    Judge Agent - Final editorial authority.
    
    Decision criteria (MUST ALL be met):
    - Truth >= 8
    - Clarity >= 7
    - Hype >= 6
    
    If no variant passes, returns REJECT with reasoning.
    If multiple pass, selects the best one.
    """
    
    # Minimum thresholds for publication
    MIN_TRUTH = 8.0
    MIN_CLARITY = 7.0
    MIN_HYPE = 6.0
    
    def __init__(self, db: Database, llm_client=None):
        """
        Initialize Judge.
        
        Args:
            db: Database instance for saving decisions
            llm_client: LLM client for complex decisions
        """
        self.db = db
        self.config = config
        self.llm = llm_client
    
    def run(self, critic_output: Dict) -> Dict:
        """
        Make final decision on which variant to publish (or reject all).
        
        Args:
            critic_output: Output from Critic with evaluated variants
            
        Returns:
            Decision dictionary with selected variant or rejection
        """
        topic = critic_output["topic"]
        evaluated_variants = critic_output["evaluated_variants"]
        
        # Find qualifying variants
        qualifying = self._filter_qualifying_variants(evaluated_variants)
        
        if not qualifying:
            # All rejected
            decision = self._make_rejection_decision(critic_output)
        else:
            # Select best from qualifying
            decision = self._select_best_variant(qualifying, critic_output)
        
        # Save to history
        self._save_decision_to_history(decision, evaluated_variants)
        
        return decision
    
    def _filter_qualifying_variants(self, variants: List[Dict]) -> List[Dict]:
        """Filter variants that meet all thresholds."""
        qualifying = []
        
        for variant in variants:
            scores = variant.get("scores", {})
            
            truth = scores.get("truth", 0)
            clarity = scores.get("clarity", 0)
            hype = scores.get("hype", 0)
            
            if (truth >= self.MIN_TRUTH and
                clarity >= self.MIN_CLARITY and
                hype >= self.MIN_HYPE):
                qualifying.append(variant)
        
        return qualifying
    
    def _select_best_variant(
        self,
        qualifying: List[Dict],
        critic_output: Dict
    ) -> Dict:
        """Select the best variant from qualifying candidates."""
        
        # Sort by average score
        sorted_variants = sorted(
            qualifying,
            key=lambda v: v["scores"]["average"],
            reverse=True
        )
        
        best = sorted_variants[0]
        
        return {
            "decision": "APPROVE",
            "topic": critic_output["topic"],
            "selected_variant": best,
            "variant_index": qualifying.index(best),
            "scores": best["scores"],
            "reasoning": f"Selected variant '{best['style']}' with scores: "
                        f"Truth={best['scores']['truth']:.1f}, "
                        f"Clarity={best['scores']['clarity']:.1f}, "
                        f"Hype={best['scores']['hype']:.1f}",
            "alternative_variants": sorted_variants[1:] if len(sorted_variants) > 1 else [],
            "source_urls": critic_output.get("source_urls", []),
            "decided_at": datetime.now().isoformat()
        }
    
    def _make_rejection_decision(self, critic_output: Dict) -> Dict:
        """Create rejection decision with reasoning."""
        
        variants = critic_output["evaluated_variants"]
        
        # Analyze why all failed
        reasons = []
        for variant in variants:
            scores = variant.get("scores", {})
            issues = variant.get("issues", [])
            
            variant_reasons = []
            if scores.get("truth", 0) < self.MIN_TRUTH:
                variant_reasons.append(f"Truth too low ({scores.get('truth', 0):.1f} < {self.MIN_TRUTH})")
            if scores.get("clarity", 0) < self.MIN_CLARITY:
                variant_reasons.append(f"Clarity too low ({scores.get('clarity', 0):.1f} < {self.MIN_CLARITY})")
            if scores.get("hype", 0) < self.MIN_HYPE:
                variant_reasons.append(f"Hype too low ({scores.get('hype', 0):.1f} < {self.MIN_HYPE})")
            
            if issues:
                variant_reasons.extend(issues)
            
            reasons.append(f"Variant '{variant.get('style', 'unknown')}': {'; '.join(variant_reasons)}")
        
        return {
            "decision": "REJECT",
            "topic": critic_output["topic"],
            "selected_variant": None,
            "scores": None,
            "reasoning": "All variants failed to meet quality thresholds.",
            "rejection_details": reasons,
            "source_urls": critic_output.get("source_urls", []),
            "decided_at": datetime.now().isoformat()
        }
    
    def _save_decision_to_history(self, decision: Dict, all_variants: List[Dict]):
        """Save decision to post history for self-improvement."""
        
        topic = decision["topic"]
        judge_decision = decision["decision"].lower()
        
        # Get content from selected variant or first variant
        if decision["selected_variant"]:
            selected = decision["selected_variant"]
            title = selected.get("title", "")
            content = selected.get("content", "")
            selected_idx = decision.get("variant_index", 0)
            
            truth_score = selected.get("scores", {}).get("truth", 0)
            clarity_score = selected.get("scores", {}).get("clarity", 0)
            hype_score = selected.get("scores", {}).get("hype", 0)
            
            rejection_reason = ""
        else:
            # Rejected - use first variant as representative
            if all_variants:
                first = all_variants[0]
                title = first.get("title", topic)
                content = first.get("content", "")
                selected_idx = -1
                
                truth_score = first.get("scores", {}).get("truth", 0)
                clarity_score = first.get("scores", {}).get("clarity", 0)
                hype_score = first.get("scores", {}).get("hype", 0)
                
                rejection_reason = decision.get("reasoning", "")
            else:
                title = topic
                content = ""
                selected_idx = -1
                truth_score = 0
                clarity_score = 0
                hype_score = 0
                rejection_reason = decision.get("reasoning", "")
        
        # Extract all variant contents
        variant_contents = [v.get("content", "") for v in all_variants]
        
        self.db.save_post_history(
            topic=topic,
            title=title,
            content=content,
            variants=variant_contents,
            selected_variant=selected_idx,
            truth_score=truth_score,
            clarity_score=clarity_score,
            hype_score=hype_score,
            judge_decision=judge_decision,
            rejection_reason=rejection_reason
        )
    
    def analyze_performance_and_improve(self) -> Dict:
        """
        Analyze recent posts and generate improvement recommendations.
        
        Called daily to provide self-improvement feedback to Writer.
        
        Returns:
            Dictionary with insights and recommendations
        """
        successful = self.db.get_successful_posts(limit=20)
        failed = self.db.get_failed_posts(limit=20)
        
        insights = {
            "successful_patterns": [],
            "failure_patterns": [],
            "recommendations": []
        }
        
        # Analyze successful posts
        if successful:
            # Check common styles
            style_counts = {}
            for post in successful:
                variants = post.get("variants", "[]")
                # Could parse and analyze patterns
            
            insights["successful_patterns"].append(
                f"Analyzed {len(successful)} successful posts"
            )
            
            # Check average scores
            avg_truth = sum(p.get("truth_score", 0) for p in successful) / len(successful)
            avg_clarity = sum(p.get("clarity_score", 0) for p in successful) / len(successful)
            avg_hype = sum(p.get("hype_score", 0) for p in successful) / len(successful)
            
            insights["successful_patterns"].append(
                f"Successful posts average: Truth={avg_truth:.1f}, Clarity={avg_clarity:.1f}, Hype={avg_hype:.1f}"
            )
        
        # Analyze failed posts
        if failed:
            rejection_reasons = [p.get("rejection_reason", "") for p in failed if p.get("rejection_reason")]
            
            if rejection_reasons:
                insights["failure_patterns"].append(
                    f"Common rejection reasons: {'; '.join(rejection_reasons[:3])}"
                )
        
        # Generate recommendations
        if insights["successful_patterns"]:
            insights["recommendations"].append(
                "Continue current approach - focus on maintaining high truth scores"
            )
        
        if insights["failure_patterns"]:
            insights["recommendations"].append(
                "Address common failure patterns in future content generation"
            )
        
        return {
            "analyzed_at": datetime.now().isoformat(),
            "successful_count": len(successful),
            "failed_count": len(failed),
            "insights": insights
        }
