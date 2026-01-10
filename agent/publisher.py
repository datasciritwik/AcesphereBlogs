"""
Publisher Module for the AI Blog Agent.
Handles saving articles and Git-based publishing.
"""

import os
import json
from datetime import datetime
from pathlib import Path
from typing import Optional

from .config import Config
from .writer import Article

# Try to import git, but make it optional for local testing
try:
    from git import Repo
    HAS_GIT = True
except ImportError:
    HAS_GIT = False


class Publisher:
    """Handles saving and publishing articles to Git repository."""
    
    def __init__(self, config: Config):
        """Initialize the publisher with configuration."""
        self.config = config
        self.content_path = config.content_path
        self.repo: Optional[Repo] = None
        
        if HAS_GIT:
            try:
                self.repo = Repo(config.base_path)
            except Exception:
                self.repo = None
    
    def save_article(self, article: Article) -> Path:
        """Save article to the content directory."""
        # Ensure directory exists
        self.content_path.mkdir(parents=True, exist_ok=True)
        
        # Generate filename from date and slug
        filename = f"{article.pub_date}-{article.slug}.md"
        filepath = self.content_path / filename
        
        # Write article content
        with open(filepath, "w", encoding="utf-8") as f:
            f.write(article.to_markdown())
        
        print(f"📝 Saved article: {filepath}")
        return filepath
    
    def update_index(self, article: Article, filepath: Path) -> None:
        """Update the published posts index."""
        post_info = article.to_dict()
        post_info["filepath"] = str(filepath.relative_to(self.config.base_path))
        post_info["topic"] = article.title  # For duplicate checking
        
        self.config.add_published_post(post_info)
        print(f"📋 Updated posts index (total: {self.config.published_posts.get('total_posts', 0)})")
    
    def git_commit_and_push(self, article: Article, filepath: Path) -> bool:
        """Commit and push changes to Git repository."""
        if not HAS_GIT or not self.repo:
            print("⚠️ Git not available or not a git repository - skipping push")
            return False
        
        try:
            # Stage the new article and updated index
            self.repo.index.add([
                str(filepath),
                str(self.config.data_path / "published_posts.json")
            ])
            
            # Create commit
            commit_message = f"📝 New post: {article.title}"
            self.repo.index.commit(commit_message)
            
            # Push to origin
            origin = self.repo.remote(name="origin")
            origin.push()
            
            print(f"✅ Pushed to Git: {commit_message}")
            return True
            
        except Exception as e:
            print(f"❌ Git error: {e}")
            return False
    
    def publish(self, article: Article, push_to_git: bool = True) -> dict:
        """Full publish workflow: save, index, and optionally push."""
        result = {
            "success": False,
            "filepath": None,
            "pushed": False,
            "error": None
        }
        
        try:
            # Save article file
            filepath = self.save_article(article)
            result["filepath"] = str(filepath)
            
            # Update index
            self.update_index(article, filepath)
            
            # Push to Git if requested
            if push_to_git:
                result["pushed"] = self.git_commit_and_push(article, filepath)
            
            result["success"] = True
            
        except Exception as e:
            result["error"] = str(e)
            print(f"❌ Publish error: {e}")
        
        return result
    
    def send_notification(self, article: Article, publish_result: dict) -> bool:
        """Send notification about published article."""
        webhook_url = self.config.notification_webhook
        
        if not webhook_url:
            return False
        
        try:
            import requests
            
            # Build notification message
            status = "✅ Published" if publish_result["success"] else "❌ Failed"
            
            message = {
                "content": f"""**{status}: New Blog Post**
                
📝 **{article.title}**
📅 {article.pub_date}
📊 {article.word_count} words
🏷️ Tags: {', '.join(article.tags)}

{f"Git pushed: {'Yes' if publish_result['pushed'] else 'No'}" if publish_result['success'] else f"Error: {publish_result.get('error', 'Unknown')}"}
"""
            }
            
            response = requests.post(webhook_url, json=message, timeout=10)
            return response.status_code == 200
            
        except Exception as e:
            print(f"Notification error: {e}")
            return False


class DryRunPublisher(Publisher):
    """Publisher that simulates publishing without actually writing files."""
    
    def save_article(self, article: Article) -> Path:
        """Simulate saving article."""
        filepath = self.content_path / f"{article.pub_date}-{article.slug}.md"
        print(f"🔍 [DRY RUN] Would save article: {filepath}")
        print(f"   Title: {article.title}")
        print(f"   Words: {article.word_count}")
        return filepath
    
    def update_index(self, article: Article, filepath: Path) -> None:
        """Simulate updating index."""
        print(f"🔍 [DRY RUN] Would update posts index")
    
    def git_commit_and_push(self, article: Article, filepath: Path) -> bool:
        """Simulate git operations."""
        print(f"🔍 [DRY RUN] Would commit and push: {article.title}")
        return True
