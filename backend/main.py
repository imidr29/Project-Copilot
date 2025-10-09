from fastapi import FastAPI, HTTPException, Request, UploadFile, File, Form
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from pydantic import BaseModel
from typing import Optional, List, Dict, Any
import os
import tempfile
from dotenv import load_dotenv
import logging
import traceback
import json

from database import Database
from langchain_agent import LangChainSQLAgent
from chart_agent import ChartAgent
from csv_processor import CSVProcessor

load_dotenv()

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

app = FastAPI(title="OEE Co-Pilot API", version="1.0.0")

# Global exception handler
@app.exception_handler(Exception)
async def global_exception_handler(request: Request, exc: Exception):
    logger.error(f"Global exception handler caught: {type(exc).__name__}")
    logger.error(f"Error message: {str(exc)}")
    logger.error(f"Traceback:\n{traceback.format_exc()}")
    
    return JSONResponse(
        status_code=500,
        content={
            "error": str(exc),
            "type": type(exc).__name__,
            "detail": traceback.format_exc()
        }
    )

# CORS for frontend (Angular on 4200 and Simple frontend on 3000)
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:4200", "http://localhost:3000", "http://localhost:3001"],
    allow_credentials=True,
    allow_methods=["GET", "POST", "PUT", "DELETE", "OPTIONS"],
    allow_headers=["*"],
    expose_headers=["*"],
)

# Initialize services
db = Database()
sql_agent = LangChainSQLAgent(db)  # Google Gemini agent
chart_agent = ChartAgent()
csv_processor = CSVProcessor(db)

# Request/Response models
class QueryRequest(BaseModel):
    query: str
    conversation_history: Optional[List[Dict[str, str]]] = []

@app.get("/")
async def root():
    return {
        "message": "OEE Co-Pilot API",
        "version": "1.0.0",
        "status": "running",
        "docs": "/docs"
    }

@app.options("/api/query")
async def options_query():
    return {"message": "OK"}

@app.get("/health")
async def health_check():
    """Health check endpoint"""
    try:
        db.test_connection()
        return {"status": "healthy", "database": "connected", "langchain": "available"}
    except Exception as e:
        raise HTTPException(status_code=503, detail=f"Service unhealthy: {str(e)}")

@app.post("/api/query")
async def process_query(request: QueryRequest):
    try:
        result = await sql_agent.process_query(
            query=request.query,
            conversation_history=request.conversation_history
        )

        chart_spec = None
        chart_image = None
        
        # Only generate charts when explicitly requested
        query_lower = request.query.lower()
        chart_keywords = ['chart', 'graph', 'plot', 'visualize', 'pie chart', 'bar chart', 'line chart', 'histogram', 'scatter plot', 'heatmap', 'pareto']
        
        if result["results"] and any(keyword in query_lower for keyword in chart_keywords):
            logger.info(f"Chart explicitly requested for query: {request.query}")
            logger.info(f"Data sample: {result['results'][:2] if result['results'] else 'No data'}")
            chart_spec = chart_agent.generate_chart_spec(
                query=request.query,
                data=result["results"]
            )
            chart_image = chart_agent.generate_chart_image(
                query=request.query,
                data=result["results"]
            )
            logger.info(f"Chart spec generated: {chart_spec is not None}")
            logger.info(f"Chart image generated: {chart_image is not None}")
            if chart_spec:
                logger.info(f"Chart type: {chart_spec.get('type', 'unknown')}")
        else:
            logger.info(f"No chart generation - query doesn't contain chart keywords: {request.query}")

        response_data = {
            "query": request.query,
            "sql_query": result["sql_query"],
            "results": result["results"],
            "chart_spec": chart_spec,
            "chart_image": chart_image,
            "natural_language_response": result["natural_language_response"],
            "metadata": {
                "result_count": len(result["results"]),
                "execution_time_ms": result.get("execution_time_ms", 0),
                "chart_type": chart_spec.get("type") if chart_spec else None
            }
        }

        # Test JSON serialization
        json.dumps(response_data)
        return response_data
    except Exception as e:
        logger.error(f"Exception in /api/query: {type(e).__name__} - {str(e)}")
        raise HTTPException(status_code=500, detail=f"{type(e).__name__}: {str(e)}")

@app.get("/api/suggestions")
async def get_query_suggestions():
    return {
        "suggestions": [
            "What % of time was the machine ACTIVE vs INACTIVE today?",
            "Show me all INACTIVE episodes less than 60 seconds",
            "Top 5 reasons contributing to INACTIVE time",
            "Trend of daily total INACTIVE minutes over last 14 days",
            "Calculate approximate MTTR for last week"
        ]
    }

@app.get("/api/schema")
async def get_schema():
    try:
        schema = db.get_database_schema()
        return {"schema": schema}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/api/upload-csv")
async def upload_csv(
    file: UploadFile = File(...),
    table_name: str = Form(...),
    upload_mode: str = Form(...),
    has_headers: bool = Form(True)
):
    """Upload and process CSV file"""
    try:
        # Validate file type
        if not file.filename.lower().endswith('.csv'):
            raise HTTPException(status_code=400, detail="Only CSV files are allowed")
        
        # Validate upload mode
        if upload_mode not in ['structured', 'unstructured']:
            raise HTTPException(status_code=400, detail="Upload mode must be 'structured' or 'unstructured'")
        
        # Validate table name
        if not table_name or not table_name.replace('_', '').replace('-', '').isalnum():
            raise HTTPException(status_code=400, detail="Table name must contain only letters, numbers, underscores, and hyphens")
        
        # Save uploaded file temporarily
        with tempfile.NamedTemporaryFile(delete=False, suffix='.csv') as temp_file:
            content = await file.read()
            temp_file.write(content)
            temp_file_path = temp_file.name
        
        try:
            # Process CSV file
            result = csv_processor.process_csv(
                file_path=temp_file_path,
                table_name=table_name,
                upload_mode=upload_mode,
                has_headers=has_headers
            )
            
            if result['success']:
                logger.info(f"CSV upload successful: {table_name} with {result['rows_inserted']} rows")
                return JSONResponse(content=result)
            else:
                raise HTTPException(status_code=400, detail=result['error'])
                
        finally:
            # Clean up temporary file
            try:
                os.unlink(temp_file_path)
            except:
                pass
                
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"CSV upload error: {e}")
        raise HTTPException(status_code=500, detail=f"Upload failed: {str(e)}")

@app.on_event("startup")
async def startup_event():
    logger.info("🚀 Starting OEE Co-Pilot API")
    try:
        db.test_connection()
        logger.info("✅ Database connected")
    except Exception as e:
        logger.error(f"❌ Database connection failed: {e}")

@app.on_event("shutdown")
async def shutdown_event():
    logger.info("👋 Shutting down OEE Co-Pilot API")
    db.close()

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000, log_level="info")
