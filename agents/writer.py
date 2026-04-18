"""
Writer Agent - Content generation specialist.
Generates 3 different variants of posts based on trends.
"""

from typing import List, Dict, Optional
from datetime import datetime

from config.settings import config
from utils.database import Database
from utils.llm_client import get_llm_client


class Writer:
    """
    Writer Agent responsible for generating viral content.
    
    Generates 3 different variants per topic:
    1. Direct & Factual
    2. Story-driven & Emotional
    3. Question-based & Engaging
    
    Style: short, punchy, honest, no fabrication
    """
    
    def __init__(self, db: Database, llm_client=None):
        """
        Initialize Writer.
        
        Args:
            db: Database instance for accessing post history
            llm_client: LLM client for generation
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
        
        # System prompt for consistent style
        self.system_prompt = """
You are a professional content writer for a popular Telegram channel.
Your writing style:
- Short, punchy sentences (max 2-3 lines per paragraph)
- Honest and factual - never fabricate information
- Engaging but not clickbait
- Use emojis sparingly (1-2 per post max)
- Include concrete numbers and specifics when available
- End with a thought-provoking question or call-to-action when appropriate

Target audience: Tech-savvy professionals interested in innovation, business, and trends.
Post length: 150-300 words total.
"""
    
    def run(self, trend_data: Dict) -> Dict:
        """
        Generate 3 post variants for a given trend.
        
        Args:
            trend_data: Trend information from TrendDetector
            
        Returns:
            Dictionary with topic, variants, and metadata
        """
        topic = trend_data["topic"]
        urls = trend_data.get("urls", [])
        sources = trend_data.get("sources", [])
        
        # Get context from successful past posts
        successful_posts = self.db.get_successful_posts(limit=10)
        style_context = self._extract_style_patterns(successful_posts)
        
        # Generate 3 variants
        variants = []
        
        # Variant 1: Direct & Factual
        variant1 = self._generate_variant(
            topic, urls, sources, style_context,
            style="direct_factual"
        )
        variants.append(variant1)
        
        # Variant 2: Story-driven
        variant2 = self._generate_variant(
            topic, urls, sources, style_context,
            style="story_driven"
        )
        variants.append(variant2)
        
        # Variant 3: Question-based
        variant3 = self._generate_variant(
            topic, urls, sources, style_context,
            style="question_based"
        )
        variants.append(variant3)
        
        return {
            "topic": topic,
            "variants": variants,
            "source_urls": urls,
            "sources": sources,
            "generated_at": datetime.now().isoformat(),
            "style_context": style_context
        }
    
    def _extract_style_patterns(self, successful_posts: List[Dict]) -> str:
        """Extract patterns from successful posts for style guidance."""
        if not successful_posts:
            return "No historical data available. Use best practices."
        
        patterns = []
        
        # Analyze common elements
        titles = [p.get("title", "") for p in successful_posts if p.get("title")]
        
        if titles:
            avg_length = sum(len(t) for t in titles) / len(titles)
            patterns.append(f"Successful titles average {avg_length:.0f} characters")
            
            # Check for questions
            question_count = sum(1 for t in titles if "?" in t)
            if question_count > len(titles) / 2:
                patterns.append("Questions perform well in headlines")
        
        return "; ".join(patterns) if patterns else "Use engaging, concise style."
    
    def _generate_variant(
        self,
        topic: str,
        urls: List[str],
        sources: List[str],
        style_context: str,
        style: str = "direct_factual"
    ) -> Dict:
        """Generate a single post variant."""
        
        style_prompts = {
            "direct_factual": """
Write a DIRECT & FACTUAL post variant:
- Lead with the most important fact
- Use clear, unambiguous language
- Include specific numbers and data points
- Minimal emotional language
- Structure: Fact → Context → Implication
""",
            "story_driven": """
Write a STORY-DRIVEN post variant:
- Start with a relatable scenario or surprising moment
- Build narrative tension
- Humanize the technology/trend
- Structure: Hook → Story → Lesson/Takeaway
""",
            "question_based": """
Write a QUESTION-BASED post variant:
- Open with a provocative but honest question
- Present the information as an answer/exploration
- End with another thought-provoking question
- Structure: Question → Evidence → New Question
"""
        }
        
        if not self.llm:
            # Fallback without LLM
            return self._generate_fallback_variant(topic, urls, style)
        
        prompt = f"""
{self.system_prompt}

{style_prompts.get(style, style_prompts["direct_factual"])}

TOPIC: {topic}
SOURCES: {', '.join(sources)}
REFERENCE URLs: {', '.join(urls[:3]) if urls else 'No URLs provided'}

STYLE GUIDANCE: {style_context}

IMPORTANT RULES:
1. NEVER fabricate facts, quotes, or statistics
2. If you don't know something, say so or skip it
3. Base everything on the topic and sources provided
4. Keep it under 300 words
5. Format for Telegram (short paragraphs, line breaks)

Generate the post now:
"""
        
        try:
            content = self.llm.generate(prompt, self.system_prompt)
            
            # Extract title (first line or generate separately)
            title = self._extract_title(content, topic)
            
            return {
                "style": style,
                "title": title,
                "content": content.strip(),
                "word_count": len(content.split())
            }
        except Exception as e:
            return self._generate_fallback_variant(topic, urls, style)
    
    def _extract_title(self, content: str, topic: str) -> str:
        """Extract or generate a title from content."""
        lines = content.strip().split("\n")
        
        # First line might be the title
        if lines and len(lines[0]) < 100:
            return lines[0].strip("#* ")
        
        # Generate from topic
        return topic[:80]
    
    def _generate_fallback_variant(
        self, topic: str, urls: List[str], style: str
    ) -> Dict:
        """Generate a basic variant without LLM."""
        
        templates = {
            "direct_factual": f"""
🔥 BREAKING: {topic}

Key developments emerging around this topic. Multiple sources reporting significant activity.

What we know:
• Major developments underway
• Multiple credible sources confirming
• Situation evolving rapidly

Stay tuned for updates.

Sources: {', '.join(urls[:2]) if urls else 'Multiple'}
""",
            "story_driven": f"""
Remember when {topic.split()[0] if topic.split() else 'everything'} seemed impossible?

Well, things just changed dramatically.

{topic}

This isn't just another headline – it's a signal that the landscape is shifting beneath our feet.

The question is: are you ready for what comes next?
""",
            "question_based": f"""
Is {topic} the beginning of something huge?

Here's what caught our attention:
→ Multiple sources reporting major developments
→ Rapid acceleration in recent days
→ Real-world implications becoming clear

What do you think this means for the industry?

Drop your thoughts below 👇
"""
        }
        
        content = templates.get(style, templates["direct_factual"])
        
        return {
            "style": style,
            "title": topic[:80],
            "content": content.strip(),
            "word_count": len(content.split())
        }
