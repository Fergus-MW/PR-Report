from fastapi import FastAPI, HTTPException
from fastapi.responses import Response
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from datetime import datetime
from typing import List, Optional
import uvicorn
import re

# Import RSS agent
from rss_agent import create_report_from_topic_memory

app = FastAPI(title="PR Coverage Report Generator", description="Generate PR coverage reports from any topic")

# Add CORS middleware with permissive settings
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Allow all origins
    allow_credentials=True,
    allow_methods=["*"],  # Allow all methods
    allow_headers=["*"],  # Allow all headers
)

# Single request model
class ReportRequest(BaseModel):
    subject: str  # The topic to search for (e.g., "Harry Styles", "Apple Inc", "climate change")
    max_articles: int = 20
    filename: str = None
    google_api_key: str = None  # Optional, can use env var
    language: str = "en-US"  # Language code
    country: str = "US"  # Country code

# New models for analytics endpoint
class AnalyticsRequest(BaseModel):
    clientId: str
    includeInternational: bool = False
    date: str  # Format: YYYY-MM-DD

class SentimentBreakdown(BaseModel):
    positive: int
    neutral: int
    negative: int

class Summary(BaseModel):
    topTierCount: int
    midTierCount: int
    blogCount: int
    totalMentions: int
    sentimentBreakdown: SentimentBreakdown

class Article(BaseModel):
    id: int
    title: str
    url: str
    outlet: str
    tier: str
    focusType: str
    estViews: int
    publishedAt: str
    sentiment: str
    summary: str
    includedInReport: bool = True

class ReportData(BaseModel):
    clientId: str
    clientName: str
    date: str
    generatedAt: str
    summary: Summary
    articles: List[Article]

class AnalyticsResponse(BaseModel):
    report: ReportData


def classify_outlet_tier(outlet: str) -> str:
    """Classify news outlet into tier based on outlet name"""
    outlet_lower = outlet.lower()
    
    # Top tier outlets
    top_tier = [
        'cnn', 'bbc', 'reuters', 'associated press', 'ap news', 'wall street journal', 
        'wsj', 'new york times', 'nytimes', 'washington post', 'guardian', 'times', 
        'bloomberg', 'npr', 'abc news', 'cbs news', 'nbc news', 'fox news'
    ]
    
    # Mid tier outlets  
    mid_tier = [
        'people', 'entertainment weekly', 'variety', 'hollywood reporter', 'rolling stone',
        'billboard', 'usa today', 'los angeles times', 'chicago tribune', 'boston globe',
        'time', 'newsweek', 'forbes', 'business insider', 'techcrunch', 'mashable'
    ]
    
    # Check for top tier
    for top in top_tier:
        if top in outlet_lower:
            return "Top"
    
    # Check for mid tier
    for mid in mid_tier:
        if mid in outlet_lower:
            return "Mid"
    
    # Default to Blog for everything else
    return "Blog"


def analyze_sentiment(title: str, description: str = "") -> str:
    """Basic sentiment analysis using keyword matching"""
    text = f"{title} {description}".lower()
    
    positive_words = [
        'success', 'amazing', 'incredible', 'fantastic', 'wonderful', 'excellent', 
        'brilliant', 'outstanding', 'celebrates', 'wins', 'triumph', 'achievement',
        'love', 'beautiful', 'stunning', 'gorgeous', 'perfect', 'best'
    ]
    
    negative_words = [
        'scandal', 'controversy', 'criticism', 'slams', 'attack', 'failure', 'disaster',
        'terrible', 'awful', 'disappointing', 'worst', 'crisis', 'problem', 'issues',
        'backlash', 'feud', 'drama', 'trouble', 'breaks up', 'divorce'
    ]
    
    positive_count = sum(1 for word in positive_words if word in text)
    negative_count = sum(1 for word in negative_words if word in text)
    
    if positive_count > negative_count:
        return "positive"
    elif negative_count > positive_count:
        return "negative"
    else:
        return "neutral"


