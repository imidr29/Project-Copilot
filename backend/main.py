from fastapi import FastAPI, HTTPException, Request, UploadFile, File, Form, Depends, Header
from fastapi.middleware.cors import CORSMiddleware
from fastapi.middleware.trustedhost import TrustedHostMiddleware
from fastapi.responses import JSONResponse
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
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
from token_guard import token_guard, require_token

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
    allow_origins=[
        "http://localhost:3000",  # Simple frontend
        "http://localhost:4200",  # Angular frontend
        "http://127.0.0.1:3000",
        "http://127.0.0.1:4200"
    ],
    allow_credentials=True,
    allow_methods=["GET", "POST", "PUT", "DELETE", "OPTIONS"],
    allow_headers=["Authorization", "Content-Type", "X-Requested-With"],
    expose_headers=["X-Rate-Limit-Remaining", "X-Rate-Limit-Reset"]
)

# Security middleware
app.add_middleware(
    TrustedHostMiddleware, 
    allowed_hosts=["localhost", "127.0.0.1", "*.localhost"]
)

# Security headers middleware
@app.middleware("http")
async def add_security_headers(request: Request, call_next):
    response = await call_next(request)
    
    # Add security headers
    response.headers["X-Content-Type-Options"] = "nosniff"
    response.headers["X-Frame-Options"] = "DENY"
    response.headers["X-XSS-Protection"] = "1; mode=block"
    response.headers["Referrer-Policy"] = "strict-origin-when-cross-origin"
    response.headers["Permissions-Policy"] = "geolocation=(), microphone=(), camera=()"
    
    return response

# Initialize services
db = Database()
sql_agent = LangChainSQLAgent(db)  # Google Gemini agent
chart_agent = ChartAgent()
csv_processor = CSVProcessor(db)

# Security
security = HTTPBearer(auto_error=False)

# Request/Response models
class QueryRequest(BaseModel):
    query: str
    conversation_history: Optional[List[Dict[str, str]]] = []
    api_token: Optional[str] = None

class TokenRequest(BaseModel):
    user_id: str
    role: str = "user"
    permissions: Optional[List[str]] = None

class TokenResponse(BaseModel):
    token: str
    expires_at: str
    user_id: str
    role: str

# Authentication dependency
async def get_current_user(credentials: HTTPAuthorizationCredentials = Depends(security), request: Request = None):
    """Get current user from token"""
    if not credentials:
        raise HTTPException(status_code=401, detail="Token required")
    
    try:
        endpoint = request.url.path if request else None
        token_info = token_guard.validate_token(credentials.credentials, endpoint)
        return token_info
    except ValueError as e:
        raise HTTPException(status_code=401, detail=f"Invalid token: {str(e)}")

# Optional authentication (for endpoints that work with or without auth)
async def get_current_user_optional(credentials: HTTPAuthorizationCredentials = Depends(security), request: Request = None):
    """Get current user from token (optional)"""
    if not credentials:
        return None
    
    try:
        endpoint = request.url.path if request else None
        token_info = token_guard.validate_token(credentials.credentials, endpoint)
        return token_info
    except ValueError:
        return None

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
async def process_query(request: QueryRequest, current_user: dict = Depends(get_current_user_optional)):
    try:
        # Log authentication status
        if current_user:
            logger.info(f"Authenticated request from user: {current_user['user_id']} (role: {current_user['role']})")
        else:
            logger.info("Unauthenticated request")
        
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

# Token management endpoints
@app.post("/api/tokens", response_model=TokenResponse)
async def create_token(request: TokenRequest, current_user: dict = Depends(get_current_user)):
    """Create a new API token (admin only)"""
    if current_user.get('role') != 'admin':
        raise HTTPException(status_code=403, detail="Admin role required")
    
    token = token_guard.generate_token(
        user_id=request.user_id,
        role=request.role,
        permissions=request.permissions
    )
    
    token_info = token_guard.get_token_info(token)
    
    return TokenResponse(
        token=token,
        expires_at=token_info['expires_at'],
        user_id=token_info['user_id'],
        role=token_info['role']
    )

@app.get("/api/tokens")
async def list_tokens(current_user: dict = Depends(get_current_user)):
    """List active tokens (admin only)"""
    if current_user.get('role') != 'admin':
        raise HTTPException(status_code=403, detail="Admin role required")
    
    tokens = token_guard.list_active_tokens()
    return {"tokens": tokens}

@app.delete("/api/tokens/{token_id}")
async def revoke_token(token_id: str, current_user: dict = Depends(get_current_user)):
    """Revoke a token (admin only)"""
    if current_user.get('role') != 'admin':
        raise HTTPException(status_code=403, detail="Admin role required")
    
    success = token_guard.revoke_token(token_id)
    if not success:
        raise HTTPException(status_code=404, detail="Token not found")
    
    return {"message": "Token revoked successfully"}

