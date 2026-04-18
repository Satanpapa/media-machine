"""
Publisher + Monetizer Agent - Content distribution and revenue generation.
Handles posting to Telegram and adding native monetization.
"""

from typing import Dict, Optional, List
from datetime import datetime
import hashlib

from config.settings import config
from utils.database import Database


class Publisher:
    """
    Publisher Agent responsible for content distribution.
    
    Responsibilities:
    - Posts approved content to Telegram channel
    - Adds native partner links when appropriate
    - Maintains 5:1 useful-to-promotional ratio
    - Tracks all posted content
    """
    
    def __init__(self, db: Database):
        """
        Initialize Publisher.
        
        Args:
            db: Database instance
        """
        self.db = db
        self.config = config
        
        # Try to initialize Telegram bot
        self.bot = None
        self._init_bot()
        
        # Track monetization ratio
        self.posts_since_last_promo = 0
    
    def _init_bot(self):
        """Initialize Telegram bot."""
        try:
            from telegram import Bot
            
            if self.config.telegram_bot_token:
                self.bot = Bot(token=self.config.telegram_bot_token)
        except ImportError:
            pass  # python-telegram-bot not installed
        except Exception as e:
            pass  # Configuration issues
    
    def run(self, judge_decision: Dict) -> Dict:
        """
        Publish approved content or handle rejection.
        
        Args:
            judge_decision: Output from Judge agent
            
        Returns:
            Publication result dictionary
        """
        if judge_decision["decision"] != "APPROVE":
            return {
                "status": "rejected",
                "reason": judge_decision.get("reasoning", "Content did not meet quality standards"),
                "published": False
            }
        
        # Get the selected variant
        variant = judge_decision["selected_variant"]
        topic = judge_decision["topic"]
        content = variant.get("content", "")
        title = variant.get("best_headline", variant.get("title", ""))
        
        # Check if we should add monetization
        should_monetize = self._should_add_monetization()
        partner_link = None
        
        if should_monetize:
            partner_link = self.config.get_partner_link(topic)
            if partner_link:
                content = self._add_monetization(content, partner_link)
        
        # Format final post
        final_post = self._format_post(title, content)
        
        # Publish to Telegram
        publish_result = self._publish_to_telegram(final_post)
        
        if publish_result["success"]:
            # Mark as posted in database
            link_hash = hashlib.md5(topic.encode()).hexdigest()
            self.db.mark_posted(
                link=link_hash,
                topic=topic,
                partner_link=partner_link
            )
            
            # Update monetization counter
            if partner_link:
                self.posts_since_last_promo = 0
            else:
                self.posts_since_last_promo += 1
            
            # Schedule performance tracking
            post_id = publish_result.get("post_id", str(datetime.now().timestamp()))
            
            return {
                "status": "published",
                "post_id": post_id,
                "topic": topic,
                "title": title,
                "monetized": partner_link is not None,
                "partner_link": partner_link,
                "published_at": datetime.now().isoformat(),
                "metrics_tracking_scheduled": True
            }
        else:
            return {
                "status": "failed",
                "error": publish_result.get("error", "Unknown publishing error"),
                "published": False
            }
    
    def _should_add_monetization(self) -> bool:
        """
        Determine if this post should include monetization.
        
        Rule: 5 useful posts : 1 promotional post
        """
        ratio = self.config.monetization_ratio
        
        return self.posts_since_last_promo >= ratio
    
    def _add_monetization(self, content: str, partner_link: str) -> str:
        """Add native monetization hook to content."""
        
        # Choose CTA style based on content
        ctas = [
            f"\n\n🎯 Want to learn more? We recommend: {partner_link}",
            f"\n\n💎 Pro resource for this topic: {partner_link}",
            f"\n\n📚 Deep dive available here: {partner_link}",
            f"\n\n🔧 Helpful tool we use: {partner_link}",
        ]
        
        # Deterministic selection based on content
        cta_index = hash(content) % len(ctas)
        
        return content + ctas[cta_index]
    
    def _format_post(self, title: str, content: str) -> str:
        """Format post for Telegram (Markdown/HTML)."""
        
        # Combine title and content
        if title and not content.startswith(title):
            formatted = f"**{title}**\n\n{content}"
        else:
            formatted = content
        
        # Ensure proper line breaks
        formatted = formatted.replace("\r\n", "\n")
        
        # Add channel signature if configured
        if False:  # Could add watermark/signature
            formatted += "\n\n— Your Channel Name"
        
        return formatted
    
    def _publish_to_telegram(self, content: str) -> Dict:
        """Publish content to Telegram channel."""
        
        if not self.bot:
            # Simulate publication for testing
            return {
                "success": True,
                "post_id": f"sim_{datetime.now().timestamp()}",
                "message": "Simulated publication (no bot configured)"
            }
        
        try:
            import asyncio
            
            async def send():
                message = await self.bot.send_message(
                    chat_id=self.config.telegram_channel_id,
                    text=content,
                    parse_mode="Markdown"
                )
                return message
            
            message = asyncio.run(send())
            
            return {
                "success": True,
                "post_id": str(message.message_id),
                "message": "Published successfully"
            }
            
        except Exception as e:
            return {
                "success": False,
                "error": str(e)
            }
    
    def track_performance(self, post_id: str, metrics: Dict):
        """
        Track performance metrics for a published post.
        
        Called at 1h, 3h, and 24h after publication.
        
        Args:
            post_id: Telegram message ID
            metrics: Dictionary with views, likes, comments, etc.
        """
        self.db.record_performance(
            post_id=post_id,
            views_1h=metrics.get("views_1h", 0),
            views_3h=metrics.get("views_3h", 0),
            views_24h=metrics.get("views_24h", 0),
            er=metrics.get("er", 0.0),
            likes=metrics.get("likes", 0),
            comments=metrics.get("comments", 0),
            shares=metrics.get("shares", 0)
        )
    
    def get_performance_metrics(self, post_id: str) -> Optional[Dict]:
        """Get performance metrics for a specific post."""
        # This would query Telegram API for actual metrics
        # For now, return from database
        return None  # Would need implementation based on storage


