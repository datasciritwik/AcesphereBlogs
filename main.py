#!/usr/bin/env python3
"""
AI Blog Agent for AcesphereAI
Main entry point for the blog generation pipeline.

Usage:
    python main.py              # Run full pipeline and publish
    python main.py --dry-run    # Test pipeline without publishing
    python main.py --topic-only # Generate topic brief only
"""

import argparse
import sys
from datetime import datetime

from agent.config import load_config, Config
from agent.topic_planner import TopicPlanner, TopicBrief
from agent.researcher import Researcher, ResearchNotes
from agent.writer import Writer, Article
from agent.publisher import Publisher, DryRunPublisher


def print_banner():
    """Print startup banner."""
    print("""
╔═══════════════════════════════════════════════════════════╗
║           🤖 AcesphereAI Blog Agent v1.0                  ║
║           Autonomous SEO Content Generation               ║
╚═══════════════════════════════════════════════════════════╝
""")


def print_section(title: str):
    """Print section header."""
    print(f"\n{'='*60}")
    print(f"  {title}")
    print(f"{'='*60}\n")


def validate_config(config: Config) -> bool:
    """Validate configuration and report errors."""
    errors = config.validate()
    
    if errors:
        print("❌ Configuration errors:")
        for error in errors:
            print(f"   - {error}")
        return False
    
    print("✅ Configuration validated successfully")
    return True


def run_topic_planner(config: Config) -> TopicBrief:
    """Run the topic planning phase."""
    print_section("📋 PHASE 1: Topic Planning")
    
    planner = TopicPlanner(config)
    topic = planner.generate_unique_topic()
    
    if topic:
        print(f"✅ Generated topic brief:")
        print(f"   Topic: {topic.topic}")
        print(f"   Title: {topic.title}")
        print(f"   Angle: {topic.angle}")
        print(f"   Keywords: {', '.join(topic.target_keywords)}")
        print(f"   Audience: {topic.target_audience}")
        print(f"   Research needed: {topic.sources_required}")
        print(f"\n   Outline:")
        for item in topic.outline:
            print(f"     - {item}")
    else:
        print("❌ Failed to generate topic")
        sys.exit(1)
    
    return topic


def run_researcher(config: Config, topic: TopicBrief) -> ResearchNotes:
    """Run the research phase."""
    print_section("🔍 PHASE 2: Research")
    
    researcher = Researcher(config)
    
    if topic.sources_required:
        print(f"Researching: {topic.topic}...")
        notes = researcher.research_topic(topic)
        
        if notes.facts or notes.key_points:
            print(f"✅ Research completed:")
            print(f"   Facts found: {len(notes.facts)}")
            print(f"   Statistics: {len(notes.statistics)}")
            print(f"   Key points: {len(notes.key_points)}")
            print(f"   Sources: {len(notes.sources)}")
        else:
            print("⚠️ Web search returned no results, using fallback...")
            notes = researcher.generate_fallback_notes(topic)
    else:
        print("ℹ️ Research not required for this topic")
        notes = ResearchNotes(
            topic=topic.topic,
            facts=[],
            statistics=[],
            sources=[],
            key_points=[]
        )
    
    return notes


def run_writer(config: Config, topic: TopicBrief, notes: ResearchNotes) -> Article:
    """Run the writing phase."""
    print_section("✍️ PHASE 3: Writing")
    
    writer = Writer(config)
    
    print(f"Writing article: {topic.title}...")
    article = writer.write_article(topic, notes)
    
    print(f"✅ Article generated:")
    print(f"   Title: {article.title}")
    print(f"   Slug: {article.slug}")
    print(f"   Words: {article.word_count}")
    print(f"   Tags: {', '.join(article.tags)}")
    print(f"   Description: {article.description[:80]}...")
    
    return article


def run_publisher(config: Config, article: Article, dry_run: bool = False) -> dict:
    """Run the publishing phase."""
    print_section("🚀 PHASE 4: Publishing")
    
    if dry_run:
        publisher = DryRunPublisher(config)
        print("🔍 Running in DRY RUN mode - no files will be written")
    else:
        publisher = Publisher(config)
    
    result = publisher.publish(article, push_to_git=not dry_run)
    
    if result["success"]:
        print(f"\n✅ Article published successfully!")
        if result["filepath"]:
            print(f"   File: {result['filepath']}")
        if result["pushed"]:
            print(f"   Git: Committed and pushed")
    else:
        print(f"\n❌ Publishing failed: {result.get('error', 'Unknown error')}")
    
    # Send notification
    if not dry_run and config.notification_webhook:
        publisher.send_notification(article, result)
    
    return result


def run_pipeline(dry_run: bool = False, topic_only: bool = False):
    """Run the full blog generation pipeline."""
    print_banner()
    
    start_time = datetime.now()
    
    # Load and validate configuration
    print_section("⚙️ Loading Configuration")
    config = load_config()
    
    if not validate_config(config):
        sys.exit(1)
    
    print(f"   Company: {config.get_company_name()}")
    print(f"   Keywords loaded: {len(config.get_all_keywords())}")
    print(f"   Previous posts: {config.published_posts.get('total_posts', 0)}")
    
    # Phase 1: Topic Planning
    topic = run_topic_planner(config)
    
    if topic_only:
        print("\n✅ Topic-only mode: Stopping after topic generation")
        return
    
    # Phase 2: Research
    notes = run_researcher(config, topic)
    
    # Phase 3: Writing
    article = run_writer(config, topic, notes)
    
    # Phase 4: Publishing
    result = run_publisher(config, article, dry_run)
    
    # Summary
    elapsed = (datetime.now() - start_time).total_seconds()
    print_section("📊 Summary")
    print(f"   Status: {'SUCCESS' if result['success'] else 'FAILED'}")
    print(f"   Time elapsed: {elapsed:.1f} seconds")
    print(f"   Article: {article.title}")
    print(f"   Word count: {article.word_count}")
    
    if not result["success"]:
        sys.exit(1)


def main():
    """Main entry point with argument parsing."""
    parser = argparse.ArgumentParser(
        description="AcesphereAI Blog Agent - Autonomous SEO content generation"
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Run pipeline without publishing (test mode)"
    )
    parser.add_argument(
        "--topic-only",
        action="store_true",
        help="Generate topic brief only, don't write article"
    )
    
    args = parser.parse_args()
    
    try:
        run_pipeline(dry_run=args.dry_run, topic_only=args.topic_only)
    except KeyboardInterrupt:
        print("\n\n⚠️ Interrupted by user")
        sys.exit(1)
    except Exception as e:
        print(f"\n❌ Fatal error: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)


if __name__ == "__main__":
    main()
