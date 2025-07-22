from fastapi import FastAPI, HTTPException
from fastapi.responses import Response
from pydantic import BaseModel
from reportlab.pdfgen import canvas
from reportlab.lib.pagesizes import letter, A4
from reportlab.lib.styles import getSampleStyleSheet
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer
from io import BytesIO
from typing import List, Dict, Any
from datetime import datetime
import uvicorn

# Import report generators
from report_generator import generate_report_pdf
from rss_agent import create_report_from_rss, ArticleCategorizer

app = FastAPI(title="PDF Generation API", description="Multiple PDF generation services")

# String to PDF models
class StringRequest(BaseModel):
    text: str
    title: str = "Generated Document"

# Report Generator models
class ReportItem(BaseModel):
    title: str
    link: str

class ReportSection(BaseModel):
    heading: str
    items: List[ReportItem]

class ReportRequest(BaseModel):
    subject: str
    sections: List[ReportSection] = None  # New format with sections
    items: List[ReportItem] = None  # Backward compatibility
    filename: str = None

# RSS Feed models
class RSSReportRequest(BaseModel):
    rss_url: str = None  # Optional, defaults to Harry Styles Google News
    max_articles: int = 20
    subject_override: str = None
    filename: str = None
    google_api_key: str = None  # Optional, can use env var

@app.post("/generate-pdf")
async def generate_pdf_from_string(request: StringRequest):
    """
    Generate a PDF from the provided string.
    
    Args:
        request: StringRequest containing the text and optional title
        
    Returns:
        PDF file as bytes
    """
    try:
        # Create a BytesIO buffer to hold the PDF
        buffer = BytesIO()
        
        # Create the PDF document
        doc = SimpleDocTemplate(buffer, pagesize=A4)
        
        # Get styles
        styles = getSampleStyleSheet()
        story = []
        
        # Add title
        title = Paragraph(request.title, styles['Title'])
        story.append(title)
        story.append(Spacer(1, 12))
        
        # Split text into paragraphs and add to story
        paragraphs = request.text.split('\n')
        for para in paragraphs:
            if para.strip():  # Only add non-empty paragraphs
                p = Paragraph(para, styles['Normal'])
                story.append(p)
                story.append(Spacer(1, 6))
        
        # Build the PDF
        doc.build(story)
        
        # Get the PDF bytes
        pdf_bytes = buffer.getvalue()
        buffer.close()
        
        # Return the PDF as a response
        return Response(
            content=pdf_bytes,
            media_type="application/pdf",
            headers={"Content-Disposition": "attachment; filename=generated_document.pdf"}
        )
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error generating PDF: {str(e)}")

# Report Generator 1 endpoints
@app.post("/generate-report-1")
async def generate_report_1_endpoint(request: ReportRequest):
    """
    Generate a structured report PDF using Report Generator 1 format.
    
    Args:
        request: ReportRequest containing subject, items list, and optional filename
        
    Returns:
        PDF file as bytes
    """
    try:
        # Handle both new format (sections) and old format (items)
        if request.sections:
            # Convert sections to dictionaries
            sections_dict = []
            for section in request.sections:
                section_dict = {
                    "heading": section.heading,
                    "items": [{"title": item.title, "link": item.link} for item in section.items]
                }
                sections_dict.append(section_dict)
            
            # Generate the PDF with sections
            pdf_bytes = generate_report_pdf(
                subject=request.subject,
                sections=sections_dict,
                filename=request.filename
            )
        elif request.items:
            # Backward compatibility: convert items to dictionaries
            items_dict = [{"title": item.title, "link": item.link} for item in request.items]
            
            # Generate the PDF with items
            pdf_bytes = generate_report_pdf(
                subject=request.subject,
                items=items_dict,
                filename=request.filename
            )
        else:
            raise HTTPException(status_code=400, detail="Either 'sections' or 'items' must be provided")
        
        # Determine filename
        filename = request.filename or f"report-1-{datetime.now().strftime('%Y%m%d-%H%M%S')}.pdf"
        
        # Return the PDF as a response
        return Response(
            content=pdf_bytes,
            media_type="application/pdf",
            headers={"Content-Disposition": f"attachment; filename={filename}"}
        )
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error generating report: {str(e)}")

