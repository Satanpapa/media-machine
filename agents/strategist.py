"""
Strategist Agent - Content strategy and idea generation.
Combines trend data with competitor insights to generate post ideas.
"""

from typing import List, Dict, Optional
from datetime import datetime

from config.settings import config
from utils.database import Database
from utils.llm_client import get_llm_client


class Strategist:
    """
    Strategist Agent responsible for content planning.
    
    Based on:
    - Trend Detector output (hot topics)
    - Analyst insights (what's working)
    - Historical performance (our own data)
    
    Generates 5 new post ideas with optimal timing recommendations.
    """
    
    def __init__(self, db: Database, llm_client=None):
        """
        Initialize Strategist.
        
        Args:
            db: Database instance
            llm_client: LLM client for ideation
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
    
    def run(
        self,
        trends: List[Dict] = None,
        analyst_insights: Dict = None
    ) -> Dict:
        """
        Generate strategic post ideas.
        
        Args:
            trends: Output from TrendDetector (optional)
            analyst_insights: Output from Analyst (optional)
            
        Returns:
            Dictionary with 5 post ideas and timing recommendations
        """
        # Get recent insights if not provided
        if analyst_insights is None:
            recent_insights = self.db.get_recent_insights(limit=5)
            analyst_insights = recent_insights[0] if recent_insights else {}
        
        # Get our own performance data
        top_posts = self.db.get_top_performing_posts(limit=10, metric="er")
        
        # Generate ideas
        ideas = self._generate_ideas(trends, analyst_insights, top_posts)
        
        # Get timing recommendation
        timing = self._get_optimal_timing()
        
        return {
            "generated_at": datetime.now().isoformat(),
            "post_ideas": ideas,
            "timing_recommendation": timing,
            "strategy_notes": self._generate_strategy_notes(trends, analyst_insights)
        }
    
    def _generate_ideas(
        self,
        trends: List[Dict],
        analyst_insights: Dict,
        top_posts: List[Dict]
    ) -> List[Dict]:
        """Generate 5 strategic post ideas."""
        
        ideas = []
        
        # Idea 1: Based on hottest trend
        if trends and len(trends) > 0:
            hottest = trends[0]
            ideas.append({
                "id": 1,
                "type": "trend_jack",
                "topic": hottest["topic"],
                "angle": "Early coverage of emerging trend",
                "priority": "high",
                "source_trend_score": hottest["trend_score"],
                "rationale": f"Trend score {hottest['trend_score']} indicates strong momentum"
            })
        
        # Idea 2: Follow-up on our best performing topic
        if top_posts:
            best_topic = top_posts[0].get("topic", "")
            if best_topic:
                ideas.append({
                    "id": 2,
                    "type": "sequel",
                    "topic": f"Update: {best_topic}",
                    "angle": "Follow-up on our successful post",
                    "priority": "medium",
                    "rationale": "Building on proven audience interest"
                })
        
        # Idea 3: Competitor gap analysis
        patterns = analyst_insights.get("patterns_identified", [])
        if patterns:
            ideas.append({
                "id": 3,
                "type": "gap_opportunity",
                "topic": "Underserved topic based on competitor analysis",
                "angle": patterns[0] if patterns else "Unique angle competitors missed",
                "priority": "medium",
                "rationale": "Exploiting competitor blind spots"
            })
        
        # Idea 4: Educational/evergreen content
        ideas.append({
            "id": 4,
            "type": "evergreen",
            "topic": "How-to or explainer on foundational concept",
            "angle": "Educational content for long-term value",
            "priority": "low",
            "rationale": "Building library of reference content"
        })
        
        # Idea 5: Contrarian take
        if trends and len(trends) > 0:
            contrarian_topic = trends[0]["topic"] if trends else "Industry trend"
            ideas.append({
                "id": 5,
                "type": "contrarian",
                "topic": f"The unpopular truth about {contrarian_topic.split()[:3]}",
                "angle": "Going against conventional wisdom",
                "priority": "medium",
                "rationale": "Contrarian takes drive engagement"
            })
        
        # If we have fewer than 5 ideas, add generic ones
        generic_ideas = [
            {"type": "news_roundup", "topic": "Weekly roundup of top stories"},
            {"type": "prediction", "topic": "Bold prediction for the industry"},
            {"type": "question", "topic": "Community question/discussion starter"},
        ]
        
        while len(ideas) < 5:
            generic = generic_ideas[len(ideas) % len(generic_ideas)]
            ideas.append({
                "id": len(ideas) + 1,
                "type": generic["type"],
                "topic": generic["topic"],
                "angle": "Filler content when no strong trends",
                "priority": "low",
                "rationale": "Maintaining consistent posting schedule"
            })
        
        # Use LLM to enhance ideas if available
        if self.llm and trends:
            ideas = self._enhance_ideas_with_llm(ideas, trends)
        
        return ideas[:5]  # Return exactly 5
    
    def _enhance_ideas_with_llm(
        self,
        ideas: List[Dict],
        trends: List[Dict]
    ) -> List[Dict]:
        """Use LLM to refine and enhance post ideas."""
        
        try:
            trend_topics = "\n".join([f"- {t['topic']} (score: {t['trend_score']})" for t in trends[:5]])
            
            prompt = f"""
