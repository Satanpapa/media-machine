"""
Media Machine - Autonomous Telegram Content Generation System

A multi-agent AI system that:
1. Detects trending topics early
2. Generates viral, factual content
3. Fact-checks and edits rigorously
4. Publishes only the best posts
5. Analyzes competitors and improves itself
6. Monetizes natively without losing trust

Usage:
    python main.py run          # Start continuous operation
    python main.py status       # Check system status
    python main.py test         # Run a single test cycle
    python main.py stats        # View detailed statistics
"""

import asyncio
import sys
import argparse
from datetime import datetime

from config.settings import config
from utils.database import Database
from utils.logger import setup_logger


def cmd_run():
    """Start the orchestrator in continuous mode."""
    from orchestrator import Orchestrator
    
    orchestrator = Orchestrator()
    
    print("\n" + "=" * 60)
    print("🚀 MEDIA MACHINE - Starting Continuous Operation")
    print("=" * 60)
    print(f"📊 Database: {config.database_path}")
    print(f"⏱️  Cycle interval: {config.trend_check_interval} minutes")
    print(f"📈 Analyst interval: {config.analyst_interval} minutes")
    print("=" * 60 + "\n")
    
    try:
        asyncio.run(orchestrator.run_continuous())
    except KeyboardInterrupt:
        print("\n⏹️  Stopped by user")
        orchestrator.stop()


def cmd_status():
    """Display current system status."""
    from orchestrator import Orchestrator
    
    orchestrator = Orchestrator()
    status = orchestrator.get_status()
    
    print("\n" + "=" * 60)
    print("📊 MEDIA MACHINE - System Status")
    print("=" * 60)
    print(f"Running: {'✅ Yes' if status['running'] else '❌ No'}")
    print(f"Posts today: {status['posts_today']}")
    print(f"Last analyst run: {status['last_analyst_run']}")
    print(f"Last improvement run: {status['last_improvement_run']}")
    print("-" * 60)
    print("Database Stats:")
    db_stats = status['database_stats']
    print(f"  Total posts: {db_stats.get('total_posts', 0)}")
    print(f"  Posts (24h): {db_stats.get('posts_24h', 0)}")
    print(f"  Avg ER: {db_stats.get('avg_er', 0):.2f}%")
    print(f"  Approval rate: {db_stats.get('approval_rate', 0):.1f}%")
    print("=" * 60 + "\n")


def cmd_test():
    """Run a single test cycle."""
    from orchestrator import Orchestrator
    
    orchestrator = Orchestrator()
    
    print("\n" + "=" * 60)
    print("🧪 MEDIA MACHINE - Running Test Cycle")
    print("=" * 60 + "\n")
    
    result = asyncio.run(orchestrator.run_cycle())
    
    print("\n" + "=" * 60)
    print("📊 Test Cycle Results")
    print("=" * 60)
    print(f"Duration: {result.get('duration_seconds', 0):.1f}s")
    print(f"Trends found: {result.get('trends_found', 0)}")
    print(f"Posts generated: {result.get('posts_generated', 0)}")
    print(f"Posts published: {result.get('posts_published', 0)}")
    print(f"Posts rejected: {result.get('posts_rejected', 0)}")
    
    if result.get('errors'):
        print("\nErrors:")
        for error in result['errors']:
            print(f"  ❌ {error}")
    
    print("=" * 60 + "\n")


def cmd_stats():
    """Display detailed statistics."""
    db = Database(config.database_path)
    stats = db.get_system_stats()
    
    print("\n" + "=" * 60)
    print("📈 MEDIA MACHINE - Detailed Statistics")
    print("=" * 60)
    print(f"Total posts published: {stats.get('total_posts', 0)}")
    print(f"Posts in last 24h: {stats.get('posts_24h', 0)}")
    print(f"Average engagement rate: {stats.get('avg_er', 0):.2f}%")
    print(f"Content approval rate: {stats.get('approval_rate', 0):.1f}%")
    
    top_topics = stats.get('top_topics', [])
    if top_topics:
        print("\nTop Topics:")
        for topic in top_topics[:5]:
            print(f"  • {topic.get('topic', 'N/A')}: {topic.get('count', 0)} posts")
    
    # Recent performance
    top_posts = db.get_top_performing_posts(limit=5, metric="er")
    if top_posts:
        print("\nTop Performing Posts (by ER):")
        for post in top_posts:
            print(f"  • {post.get('post_id', 'N/A')[:50]}... - ER: {post.get('er', 0):.2f}%")
    
    print("=" * 60 + "\n")


def cmd_init_db():
    """Initialize/reset the database."""
    db = Database(config.database_path)
    print(f"✅ Database initialized at {config.database_path}")
    print("Tables created: posted, performance, post_history, trend_signals, competitor_posts, analyst_insights")


def main():
    """Main entry point."""
    parser = argparse.ArgumentParser(
        description="Media Machine - Autonomous Telegram Content Generation",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=__doc__
    )
    
    subparsers = parser.add_subparsers(dest='command', help='Available commands')
    
    # run command
    subparsers.add_parser('run', help='Start continuous operation')
    
    # status command
    subparsers.add_parser('status', help='Show system status')
    
    # test command
    subparsers.add_parser('test', help='Run a single test cycle')
    
    # stats command
    subparsers.add_parser('stats', help='Show detailed statistics')
    
    # init command
    subparsers.add_parser('init', help='Initialize database')
    
    args = parser.parse_args()
    
    if args.command == 'run':
        cmd_run()
    elif args.command == 'status':
        cmd_status()
    elif args.command == 'test':
        cmd_test()
    elif args.command == 'stats':
        cmd_stats()
    elif args.command == 'init':
        cmd_init_db()
    else:
        parser.print_help()
        print("\nExample usage:")
        print("  python main.py init     # Initialize database")
        print("  python main.py test     # Run test cycle")
        print("  python main.py run      # Start continuous operation")


if __name__ == "__main__":
    main()
