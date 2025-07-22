# PDF Generation API

A FastAPI service with multiple PDF generation capabilities.

## Components

1. **Main API** (`main.py`) - Consolidated API server
2. **Report Generator 1** (`report_generator.py`) - Core logic for structured reports with links
3. **RSS Agent** (`rss_agent.py`) - LangChain-powered agent for RSS feed processing
4. **Future Report Generators** - Additional generators will be added as separate modules

## Installation

1. Install the required dependencies:
```bash
pip install -r requirements.txt
```

2. Set up your Google API key (required for RSS agent):
```bash
export GOOGLE_API_KEY="your-google-api-key-here"
```
Get your API key from: https://aistudio.google.com/app/apikey
Or pass it directly in API requests.

## Usage

1. Start the API server:
```bash
python main.py
```

Or use uvicorn directly:
```bash
uvicorn main:app --reload --host 0.0.0.0 --port 8000
```

2. The API will be available at `http://localhost:8000`

## API Endpoints

### String to PDF

#### POST /generate-pdf

Converts a string to a PDF document.

**Request Body:**
```json
{
    "text": "Your text content here",
    "title": "Document Title (optional)"
}
```

**Response:** PDF file (application/pdf)

**Example using curl:**
```bash
curl -X POST "http://localhost:8000/generate-pdf" \
     -H "Content-Type: application/json" \
     -d '{"text": "Hello World!\nThis is a test document.", "title": "My Test Document"}' \
     --output document.pdf
```

### Report Generator 1

#### POST /generate-report-1

Generates a structured report PDF with sections, subheadings, and clickable links (format matches example1.pdf).

**Request Body (New format with sections):**
```json
{
    "subject": "Report Title",
    "sections": [
        {
            "heading": "Section Heading",
            "items": [
                {
                    "title": "Item description",
                    "link": "https://example.com"
                }
            ]
        }
    ],
    "filename": "optional-filename.pdf"
}
```

**Request Body (Legacy format):**
```json
{
    "subject": "Report Title",
    "items": [
        {
            "title": "Item description",
            "link": "https://example.com"
        }
    ],
    "filename": "optional-filename.pdf"
}
```

**Response:** PDF file (application/pdf)

#### POST /generate-report-1-from-json

Generates a report from raw JSON data using Report Generator 1.

**Request Body (New format with sections):**
```json
{
    "subject": "Technology News Summary",
    "sections": [
        {
            "heading": "AI & Technology",
            "items": [
                {
                    "title": "Latest AI developments in healthcare sector",
                    "link": "https://example.com/ai-healthcare"
                },
                {
                    "title": "New breakthrough in quantum computing research",
                    "link": "https://example.com/quantum-computing"
                }
            ]
        },
        {
            "heading": "Market Analysis",
            "items": [
                {
                    "title": "Tech market showing strong growth",
                    "link": "https://example.com/market-analysis"
                }
            ]
        }
    ],
    "filename": "tech-news-report.pdf"
}
```

**Request Body (Legacy format):**
```json
{
    "subject": "Technology News Summary",
    "items": [
        {
            "title": "Latest AI developments in healthcare sector",
            "link": "https://example.com/ai-healthcare"
        },
        {
            "title": "New breakthrough in quantum computing research",
            "link": "https://example.com/quantum-computing"
        }
    ],
    "filename": "tech-news-report.pdf"
}
```

**Example using curl:**
```bash
curl -X POST "http://localhost:8000/generate-report-1-from-json" \
     -H "Content-Type: application/json" \
     -d @example_report_data.json \
     --output report.pdf
```

### RSS-Powered Report Generation

#### POST /generate-report-from-rss

Automatically generates a report from an RSS feed using AI categorization.

**Request Body:**
```json
{
    "rss_url": "https://news.google.com/rss/search?q=Harry%Styles&hl=en-US&gl=US&ceid=US:en",
    "max_articles": 15,
    "subject_override": "Harry Styles News Summary", 
    "filename": "harry-styles-news-report.pdf",
    "google_api_key": "your-api-key-here"
}
```

**Response:** PDF file (application/pdf)

#### POST /process-rss-to-json

Processes RSS feed and returns categorized JSON without generating PDF.

**Request Body:**
```json
{
    "rss_url": "https://news.google.com/rss/search?q=Harry%Styles&hl=en-US&gl=US&ceid=US:en",
    "max_articles": 20,
    "subject_override": "Harry Styles News Roundup"
}
```

**Response:** JSON structure with categorized articles

**Example using curl:**
```bash
# Generate PDF directly from RSS (defaults to Harry Styles news)
curl -X POST "http://localhost:8000/generate-report-from-rss" \
     -H "Content-Type: application/json" \
     -d '{"max_articles": 15}' \
     --output harry-styles-report.pdf

# Get JSON structure only
curl -X POST "http://localhost:8000/process-rss-to-json" \
     -H "Content-Type: application/json" \
     -d '{"max_articles": 10}'
```

