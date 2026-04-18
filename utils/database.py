"""
Database layer for the Media Machine system.
Handles all SQLite operations for memory, performance tracking, and posted content.
"""

import sqlite3
from datetime import datetime, timedelta
from typing import List, Dict, Optional, Any
from pathlib import Path
import json


class Database:
    """SQLite database manager for system memory and analytics."""
    
    def __init__(self, db_path: str):
        """
        Initialize database connection and create tables if needed.
        
        Args:
            db_path: Path to SQLite database file.
        """
        self.db_path = db_path
        Path(db_path).parent.mkdir(parents=True, exist_ok=True)
        self._init_tables()
    
    def _get_connection(self) -> sqlite3.Connection:
        """Get database connection with row factory."""
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        return conn
    
    def _init_tables(self):
        """Create all required tables if they don't exist."""
        conn = self._get_connection()
        cursor = conn.cursor()
        
        # Table: Posted content (to avoid duplicates)
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS posted (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                link TEXT UNIQUE NOT NULL,
                topic TEXT,
                posted_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                partner_link TEXT,
                status TEXT DEFAULT 'published'
            )
        """)
        
        # Table: Performance metrics
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS performance (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                post_id TEXT NOT NULL,
                topic TEXT,
                views_1h INTEGER DEFAULT 0,
                views_3h INTEGER DEFAULT 0,
                views_24h INTEGER DEFAULT 0,
                er REAL DEFAULT 0.0,
                likes INTEGER DEFAULT 0,
                comments INTEGER DEFAULT 0,
                shares INTEGER DEFAULT 0,
                measured_at_1h TIMESTAMP,
                measured_at_3h TIMESTAMP,
                measured_at_24h TIMESTAMP,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)
        
        # Table: Post history (for self-improvement)
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS post_history (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                topic TEXT NOT NULL,
                title TEXT,
                content TEXT,
                variants TEXT,  -- JSON array of all generated variants
                selected_variant INTEGER,
                truth_score REAL,
                clarity_score REAL,
                hype_score REAL,
                judge_decision TEXT,  -- 'approved' or 'rejected'
                rejection_reason TEXT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                success_label TEXT  -- 'success', 'failure', or null if not measured yet
            )
        """)
        
        # Table: Trend signals (for analysis)
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS trend_signals (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                source TEXT NOT NULL,
                topic TEXT,
                raw_data TEXT,  -- JSON
                trend_score REAL,
                novelty_score REAL,
                processed BOOLEAN DEFAULT FALSE,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)
        
        # Table: Competitor analysis
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS competitor_posts (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                channel TEXT NOT NULL,
                post_id TEXT,
                content TEXT,
                views INTEGER,
                likes INTEGER,
                shares INTEGER,
                length INTEGER,
                posted_at TIMESTAMP,
                collected_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)
        
        # Table: Analyst insights
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS analyst_insights (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                insight_type TEXT NOT NULL,
                data TEXT,  -- JSON
                confidence REAL,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)
        
        # Create indexes for performance
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_posted_link ON posted(link)")
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_performance_post_id ON performance(post_id)")
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_post_history_created ON post_history(created_at)")
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_trend_signals_processed ON trend_signals(processed)")
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_competitor_channel ON competitor_posts(channel)")
        
        conn.commit()
        conn.close()
    
    # ==================== POSTED CONTENT ====================
    
    def is_posted(self, link: str) -> bool:
        """Check if a link has already been posted."""
        conn = self._get_connection()
        cursor = conn.cursor()
        cursor.execute("SELECT 1 FROM posted WHERE link = ?", (link,))
        result = cursor.fetchone()
        conn.close()
        return result is not None
    
    def mark_posted(self, link: str, topic: str = None, partner_link: str = None):
        """Mark a link as posted."""
        conn = self._get_connection()
        cursor = conn.cursor()
        cursor.execute(
            "INSERT OR IGNORE INTO posted (link, topic, partner_link) VALUES (?, ?, ?)",
            (link, topic, partner_link)
        )
        conn.commit()
        conn.close()
    
    def get_recent_posts(self, limit: int = 50) -> List[Dict]:
        """Get recently posted items."""
        conn = self._get_connection()
        cursor = conn.cursor()
        cursor.execute(
            "SELECT * FROM posted ORDER BY posted_at DESC LIMIT ?",
            (limit,)
        )
        results = [dict(row) for row in cursor.fetchall()]
        conn.close()
        return results
    
    def get_post_count_last_24h(self) -> int:
        """Get number of posts in the last 24 hours."""
        conn = self._get_connection()
        cursor = conn.cursor()
        cursor.execute(
            "SELECT COUNT(*) FROM posted WHERE posted_at >= datetime('now', '-1 day')"
        )
        result = cursor.fetchone()[0]
        conn.close()
        return result
    
    # ==================== PERFORMANCE METRICS ====================
    
    def record_performance(
        self,
        post_id: str,
        topic: str = None,
        views_1h: int = 0,
        views_3h: int = 0,
        views_24h: int = 0,
        er: float = 0.0,
        likes: int = 0,
        comments: int = 0,
        shares: int = 0
    ):
        """Record or update performance metrics for a post."""
        conn = self._get_connection()
        cursor = conn.cursor()
        
        now = datetime.now()
        
        # Check if exists
        cursor.execute("SELECT id FROM performance WHERE post_id = ?", (post_id,))
        existing = cursor.fetchone()
        
        if existing:
            cursor.execute("""
                UPDATE performance SET
                    views_1h = ?, views_3h = ?, views_24h = ?,
                    er = ?, likes = ?, comments = ?, shares = ?,
                    measured_at_24h = ?
                WHERE post_id = ?
            """, (views_1h, views_3h, views_24h, er, likes, comments, shares, now, post_id))
        else:
            cursor.execute("""
                INSERT INTO performance 
                (post_id, topic, views_1h, views_3h, views_24h, er, likes, comments, shares, measured_at_1h)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (post_id, topic, views_1h, views_3h, views_24h, er, likes, comments, shares, now))
        
        conn.commit()
        conn.close()
    
    def get_top_performing_posts(self, limit: int = 20, metric: str = "er") -> List[Dict]:
        """Get top performing posts by specified metric."""
        conn = self._get_connection()
        cursor = conn.cursor()
        
        valid_metrics = ["er", "views_1h", "views_3h", "likes"]
        if metric not in valid_metrics:
            metric = "er"
        
        cursor.execute(f"""
            SELECT * FROM performance 
            WHERE {metric} > 0
            ORDER BY {metric} DESC 
            LIMIT ?
        """, (limit,))
        
        results = [dict(row) for row in cursor.fetchall()]
        conn.close()
        return results
    
    def get_worst_performing_posts(self, limit: int = 20) -> List[Dict]:
        """Get worst performing posts by engagement rate."""
        conn = self._get_connection()
        cursor = conn.cursor()
        cursor.execute("""
            SELECT * FROM performance 
            WHERE views_1h > 0
            ORDER BY er ASC 
            LIMIT ?
        """, (limit,))
        results = [dict(row) for row in cursor.fetchall()]
        conn.close()
        return results
    
    # ==================== POST HISTORY ====================
    
    def save_post_history(
        self,
        topic: str,
        title: str,
        content: str,
        variants: List[str],
        selected_variant: int,
        truth_score: float,
        clarity_score: float,
        hype_score: float,
        judge_decision: str,
        rejection_reason: str = None
    ):
        """Save post generation history for self-improvement."""
        conn = self._get_connection()
        cursor = conn.cursor()
        
        variants_json = json.dumps(variants)
        
        cursor.execute("""
            INSERT INTO post_history 
            (topic, title, content, variants, selected_variant, 
             truth_score, clarity_score, hype_score, judge_decision, rejection_reason)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, (
            topic, title, content, variants_json, selected_variant,
            truth_score, clarity_score, hype_score, judge_decision, rejection_reason
        ))
        
        conn.commit()
        conn.close()
    
    def get_successful_posts(self, limit: int = 50) -> List[Dict]:
        """Get posts marked as successful."""
        conn = self._get_connection()
        cursor = conn.cursor()
        cursor.execute("""
            SELECT ph.*, p.er, p.views_1h 
            FROM post_history ph
            LEFT JOIN performance p ON ph.title = p.post_id
            WHERE ph.judge_decision = 'approved' 
              AND (ph.success_label = 'success' OR p.er > 0.05)
            ORDER BY ph.created_at DESC 
            LIMIT ?
        """, (limit,))
        results = [dict(row) for row in cursor.fetchall()]
        conn.close()
        return results
    
    def get_failed_posts(self, limit: int = 50) -> List[Dict]:
        """Get posts that were rejected or performed poorly."""
        conn = self._get_connection()
        cursor = conn.cursor()
        cursor.execute("""
            SELECT ph.*, p.er 
            FROM post_history ph
            LEFT JOIN performance p ON ph.title = p.post_id
            WHERE ph.judge_decision = 'rejected' 
              OR (ph.success_label = 'failure' AND p.er < 0.02)
            ORDER BY ph.created_at DESC 
            LIMIT ?
        """, (limit,))
        results = [dict(row) for row in cursor.fetchall()]
        conn.close()
        return results
    
    def mark_post_success(self, post_title: str, success: bool):
        """Mark a post as success or failure after performance measurement."""
        conn = self._get_connection()
        cursor = conn.cursor()
        label = "success" if success else "failure"
        cursor.execute(
            "UPDATE post_history SET success_label = ? WHERE title = ?",
            (label, post_title)
        )
        conn.commit()
        conn.close()
    
    # ==================== TREND SIGNALS ====================
    
    def save_trend_signal(
        self,
        source: str,
        topic: str,
        raw_data: Dict,
        trend_score: float,
        novelty_score: float = 0.0
    ):
        """Save a detected trend signal."""
        conn = self._get_connection()
        cursor = conn.cursor()
        cursor.execute("""
            INSERT INTO trend_signals 
            (source, topic, raw_data, trend_score, novelty_score)
            VALUES (?, ?, ?, ?, ?)
        """, (
            source, topic, json.dumps(raw_data), trend_score, novelty_score
        ))
        conn.commit()
        conn.close()
    
    def get_unprocessed_trends(self, min_score: float = 7.0) -> List[Dict]:
        """Get unprocessed trend signals above minimum score."""
        conn = self._get_connection()
        cursor = conn.cursor()
        cursor.execute("""
            SELECT * FROM trend_signals 
            WHERE processed = FALSE AND trend_score >= ?
            ORDER BY trend_score DESC
        """, (min_score,))
        results = [dict(row) for row in cursor.fetchall()]
        conn.close()
        return results
    
    def mark_trend_processed(self, trend_id: int):
        """Mark a trend signal as processed."""
        conn = self._get_connection()
        cursor = conn.cursor()
        cursor.execute(
            "UPDATE trend_signals SET processed = TRUE WHERE id = ?",
            (trend_id,)
        )
        conn.commit()
        conn.close()
    
    # ==================== COMPETITOR ANALYSIS ====================
    
    def save_competitor_post(
        self,
        channel: str,
        post_id: str,
        content: str,
        views: int,
        likes: int,
        shares: int,
        length: int,
        posted_at: datetime
    ):
        """Save a competitor's post for analysis."""
        conn = self._get_connection()
        cursor = conn.cursor()
        cursor.execute("""
            INSERT INTO competitor_posts 
            (channel, post_id, content, views, likes, shares, length, posted_at)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?)
        """, (channel, post_id, content, views, likes, shares, length, posted_at))
        conn.commit()
        conn.close()
    
    def get_competitor_stats(self, channel: str = None, hours: int = 24) -> List[Dict]:
        """Get competitor statistics for recent posts."""
        conn = self._get_connection()
        cursor = conn.cursor()
        
        if channel:
            cursor.execute("""
                SELECT channel, COUNT(*) as post_count,
                       AVG(views) as avg_views, AVG(likes) as avg_likes,
                       AVG(length) as avg_length,
                       MAX(posted_at) as last_post
                FROM competitor_posts
                WHERE channel = ? AND collected_at >= datetime('now', ?)
                GROUP BY channel
            """, (channel, f'-{hours} hours'))
        else:
            cursor.execute("""
                SELECT channel, COUNT(*) as post_count,
                       AVG(views) as avg_views, AVG(likes) as avg_likes,
                       AVG(length) as avg_length,
                       MAX(posted_at) as last_post
                FROM competitor_posts
                WHERE collected_at >= datetime('now', ?)
                GROUP BY channel
            """, (f'-{hours} hours',))
        
        results = [dict(row) for row in cursor.fetchall()]
        conn.close()
        return results
    
    # ==================== ANALYST INSIGHTS ====================
    
    def save_insight(self, insight_type: str, data: Dict, confidence: float):
        """Save an analyst insight."""
        conn = self._get_connection()
        cursor = conn.cursor()
        cursor.execute("""
            INSERT INTO analyst_insights (insight_type, data, confidence)
            VALUES (?, ?, ?)
        """, (insight_type, json.dumps(data), confidence))
        conn.commit()
        conn.close()
    
    def get_recent_insights(self, limit: int = 10) -> List[Dict]:
        """Get recent analyst insights."""
        conn = self._get_connection()
        cursor = conn.cursor()
        cursor.execute("""
            SELECT * FROM analyst_insights 
            ORDER BY created_at DESC 
            LIMIT ?
        """, (limit,))
        results = [dict(row) for row in cursor.fetchall()]
        conn.close()
        return results
    
    # ==================== ANALYTICS & REPORTING ====================
    
    def get_system_stats(self) -> Dict[str, Any]:
        """Get overall system statistics."""
        conn = self._get_connection()
        cursor = conn.cursor()
        
        stats = {}
        
        # Total posts
        cursor.execute("SELECT COUNT(*) FROM posted")
        stats["total_posts"] = cursor.fetchone()[0]
        
        # Posts last 24h
        cursor.execute("SELECT COUNT(*) FROM posted WHERE posted_at >= datetime('now', '-1 day')")
        stats["posts_24h"] = cursor.fetchone()[0]
        
        # Average ER
        cursor.execute("SELECT AVG(er) FROM performance WHERE er > 0")
        stats["avg_er"] = cursor.fetchone()[0] or 0.0
        
        # Success rate
        cursor.execute("SELECT COUNT(*) FROM post_history WHERE judge_decision = 'approved'")
        approved = cursor.fetchone()[0]
        cursor.execute("SELECT COUNT(*) FROM post_history")
        total = cursor.fetchone()[0]
        stats["approval_rate"] = (approved / total * 100) if total > 0 else 0.0
        
        # Top topics
        cursor.execute("""
            SELECT topic, COUNT(*) as count 
            FROM post_history 
            WHERE topic IS NOT NULL 
            GROUP BY topic 
            ORDER BY count DESC 
            LIMIT 5
        """)
        stats["top_topics"] = [dict(row) for row in cursor.fetchall()]
        
        conn.close()
        return stats
    
    def cleanup_old_data(self, days: int = 90):
        """Clean up old data to keep database size manageable."""
        conn = self._get_connection()
        cursor = conn.cursor()
        
        cutoff = f'datetime("now", "-{days} days")'
        
        # Archive old performance data
        cursor.execute(f"DELETE FROM performance WHERE created_at < {cutoff}")
        
        # Archive old trend signals
        cursor.execute(f"DELETE FROM trend_signals WHERE created_at < {cutoff}")
        
        # Keep only last N competitor posts per channel
        cursor.execute("""
            DELETE FROM competitor_posts 
            WHERE id NOT IN (
                SELECT id FROM (
                    SELECT id, ROW_NUMBER() OVER (PARTITION BY channel ORDER BY collected_at DESC) as rn
                    FROM competitor_posts
                ) WHERE rn <= 100
            )
        """)
        
        conn.commit()
        conn.close()