@app.post("/api/tokens/cleanup")
async def cleanup_expired_tokens(current_user: dict = Depends(get_current_user)):
    """Clean up expired tokens (admin only)"""
    if current_user.get('role') != 'admin':
        raise HTTPException(status_code=403, detail="Admin role required")
    
    cleaned_count = token_guard.cleanup_expired_tokens()
    return {"message": f"Cleaned up {cleaned_count} expired tokens"}

# Rate limiting for token endpoints
from collections import defaultdict
from time import time

# Simple in-memory rate limiter
rate_limiter = defaultdict(list)
RATE_LIMIT_WINDOW = 60  # 1 minute
RATE_LIMIT_MAX_REQUESTS = 10  # Max 10 requests per minute for token endpoints

def check_rate_limit(client_ip: str) -> bool:
    """Check if client has exceeded rate limit"""
    now = time()
    # Clean old entries
    rate_limiter[client_ip] = [req_time for req_time in rate_limiter[client_ip] if now - req_time < RATE_LIMIT_WINDOW]
    
    # Check if limit exceeded
    if len(rate_limiter[client_ip]) >= RATE_LIMIT_MAX_REQUESTS:
        return False
    
    # Add current request
    rate_limiter[client_ip].append(now)
    return True

@app.get("/api/tokens/default")
async def get_default_tokens(request: Request):
    """Get default tokens for testing (no auth required) - Rate limited"""
    client_ip = request.client.host
    
    # Check rate limit
    if not check_rate_limit(client_ip):
        raise HTTPException(status_code=429, detail="Rate limit exceeded. Max 10 requests per minute.")
    
    # Return the actual tokens from the token guard
    active_tokens = token_guard.list_active_tokens()
    
    # Extract tokens by role
    tokens = {}
    for token_info in active_tokens:
        role = token_info.get('role', 'unknown')
        token = token_info.get('full_token', '')  # Use full token
        if role in ['admin', 'user', 'readonly']:
            tokens[role] = token
    
    return {
        "message": "Default tokens retrieved",
        "tokens": tokens
    }

# Usage statistics endpoints
@app.get("/api/usage/stats")
async def get_usage_stats(current_user: dict = Depends(get_current_user)):
    """Get usage statistics for the current user"""
    user_id = current_user['user_id']
    stats = token_guard.get_usage_stats(user_id)
    
    if not stats:
        return {"message": "No usage statistics found for this user"}
    
    return {
        "user_id": user_id,
        "role": current_user['role'],
        "total_requests": stats['total_requests'],
        "daily_requests": stats['daily_requests'],
        "total_tokens": stats['total_tokens'],
        "last_reset": stats['last_reset'],
        "tokens": stats['tokens']
    }

@app.get("/api/usage/token/{token_id}")
async def get_token_usage(token_id: str, current_user: dict = Depends(get_current_user)):
    """Get usage statistics for a specific token"""
    # Users can only view their own token usage
    if current_user['role'] != 'admin':
        # Check if the token belongs to the current user
        token_data = token_guard.get_token_info(token_id)
        if not token_data or token_data['user_id'] != current_user['user_id']:
            raise HTTPException(status_code=403, detail="Access denied")
    
    usage = token_guard.get_token_usage(token_id)
    if not usage:
        raise HTTPException(status_code=404, detail="Token not found")
    
    return usage

@app.get("/api/usage/all")
async def get_all_usage_stats(current_user: dict = Depends(get_current_user)):
    """Get usage statistics for all users (admin only)"""
    if current_user['role'] != 'admin':
        raise HTTPException(status_code=403, detail="Admin role required")
    
    stats = token_guard.get_all_usage_stats()
    return {"users": stats}

@app.get("/api/usage/system")
async def get_system_stats(current_user: dict = Depends(get_current_user)):
    """Get system-wide usage statistics (admin only)"""
    if current_user['role'] != 'admin':
        raise HTTPException(status_code=403, detail="Admin role required")
    
    stats = token_guard.get_system_stats()
    return stats

@app.post("/api/usage/reset-daily")
async def reset_daily_counters(current_user: dict = Depends(get_current_user)):
    """Reset daily counters for all users (admin only)"""
    if current_user['role'] != 'admin':
        raise HTTPException(status_code=403, detail="Admin role required")
    
    token_guard.reset_daily_counters()
    return {"message": "Daily counters reset successfully"}

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
        
        # Create default tokens for testing
        from token_guard import create_default_tokens
        default_tokens = create_default_tokens()
        logger.info("✅ Default tokens created")
        
    except Exception as e:
        logger.error(f"❌ Database connection failed: {e}")

@app.on_event("shutdown")
async def shutdown_event():
    logger.info("👋 Shutting down OEE Co-Pilot API")
    db.close()

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000, log_level="info")
