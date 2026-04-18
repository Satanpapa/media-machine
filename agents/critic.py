"""
Critic Agent - Strict fact-checker and quality controller.
Evaluates content for truthfulness, clarity, and appropriate hype level.
"""

from typing import List, Dict, Optional, Tuple
from datetime import datetime

from config.settings import config
from utils.database import Database
from utils.llm_client import get_llm_client


class Critic:
    """
    Critic Agent responsible for rigorous fact-checking.
    
    Evaluates each variant on three metrics (1-10 scale):
    - Truth: Is everything factually accurate?
    - Clarity: Is the message clear and understandable?
    - Hype: Is it engaging without being clickbait?
    
    Rejects content with:
    - Fabricated facts or quotes
    - Misleading claims
    - Excessive clickbait
    """
    
    def __init__(self, db: Database, llm_client=None):
        """
        Initialize Critic.
        
        Args:
            db: Database instance
            llm_client: LLM client for evaluation
        """
        self.db = db
        self.config = config
        
        if llm_client is None and config.is_llm_configured:
            self.llm = get_llm_client(
                config.llm_provider,
                getattr(config, f"{config.llm_provider}_api_key"),
                config.llm_model
            )
        else:
            self.llm = llm_client
        
        self.system_prompt = """
You are a strict fact-checker and content critic for a professional media outlet.

Your role is to evaluate content on three dimensions:

1. TRUTH (1-10):
   - 10: Every claim is verifiable and accurate
   - 7-9: Minor ambiguities but no falsehoods
   - 4-6: Some unsupported claims or exaggerations
   - 1-3: Contains fabrications or serious misinformation
   
2. CLARITY (1-10):
   - 10: Crystal clear, anyone can understand
   - 7-9: Clear with minor confusion points
   - 4-6: Some confusing passages
   - 1-3: Muddled, hard to follow
   
3. HYPE (1-10):
   - 10: Perfectly engaging without crossing into clickbait
   - 7-9: Engaging with slight over-promising
   - 4-6: Either too dry OR too sensational
   - 1-3: Extreme clickbait or completely boring

CRITICAL RULES:
- Compare content against provided source URLs/topics
- Flag ANY fabricated quotes, statistics, or claims
- Detect misleading implications even if technically true
- Be harsh on clickbait that promises more than delivered
"""
    
    def run(self, hype_output: Dict) -> Dict:
        """
        Evaluate all optimized variants.
        
        Args:
            hype_output: Output from HypeOptimizer
            
        Returns:
            Dictionary with evaluated variants and scores
        """
        topic = hype_output["topic"]
        variants = hype_output["optimized_variants"]
        source_urls = hype_output.get("source_urls", [])
        
        evaluated_variants = []
        
        for variant in variants:
            evaluation = self._evaluate_variant(variant, topic, source_urls)
            evaluated_variants.append(evaluation)
        
        return {
            "topic": topic,
            "evaluated_variants": evaluated_variants,
            "source_urls": source_urls,
            "evaluated_at": datetime.now().isoformat()
        }
    
    def _evaluate_variant(
        self,
        variant: Dict,
        topic: str,
        source_urls: List[str]
    ) -> Dict:
        """Evaluate a single variant."""
        
        title = variant.get("best_headline", variant.get("original_title", ""))
        content = variant.get("content", "")
        style = variant.get("style", "unknown")
        
        if not self.llm:
            # Fallback evaluation without LLM
            return self._evaluate_fallback(variant, topic)
        
        prompt = f"""
{self.system_prompt}

TOPIC: {topic}
SOURCE URLS: {', '.join(source_urls) if source_urls else 'No specific URLs provided'}

CONTENT TO EVALUATE:
TITLE: {title}

{content}

TASK:
Carefully evaluate this content and respond in JSON format:

{{
    "truth_score": <number 1-10>,
    "truth_reasoning": "<explanation>",
    "clarity_score": <number 1-10>,
    "clarity_reasoning": "<explanation>",
    "hype_score": <number 1-10>,
    "hype_reasoning": "<explanation>",
    "issues_found": ["list of any problems: fabrications, misleading claims, excessive clickbait"],
    "recommendation": "approve" or "reject",
    "rejection_reason": "<if rejected, explain why>"
}}

Be extremely strict on truth. Any fabrication = automatic rejection.
"""
        
        try:
            result = self.llm.generate_json(prompt, self.system_prompt)
            
            truth_score = float(result.get("truth_score", 5))
            clarity_score = float(result.get("clarity_score", 5))
            hype_score = float(result.get("hype_score", 5))
            
            return {
                "style": style,
                "title": title,
                "content": content,
                "scores": {
                    "truth": truth_score,
                    "clarity": clarity_score,
                    "hype": hype_score,
                    "average": (truth_score + clarity_score + hype_score) / 3
                },
                "reasoning": {
                    "truth": result.get("truth_reasoning", ""),
                    "clarity": result.get("clarity_reasoning", ""),
                    "hype": result.get("hype_reasoning", "")
                },
                "issues": result.get("issues_found", []),
                "recommendation": result.get("recommendation", "reject"),
                "rejection_reason": result.get("rejection_reason", "")
            }
            
        except Exception as e:
            return self._evaluate_fallback(variant, topic)
    
    def _evaluate_fallback(self, variant: Dict, topic: str) -> Dict:
        """Basic evaluation without LLM."""
        
        title = variant.get("best_headline", "")
        content = variant.get("content", "")
        style = variant.get("style", "unknown")
        
        # Simple heuristics
        issues = []
        
        # Check for excessive capitalization
        if title.isupper() and len(title) > 10:
            issues.append("Excessive capitalization in title")
        
        # Check for too many emojis
        emoji_count = sum(1 for c in content if c in '🔥🚨⚡💥😱🤯')
        if emoji_count > 5:
            issues.append("Too many emojis")
        
        # Check for clickbait phrases
        clickbait_phrases = ["you won't believe", "shocking", "mind-blowing"]
        for phrase in clickbait_phrases:
            if phrase.lower() in content.lower():
                issues.append(f"Clickbait phrase detected: '{phrase}'")
        
        # Assign scores based on issues
        base_score = 7.0
        penalty = len(issues) * 1.5
        
        truth_score = max(5.0, base_score)  # Assume truth without sources
        clarity_score = max(4.0, base_score - (penalty / 2))
        hype_score = max(4.0, base_score - (penalty / 3))
        
        recommendation = "approve" if len(issues) <= 1 else "reject"
        
        return {
            "style": style,
            "title": title,
            "content": content,
            "scores": {
                "truth": truth_score,
                "clarity": clarity_score,
                "hype": hype_score,
                "average": (truth_score + clarity_score + hype_score) / 3
            },
            "reasoning": {
                "truth": "No sources to verify against, assuming neutral",
                "clarity": "Basic readability check passed" if clarity_score > 5 else "Some clarity issues detected",
                "hype": "Moderate engagement level"
            },
            "issues": issues,
            "recommendation": recommendation,
            "rejection_reason": "; ".join(issues) if issues else ""
        }
    
    def get_best_variant(self, evaluated_variants: List[Dict]) -> Optional[Dict]:
        """
        Select the best variant based on scores.
        
        Criteria:
        - Truth >= 8
        - Clarity >= 7
        - Hype >= 6
        
        Returns None if no variant meets criteria.
        """
        qualifying = []
        
        for variant in evaluated_variants:
            scores = variant.get("scores", {})
            
            if (scores.get("truth", 0) >= 8 and
                scores.get("clarity", 0) >= 7 and
                scores.get("hype", 0) >= 6):
                qualifying.append(variant)
        
        if not qualifying:
            return None
        
        # Return the one with highest average score
        return max(qualifying, key=lambda v: v["scores"]["average"])
