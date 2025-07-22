import json
import feedparser
from datetime import datetime
from typing import List, Dict, Any, Optional
from langchain_google_genai import ChatGoogleGenerativeAI
from langchain.prompts import PromptTemplate, ChatPromptTemplate
from langchain.schema import BaseOutputParser
from langchain.chains import LLMChain
import os
from urllib.parse import urlparse
import requests

RSS_URL = "https://news.google.com/rss/search?q=Harry%20Styles&hl=en-US&gl=US&ceid=US:en"

class ArticleCategorizer:
    """LangChain-powered agent for categorizing RSS articles into sections"""
    
    def __init__(self, google_api_key: str = None, model_name: str = "gemini-2.5-pro"):
        """
        Initialize the article categorizer
        
        Args:
            google_api_key: Google API key (can also be set via GOOGLE_API_KEY env var)
            model_name: Model to use for categorization (default: gemini-2.0-flash-exp)
        """
        if google_api_key:
            os.environ["GOOGLE_API_KEY"] = google_api_key
        elif not os.getenv("GOOGLE_API_KEY"):
            raise ValueError("Google API key must be provided either as parameter or GOOGLE_API_KEY env var")
        
        self.llm = ChatGoogleGenerativeAI(model=model_name, temperature=0.3)
        
        # Prompt for categorizing articles
        self.categorization_prompt = ChatPromptTemplate.from_template(
            """You are an expert media analyst and content categorizer. Given a list of news articles, analyze and categorize them with media tier classification and coverage differentiation.

Articles to categorize:
{articles_text}

Instructions:
1. **Media Tier Classification** - Classify each source:
   - **Top-tier**: Major publications (BBC, CNN, Reuters, The Guardian, New York Times, Associated Press, etc.)
   - **Mid-tier**: Regional publications, entertainment magazines, music industry publications
   - **Low-tier**: Blogs, social media mentions, unknown/unverified sources

2. **Coverage Differentiation** - Determine coverage type:
   - **headline**: Subject is the main focus of the article (mentioned in title/headline)
   - **mention**: Subject is mentioned but not the primary focus

3. **Section Organization** - Group by tier and coverage type:
   - Create sections like "Top-Tier Headlines", "Top-Tier Mentions", "Mid-Tier Coverage", etc.
   - Prioritize top-tier headline coverage first
   - Group similar tiers together

4. **Article Processing**:
   - Extract source name from URL or article details
   - Create clear, descriptive titles
   - Preserve original URLs exactly
   - Aim for 4-8 sections based on tier/coverage combinations

Output the result as valid JSON in this exact format:
{{
    "subject": "News Summary - [Current Date]",
    "sections": [
        {{
            "heading": "Top-Tier Headlines",
            "items": [
                {{
                    "title": "Clear, descriptive article title",
                    "link": "original_url",
                    "source": "Source Name",
                    "tier": "top-tier",
                    "coverage_type": "headline"
                }}
            ]
        }},
        {{
            "heading": "Mid-Tier Coverage",
            "items": [
                {{
                    "title": "Article title",
                    "link": "original_url", 
                    "source": "Source Name",
                    "tier": "mid-tier",
                    "coverage_type": "mention"
                }}
            ]
        }}
    ],
    "filename": "news-report-[timestamp].pdf"
}}

Ensure the JSON is valid and properly formatted. Always include source, tier, and coverage_type for each item."""
        )
        
        self.categorization_chain = LLMChain(
            llm=self.llm,
            prompt=self.categorization_prompt
        )

    def fetch_rss_articles(self, rss_url: str, max_articles: int = 20) -> List[Dict[str, str]]:
        """
        Fetch articles from RSS feed with source detection
        
        Args:
            rss_url: URL of the RSS feed
            max_articles: Maximum number of articles to fetch
            
        Returns:
            List of articles with title, link, summary, and source
        """
        try:
            # Parse the RSS feed
            feed = feedparser.parse(rss_url)
            
            if feed.bozo:
                print(f"Warning: RSS feed may have issues: {feed.bozo_exception}")
            
            # Extract source info from feed
            feed_source = "Unknown Source"
            if hasattr(feed.feed, 'title'):
                feed_source = feed.feed.title
            elif hasattr(feed.feed, 'link'):
                parsed_url = urlparse(feed.feed.link)
                feed_source = parsed_url.netloc.replace('www.', '')
            
            articles = []
            for entry in feed.entries[:max_articles]:
                # Extract source from individual article if available
                article_source = feed_source
                if entry.get("link"):
                    try:
                        parsed_url = urlparse(entry.get("link"))
                        domain = parsed_url.netloc.replace('www.', '')
                        if domain:
                            article_source = domain
                    except:
                        pass
                
                article = {
                    "title": entry.get("title", "Untitled"),
                    "link": entry.get("link", ""),
                    "summary": entry.get("summary", entry.get("description", "")),
                    "published": entry.get("published", ""),
                    "source": article_source
                }
                
                # Clean up the title and summary
                article["title"] = self._clean_text(article["title"])
                article["summary"] = self._clean_text(article["summary"])
                
                articles.append(article)
            
            print(f"Successfully fetched {len(articles)} articles from {feed_source}")
            return articles
            
        except Exception as e:
            raise Exception(f"Error fetching RSS feed {rss_url}: {str(e)}")

    def _clean_text(self, text: str) -> str:
        """Clean HTML tags and extra whitespace from text"""
        import re
        # Remove HTML tags
        text = re.sub(r'<[^>]+>', '', text)
        # Clean up whitespace
        text = ' '.join(text.split())
        return text.strip()

    def categorize_articles(self, articles: List[Dict[str, str]], subject_override: str = None) -> Dict[str, Any]:
        """
        Categorize articles into sections using LangChain
        
        Args:
            articles: List of articles to categorize
            subject_override: Override the auto-generated subject
            
        Returns:
            JSON structure with categorized articles
        """
        if not articles:
            return {
                "subject": subject_override or f"News Summary - {datetime.now().strftime('%B %d, %Y')}",
                "sections": [],
                "filename": f"news-report-{datetime.now().strftime('%Y%m%d-%H%M%S')}.pdf"
            }
        
        # Prepare articles text for the prompt
        articles_text = ""
        for i, article in enumerate(articles, 1):
            articles_text += f"{i}. Title: {article['title']}\n"
            articles_text += f"   URL: {article['link']}\n"
            if article['summary']:
                articles_text += f"   Summary: {article['summary'][:200]}...\n"
            articles_text += "\n"
        
        try:
            # Get categorization from LangChain
            result = self.categorization_chain.run(articles_text=articles_text)
            
            # Parse the JSON response
            categorized_data = json.loads(result)
            
            # Override subject if provided
            if subject_override:
                categorized_data["subject"] = subject_override
            
            # Ensure filename has timestamp
            if "filename" not in categorized_data:
                categorized_data["filename"] = f"news-report-{datetime.now().strftime('%Y%m%d-%H%M%S')}.pdf"
            
            return categorized_data
            
        except json.JSONDecodeError as e:
            print(f"Error parsing LLM response as JSON: {e}")
            print(f"Raw response: {result}")
            # Fallback to simple categorization
            return self._fallback_categorization(articles, subject_override)
        except Exception as e:
            print(f"Error in categorization: {e}")
            return self._fallback_categorization(articles, subject_override)

    def _fallback_categorization(self, articles: List[Dict[str, str]], subject_override: str = None) -> Dict[str, Any]:
        """
        Fallback categorization with basic tier and coverage classification
        """
        print("Using fallback categorization with basic tier classification...")
        
        # Basic tier classification based on domain patterns
        def classify_source_tier(source: str) -> str:
            source_lower = source.lower()
            
            # Top-tier sources
            top_tier_domains = [
                'bbc.co.uk', 'cnn.com', 'reuters.com', 'theguardian.com', 
                'nytimes.com', 'apnews.com', 'washingtonpost.com', 'npr.org',
                'abcnews.go.com', 'cbsnews.com', 'nbcnews.com', 'news.google.com'
            ]
            
            # Mid-tier sources  
            mid_tier_domains = [
                'variety.com', 'hollywoodreporter.com', 'entertainment.ie',
                'rollingstone.com', 'billboard.com', 'pitchfork.com',
                'sky.com', 'independent.co.uk', 'mirror.co.uk', 'thesun.co.uk'
            ]
            
            for domain in top_tier_domains:
                if domain in source_lower:
                    return "top-tier"
            
            for domain in mid_tier_domains:
                if domain in source_lower:
                    return "mid-tier"
            
            return "low-tier"
        
        # Basic coverage type classification
        def classify_coverage_type(title: str, subject: str = "Harry Styles") -> str:
            title_lower = title.lower()
            subject_lower = subject.lower()
            
            # Check if subject appears early in title (likely headline coverage)
            words = title_lower.split()
            if len(words) >= 3:
                first_three = ' '.join(words[:3])
                if any(part in first_three for part in subject_lower.split()):
                    return "headline"
            
            # If subject is mentioned but not prominently, it's a mention
            if any(part in title_lower for part in subject_lower.split()):
                return "mention"
            
            return "mention"  # Default to mention
        
        # Categorize articles by tier and coverage
        categorized = {"top-tier": {"headline": [], "mention": []}, 
                      "mid-tier": {"headline": [], "mention": []},
                      "low-tier": {"headline": [], "mention": []}}
        
        for article in articles:
            source = article.get('source', 'Unknown')
            tier = classify_source_tier(source)
            coverage = classify_coverage_type(article['title'])
            
            categorized[tier][coverage].append({
                "title": article["title"],
                "link": article["link"],
                "source": source,
                "tier": tier,
                "coverage_type": coverage
            })
        
        # Build sections with priority order
        sections = []
        
        if categorized["top-tier"]["headline"]:
            sections.append({
                "heading": "Top-Tier Headlines",
                "items": categorized["top-tier"]["headline"]
            })
        
        if categorized["top-tier"]["mention"]:
            sections.append({
                "heading": "Top-Tier Mentions", 
                "items": categorized["top-tier"]["mention"]
            })
        
        if categorized["mid-tier"]["headline"]:
            sections.append({
                "heading": "Mid-Tier Headlines",
                "items": categorized["mid-tier"]["headline"]
            })
        
        if categorized["mid-tier"]["mention"]:
            sections.append({
                "heading": "Mid-Tier Coverage",
                "items": categorized["mid-tier"]["mention"]
            })
        
        if categorized["low-tier"]["headline"] or categorized["low-tier"]["mention"]:
            low_tier_items = categorized["low-tier"]["headline"] + categorized["low-tier"]["mention"]
            sections.append({
                "heading": "Other Coverage",
                "items": low_tier_items
            })
        
        # Fallback if no sections created
        if not sections:
            sections = [{
                "heading": "News Updates",
                "items": [{
                    "title": article["title"],
                    "link": article["link"],
                    "source": article.get("source", "Unknown"),
                    "tier": "low-tier",
                    "coverage_type": "mention"
                } for article in articles]
            }]
        
        return {
            "subject": subject_override or f"News Summary - {datetime.now().strftime('%B %d, %Y')}",
            "sections": sections,
            "filename": f"news-report-{datetime.now().strftime('%Y%m%d-%H%M%S')}.pdf"
        }

    def process_rss_to_json(self, rss_url: str, max_articles: int = 20, subject_override: str = None) -> Dict[str, Any]:
        """
        Complete pipeline: fetch RSS -> categorize -> return JSON
        
        Args:
            rss_url: RSS feed URL
            max_articles: Maximum articles to process
            subject_override: Custom subject line
            
        Returns:
            JSON structure ready for report generation
        """
        print(f"Fetching articles from: {rss_url}")
        articles = self.fetch_rss_articles(rss_url, max_articles)
        print(f"Fetched {len(articles)} articles")
        
        print("Categorizing articles...")
        categorized_data = self.categorize_articles(articles, subject_override)
        print(f"Created {len(categorized_data['sections'])} sections")
        
        return categorized_data

    def save_json(self, data: Dict[str, Any], output_path: str) -> str:
        """Save categorized data to JSON file"""
        with open(output_path, 'w', encoding='utf-8') as f:
            json.dump(data, f, indent=2, ensure_ascii=False)
        return output_path


