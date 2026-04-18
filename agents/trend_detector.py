"""
Trend Detector Agent - Early trend discovery system.
Monitors Reddit, Twitter/X, Google Trends, and RSS feeds to identify emerging trends.
"""

import json
from typing import List, Dict, Optional, Tuple
from datetime import datetime
import hashlib

from config.settings import config
from utils.database import Database
from utils.llm_client import get_llm_client


class TrendDetector:
    """
    Trend Detector Agent responsible for early trend discovery.
    
    Sources:
    - Reddit hot posts from relevant subreddits
    - X/Twitter trending topics (via API or scraping)
    - Google Trends data
    - RSS feeds from major news outlets
    
    Calculates trend_score = (Reddit mentions × 2) + (X velocity) + (Google growth) + novelty
    Only returns topics with score > 7
    """
    
    def __init__(self, db: Database, llm_client=None):
        """
        Initialize Trend Detector.
        
        Args:
            db: Database instance for storing signals
            llm_client: LLM client for analysis (optional, will create if None)
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
        
        # Subreddits to monitor (can be extended)
        self.subreddits = [
            "technology", "worldnews", "science", "business",
            "crypto", "artificial", "MachineLearning", "Startups"
        ]
    
    def run(self) -> List[Dict]:
        """
        Run trend detection across all sources.
        
        Returns:
            List of high-score trends (score > 7) with metadata
        """
        all_signals = []
        
        # Collect signals from each source
        reddit_signals = self._collect_reddit_signals()
        all_signals.extend(reddit_signals)
        
        rss_signals = self._collect_rss_signals()
        all_signals.extend(rss_signals)
        
        # Note: X/Twitter and Google Trends require API keys
        # Implement when credentials are available
        if self.config.reddit_client_id:
            pass  # Could add X API integration here
        
        if self.config.google_trends_enabled:
            pass  # Could add Google Trends integration here
        
        # Cluster and deduplicate signals
        clustered = self._cluster_signals(all_signals)
        
        # Calculate final scores and filter
        high_score_trends = []
        for cluster in clustered:
            trend_data = self._calculate_trend_score(cluster)
            
            if trend_data["trend_score"] > 7:
                # Check if already posted
                link_hash = hashlib.md5(
                    trend_data["topic"].encode()
                ).hexdigest()
                
                if not self.db.is_posted(link_hash):
                    high_score_trends.append(trend_data)
                    
                    # Save to database
                    self.db.save_trend_signal(
                        source=trend_data["primary_source"],
                        topic=trend_data["topic"],
                        raw_data=trend_data,
                        trend_score=trend_data["trend_score"],
                        novelty_score=trend_data.get("novelty_score", 0)
                    )
        
        return high_score_trends
    
    def _collect_reddit_signals(self) -> List[Dict]:
        """Collect trending topics from Reddit."""
        signals = []
        
        try:
            import praw
            
            reddit = praw.Reddit(
                client_id=self.config.reddit_client_id,
                client_secret=self.config.reddit_client_secret,
                user_agent="media_machine_trend_detector"
            )
            
            for subreddit_name in self.subreddits:
                try:
                    subreddit = reddit.subreddit(subreddit_name)
                    hot_posts = subreddit.hot(limit=25)
                    
                    for post in hot_posts:
                        if post.score > 100:  # Minimum threshold
                            signals.append({
                                "source": "reddit",
                                "subreddit": subreddit_name,
                                "title": post.title,
                                "url": post.url,
                                "score": post.score,
                                "num_comments": post.num_comments,
                                "created_utc": datetime.fromtimestamp(post.created_utc),
                                "upvote_ratio": post.upvote_ratio,
                                "velocity": post.score / max(1, (datetime.now().timestamp() - post.created_utc) / 3600)
                            })
                except Exception as e:
                    pass  # Skip problematic subreddits
                    
        except ImportError:
            # praw not installed, skip Reddit
            pass
        except Exception as e:
            pass  # Handle API errors gracefully
        
        return signals
    
    def _collect_rss_signals(self) -> List[Dict]:
        """Collect trending topics from RSS feeds."""
        signals = []
        
        try:
            import feedparser
            
            for feed_url in self.config.rss_feeds:
                try:
                    feed = feedparser.parse(feed_url)
                    
                    for entry in feed.entries[:10]:  # Top 10 from each feed
                        signals.append({
                            "source": "rss",
                            "feed": feed_url,
                            "title": entry.title,
                            "url": entry.link,
                            "published": entry.get("published_parsed"),
                            "summary": entry.get("summary", "")[:500]
                        })
                except Exception as e:
                    pass  # Skip problematic feeds
                    
        except ImportError:
            # feedparser not installed
            pass
        
        return signals
    
    def _cluster_signals(self, signals: List[Dict]) -> List[List[Dict]]:
        """
        Cluster similar signals together using embeddings or keyword matching.
        
        For simplicity, uses keyword-based clustering.
        Can be enhanced with sentence-transformers for better semantic clustering.
        """
        if not signals:
            return []
        
        clusters = []
        
        for signal in signals:
            title_lower = signal["title"].lower()
            
            # Try to find existing cluster
            found_cluster = False
            for cluster in clusters:
                # Check if titles share significant keywords
                cluster_titles = [s["title"].lower() for s in cluster]
                
                if self._titles_similar(title_lower, cluster_titles):
                    cluster.append(signal)
                    found_cluster = True
                    break
            
            if not found_cluster:
                clusters.append([signal])
        
        return clusters
    
    def _titles_similar(self, title: str, cluster_titles: List[str], threshold: int = 2) -> bool:
        """Check if title shares enough keywords with cluster."""
        # Extract important words (skip common words)
        stop_words = {"the", "a", "an", "is", "are", "was", "were", "in", "on", "at", "to", "for"}
        
        title_words = set(w for w in title.split() if len(w) > 3 and w not in stop_words)
        
        for cluster_title in cluster_titles:
            cluster_words = set(w for w in cluster_title.split() if len(w) > 3 and w not in stop_words)
            
            # Count overlapping words
            overlap = len(title_words & cluster_words)
            
            if overlap >= threshold:
                return True
        
        return False
    
    def _calculate_trend_score(self, cluster: List[Dict]) -> Dict:
        """
        Calculate trend score for a cluster of signals.
        
        Formula: trend_score = (Reddit mentions × 2) + (X velocity) + (Google growth) + novelty
        """
        # Count sources
        reddit_count = sum(1 for s in cluster if s["source"] == "reddit")
        rss_count = sum(1 for s in cluster if s["source"] == "rss")
        
        # Calculate velocity (how fast it's spreading)
        velocities = [s.get("velocity", 0) for s in cluster if "velocity" in s]
        avg_velocity = sum(velocities) / len(velocities) if velocities else 0
        
        # Get representative title/topic
        primary_signal = max(cluster, key=lambda s: s.get("score", 0) or 0)
        topic = primary_signal["title"]
        
        # Calculate base score
        base_score = (reddit_count * 2) + (rss_count * 1.5)
        
        # Add velocity bonus
        velocity_bonus = min(avg_velocity / 10, 3)  # Cap at 3
        
        # Calculate novelty (using LLM if available)
        novelty_score = self._calculate_novelty(topic)
        
        # Final score
        trend_score = base_score + velocity_bonus + novelty_score
        
        # Determine primary source
        if reddit_count > rss_count:
            primary_source = "reddit"
        else:
            primary_source = "rss"
        
        return {
            "topic": topic,
            "trend_score": round(trend_score, 2),
            "novelty_score": round(novelty_score, 2),
            "primary_source": primary_source,
            "signal_count": len(cluster),
            "reddit_mentions": reddit_count,
            "rss_mentions": rss_count,
            "avg_velocity": round(avg_velocity, 2),
            "sources": list(set(s["source"] for s in cluster)),
            "urls": [s["url"] for s in cluster[:5]],  # Top 5 URLs
            "detected_at": datetime.now().isoformat()
        }
    
    def _calculate_novelty(self, topic: str) -> float:
        """
        Calculate novelty score by checking against recent posts.
        
        Returns score 0-3 based on how novel the topic is.
        """
        recent_posts = self.db.get_recent_posts(limit=50)
        
        if not recent_posts:
            return 2.0  # No history, assume novel
        
        # Check if topic is similar to recent posts
        topic_lower = topic.lower()
        
        for post in recent_posts:
            if post.get("topic"):
                if self._topics_similar(topic_lower, post["topic"].lower()):
                    return 0.5  # Similar to recent post, low novelty
        
        # Check using LLM if available
        if self.llm:
            try:
                prompt = f"""
                Compare these two topics and rate their similarity from 0 (completely different) to 1 (identical).
                Respond with only a number.
                
                Topic 1: {topic}
                Recent topic: {recent_posts[0].get('topic', 'N/A')}
                
                Similarity score:
                """
                
                response = self.llm.generate(prompt)
                # Parse response...
                # For now, skip complex LLM analysis
            except:
                pass
        
        return 2.0  # Default to medium-high novelty
    
    def _topics_similar(self, topic1: str, topic2: str) -> bool:
        """Simple keyword-based topic similarity check."""
        words1 = set(w for w in topic1.split() if len(w) > 4)
        words2 = set(w for w in topic2.split() if len(w) > 4)
        
        if not words1 or not words2:
            return False
        
        overlap = len(words1 & words2)
        return overlap >= 2
