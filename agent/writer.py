"""
Writer Module for the AI Blog Agent.
Generates SEO-optimized blog articles in Markdown format.
"""

import re
from datetime import datetime
from dataclasses import dataclass
from typing import List, Optional
from openai import OpenAI

from .config import Config
from .topic_planner import TopicBrief
from .researcher import ResearchNotes


@dataclass
class Article:
    """Generated blog article."""
    title: str
    slug: str
    description: str
    content: str
    pub_date: str
    tags: List[str]
    keywords: List[str]
    word_count: int
    
    def to_markdown(self) -> str:
        """Convert article to full Markdown with frontmatter."""
        frontmatter = f"""---
title: "{self.title}"
description: "{self.description}"
pubDate: "{self.pub_date}"
tags: {self.tags}
keywords: {self.keywords}
---

"""
        return frontmatter + self.content
    
    def to_dict(self) -> dict:
        """Convert to dictionary for indexing."""
        return {
            "title": self.title,
            "slug": self.slug,
            "description": self.description,
            "pub_date": self.pub_date,
            "tags": self.tags,
            "keywords": self.keywords,
            "word_count": self.word_count
        }


class Writer:
    """Generates SEO-optimized blog articles using LLM."""
    
    SYSTEM_PROMPT = """You are an expert content writer for {company_name}, an AI-driven hiring and recruitment platform.

Your writing style:
- Tone: {tone}
- Style: {style}
- Approach: {approach}

You write engaging, informative blog articles that:
1. Provide genuine value to readers
2. Are optimized for SEO without being spammy
3. Include practical insights and actionable advice
4. Maintain a professional yet accessible voice
5. Build topical authority in AI hiring and HR tech

Company website: {website}"""

    ARTICLE_PROMPT = """Write a comprehensive blog article based on this brief:

**Topic:** {topic}
**Title:** {title}
**Angle:** {angle}
**Target Keywords:** {keywords}
**Target Audience:** {audience}

**Article Outline:**
{outline}

**Research Notes:**
{research_notes}

**Requirements:**
1. Length: {min_words}-{max_words} words
2. Include the title as H1 at the start
3. Follow the outline structure using H2 headings
4. Naturally incorporate target keywords (don't stuff)
5. First 100 words should clearly state the value proposition
6. Include at least 2 external links to authoritative sources (use markdown format)
7. End with a compelling conclusion or call-to-action
8. Write in Markdown format

**Internal Links to Include:**
{internal_links}

Write the full article now (Markdown only, no frontmatter):"""

    META_PROMPT = """Based on this article title and content, generate:

Title: {title}

Content Preview:
{content_preview}

Generate a JSON response with:
1. "description": A compelling meta description (150-160 chars) that includes the primary keyword
2. "tags": 3-5 relevant tags as an array
3. "slug": URL-friendly slug (lowercase, hyphens, no special chars)

JSON only:"""

    def __init__(self, config: Config):
        """Initialize the writer with configuration."""
        self.config = config
        self.client = OpenAI(
            api_key=config.groq_api_key,
            base_url="https://api.groq.com/openai/v1"
        )
    
    def _build_system_prompt(self) -> str:
        """Build the system prompt with brand context."""
        brand_voice = self.config.get_brand_voice()
        
        return self.SYSTEM_PROMPT.format(
            company_name=self.config.get_company_name(),
            tone=brand_voice.get("tone", "Professional but accessible"),
            style=brand_voice.get("style", "Insight-driven"),
            approach=brand_voice.get("approach", "Educational and practical"),
            website=self.config.business_context.get("website", "https://acesphereai.com")
        )
    
    def _get_internal_links(self, limit: int = 3) -> str:
        """Get recent posts for internal linking."""
        posts = self.config.published_posts.get("posts", [])
        
        if not posts:
            return "No previous posts yet - skip internal linking for this article."
        
        recent = posts[-limit:]
        links = []
        for post in recent:
            title = post.get("title", "")
            slug = post.get("slug", "")
            if title and slug:
                links.append(f"- [{title}](/posts/{slug})")
        
        if links:
            return "Include natural references to these previous articles:\n" + "\n".join(links)
        return "No previous posts yet - skip internal linking for this article."
    
    def _build_article_prompt(
        self, 
        topic_brief: TopicBrief, 
        research_notes: Optional[ResearchNotes]
    ) -> str:
        """Build the article generation prompt."""
        research_context = ""
        if research_notes and (research_notes.facts or research_notes.key_points):
            research_context = research_notes.to_prompt_context()
        else:
            research_context = "No specific research notes - use your knowledge of HR tech and AI hiring."
        
        outline_text = "\n".join(f"- {item}" for item in topic_brief.outline)
        
        return self.ARTICLE_PROMPT.format(
            topic=topic_brief.topic,
            title=topic_brief.title,
            angle=topic_brief.angle,
            keywords=", ".join(topic_brief.target_keywords),
            audience=topic_brief.target_audience,
            outline=outline_text,
            research_notes=research_context,
            min_words=self.config.article_settings.min_words,
            max_words=self.config.article_settings.max_words,
            internal_links=self._get_internal_links()
        )
    
    def generate_article_content(
        self, 
        topic_brief: TopicBrief, 
        research_notes: Optional[ResearchNotes] = None
    ) -> str:
        """Generate the article content using LLM."""
        system_prompt = self._build_system_prompt()
        article_prompt = self._build_article_prompt(topic_brief, research_notes)
        
        response = self.client.chat.completions.create(
            model="openai/gpt-oss-120b",
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": article_prompt}
            ],
            temperature=0.7,
            max_tokens=2500
        )
        
        return response.choices[0].message.content
    
    def generate_meta(self, title: str, content: str) -> dict:
        """Generate metadata (description, tags, slug) for the article."""
        # Take first 500 chars of content for context
        content_preview = content[:500] + "..."
        
        prompt = self.META_PROMPT.format(
            title=title,
            content_preview=content_preview
        )
        
        response = self.client.chat.completions.create(
            model="openai/gpt-oss-20b",
            messages=[{"role": "user", "content": prompt}],
            temperature=0.3,
            max_tokens=200
        )
        
        import json
        import re
        response_content = response.choices[0].message.content
        
        # Try to extract JSON from response (handle markdown code blocks)
        try:
            # Try finding JSON object in the response
            json_match = re.search(r'\{[\s\S]*"description"[\s\S]*\}', response_content)
            if json_match:
                result = json.loads(json_match.group())
            else:
                result = {}
        except json.JSONDecodeError:
            result = {}
        
        # Ensure required fields have fallback values
        fallback_slug = self._generate_slug(title)
        fallback_desc = content_preview[:150].replace('"', "'").strip() + "..."
        
        return {
            "description": result.get("description") or fallback_desc,
            "tags": result.get("tags") or [],
            "slug": result.get("slug") or fallback_slug
        }
    
    def _count_words(self, text: str) -> int:
        """Count words in text."""
        # Remove markdown formatting for accurate count
        clean = re.sub(r'[#*_\[\]()>`]', '', text)
        words = clean.split()
        return len(words)
    
    def _generate_slug(self, title: str) -> str:
        """Generate URL-friendly slug from title."""
        # Convert to lowercase
        slug = title.lower()
        # Remove special characters
        slug = re.sub(r'[^a-z0-9\s-]', '', slug)
        # Replace spaces with hyphens
        slug = re.sub(r'\s+', '-', slug)
        # Remove multiple hyphens
        slug = re.sub(r'-+', '-', slug)
        # Trim hyphens from ends
        slug = slug.strip('-')
        return slug[:60]  # Limit length
    
    def write_article(
        self, 
        topic_brief: TopicBrief, 
        research_notes: Optional[ResearchNotes] = None
    ) -> Article:
        """Generate a complete article with metadata."""
        # Generate content
        content = self.generate_article_content(topic_brief, research_notes)
        
        # Generate metadata
        meta = self.generate_meta(topic_brief.title, content)
        
        # Build article object
        pub_date = datetime.now().strftime("%Y-%m-%d")
        
        return Article(
            title=topic_brief.title,
            slug=meta.get("slug") or self._generate_slug(topic_brief.title),
            description=meta.get("description", ""),
            content=content,
            pub_date=pub_date,
            tags=meta.get("tags", []),
            keywords=topic_brief.target_keywords,
            word_count=self._count_words(content)
        )