def create_report_from_rss(rss_url: str = None, max_articles: int = 20, subject_override: str = None, 
                          output_json: str = None, output_pdf: str = None, 
                          google_api_key: str = None) -> tuple[str, str]:
    """
    High-level function to create a report from RSS feed
    
    Args:
        rss_url: RSS feed URL (defaults to Harry Styles Google News)
        max_articles: Maximum articles to process
        subject_override: Custom subject line
        output_json: Output path for JSON file
        output_pdf: Output path for PDF file
        google_api_key: Google API key
        
    Returns:
        Tuple of (json_path, pdf_path)
    """
    from report_generator import generate_report_pdf
    
    # Use default RSS URL if none provided
    if rss_url is None:
        rss_url = RSS_URL
        if subject_override is None:
            subject_override = "Harry Styles News Summary"
    
    # Initialize the agent
    agent = ArticleCategorizer(google_api_key)
    
    # Process RSS to JSON
    data = agent.process_rss_to_json(rss_url, max_articles, subject_override)
    
    # Save JSON
    if not output_json:
        output_json = f"rss-data-{datetime.now().strftime('%Y%m%d-%H%M%S')}.json"
    json_path = agent.save_json(data, output_json)
    
    # Generate PDF
    if not output_pdf:
        output_pdf = data["filename"]
    
    pdf_bytes = generate_report_pdf(
        subject=data["subject"],
        sections=data["sections"]
    )
    
    with open(output_pdf, 'wb') as f:
        f.write(pdf_bytes)
    
    return json_path, output_pdf


if __name__ == "__main__":
    # Example usage
    import sys
    
    # Check for API key
    if not os.getenv("GOOGLE_API_KEY"):
        print("Please set GOOGLE_API_KEY environment variable")
        print("You can get an API key from: https://aistudio.google.com/app/apikey")
        sys.exit(1)
    
    print("RSS to Report Generator Demo")
    print("=" * 40)
    
    # Use the default RSS URL (Harry Styles Google News)
    print(f"Processing: Harry Styles Google News")
    print(f"RSS URL: {RSS_URL}")
    
    try:
        json_path, pdf_path = create_report_from_rss(
            max_articles=15,
            subject_override="Harry Styles News Summary"
        )
        
        print(f"✅ Success!")
        print(f"📄 JSON saved: {json_path}")
        print(f"📄 PDF saved: {pdf_path}")
        
    except Exception as e:
        print(f"❌ Error: {e}")
        sys.exit(1) 