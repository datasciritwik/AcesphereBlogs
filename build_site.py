#!/usr/bin/env python3
"""
Static site builder for AcesphereAI Blog.
Converts Markdown posts to HTML and generates the site.
"""

import os
import re
import json
from pathlib import Path
from datetime import datetime

import markdown
import yaml
from jinja2 import Environment, FileSystemLoader


# Paths
BASE_PATH = Path(__file__).parent
CONTENT_PATH = BASE_PATH / "content" / "posts"
SITE_PATH = BASE_PATH / "site"
TEMPLATES_PATH = BASE_PATH / "site" / "templates"


def ensure_dirs():
    """Ensure output directories exist."""
    (SITE_PATH / "posts").mkdir(parents=True, exist_ok=True)


def parse_frontmatter(content: str) -> tuple[dict, str]:
    """Parse YAML frontmatter from markdown content."""
    if content.startswith("---"):
        parts = content.split("---", 2)
        if len(parts) >= 3:
            frontmatter = yaml.safe_load(parts[1])
            body = parts[2].strip()
            return frontmatter, body
    return {}, content


def get_all_posts() -> list[dict]:
    """Get all posts sorted by date (newest first)."""
    posts = []
    
    if not CONTENT_PATH.exists():
        return posts
    
    for md_file in CONTENT_PATH.glob("*.md"):
        with open(md_file, "r", encoding="utf-8") as f:
            content = f.read()
        
        frontmatter, body = parse_frontmatter(content)
        
        # Generate slug from filename
        slug = md_file.stem
        # Remove date prefix if present (YYYY-MM-DD-)
        if re.match(r"^\d{4}-\d{2}-\d{2}-", slug):
            slug = slug[11:]
        
        # If slug is empty, generate from title
        if not slug:
            title = frontmatter.get("title", "untitled")
            slug = re.sub(r'[^a-z0-9\s-]', '', title.lower())
            slug = re.sub(r'\s+', '-', slug)
            slug = re.sub(r'-+', '-', slug).strip('-')[:60]
        
        posts.append({
            "title": frontmatter.get("title", "Untitled"),
            "description": frontmatter.get("description", ""),
            "pub_date": frontmatter.get("pubDate", ""),
            "tags": frontmatter.get("tags", []),
            "slug": slug,
            "body": body,
            "filepath": md_file
        })
    
    # Sort by date (newest first)
    posts.sort(key=lambda p: p.get("pub_date", ""), reverse=True)
    return posts


def build_post_html(post: dict, env: Environment) -> str:
    """Build HTML for a single post."""
    template = env.get_template("post.html")
    
    # Convert markdown to HTML
    md = markdown.Markdown(extensions=["fenced_code", "tables", "toc"])
    html_content = md.convert(post["body"])
    
    return template.render(
        title=post["title"],
        description=post["description"],
        pub_date=post["pub_date"],
        tags=post["tags"],
        content=html_content,
        base_url="../"  # Relative path from posts/ to root
    )


def build_index_html(posts: list[dict], env: Environment) -> str:
    """Build the index page HTML."""
    template = env.get_template("index.html")
    return template.render(posts=posts, base_url="")