@app.post("/generate-report-1-from-json")
async def generate_report_1_from_json(json_data: Dict[str, Any]):
    """
    Generate a report using Report Generator 1 from raw JSON data.
    
    Expected JSON format (new with sections):
    {
        "subject": "Report Title",
        "sections": [
            {
                "heading": "Section 1",
                "items": [
                    {"title": "Item title", "link": "https://example.com"}
                ]
            }
        ],
        "filename": "optional-filename.pdf"
    }
    
    Or legacy format:
    {
        "subject": "Report Title", 
        "items": [
            {"title": "Item title", "link": "https://example.com"}
        ],
        "filename": "optional-filename.pdf"
    }
    """
    try:
        # Validate required fields
        if "subject" not in json_data:
            raise HTTPException(status_code=400, detail="Missing required field: subject")
        
        # Support both new format (sections) and legacy format (items)
        if "sections" in json_data:
            # Validate sections format
            sections = json_data["sections"]
            if not isinstance(sections, list):
                raise HTTPException(status_code=400, detail="Sections must be a list")
            
            for i, section in enumerate(sections):
                if not isinstance(section, dict):
                    raise HTTPException(status_code=400, detail=f"Section {i} must be a dictionary")
                if "heading" not in section:
                    raise HTTPException(status_code=400, detail=f"Section {i} must have a 'heading' field")
                if "items" not in section:
                    raise HTTPException(status_code=400, detail=f"Section {i} must have an 'items' field")
                
                items = section["items"]
                if not isinstance(items, list):
                    raise HTTPException(status_code=400, detail=f"Section {i} items must be a list")
                
                for j, item in enumerate(items):
                    if not isinstance(item, dict):
                        raise HTTPException(status_code=400, detail=f"Section {i} item {j} must be a dictionary")
                    if "title" not in item or "link" not in item:
                        raise HTTPException(status_code=400, detail=f"Section {i} item {j} must have 'title' and 'link' fields")
            
            # Generate the PDF with sections
            pdf_bytes = generate_report_pdf(
                subject=json_data["subject"],
                sections=sections,
                filename=json_data.get("filename")
            )
            
        elif "items" in json_data:
            # Legacy format validation
            items = json_data["items"]
            if not isinstance(items, list):
                raise HTTPException(status_code=400, detail="Items must be a list")
            
            for i, item in enumerate(items):
                if not isinstance(item, dict):
                    raise HTTPException(status_code=400, detail=f"Item {i} must be a dictionary")
                if "title" not in item or "link" not in item:
                    raise HTTPException(status_code=400, detail=f"Item {i} must have 'title' and 'link' fields")
            
            # Generate the PDF with items (legacy)
            pdf_bytes = generate_report_pdf(
                subject=json_data["subject"],
                items=items,
                filename=json_data.get("filename")
            )
        else:
            raise HTTPException(status_code=400, detail="JSON must contain either 'sections' or 'items' field")
        
        # Determine filename
        filename = json_data.get("filename") or f"report-1-{datetime.now().strftime('%Y%m%d-%H%M%S')}.pdf"
        
        # Return the PDF as a response
        return Response(
            content=pdf_bytes,
            media_type="application/pdf",
            headers={"Content-Disposition": f"attachment; filename={filename}"}
        )
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error generating report: {str(e)}")

# RSS-powered report generation endpoints
@app.post("/generate-report-from-rss")
async def generate_report_from_rss_endpoint(request: RSSReportRequest):
    """
    Generate a report directly from an RSS feed using LangChain agent.
    
    Args:
        request: RSSReportRequest with RSS URL and configuration
        
    Returns:
        PDF file as bytes
    """
    try:
        # Create report from RSS feed
        json_path, pdf_path = create_report_from_rss(
            rss_url=request.rss_url,
            max_articles=request.max_articles,
            subject_override=request.subject_override,
            google_api_key=request.google_api_key
        )
        
        # Read the generated PDF
        with open(pdf_path, 'rb') as f:
            pdf_bytes = f.read()
        
        # Clean up temporary files
        import os
        try:
            os.remove(json_path)
            os.remove(pdf_path)
        except:
            pass  # Don't fail if cleanup fails
        
        # Determine filename
        filename = request.filename or f"rss-report-{datetime.now().strftime('%Y%m%d-%H%M%S')}.pdf"
        
        # Return the PDF as a response
        return Response(
            content=pdf_bytes,
            media_type="application/pdf",
            headers={"Content-Disposition": f"attachment; filename={filename}"}
        )
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error generating RSS report: {str(e)}")

@app.post("/process-rss-to-json")
async def process_rss_to_json_endpoint(request: RSSReportRequest):
    """
    Process RSS feed and return categorized JSON (without generating PDF).
    
    Args:
        request: RSSReportRequest with RSS URL and configuration
        
    Returns:
        JSON structure with categorized articles
    """
    try:
        # Initialize the agent
        agent = ArticleCategorizer(request.google_api_key)
        
        # Process RSS to JSON
        data = agent.process_rss_to_json(
            rss_url=request.rss_url,
            max_articles=request.max_articles,
            subject_override=request.subject_override
        )
        
        return data
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error processing RSS feed: {str(e)}")

@app.get("/")
async def root():
    """
    Root endpoint with API information
    """
    return {
        "message": "PDF Generation API", 
        "description": "Multiple PDF generation services",
        "endpoints": {
            "POST /generate-pdf": "Generate PDF from string",
            "POST /generate-report-1": "Generate report using Report Generator 1 (structured request)",
            "POST /generate-report-1-from-json": "Generate report using Report Generator 1 (raw JSON)",
            "POST /generate-report-from-rss": "Generate report directly from RSS feed using AI categorization",
            "POST /process-rss-to-json": "Process RSS feed to categorized JSON (no PDF)",
            "GET /": "This information",
            "GET /health": "Health check"
        },
        "examples": {
            "string_to_pdf": {
                "text": "Your text content here",
                "title": "Document Title (optional)"
            },
            "report_generator_1": {
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
                        "heading": "Market Trends",
                        "items": [
                            {
                                "title": "Tech stocks showing positive momentum",
                                "link": "https://example.com/market-trends"
                            }
                        ]
                    }
                ],
                "filename": "tech-news-report.pdf"
            },
            "rss_to_report": {
                "rss_url": "https://news.google.com/rss/search?q=Harry%Styles&hl=en-US&gl=US&ceid=US:en",
                "max_articles": 15,
                "subject_override": "Harry Styles News Summary",
                "filename": "harry-styles-news-report.pdf"
            }
        }
    }

@app.get("/health")
async def health_check():
    """
    Health check endpoint
    """
    return {
        "status": "healthy",
        "services": {
            "string_to_pdf": "operational",
            "report_generator_1": "operational",
            "rss_agent": "operational"
        }
    }

if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=8000) 