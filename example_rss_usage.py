#!/usr/bin/env python3
"""
Example script demonstrating RSS Agent usage for automatic report generation
"""

import os
from rss_agent import create_report_from_rss, ArticleCategorizer


def main():
    """Main example function"""
    
    # Check for Google API key
    if not os.getenv("GOOGLE_API_KEY"):
        print("❌ Please set GOOGLE_API_KEY environment variable")
        print("   You can get an API key from: https://aistudio.google.com/app/apikey")
        print("   Then run: export GOOGLE_API_KEY='your-key-here'")
        return
    
    print("🤖 RSS Agent Demo")
    print("=" * 50)
    
    # Use Harry Styles Google News RSS feed
    from rss_agent import RSS_URL
    feed_name = "Harry Styles Google News"
    rss_url = RSS_URL
    
    print(f"\n📡 Processing: {feed_name}")
    print(f"   URL: {rss_url}")
    print(f"   Max articles: 15")
    
    try:
        # Method 1: Complete pipeline (RSS -> JSON -> PDF)
        print("\n🔄 Method 1: Complete pipeline (RSS -> JSON -> PDF)")
        json_path, pdf_path = create_report_from_rss(
            rss_url=rss_url,
            max_articles=15,
            subject_override=f"{feed_name} Daily Summary",
            output_json="example_rss_output.json",
            output_pdf="example_rss_report.pdf"
        )
        
        print(f"✅ Complete!")
        print(f"   📄 JSON: {json_path}")
        print(f"   📄 PDF: {pdf_path}")
        
        # Method 2: Just process RSS to JSON (for inspection)
        print("\n🔄 Method 2: RSS to JSON only")
        agent = ArticleCategorizer()
        data = agent.process_rss_to_json(
            rss_url=rss_url,
            max_articles=10,
            subject_override=f"{feed_name} Headlines"
        )
        
        print(f"✅ Processed {len(data.get('sections', []))} sections:")
        for section in data.get('sections', []):
            print(f"   📰 {section['heading']}: {len(section['items'])} articles")
        
        # Save JSON for inspection
        agent.save_json(data, "example_headlines_only.json")
        print(f"   📄 JSON saved: example_headlines_only.json")
        
    except Exception as e:
        print(f"❌ Error: {e}")
        print("\nTroubleshooting:")
        print("1. Check your Google API key")
        print("2. Ensure you have internet connection")
        print("3. Try a different RSS feed if one is down")
        print("4. Check the RSS URL is valid")


def test_multiple_feeds():
    """Test processing multiple RSS feeds"""
    
    if not os.getenv("GOOGLE_API_KEY"):
        print("❌ GOOGLE_API_KEY not set")
        return
    
    from rss_agent import RSS_URL
    feeds = [
        ("Harry Styles News", RSS_URL),
        ("Tech News", "https://feeds.feedburner.com/TechCrunch")
    ]
    
    print("🔄 Testing multiple RSS feeds...")
    
    for name, url in feeds:
        try:
            print(f"\nProcessing {name}...")
            agent = ArticleCategorizer()
            data = agent.process_rss_to_json(url, max_articles=5)
            
            print(f"✅ {name}: {len(data['sections'])} sections")
            
        except Exception as e:
            print(f"❌ {name} failed: {e}")


if __name__ == "__main__":
    print("Choose an option:")
    print("1. Run main demo")
    print("2. Test multiple feeds")
    
    choice = input("Enter choice (1 or 2): ").strip()
    
    if choice == "2":
        test_multiple_feeds()
    else:
        main() 