Given these trending topics:
{trend_topics}

And these current post ideas:
{ideas}

Enhance each idea with:
1. More specific angle
2. Suggested headline
3. Key points to cover

Respond in JSON format as a list of enhanced ideas.
"""
            
            enhanced = self.llm.generate_json(prompt)
            
            # Merge enhancements
            if isinstance(enhanced, list) and len(enhanced) == len(ideas):
                for i, enhancement in enumerate(enhanced):
                    ideas[i]["enhanced_angle"] = enhancement.get("angle", ideas[i]["angle"])
                    ideas[i]["suggested_headline"] = enhancement.get("headline", "")
                    ideas[i]["key_points"] = enhancement.get("key_points", [])
            
        except Exception:
            pass  # Keep original ideas if LLM fails
        
        return ideas
    
    def _get_optimal_timing(self) -> Dict:
        """Determine optimal posting time."""
        
        # Try to get from Analyst
        try:
            from .analyst import Analyst
            analyst = Analyst(self.db)
            timing_data = analyst.get_optimal_posting_time()
        except:
            timing_data = {
                "recommended_hour": 10,
                "confidence": 0.5,
                "reasoning": "Default recommendation"
            }
        
        # Add day-of-week analysis
        dow_recommendation = "weekday"  # Default
        
        return {
            "hour": timing_data.get("recommended_hour", 10),
            "day_type": dow_recommendation,
            "timezone": "UTC",
            "confidence": timing_data.get("confidence", 0.5),
            "reasoning": timing_data.get("reasoning", "")
        }
    
    def _generate_strategy_notes(
        self,
        trends: List[Dict],
        analyst_insights: Dict
    ) -> str:
        """Generate overall strategy notes."""
        
        notes = []
        
        # Trend assessment
        if trends:
            high_score_count = sum(1 for t in trends if t.get("trend_score", 0) > 8)
            if high_score_count > 3:
                notes.append("🔥 Strong trend environment - prioritize speed")
            elif high_score_count > 0:
                notes.append("⚡ Moderate trends - focus on quality over speed")
            else:
                notes.append("📊 Weak trends - lean on evergreen content")
        
        # Competitor assessment
        if analyst_insights:
            recommendations = analyst_insights.get("recommendations", [])
            if recommendations:
                notes.append(f"💡 Analyst insight: {recommendations[0]}")
        
        # Performance assessment
        recent_posts_24h = self.db.get_post_count_last_24h()
        if recent_posts_24h >= 5:
            notes.append("⚠️ High posting frequency - consider quality over quantity")
        elif recent_posts_24h == 0:
            notes.append("📝 No posts in 24h - prioritize getting content out")
        
        return " | ".join(notes) if notes else "No specific strategic notes at this time."
