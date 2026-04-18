"""
Main Orchestrator - Central coordinator for all agents.
Runs the complete content generation pipeline on a schedule.
"""

import asyncio
from datetime import datetime, timedelta
from typing import Dict, Optional, List
import logging

from config.settings import config
from utils.database import Database
from utils.logger import setup_logger
from agents.trend_detector import TrendDetector
from agents.writer import Writer
from agents.hype_optimizer import HypeOptimizer
from agents.critic import Critic
from agents.judge import Judge
from agents.analyst import Analyst
from agents.strategist import Strategist
from agents.publisher import Publisher


class Orchestrator:
    """
    Central orchestrator coordinating all agents.
    
    Main Loop (every 20-30 minutes):
    1. Trend Detector → collects fresh signals
    2. If strong trend → Strategist → Writer → Hype Optimizer
    3. Critic → Judge
    4. If approved → Publisher
    
    Secondary Loops:
    - Analyst: Every 6 hours
    - Self-improvement: Daily
    - Performance tracking: 1h, 3h, 24h after each post
    """
    
    def __init__(self):
        """Initialize the orchestrator and all agents."""
        
        # Setup logging
        self.logger = setup_logger(
            name="orchestrator",
            log_file=config.log_file,
            level=config.log_level
        )
        
        self.logger.info("🚀 Initializing Media Machine Orchestrator...")
        
        # Initialize database
        self.db = Database(config.database_path)
        self.logger.info(f"📊 Database initialized: {config.database_path}")
        
        # Initialize agents
        self.trend_detector = TrendDetector(self.db)
        self.writer = Writer(self.db)
        self.hype_optimizer = HypeOptimizer(self.db)
        self.critic = Critic(self.db)
        self.judge = Judge(self.db)
        self.analyst = Analyst(self.db)
        self.strategist = Strategist(self.db)
        self.publisher = Publisher(self.db)
        
        self.logger.info("✅ All agents initialized")
        
        # State tracking
        self.last_analyst_run = datetime.now() - timedelta(hours=6)  # Run soon
        self.last_improvement_run = datetime.now() - timedelta(days=1)
        self.posts_today = 0
        self.running = False
    
    async def run_cycle(self) -> Dict:
        """
        Run one complete content generation cycle.
        
        Returns:
            Dictionary with cycle results
        """
        cycle_start = datetime.now()
        self.logger.info(f"🔄 Starting new cycle at {cycle_start.isoformat()}")
        
        result = {
            "cycle_start": cycle_start.isoformat(),
            "trends_found": 0,
            "posts_generated": 0,
            "posts_published": 0,
            "posts_rejected": 0,
            "errors": []
        }
        
        try:
            # Step 1: Detect trends
            self.logger.info("🔍 Running Trend Detector...")
            trends = self.trend_detector.run()
            result["trends_found"] = len(trends)
            
            if not trends:
                self.logger.info("ℹ️ No strong trends found this cycle")
                result["cycle_end"] = datetime.now().isoformat()
                return result
            
            self.logger.info(f"✨ Found {len(trends)} strong trends")
            
            # Step 2: Process top trend through pipeline
            for trend in trends[:3]:  # Process up to 3 trends per cycle
                self.logger.info(f"📝 Processing trend: {trend['topic'][:50]}...")
                
                try:
                    post_result = await self._process_trend(trend)
                    
                    if post_result.get("status") == "published":
                        result["posts_published"] += 1
                        self.posts_today += 1
                    elif post_result.get("status") == "rejected":
                        result["posts_rejected"] += 1
                    
                    result["posts_generated"] += 1
                    
                except Exception as e:
                    error_msg = f"Error processing trend '{trend['topic']}': {str(e)}"
                    self.logger.error(error_msg)
                    result["errors"].append(error_msg)
            
            # Step 3: Check if analyst should run
            if self._should_run_analyst():
                self.logger.info("📈 Running Analyst...")
                try:
                    analyst_result = self.analyst.run()
                    self.last_analyst_run = datetime.now()
                    self.logger.info(f"💡 Analyst insights: {len(analyst_result.get('patterns_identified', []))} patterns found")
                except Exception as e:
                    self.logger.error(f"Analyst error: {e}")
            
            # Step 4: Check if self-improvement should run
            if self._should_run_improvement():
                self.logger.info("🧠 Running self-improvement analysis...")
                try:
                    improvement = self.judge.analyze_performance_and_improve()
                    self.last_improvement_run = datetime.now()
                    self.logger.info(f"📚 Improvement insights: {len(improvement.get('insights', {}).get('recommendations', []))} recommendations")
                except Exception as e:
                    self.logger.error(f"Self-improvement error: {e}")
            
        except Exception as e:
            error_msg = f"Cycle error: {str(e)}"
            self.logger.error(error_msg)
            result["errors"].append(error_msg)
        
        result["cycle_end"] = datetime.now().isoformat()
        result["duration_seconds"] = (datetime.now() - cycle_start).total_seconds()
        
        self.logger.info(f"✅ Cycle completed in {result['duration_seconds']:.1f}s")
        self.logger.info(f"📊 Results: {result['posts_published']} published, {result['posts_rejected']} rejected")
        
        return result
    
    async def _process_trend(self, trend: Dict) -> Dict:
        """
        Process a single trend through the full pipeline.
        
        Args:
            trend: Trend data from TrendDetector
            
        Returns:
            Publication result
        """
        topic = trend["topic"]
        
        # Step 1: Writer generates 3 variants
        self.logger.debug(f"  ✍️  Writer generating variants for: {topic[:40]}...")
        writer_output = self.writer.run(trend)
        
        # Step 2: Hype Optimizer enhances variants
        self.logger.debug("  ⚡ Hype Optimizer enhancing...")
        hype_output = self.hype_optimizer.run(writer_output)
        
        # Step 3: Critic evaluates all variants
        self.logger.debug("  🔍 Critic fact-checking...")
        critic_output = self.critic.run(hype_output)
        
        # Step 4: Judge makes final decision
        self.logger.debug("  ⚖️  Judge making decision...")
        judge_decision = self.judge.run(critic_output)
        
        # Step 5: Publisher publishes if approved
        if judge_decision["decision"] == "APPROVE":
            self.logger.info(f"  ✅ APPROVED: {judge_decision['selected_variant']['title'][:50]}...")
            publish_result = self.publisher.run(judge_decision)
            return publish_result
        else:
            self.logger.info(f"  ❌ REJECTED: {judge_decision.get('reasoning', 'Quality thresholds not met')}")
            return {
                "status": "rejected",
                "reason": judge_decision.get("reasoning", "")
            }
    
    def _should_run_analyst(self) -> bool:
        """Check if analyst should run."""
        return (datetime.now() - self.last_analyst_run).total_seconds() >= config.analyst_interval * 60
    
    def _should_run_improvement(self) -> bool:
        """Check if self-improvement should run."""
        return (datetime.now() - self.last_improvement_run).total_seconds() >= 86400  # 24 hours
    
    async def run_continuous(self):
        """Run the orchestrator continuously on schedule."""
        self.running = True
        self.logger.info("▶️  Starting continuous operation mode")
        
        while self.running:
            try:
                await self.run_cycle()
                
                # Wait until next cycle
                wait_seconds = config.trend_check_interval * 60
                self.logger.info(f"😴 Sleeping for {wait_seconds/60:.0f} minutes...")
                
                await asyncio.sleep(wait_seconds)
                
            except KeyboardInterrupt:
                self.logger.info("⏹️  Stopping orchestrator...")
                self.running = False
                break
            except Exception as e:
                self.logger.error(f"Unexpected error in main loop: {e}")
                await asyncio.sleep(60)  # Wait 1 minute before retry
    
    def stop(self):
        """Stop the orchestrator."""
        self.running = False
        self.logger.info("⏹️  Orchestrator stopped")
    
    def get_status(self) -> Dict:
        """Get current system status."""
        stats = self.db.get_system_stats()
        
        return {
            "running": self.running,
            "posts_today": self.posts_today,
            "last_analyst_run": self.last_analyst_run.isoformat(),
            "last_improvement_run": self.last_improvement_run.isoformat(),
            "database_stats": stats,
            "timestamp": datetime.now().isoformat()
        }
