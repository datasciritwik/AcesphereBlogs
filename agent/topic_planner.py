"""
Topic Planner Module for the AI Blog Agent.
Generates structured topic briefs using LLM based on business context and keywords.
"""

import json
import random
from dataclasses import dataclass
from typing import List, Optional
from openai import OpenAI

from .config import Config


@dataclass
class TopicBrief:
    """Structured topic brief for article generation."""
    topic: str
    title: str
    angle: str
    target_keywords: List[str]
    target_audience: str
    sources_required: bool
    outline: List[str]
    
    def to_dict(self) -> dict:
        """Convert to dictionary."""
        return {
            "topic": self.topic,
            "title": self.title,
            "angle": self.angle,
            "target_keywords": self.target_keywords,
            "target_audience": self.target_audience,
            "sources_required": self.sources_required,
            "outline": self.outline
        }
    
    @classmethod
    def from_dict(cls, data: dict) -> "TopicBrief":
        """Create from dictionary."""
        return cls(
            topic=data.get("topic", ""),
            title=data.get("title", ""),
            angle=data.get("angle", ""),
            target_keywords=data.get("target_keywords", []),
            target_audience=data.get("target_audience", ""),
            sources_required=data.get("sources_required", True),
            outline=data.get("outline", [])
        )


class TopicPlanner:
    """Generates topic briefs for blog articles using LLM."""
    
    SYSTEM_PROMPT = """You are an expert content strategist for {company_name}, an AI-driven hiring and recruitment platform.

Your job is to generate unique, SEO-optimized blog topic ideas that:
1. Align with the company's content pillars and business focus
2. Target relevant keywords for organic search traffic
3. Provide value to the target audience
4. Have NOT been covered in previous posts

Company Context:
{business_context}

Brand Voice:
- Tone: {tone}
- Style: {style}
- Focus: {focus}

Content Pillars:
{content_pillars}

Target Audience:
{target_audience}

Previously Published Topics (AVOID THESE):
{used_topics}

Available Keywords to Target:
{keywords}"""

    USER_PROMPT = """Generate a unique blog topic brief for {company_name}.

Requirements:
1. Topic must be DIFFERENT from all previously published topics
2. Title should include a primary keyword and be compelling (under 60 chars)
3. Angle should specify the perspective or unique take
4. Include 3-5 target keywords for SEO
5. Specify which audience segment this targets
6. Indicate if web research is needed for facts/statistics
7. Provide a 4-6 point outline with H2 headings

Respond ONLY with valid JSON in this exact format:
{{
    "topic": "Main topic/theme",
    "title": "SEO-optimized article title",
    "angle": "Unique perspective or approach",
    "target_keywords": ["keyword1", "keyword2", "keyword3"],
    "target_audience": "Primary audience segment",
    "sources_required": true,
    "outline": [
        "H2: First main section",
        "H2: Second main section",
        "H2: Third main section",
        "H2: Conclusion or call to action"
    ]
}}"""

    def __init__(self, config: Config):
        """Initialize the topic planner with configuration."""
        self.config = config
        self.client = OpenAI(
            api_key=config.groq_api_key,
            base_url="https://api.groq.com/openai/v1"
        )
    
    def _build_system_prompt(self) -> str:
        """Build the system prompt with context."""
        brand_voice = self.config.get_brand_voice()
        
        return self.SYSTEM_PROMPT.format(
            company_name=self.config.get_company_name(),
            business_context=self.config.business_context.get("business_focus", ""),
            tone=brand_voice.get("tone", "Professional"),
            style=brand_voice.get("style", "Informative"),
            focus=brand_voice.get("focus", "Value"),
            content_pillars="\n".join(f"- {p}" for p in self.config.get_content_pillars()),
            target_audience="\n".join(f"- {a}" for a in self.config.get_target_audience()),
            used_topics="\n".join(f"- {t}" for t in self.config.get_used_topics()) or "None yet",
            keywords=", ".join(random.sample(
                self.config.get_all_keywords(), 
                min(20, len(self.config.get_all_keywords()))
            ))
        )
    
    def _build_user_prompt(self) -> str:
        """Build the user prompt."""
        return self.USER_PROMPT.format(
            company_name=self.config.get_company_name()
        )
    
    def generate_topic(self) -> TopicBrief:
        """Generate a new topic brief using the LLM."""
        system_prompt = self._build_system_prompt()
        user_prompt = self._build_user_prompt()
        
        response = self.client.chat.completions.create(
            model="openai/gpt-oss-120b",
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt}
            ],
            temperature=0.8,  # Higher creativity for unique topics
            max_tokens=1000,
            response_format={"type": "json_object"}
        )
        
        # Parse the response
        content = response.choices[0].message.content
        topic_data = json.loads(content)
        
        return TopicBrief.from_dict(topic_data)
    
    def validate_topic(self, topic: TopicBrief) -> bool:
        """Validate that topic hasn't been used before."""
        used_topics = [t.lower() for t in self.config.get_used_topics()]
        
        # Check if topic or title is too similar to existing ones
        if topic.topic.lower() in used_topics:
            return False
        
        # Check for significant title overlap
        for used in used_topics:
            if self._similarity_score(topic.title.lower(), used) > 0.7:
                return False
        
        return True
    
    def _similarity_score(self, s1: str, s2: str) -> float:
        """Calculate simple word overlap similarity."""
        words1 = set(s1.split())
        words2 = set(s2.split())
        
        if not words1 or not words2:
            return 0.0
        
        intersection = words1.intersection(words2)
        union = words1.union(words2)
        
        return len(intersection) / len(union)
    
    def generate_unique_topic(self, max_attempts: int = 3) -> Optional[TopicBrief]:
        """Generate a topic, retrying if it's too similar to existing ones."""
        for attempt in range(max_attempts):
            topic = self.generate_topic()
            
            if self.validate_topic(topic):
                return topic
            
            print(f"Topic too similar to existing, retrying... (attempt {attempt + 1})")
        
        # Return the last generated topic even if validation failed
        return topic