def create_default_templates():
    """Create default templates if they don't exist."""
    TEMPLATES_PATH.mkdir(parents=True, exist_ok=True)
    
    # Base template
    base_template = '''<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <meta name="description" content="{{ description | default('AcesphereAI Blog - AI Hiring Insights') }}">
    <title>{% block title %}AcesphereAI Blog{% endblock %}</title>
    <link rel="preconnect" href="https://fonts.googleapis.com">
    <link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>
    <link href="https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700&display=swap" rel="stylesheet">
    <style>
        :root {
            --primary: #6366f1;
            --primary-dark: #4f46e5;
            --bg: #0f172a;
            --bg-card: #1e293b;
            --text: #e2e8f0;
            --text-muted: #94a3b8;
            --border: #334155;
            --accent: #22d3ee;
        }
        
        * {
            margin: 0;
            padding: 0;
            box-sizing: border-box;
        }
        
        body {
            font-family: 'Inter', -apple-system, BlinkMacSystemFont, sans-serif;
            background: var(--bg);
            color: var(--text);
            line-height: 1.7;
            min-height: 100vh;
        }
        
        .container {
            max-width: 800px;
            margin: 0 auto;
            padding: 2rem 1.5rem;
        }
        
        header {
            border-bottom: 1px solid var(--border);
            padding-bottom: 2rem;
            margin-bottom: 3rem;
        }
        
        .logo {
            font-size: 1.5rem;
            font-weight: 700;
            color: var(--accent);
            text-decoration: none;
            display: flex;
            align-items: center;
            gap: 0.5rem;
        }
        
        .logo:hover {
            opacity: 0.9;
        }
        
        .tagline {
            color: var(--text-muted);
            margin-top: 0.5rem;
            font-size: 0.95rem;
        }
        
        {% block styles %}{% endblock %}
    </style>
</head>
<body>
    <div class="container">
        <header>
            <a href="/" class="logo">
                <span>🤖</span> AcesphereAI Blog
            </a>
            <p class="tagline">Insights on AI-powered hiring and recruitment</p>
        </header>
        
        <main>
            {% block content %}{% endblock %}
        </main>
        
        <footer style="margin-top: 4rem; padding-top: 2rem; border-top: 1px solid var(--border); color: var(--text-muted); font-size: 0.875rem;">
            <p>&copy; {{ now.year }} AcesphereAI. All rights reserved.</p>
            <p style="margin-top: 0.5rem;">
                <a href="https://acesphereai.com" style="color: var(--accent); text-decoration: none;">Main Site</a>
            </p>
        </footer>
    </div>
</body>
</html>'''
    
    # Index template
    index_template = '''{% extends "base.html" %}

{% block title %}AcesphereAI Blog - AI Hiring Insights{% endblock %}

{% block styles %}
.posts-list {
    display: flex;
    flex-direction: column;
    gap: 2rem;
}

.post-card {
    background: var(--bg-card);
    border-radius: 12px;
    padding: 1.5rem;
    border: 1px solid var(--border);
    transition: transform 0.2s, border-color 0.2s;
}

.post-card:hover {
    transform: translateY(-2px);
    border-color: var(--primary);
}

.post-card h2 {
    font-size: 1.25rem;
    margin-bottom: 0.5rem;
}

.post-card h2 a {
    color: var(--text);
    text-decoration: none;
}

.post-card h2 a:hover {
    color: var(--accent);
}

.post-meta {
    color: var(--text-muted);
    font-size: 0.875rem;
    margin-bottom: 0.75rem;
}

.post-description {
    color: var(--text-muted);
    font-size: 0.95rem;
}

.tags {
    display: flex;
    gap: 0.5rem;
    margin-top: 1rem;
    flex-wrap: wrap;
}

.tag {
    background: var(--primary);
    color: white;
    padding: 0.25rem 0.75rem;
    border-radius: 999px;
    font-size: 0.75rem;
    font-weight: 500;
}

.empty-state {
    text-align: center;
    padding: 4rem 2rem;
    color: var(--text-muted);
}
{% endblock %}

{% block content %}
<h1 style="font-size: 2rem; margin-bottom: 2rem;">Latest Posts</h1>

{% if posts %}
<div class="posts-list">
    {% for post in posts %}
    <article class="post-card">
        <h2><a href="/posts/{{ post.slug }}">{{ post.title }}</a></h2>
        <p class="post-meta">{{ post.pub_date }}</p>
        <p class="post-description">{{ post.description }}</p>
        {% if post.tags %}
        <div class="tags">
            {% for tag in post.tags %}
            <span class="tag">{{ tag }}</span>
            {% endfor %}
        </div>
        {% endif %}
    </article>
    {% endfor %}
</div>
{% else %}
<div class="empty-state">
    <p>No posts yet. Check back soon!</p>
</div>
{% endif %}
{% endblock %}'''
    
    # Post template
    post_template = '''{% extends "base.html" %}

{% block title %}{{ title }} | AcesphereAI Blog{% endblock %}

{% block styles %}
article {
    line-height: 1.8;
}

article h1 {
    font-size: 2.25rem;
    margin-bottom: 1rem;
    line-height: 1.3;
}

article h2 {
    font-size: 1.5rem;
    margin: 2.5rem 0 1rem;
    color: var(--accent);
}

article h3 {
    font-size: 1.25rem;
    margin: 2rem 0 0.75rem;
}

article p {
    margin-bottom: 1.25rem;
}

article a {
    color: var(--accent);
    text-decoration: none;
    border-bottom: 1px solid transparent;
}

article a:hover {
    border-bottom-color: var(--accent);
}

article ul, article ol {
    margin: 1rem 0 1.5rem 1.5rem;
}

article li {
    margin-bottom: 0.5rem;
}

article code {
    background: var(--bg-card);
    padding: 0.2rem 0.4rem;
    border-radius: 4px;
    font-size: 0.9em;
}

article pre {
    background: var(--bg-card);
    padding: 1rem;
    border-radius: 8px;
    overflow-x: auto;
    margin: 1.5rem 0;
}

article pre code {
    background: none;
    padding: 0;
}

article blockquote {
    border-left: 3px solid var(--primary);
    padding-left: 1rem;
    margin: 1.5rem 0;
    color: var(--text-muted);
    font-style: italic;
}

.post-header {
    margin-bottom: 2.5rem;
    padding-bottom: 1.5rem;
    border-bottom: 1px solid var(--border);
}

.post-meta {
    color: var(--text-muted);
    font-size: 0.9rem;
    margin-top: 0.75rem;
}

.tags {
    display: flex;
    gap: 0.5rem;
    margin-top: 1rem;
    flex-wrap: wrap;
}

.tag {
    background: var(--primary);
    color: white;
    padding: 0.25rem 0.75rem;
    border-radius: 999px;
    font-size: 0.75rem;
    font-weight: 500;
}

.back-link {
    display: inline-block;
    margin-bottom: 2rem;
    color: var(--text-muted);
    text-decoration: none;
    font-size: 0.9rem;
}

.back-link:hover {
    color: var(--accent);
}
{% endblock %}

{% block content %}
<a href="/" class="back-link">← Back to all posts</a>

<article>
    <div class="post-header">
        <h1>{{ title }}</h1>
        <p class="post-meta">Published on {{ pub_date }}</p>
        {% if tags %}
        <div class="tags">
            {% for tag in tags %}
            <span class="tag">{{ tag }}</span>
            {% endfor %}
        </div>
        {% endif %}
    </div>
    
    <div class="post-content">
        {{ content | safe }}
    </div>
</article>
{% endblock %}'''
    
    # Write templates
    with open(TEMPLATES_PATH / "base.html", "w", encoding="utf-8") as f:
        f.write(base_template)
    
    with open(TEMPLATES_PATH / "index.html", "w", encoding="utf-8") as f:
        f.write(index_template)
    
    with open(TEMPLATES_PATH / "post.html", "w", encoding="utf-8") as f:
        f.write(post_template)
    
    print("✅ Created default templates")


def build_site():
    """Build the complete static site."""
    print("🔨 Building AcesphereAI Blog...")
    
    # Ensure directories and templates exist
    ensure_dirs()
    
    if not TEMPLATES_PATH.exists() or not (TEMPLATES_PATH / "base.html").exists():
        create_default_templates()
    
    # Set up Jinja2 environment
    env = Environment(loader=FileSystemLoader(TEMPLATES_PATH))
    env.globals["now"] = datetime.now()
    
    # Get all posts
    posts = get_all_posts()
    print(f"📝 Found {len(posts)} posts")
    
    # Build individual post pages
    for post in posts:
        html = build_post_html(post, env)
        output_path = SITE_PATH / "posts" / f"{post['slug']}.html"
        
        with open(output_path, "w", encoding="utf-8") as f:
            f.write(html)
        
        print(f"   ✓ Built: {post['slug']}")
    
    # Build index page
    index_html = build_index_html(posts, env)
    with open(SITE_PATH / "index.html", "w", encoding="utf-8") as f:
        f.write(index_html)
    
    print(f"\n✅ Site built successfully!")
    print(f"   Output: {SITE_PATH}")
    print(f"   Posts: {len(posts)}")


if __name__ == "__main__":
    build_site()
