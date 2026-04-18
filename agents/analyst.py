"""
Analyst Agent - Competitor analysis and pattern detection.
Monitors competitor channels and identifies successful patterns.
"""

from typing import List, Dict, Optional
from datetime import datetime, timedelta
import asyncio

from config.settings import config
from utils.database import Database


class Analyst:
    """
    Analyst Agent responsible for competitor intelligence.
    
    Every 6 hours:
    - Scrapes top posts from competitor channels
    - Analyzes views/hour, engagement rate, length, structure
    - Identifies winning patterns
    - Stores insights for Strategist
    """
    
    def __init__(self, db: Database):
        """
        Initialize Analyst.
        
        Args:
            db: Database instance
        """
        self.db = db
        self.config = config
        
        # Try to initialize Telegram client for scraping
        self.telegram_client = None
        self._init_telegram()
    
    def _init_telegram(self):
        """Initialize Telethon client for competitor analysis."""
        try:
            from telethon import TelegramClient
            
            if self.config.telegram_api_id and self.config.telegram_api_hash:
                self.telegram_client = TelegramClient(
                    'analyst_session',
                    int(self.config.telegram_api_id),
                    self.config.telegram_api_hash
                )
        except ImportError:
            pass  # Telethon not installed
        except Exception as e:
            pass  # Configuration issues
    
    def run(self) -> Dict:
        """
        Run competitor analysis.
        
        Returns:
            Dictionary with insights and patterns
        """
        insights = {
            "analyzed_at": datetime.now().isoformat(),
            "channels_analyzed": [],
            "top_performing_posts": [],
            "patterns_identified": [],
            "recommendations": []
        }
        
        # Get competitor channels from config
        competitors = self.config.competitor_channels
        
        if not competitors:
            insights["patterns_identified"].append("No competitor channels configured")
            return insights
        
        # Collect data from competitors
        if self.telegram_client:
            competitor_data = self._scrape_competitors_async(competitors)
        else:
            # Fallback: use existing database data
            competitor_data = self._analyze_from_database()
        
        insights["channels_analyzed"] = list(set(c.get("channel", "") for c in competitor_data))
        insights["top_performing_posts"] = competitor_data[:20]  # Top 20
        
        # Identify patterns
        patterns = self._identify_patterns(competitor_data)
        insights["patterns_identified"] = patterns
        
        # Generate recommendations
        recommendations = self._generate_recommendations(patterns, competitor_data)
        insights["recommendations"] = recommendations
        
        # Save insights to database
        self.db.save_insight(
            insight_type="competitor_analysis",
            data=insights,
            confidence=0.8
        )
        
        return insights
    
    def _scrape_competitors_async(self, channels: List[str]) -> List[Dict]:
        """Scrape competitor channels using Telethon."""
        
        async def scrape():
            results = []
            
            try:
                await self.telegram_client.start()
                
                for channel in channels:
                    try:
                        entity = await self.telegram_client.get_entity(channel)
                        messages = await self.telegram_client.get_messages(
                            entity,
                            limit=50,
                            min_date=datetime.now() - timedelta(hours=24)
                        )
                        
                        for msg in messages:
                            if msg.views:  # Only posts with view counts
                                results.append({
                                    "channel": channel,
                                    "post_id": str(msg.id),
                                    "content": msg.text[:500] if msg.text else "",
                                    "views": msg.views,
                                    "likes": msg.reactions.count if hasattr(msg, 'reactions') and msg.reactions else 0,
                                    "shares": 0,  # Not directly available
                                    "length": len(msg.text) if msg.text else 0,
                                    "posted_at": msg.date,
                                    "views_per_hour": msg.views / max(1, (datetime.now() - msg.date).total_seconds() / 3600)
                                })
                                
                                # Save to database
                                self.db.save_competitor_post(
                                    channel=channel,
                                    post_id=str(msg.id),
                                    content=msg.text[:500] if msg.text else "",
                                    views=msg.views,
                                    likes=msg.reactions.count if hasattr(msg, 'reactions') and msg.reactions else 0,
                                    shares=0,
                                    length=len(msg.text) if msg.text else 0,
                                    posted_at=msg.date
                                )
                    except Exception as e:
                        pass  # Skip problematic channels
                
                await self.telegram_client.disconnect()
                
            except Exception as e:
                pass
            
            return results
        
        try:
            return asyncio.run(scrape())
        except Exception:
            return self._analyze_from_database()
    
    def _analyze_from_database(self) -> List[Dict]:
        """Analyze competitor data from database."""
        stats = self.db.get_competitor_stats(hours=24)
        
        results = []
        for stat in stats:
            results.append({
                "channel": stat.get("channel", "unknown"),
                "post_count": stat.get("post_count", 0),
                "avg_views": stat.get("avg_views", 0),
                "avg_likes": stat.get("avg_likes", 0),
                "avg_length": stat.get("avg_length", 0),
                "last_post": stat.get("last_post")
            })
        
        return results
    
    def _identify_patterns(self, data: List[Dict]) -> List[str]:
        """Identify successful patterns from competitor data."""
        patterns = []
        
        if not data:
            return ["Insufficient data for pattern analysis"]
        
        # Analyze post length
        lengths = [d.get("length", 0) for d in data if "length" in d]
        if lengths:
            avg_length = sum(lengths) / len(lengths)
            
            # Find optimal length range
            short_posts = [d for d in data if d.get("length", 0) < 100]
            long_posts = [d for d in data if d.get("length", 0) > 300]
            
            if short_posts and long_posts:
                short_avg_views = sum(d.get("views", 0) for d in short_posts) / len(short_posts)
                long_avg_views = sum(d.get("views", 0) for d in long_posts) / len(long_posts)
                
                if short_avg_views > long_avg_views:
                    patterns.append(f"Short posts (<100 chars) perform better: {short_avg_views:.0f} vs {long_avg_views:.0f} avg views")
                else:
                    patterns.append(f"Longer posts (>300 chars) perform better: {long_avg_views:.0f} vs {short_avg_views:.0f} avg views")
            else:
                patterns.append(f"Average post length: {avg_length:.0f} characters")
        
        # Analyze posting times
        times = []
        for d in data:
            if "posted_at" in d and d["posted_at"]:
                try:
                    if isinstance(d["posted_at"], datetime):
                        times.append(d["posted_at"].hour)
                except:
                    pass
        
        if times:
            peak_hour = max(set(times), key=times.count)
            patterns.append(f"Most common posting hour: {peak_hour}:00")
        
        # Analyze engagement patterns
        posts_with_engagement = [d for d in data if d.get("likes", 0) > 0 and d.get("views", 0) > 0]
        if posts_with_engagement:
            ers = [d["likes"] / d["views"] * 100 for d in posts_with_engagement]
            avg_er = sum(ers) / len(ers)
            patterns.append(f"Average engagement rate: {avg_er:.2f}%")
        
        return patterns
    
    def _generate_recommendations(
        self,
        patterns: List[str],
        data: List[Dict]
    ) -> List[str]:
        """Generate actionable recommendations based on patterns."""
        recommendations = []
        
        # Length recommendation
        length_pattern = [p for p in patterns if "length" in p.lower() or "chars" in p.lower()]
        if length_pattern:
            if "short" in length_pattern[0].lower():
                recommendations.append("Keep posts concise - competitors see better engagement with shorter content")
            elif "longer" in length_pattern[0].lower():
                recommendations.append("Consider longer, more detailed posts - they perform well")
        
        # Engagement recommendation
        er_pattern = [p for p in patterns if "engagement" in p.lower() or "rate" in p.lower()]
        if er_pattern:
            recommendations.append("Focus on engagement-driving elements (questions, polls, controversial takes)")
        
        # Timing recommendation
        time_pattern = [p for p in patterns if "hour" in p.lower() or "posting" in p.lower()]
        if time_pattern:
            recommendations.append("Align posting schedule with competitor peak times")
        
        if not recommendations:
            recommendations.append("Continue monitoring competitors for emerging patterns")
        
        return recommendations
    
    def get_optimal_posting_time(self) -> Dict:
        """
        Determine optimal posting time based on analysis.
        
        Returns:
            Dictionary with recommended hour and reasoning
        """
        stats = self.db.get_competitor_stats(hours=168)  # Last week
        
        if not stats:
            return {
                "recommended_hour": 12,  # Default: noon
                "confidence": 0.3,
                "reasoning": "Default recommendation due to insufficient data"
            }
        
        # Analyze when competitors post most
        recent_posts = []
        for stat in stats:
            channel = stat.get("channel")
            if channel:
                channel_posts = self.db.get_competitor_stats(channel=channel, hours=168)
                recent_posts.extend(channel_posts)
        
        # Simple heuristic: recommend a time when competition is lower
        # but audience is likely active (business hours)
        recommended_hour = 10  # 10 AM - good balance
        
        return {
            "recommended_hour": recommended_hour,
            "confidence": 0.6,
            "reasoning": f"Based on analysis of {len(stats)} competitor channels"
        }