def determine_focus_type(title: str, client_name: str) -> str:
    """Determine if the article is a headline focus or just a mention"""
    title_lower = title.lower()
    client_lower = client_name.lower()
    
    # If client name is in the first half of the title, it's likely headline focus
    title_words = title_lower.split()
    first_half = " ".join(title_words[:len(title_words)//2])
    
    if client_lower in first_half:
        return "Headline"
    elif client_lower in title_lower:
        return "Mention"
    else:
        return "Mention"


def estimate_views_by_tier(tier: str) -> int:
    """Estimate views based on outlet tier"""
    if tier == "Top":
        return 500000  # 500K average for top tier
    elif tier == "Mid":
        return 100000  # 100K average for mid tier
    else:
        return 25000   # 25K average for blogs


def format_client_name(client_id: str) -> str:
    """Convert client ID to proper client name"""
    # Convert kebab-case to proper case
    return client_id.replace('-', ' ').title()


@app.post("/generate-report")
async def generate_report(request: ReportRequest):
    """
    Generate a PR coverage report for any subject using AI-powered RSS analysis.
    
    Args:
        request: ReportRequest with subject and configuration
        
    Returns:
        PDF file as bytes with categorized news coverage
    """
    try:
        # Generate report from topic using RSS agent (in-memory for Cloud Run)
        json_data, pdf_bytes = create_report_from_topic_memory(
            topic=request.subject,
            max_articles=request.max_articles,
            subject_override=f"{request.subject} Coverage Report",
            google_api_key=request.google_api_key,
            language=request.language,
            country=request.country
        )
        
        # Generate filename
        filename = request.filename or f"{request.subject.replace(' ', '_')}-coverage-{datetime.now().strftime('%Y%m%d-%H%M%S')}.pdf"
        
        # Return the PDF as a response
        return Response(
            content=pdf_bytes,
            media_type="application/pdf",
            headers={"Content-Disposition": f"attachment; filename={filename}"}
        )
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error generating coverage report: {str(e)}")

@app.post("/analytics", response_model=AnalyticsResponse)
async def get_analytics(request: AnalyticsRequest):
    """
    Generate analytics report with structured data and metrics.
    
    Args:
        request: AnalyticsRequest with clientId and configuration
        
    Returns:
        Structured JSON with analytics data including tier counts, sentiment analysis, etc.
    """
    try:
        # Convert clientId to proper search term
        client_name = format_client_name(request.clientId)
        
        # Set language/country based on includeInternational flag
        language = "en" if request.includeInternational else "en-US"
        country = "US" if not request.includeInternational else None
        
        # Generate report data using RSS agent (in-memory)
        json_data, _ = create_report_from_topic_memory(
            topic=client_name,
            max_articles=50,  # Get more articles for better analytics
            subject_override=f"{client_name} Coverage Analysis",
            language=language,
            country=country
        )
        
        # Process articles and extract analytics
        articles = []
        article_id = 1
        
        # Extract articles from sections in the JSON data
        all_items = []
        if 'sections' in json_data:
            for section in json_data['sections']:
                if 'items' in section:
                    all_items.extend(section['items'])
        elif 'items' in json_data:
            all_items = json_data['items']
        
        # Process each article
        for item in all_items:
            # Extract outlet from source or infer from URL
            outlet = item.get('source', 'Unknown')
            if outlet == 'Unknown' and 'link' in item:
                # Try to extract domain from URL
                import re
                domain_match = re.search(r'https?://(?:www\.)?([^/]+)', item['link'])
                if domain_match:
                    outlet = domain_match.group(1).replace('.com', '').replace('.co.uk', '').title()
            
            # Classify and analyze
            tier = classify_outlet_tier(outlet)
            sentiment = analyze_sentiment(item['title'], item.get('summary', ''))
            focus_type = determine_focus_type(item['title'], client_name)
            est_views = estimate_views_by_tier(tier)
            
            # Create article object
            article = Article(
                id=article_id,
                title=item['title'],
                url=item['link'],
                outlet=outlet,
                tier=tier,
                focusType=focus_type,
                estViews=est_views,
                publishedAt=datetime.now().isoformat() + "Z",  # Use current time as placeholder
                sentiment=sentiment,
                summary=item.get('summary', item['title'][:100] + "..."),
                includedInReport=True
            )
            
            articles.append(article)
            article_id += 1
        
        # Calculate summary statistics
        top_tier_count = len([a for a in articles if a.tier == "Top"])
        mid_tier_count = len([a for a in articles if a.tier == "Mid"])
        blog_count = len([a for a in articles if a.tier == "Blog"])
        total_mentions = len(articles)
        
        # Calculate sentiment breakdown
        positive_count = len([a for a in articles if a.sentiment == "positive"])
        neutral_count = len([a for a in articles if a.sentiment == "neutral"])
        negative_count = len([a for a in articles if a.sentiment == "negative"])
        
        # Create response
        response_data = AnalyticsResponse(
            report=ReportData(
                clientId=request.clientId,
                clientName=client_name,
                date=request.date,
                generatedAt=datetime.now().isoformat() + "Z",
                summary=Summary(
                    topTierCount=top_tier_count,
                    midTierCount=mid_tier_count,
                    blogCount=blog_count,
                    totalMentions=total_mentions,
                    sentimentBreakdown=SentimentBreakdown(
                        positive=positive_count,
                        neutral=neutral_count,
                        negative=negative_count
                    )
                ),
                articles=articles
            )
        )
        
        return response_data
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error generating analytics report: {str(e)}")

@app.get("/")
async def root():
    """
    Root endpoint with API information
    """
    return {
        "message": "PR Coverage Report Generator", 
        "description": "Generate AI-powered PR coverage reports for any topic",
        "endpoints": {
            "POST /generate-report": "Generate PDF coverage report for any subject using AI analysis of news sources",
            "POST /analytics": "Generate structured JSON analytics data with tier counts, sentiment analysis, and article metadata"
        },
        "examples": {
            "generate_report": {
                "subject": "Harry Styles",
                "max_articles": 20,
                "filename": "harry-styles-coverage.pdf",
                "language": "en-US",
                "country": "US"
            },
            "analytics": {
                "clientId": "harry-styles",
                "includeInternational": false,
                "date": "2025-01-22"
            }
        },
        "supported_topics": [
            "People: Harry Styles, Taylor Swift, Elon Musk",
            "Companies: Apple, Tesla, Microsoft, Netflix", 
            "Events: COP28, Olympics, World Cup",
            "Technology: artificial intelligence, blockchain, quantum computing",
            "Any topic covered by Google News"
        ],
        "features": [
            "AI-powered content categorization with Google Gemini",
            "Media tier classification (top-tier, mid-tier, low-tier sources)",
            "Coverage differentiation (headline vs mention)",
            "Professional PDF formatting with clickable links",
            "Multi-language and multi-region support",
            "Structured JSON analytics with sentiment analysis",
            "Automated tier counting and view estimation",
            "Real-time article processing and metadata extraction"
        ]
    }

@app.get("/health")
async def health_check():
    """
    Health check endpoint
    """
    return {
        "status": "healthy",
        "service": "pr_coverage_generator",
        "version": "1.0.0",
        "ai_engine": "google_gemini",
        "features": ["rss_processing", "ai_categorization", "media_tier_classification", "coverage_analysis"]
    }

if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=8000) 