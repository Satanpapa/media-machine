"""
Hype Optimizer Agent - Content enhancement specialist.
Amplifies headlines and opening paragraphs without adding falsehoods.
"""

from typing import List, Dict, Optional
from datetime import datetime

from config.settings import config
from utils.database import Database
from utils.llm_client import get_llm_client


class HypeOptimizer:
    """
    Hype Optimizer Agent responsible for enhancing content virality.
    
    Enhances:
    - Headlines (makes them more compelling)
    - First paragraph (stronger hook)
    - Adds viral elements (questions, numbers, urgency)
    
    WITHOUT adding lies or misinformation.
    """
    
    def __init__(self, db: Database, llm_client=None):
        """
        Initialize Hype Optimizer.
        
        Args:
            db: Database instance
            llm_client: LLM client for optimization
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
You are a viral content optimizer specializing in maximizing engagement while maintaining 100% truthfulness.

Your enhancements MUST:
✓ Make headlines more compelling and clickable
✓ Strengthen the opening hook
✓ Add urgency, curiosity, or emotional resonance
✓ Include specific numbers when available
✓ Use power words (breaking, shocking, revealed, finally, etc.)

Your enhancements MUST NOT:
✗ Add false information or fabricate facts
✗ Exaggerate beyond what sources support
✗ Use misleading clickbait tactics
✗ Promise something the content doesn't deliver

Balance: High engagement + Complete honesty = Trust + Virality
"""
    
    def run(self, writer_output: Dict) -> Dict:
        """
        Optimize all variants from the Writer.
        
        Args:
            writer_output: Output from Writer agent with variants
            
        Returns:
            Dictionary with optimized variants
        """
        topic = writer_output["topic"]
        variants = writer_output["variants"]
        
        optimized_variants = []
        
        for variant in variants:
            optimized = self._optimize_variant(variant, topic)
            optimized_variants.append(optimized)
        
        return {
            "topic": topic,
            "optimized_variants": optimized_variants,
            "source_urls": writer_output.get("source_urls", []),
            "sources": writer_output.get("sources", []),
            "optimized_at": datetime.now().isoformat()
        }
    
    def _optimize_variant(self, variant: Dict, topic: str) -> Dict:
        """Optimize a single variant."""
        
        original_title = variant.get("title", "")
        original_content = variant.get("content", "")
        style = variant.get("style", "unknown")
        
        if not self.llm:
            # Fallback optimization without LLM
            return self._optimize_fallback(variant)
        
        prompt = f"""
{self.system_prompt}

ORIGINAL TITLE: {original_title}
ORIGINAL CONTENT:
{original_content}

STYLE: {style}

TASK: 
1. Create 2 alternative headlines that are more compelling but 100% truthful
2. Rewrite the first paragraph to be a stronger hook
3. Identify where to add: questions, numbers, or urgency triggers

Respond in this JSON format:
{{
    "headline_options": ["option1", "option2"],
    "enhanced_opening": "rewritten first paragraph",
    "viral_elements_added": ["list of elements added"],
    "explanation": "brief explanation of changes"
}}
"""
        
        try:
            result = self.llm.generate_json(prompt, self.system_prompt)
            
            # Apply optimizations
            headline_options = result.get("headline_options", [original_title])
            enhanced_opening = result.get("enhanced_opening", original_content.split("\n\n")[0])
            
            # Reconstruct content with enhanced opening
            content_parts = original_content.split("\n\n")
            if len(content_parts) > 1:
                enhanced_content = enhanced_opening + "\n\n" + "\n\n".join(content_parts[1:])
            else:
                enhanced_content = enhanced_opening + "\n\n" + original_content[len(enhanced_opening):]
            
            return {
                "style": style,
                "original_title": original_title,
                "headline_options": headline_options[:2],  # Keep top 2 for A/B testing
                "best_headline": headline_options[0] if headline_options else original_title,
                "content": enhanced_content.strip(),
                "original_content": original_content,
                "viral_elements": result.get("viral_elements_added", []),
                "word_count": len(enhanced_content.split())
            }
            
        except Exception as e:
            return self._optimize_fallback(variant)
    
    def _optimize_fallback(self, variant: Dict) -> Dict:
        """Apply basic optimization without LLM."""
        
        original_title = variant.get("title", "")
        original_content = variant.get("content", "")
        style = variant.get("style", "unknown")
        
        # Simple headline enhancements
        headline_options = [original_title]
        
        # Add urgency/curiosity markers based on style
        if "breaking" not in original_title.lower():
            headline_options.append(f"🚨 BREAKING: {original_title}")
        
        if "?" not in original_title:
            headline_options.append(f"{original_title} — What This Really Means")
        
        # Enhance opening with emoji and formatting
        lines = original_content.split("\n")
        if lines and not lines[0].startswith(("🔥", "🚨", "⚡", "💥")):
            lines[0] = "⚡ " + lines[0]
        
        enhanced_content = "\n".join(lines)
        
        return {
            "style": style,
            "original_title": original_title,
            "headline_options": headline_options[:2],
            "best_headline": headline_options[0],
            "content": enhanced_content.strip(),
            "original_content": original_content,
            "viral_elements": ["emoji_enhancement", "alternative_headlines"],
            "word_count": len(enhanced_content.split())
        }
    
    def add_monetization_hook(self, content: str, partner_link: Optional[str] = None) -> str:
        """
        Add a natural monetization hook if partner link exists.
        
        Args:
            content: Post content
            partner_link: Affiliate/partner link to include
            
        Returns:
            Content with optional monetization hook
        """
        if not partner_link:
            return content
        
        # Choose appropriate CTA based on content
        ctas = [
            f"\n\n🎁 Want to dive deeper? Check this out: {partner_link}",
            f"\n\n💡 Pro tip: We found a great resource for this → {partner_link}",
            f"\n\n📌 Helpful tool related to this: {partner_link}",
        ]
        
        # Pick one based on content hash (deterministic but varied)
        cta_index = hash(content) % len(ctas)
        
        return content + ctas[cta_index]