**Example using Python requests:**
```python
import requests

# For string-to-PDF
response = requests.post(
    "http://localhost:8000/generate-pdf",
    json={
        "text": "Hello World!\nThis is a test document with multiple lines.",
        "title": "My Generated Document"
    }
)

if response.status_code == 200:
    with open("generated_document.pdf", "wb") as f:
        f.write(response.content)
    print("PDF generated successfully!")

# For report generator 1 (new format with sections)
report_data = {
    "subject": "Weekly News Report",
    "sections": [
        {
            "heading": "Technology News",
            "items": [
                {
                    "title": "Breaking news: Technology advancement in AI",
                    "link": "https://example.com/ai-news"
                }
            ]
        },
        {
            "heading": "Market Analysis",
            "items": [
                {
                    "title": "Market trends show positive growth",
                    "link": "https://example.com/market-trends"
                }
            ]
        }
    ]
}

response = requests.post(
    "http://localhost:8000/generate-report-1",
    json=report_data
)

if response.status_code == 200:
    with open("weekly_report.pdf", "wb") as f:
        f.write(response.content)
    print("Report generated successfully!")

# For RSS-powered reports (defaults to Harry Styles news)
rss_data = {
    "max_articles": 15,
    "subject_override": "Harry Styles News Summary"
}

response = requests.post(
    "http://localhost:8000/generate-report-from-rss",
    json=rss_data
)

if response.status_code == 200:
    with open("harry_styles_report.pdf", "wb") as f:
        f.write(response.content)
    print("RSS report generated successfully!")
```

### Using Direct Functions

**From JSON files:**
```python
from report_generator import create_report_from_json_file

# Generate report from JSON file
create_report_from_json_file("example_report_data.json", "my_report.pdf")
```

**From RSS feeds:**
```python
from rss_agent import create_report_from_rss

# Generate report directly from RSS feed (defaults to Harry Styles news)
json_path, pdf_path = create_report_from_rss(
    max_articles=15,
    subject_override="Harry Styles News Summary"
)
print(f"Generated: {pdf_path}")
```

**RSS processing only:**
```python
from rss_agent import ArticleCategorizer

# Just process RSS to JSON (defaults to Harry Styles news)
agent = ArticleCategorizer()
data = agent.process_rss_to_json(
    rss_url="https://news.google.com/rss/search?q=Harry%Styles&hl=en-US&gl=US&ceid=US:en",
    max_articles=10
)
print(f"Categorized into {len(data['sections'])} sections")
```

### Common Endpoints

#### GET /

Returns API information and available endpoints.

#### GET /health

Health check endpoint showing status of all services.

## Interactive Documentation

When the server is running, you can access the interactive API documentation at:
- Swagger UI: `http://localhost:8000/docs`
- ReDoc: `http://localhost:8000/redoc`

## Features

### String to PDF
- Converts plain text to PDF
- Supports multi-line text (separated by newlines)
- Optional document title
- Returns PDF as downloadable file

### Report Generator 1
- Generates structured reports with sections and subheadings
- Supports clickable links in PDF output
- Mimics the format of example1.pdf with subheadings
- New format: sections with headings and items
- Legacy format: direct items list (backward compatible)
- Customizable filenames
- Professional formatting with proper spacing
- Blue clickable links in PDF output

### RSS Agent (AI-Powered)
- **Automatic categorization** using LangChain and Google Gemini 2.0 Flash
- **RSS feed processing** with feedparser
- **Smart section creation** based on article content
- **Configured for Harry Styles news** from Google News RSS
- **Fallback handling** if AI categorization fails
- **Direct PDF generation** from RSS feeds
- **JSON export** for inspection and customization

### System Architecture
- **Modular design** allowing easy addition of new report generators
- **Each report generator** has its own routes (`/generate-report-1`, `/generate-report-2`, etc.)
- **RSS integration** with dedicated endpoints for feed processing
- **Consolidated API** on single port (8000)
- **Separate logic modules** for each generator type
- **LangChain + Google Gemini** for AI-powered content categorization

## Common Features
- Health check endpoint showing all service statuses
- Interactive API documentation
- Comprehensive error handling
- FastAPI framework with automatic validation
- Extensible architecture for multiple report types
- AI-powered content categorization with Google Gemini 2.0 Flash
- RSS feed integration (Harry Styles Google News by default)
- Environment variable configuration

## Example Usage

### Quick Start with RSS

1. **Set your Google API key:**
   ```bash
   export GOOGLE_API_KEY="your-key-here"
   ```

2. **Run the example:**
   ```bash
   python example_rss_usage.py
   ```

3. **Or use the API:**
   ```bash
   curl -X POST "http://localhost:8000/generate-report-from-rss" \
        -H "Content-Type: application/json" \
        -d '{"max_articles": 15}' \
        --output harry-styles-news-report.pdf
   ```

### Default RSS Feed

- **Harry Styles Google News**: `https://news.google.com/rss/search?q=Harry%Styles&hl=en-US&gl=US&ceid=US:en`

### Other Compatible RSS Feeds

- **TechCrunch**: `https://feeds.feedburner.com/TechCrunch`
- **BBC News**: `https://feeds.bbci.co.uk/news/rss.xml`
- **CNN**: `https://rss.cnn.com/rss/edition.rss`
- **Reuters**: `https://feeds.reuters.com/Reuters/worldNews` # PR-Report
