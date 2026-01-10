"""
Configuration loader for the AI Blog Agent.
Reads business context, keywords, and settings from YAML/JSON files.
"""

import os
import json
import yaml
from pathlib import Path
from dataclasses import dataclass, field
from typing import List, Dict, Any, Optional
from dotenv import load_dotenv

# Load environment variables
load_dotenv()


@dataclass
class ArticleSettings:
    """Settings for article generation."""
    min_words: int = 800
    max_words: int = 1200
    include_internal_links: bool = True
    include_external_links: bool = True
    min_external_links: int = 2
    include_sources: bool = True


@dataclass
class ScheduleSettings:
    """Settings for publication schedule."""
    posts_per_day: int = 3
    timezone: str = "UTC"


@dataclass
class Config:
    """Main configuration class for the AI Blog Agent."""
    
    # Paths
    base_path: Path = field(default_factory=lambda: Path(__file__).parent.parent)
    data_path: Path = field(default_factory=lambda: Path(__file__).parent.parent / "data")
    content_path: Path = field(default_factory=lambda: Path(__file__).parent.parent / "content" / "posts")
    
    # Business context
    business_context: Dict[str, Any] = field(default_factory=dict)
    
    # Keywords
    keywords: Dict[str, Any] = field(default_factory=dict)
    
    # Published posts index
    published_posts: Dict[str, Any] = field(default_factory=dict)
    
    # Settings
    article_settings: ArticleSettings = field(default_factory=ArticleSettings)
    schedule_settings: ScheduleSettings = field(default_factory=ScheduleSettings)
    
    # API Keys (from environment)
    groq_api_key: Optional[str] = None
    github_token: Optional[str] = None
    notification_webhook: Optional[str] = None
    
    def __post_init__(self):
        """Load configuration from files after initialization."""
        self.load_all()
    
    def load_all(self) -> None:
        """Load all configuration files."""
        self._load_env()
        self._load_business_context()
        self._load_keywords()
        self._load_published_posts()
        self._ensure_content_dir()
    
    def _load_env(self) -> None:
        """Load environment variables."""
        self.groq_api_key = os.getenv("GROQ_API_KEY")
        self.github_token = os.getenv("GITHUB_TOKEN")
        self.notification_webhook = os.getenv("NOTIFICATION_WEBHOOK")
    
    def _load_business_context(self) -> None:
        """Load business context from YAML."""
        context_file = self.data_path / "business_context.yaml"
        if context_file.exists():
            with open(context_file, "r", encoding="utf-8") as f:
                self.business_context = yaml.safe_load(f)
    
    def _load_keywords(self) -> None:
        """Load SEO keywords from YAML."""
        keywords_file = self.data_path / "keywords.yaml"
        if keywords_file.exists():
            with open(keywords_file, "r", encoding="utf-8") as f:
                self.keywords = yaml.safe_load(f)
    
    def _load_published_posts(self) -> None:
        """Load published posts index from JSON."""
        posts_file = self.data_path / "published_posts.json"
        if posts_file.exists():
            with open(posts_file, "r", encoding="utf-8") as f:
                self.published_posts = json.load(f)
    
    def _ensure_content_dir(self) -> None:
        """Ensure content directory exists."""
        self.content_path.mkdir(parents=True, exist_ok=True)
    
    def save_published_posts(self) -> None:
        """Save updated published posts index."""
        posts_file = self.data_path / "published_posts.json"
        with open(posts_file, "w", encoding="utf-8") as f:
            json.dump(self.published_posts, f, indent=2)
    
    def get_company_name(self) -> str:
        """Get company name from business context."""
        return self.business_context.get("company_name", "")
    
    def get_brand_voice(self) -> Dict[str, str]:
        """Get brand voice settings."""
        return self.business_context.get("brand_voice", {})
    
    def get_content_pillars(self) -> List[str]:
        """Get content pillars/topics."""
        return self.business_context.get("content_pillars", [])
    
    def get_target_audience(self) -> List[str]:
        """Get target audience segments."""
        return self.business_context.get("target_audience", [])
    
    def get_all_keywords(self) -> List[str]:
        """Get flattened list of all keywords."""
        all_keywords = []
        
        # Primary keywords
        all_keywords.extend(self.keywords.get("primary_keywords", []))
        
        # Keywords from clusters
        clusters = self.keywords.get("keyword_clusters", {})
        for cluster in clusters.values():
            if isinstance(cluster, dict):
                all_keywords.append(cluster.get("primary", ""))
                all_keywords.extend(cluster.get("related", []))
        
        # Long tail topics
        all_keywords.extend(self.keywords.get("long_tail_topics", []))
        
        return [k for k in all_keywords if k]  # Filter empty strings
    
    def get_used_topics(self) -> List[str]:
        """Get list of already used topics."""
        return self.published_posts.get("topics_used", [])
    
    def add_published_post(self, post_info: Dict[str, Any]) -> None:
        """Add a new published post to the index."""
        if "posts" not in self.published_posts:
            self.published_posts["posts"] = []
        if "topics_used" not in self.published_posts:
            self.published_posts["topics_used"] = []
        
        self.published_posts["posts"].append(post_info)
        self.published_posts["topics_used"].append(post_info.get("topic", ""))
        self.published_posts["total_posts"] = len(self.published_posts["posts"])
        self.published_posts["last_updated"] = post_info.get("pub_date", "")
        
        self.save_published_posts()
    
    def validate(self) -> List[str]:
        """Validate configuration and return list of errors."""
        errors = []
        
        if not self.groq_api_key:
            errors.append("GROQ_API_KEY environment variable not set")
        
        if not self.business_context:
            errors.append("Business context file not found or empty")
        
        if not self.keywords:
            errors.append("Keywords file not found or empty")
        
        return errors


def load_config() -> Config:
    """Factory function to create and load configuration."""
    return Config()