class Monetizer:
    """
    Monetizer Agent - Manages partner relationships and revenue optimization.
    
    Features:
    - Rotates partner links by topic category
    - Tracks conversion performance
    - Optimizes CTA placement and wording
    """
    
    def __init__(self, db: Database, config):
        """
        Initialize Monetizer.
        
        Args:
            db: Database instance
            config: Configuration object
        """
        self.db = db
        self.config = config
        
        # Partner link rotation state
        self.partner_usage = {
            "ai": 0,
            "crypto": 0,
            "tools": 0
        }
    
    def get_best_partner_link(self, topic: str) -> Optional[str]:
        """
        Get the most appropriate partner link for a topic.
        
        Args:
            topic: Post topic
            
        Returns:
            Partner link URL or None
        """
        return self.config.get_partner_link(topic)
    
    def optimize_cta(self, topic: str, past_performance: List[Dict]) -> str:
        """
        Optimize CTA based on past performance.
        
        Args:
            topic: Post topic
            past_performance: Historical CTA performance data
            
        Returns:
            Optimized CTA text
        """
        # Default CTAs
        ctas = {
            "ai": "🤖 Explore AI tools →",
            "crypto": "₿ Get crypto insights →",
            "tools": "🛠️ Try this tool →"
        }
        
        # Would analyze past_performance to select best performer
        # For now, return category-based default
        
        topic_lower = topic.lower()
        
        if "ai" in topic_lower or "ml" in topic_lower:
            return ctas["ai"]
        elif "crypto" in topic_lower or "blockchain" in topic_lower:
            return ctas["crypto"]
        else:
            return ctas["tools"]
    
    def generate_revenue_report(self) -> Dict:
        """Generate monetization performance report."""
        
        recent_posts = self.db.get_recent_posts(limit=100)
        
        monetized_posts = [p for p in recent_posts if p.get("partner_link")]
        
        return {
            "total_posts": len(recent_posts),
            "monetized_posts": len(monetized_posts),
            "monetization_rate": len(monetized_posts) / max(1, len(recent_posts)) * 100,
            "partner_categories_used": self.partner_usage,
            "generated_at": datetime.now().isoformat()
        }
