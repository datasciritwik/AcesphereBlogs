"""
Researcher Module for the AI Blog Agent.
Performs web research to gather facts and statistics for article content.
"""

import re
from dataclasses import dataclass
from typing import List, Optional
from openai import OpenAI

from .config import Config
from .topic_planner import TopicBrief

# Try to import duckduckgo_search, but make it optional
try:
    from duckduckgo_search import DDGS
    HAS_DDGS = True
except ImportError:
    HAS_DDGS = False


@dataclass
class ResearchNotes:
    """Structured research notes for article writing."""
    topic: str
    facts: List[str]
    statistics: List[str]
    sources: List[dict]
    key_points: List[str]
    
    def to_dict(self) -> dict:
        """Convert to dictionary."""
        return {
            "topic": self.topic,
            "facts": self.facts,
            "statistics": self.statistics,
            "sources": self.sources,
            "key_points": self.key_points
        }
    
    def to_prompt_context(self) -> str:
        """Format research notes for use in article writing prompt."""
        sections = []
        
        if self.facts:
            sections.append("Key Facts:\n" + "\n".join(f"- {f}" for f in self.facts))
        
        if self.statistics:
            sections.append("Statistics:\n" + "\n".join(f"- {s}" for s in self.statistics))
        
        if self.key_points:
            sections.append("Key Points:\n" + "\n".join(f"- {p}" for p in self.key_points))
        
        if self.sources:
            sources_text = "\n".join(
                f"- {s.get('title', 'Source')}: {s.get('url', '')}" 
                for s in self.sources[:5]
            )
            sections.append(f"Sources:\n{sources_text}")
        
        return "\n\n".join(sections)


class Researcher:
    """Gathers research and facts for article writing."""
    
    SYNTHESIS_PROMPT = """You are a research analyst. Given the following search results about "{topic}", extract and synthesize:

1. Key facts (verified, factual statements)
2. Statistics (numbers, percentages, data points)  
3. Key points (important insights and takeaways)

Search Results:
{search_results}

Respond in this JSON format:
{{
    "facts": ["fact 1", "fact 2", ...],
    "statistics": ["stat 1", "stat 2", ...],
    "key_points": ["point 1", "point 2", ...]
}}

Rules:
- Only include accurate, verifiable information
- Do not make up statistics
- Keep each point concise (1-2 sentences max)
- Include 3-5 items per category
- Focus on information relevant to HR tech and AI hiring"""

    def __init__(self, config: Config):
        """Initialize the researcher with configuration."""
        self.config = config
        self.client = OpenAI(
            api_key=config.groq_api_key,
            base_url="https://api.groq.com/openai/v1"
        )
    
    def search_web(self, query: str, max_results: int = 5) -> List[dict]:
        """Search the web for information on a topic."""
        if not HAS_DDGS:
            # Fallback: return empty results if duckduckgo-search not installed
            print("Warning: duckduckgo-search not installed, skipping web search")
            return []
        
        try:
            with DDGS() as ddgs:
                results = list(ddgs.text(query, max_results=max_results))
                return [
                    {
                        "title": r.get("title", ""),
                        "body": r.get("body", ""),
                        "url": r.get("href", "")
                    }
                    for r in results
                ]
        except Exception as e:
            print(f"Web search error: {e}")
            return []
    
    def _format_search_results(self, results: List[dict]) -> str:
        """Format search results for the LLM."""
        if not results:
            return "No search results available."
        
        formatted = []
        for i, r in enumerate(results, 1):
            formatted.append(f"""
Result {i}:
Title: {r.get('title', 'N/A')}
Content: {r.get('body', 'N/A')}
URL: {r.get('url', 'N/A')}
""")
        return "\n".join(formatted)
    
    def synthesize_research(self, topic: str, search_results: List[dict]) -> ResearchNotes:
        """Use LLM to synthesize search results into structured notes."""
        formatted_results = self._format_search_results(search_results)
        
        prompt = self.SYNTHESIS_PROMPT.format(
            topic=topic,
            search_results=formatted_results
        )
        
        response = self.client.chat.completions.create(
            model="openai/gpt-oss-20b",  # Use smaller model for research synthesis
            messages=[
                {"role": "user", "content": prompt}
            ],
            temperature=0.3,  # Lower temperature for factual accuracy
            max_tokens=800
        )
        
        import json
        import re
        content = response.choices[0].message.content
        # Extract JSON from response
        json_match = re.search(r'\{[^{}]*"facts"[^{}]*\}', content, re.DOTALL)
        if json_match:
            data = json.loads(json_match.group())
        else:
            data = {"facts": [], "statistics": [], "key_points": []}
        
        # Format sources from search results
        sources = [
            {"title": r.get("title", ""), "url": r.get("url", "")}
            for r in search_results if r.get("url")
        ]
        
        return ResearchNotes(
            topic=topic,
            facts=data.get("facts", []),
            statistics=data.get("statistics", []),
            sources=sources,
            key_points=data.get("key_points", [])
        )
    
    def research_topic(self, topic_brief: TopicBrief) -> ResearchNotes:
        """Perform full research for a topic brief."""
        # Build search queries from topic and keywords
        queries = [
            f"{topic_brief.topic} {topic_brief.target_keywords[0] if topic_brief.target_keywords else ''}",
            f"{topic_brief.title} statistics data",
        ]
        
        # Collect all search results
        all_results = []
        for query in queries:
            results = self.search_web(query, max_results=3)
            all_results.extend(results)
        
        # Remove duplicates by URL
        seen_urls = set()
        unique_results = []
        for r in all_results:
            url = r.get("url", "")
            if url and url not in seen_urls:
                seen_urls.add(url)
                unique_results.append(r)
        
        # Synthesize into structured notes
        if unique_results:
            return self.synthesize_research(topic_brief.topic, unique_results)
        else:
            # Return empty notes if no search results
            return ResearchNotes(
                topic=topic_brief.topic,
                facts=[],
                statistics=[],
                sources=[],
                key_points=[]
            )
    
    def generate_fallback_notes(self, topic_brief: TopicBrief) -> ResearchNotes:
        """Generate research notes using LLM knowledge when web search fails."""
        prompt = f"""As an expert in HR tech and AI hiring, provide factual information about:
Topic: {topic_brief.topic}
Title: {topic_brief.title}

Provide accurate, well-known facts and general industry statistics (you can use approximations like "studies show..." or "according to industry reports...").

Respond in JSON format:
{{
    "facts": ["fact 1", "fact 2", "fact 3"],
    "statistics": ["stat 1", "stat 2"],
    "key_points": ["point 1", "point 2", "point 3"]
}}"""

        response = self.client.chat.completions.create(
            model="openai/gpt-oss-20b",
            messages=[{"role": "user", "content": prompt}],
            temperature=0.5,
            max_tokens=600
        )
        
        import json
        import re
        content = response.choices[0].message.content
        json_match = re.search(r'\{[^{}]*"facts"[^{}]*\}', content, re.DOTALL)
        if json_match:
            data = json.loads(json_match.group())
        else:
            data = {"facts": [], "statistics": [], "key_points": []}
        
        return ResearchNotes(
            topic=topic_brief.topic,
            facts=data.get("facts", []),
            statistics=data.get("statistics", []),
            sources=[],
            key_points=data.get("key_points", [])
        )
