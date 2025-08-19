"""
FastAPI backend for Weaver AI
Provides REST API for querying the intelligent knowledge base
"""

import os
import sys
import uuid
from datetime import datetime
from typing import Dict, Any

# Add the project root to the Python path
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

# Import dependencies with fallback
try:
    from fastapi import FastAPI, HTTPException, Request
    from fastapi.middleware.cors import CORSMiddleware
    from fastapi.responses import JSONResponse
    FASTAPI_AVAILABLE = True
except ImportError:
    FASTAPI_AVAILABLE = False
    print("❌ FastAPI not available. Install with: pip install fastapi uvicorn")
    sys.exit(1)

try:
    from backend.models import (
        QueryRequest, QueryResponse, SourceDocument, 
        HealthResponse, StatsResponse, ErrorResponse
    )
    MODELS_AVAILABLE = True
except ImportError:
    MODELS_AVAILABLE = False
    print("⚠️ Pydantic models not available, using basic responses")

from backend.rag_engine import RAGEngine
from config.settings import get_settings

settings = get_settings()

# Initialize FastAPI app
app = FastAPI(
    title="Weaver AI API",
    description="Intelligent project knowledge assistant powered by RAG",
    version="1.0.0",
    docs_url="/docs",
    redoc_url="/redoc"
)

# Add CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # In production, replace with specific origins
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Initialize RAG engine
rag_engine = RAGEngine()

# Global error handler
@app.exception_handler(Exception)
async def global_exception_handler(request: Request, exc: Exception):
    """Global exception handler"""
    request_id = str(uuid.uuid4())
    
    error_detail = {
        "error": "Internal server error",
        "detail": str(exc),
        "timestamp": datetime.now().isoformat(),
        "request_id": request_id,
        "path": str(request.url)
    }
    
    print(f"❌ Error {request_id}: {str(exc)}")
    
    return JSONResponse(
        status_code=500,
        content=error_detail
    )

@app.get("/", summary="API Root")
async def root():
    """API root endpoint"""
    return {
        "message": "Welcome to Weaver AI API",
        "version": "1.0.0",
        "documentation": "/docs",
        "health": "/health",
        "stats": "/stats"
    }

@app.get("/health", summary="Health Check")
async def health():
    """Health check endpoint"""
    status = rag_engine.get_status()
    overall_status = "healthy" if status["overall"] == "ready" else "degraded"
    
    if MODELS_AVAILABLE:
        from .models import HealthResponse
        return HealthResponse(
            status=overall_status,
            version="1.0.0",
            components=status
        )
    else:
        return {
            "status": overall_status,
            "timestamp": datetime.now().isoformat(),
            "version": "1.0.0",
            "components": status
        }

@app.get("/stats", summary="Knowledge Base Statistics")
async def get_stats():
    """Get knowledge base statistics"""
    stats = rag_engine.get_stats()
    
    if MODELS_AVAILABLE:
        from .models import StatsResponse
        return StatsResponse(
            total_documents=stats.get("total_documents", 0),
            sources=stats.get("sources", {}),
            last_updated=stats.get("last_updated"),
            vector_db_path=stats.get("vector_db_path")
        )
    else:
        return stats

@app.post("/ask", summary="Ask Question")
async def ask_question(request: Dict[str, Any]):
    """Ask a question to the AI assistant"""
    
    # Extract parameters from request dict
    question = request.get("question", "")
    max_results = request.get("max_results", 5)
    include_metadata = request.get("include_metadata", True)
    
    # Validate question
    if not question or not question.strip():
        raise HTTPException(status_code=400, detail="Question cannot be empty")
    
    if len(question) > 1000:
        raise HTTPException(status_code=400, detail="Question too long (max 1000 characters)")
    
    # Check if RAG engine is ready
    if not rag_engine.is_ready():
        raise HTTPException(
            status_code=503, 
            detail="Service temporarily unavailable. Please ensure the knowledge base is loaded and OpenAI is configured."
        )
    
    try:
        # Process the query
        answer, documents, processing_time = rag_engine.process_query(question, max_results)
        
        # Format source documents
        sources = []
        for doc in documents:
            metadata = doc.get("metadata", {})
            
            # Create source document
            source_doc = {
                "text": doc["text"][:500] + "..." if len(doc["text"]) > 500 else doc["text"],
                "source": metadata.get("source", "unknown"),
                "type": metadata.get("type", "document"),
                "url": metadata.get("url"),
                "title": metadata.get("title"),
                "author": metadata.get("author"),
                "created_at": metadata.get("created_at"),
                "similarity_score": doc.get("similarity_score")
            }
            
            # Add metadata if requested
            if include_metadata:
                source_doc["metadata"] = metadata
            
            sources.append(source_doc)
        
        # Create response
        response_data = {
            "answer": answer,
            "sources": sources,
            "query": question,
            "timestamp": datetime.now(),
            "model_used": settings.CHAT_MODEL if rag_engine.openai_client else "fallback",
            "processing_time": processing_time
        }
        
        # Convert datetime to string for JSON serialization
        response_data["timestamp"] = response_data["timestamp"].isoformat()
        return response_data
    
    except Exception as e:
        print(f"❌ Query processing error: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Failed to process query: {str(e)}")

@app.get("/search", summary="Search Documents")
async def search_documents(q: str, limit: int = 5):
    """Search for documents without generating an answer"""
    
    if not q or not q.strip():
        raise HTTPException(status_code=400, detail="Query parameter 'q' cannot be empty")
    
    if not rag_engine.collection:
        raise HTTPException(status_code=503, detail="Vector database not available")
    
    try:
        documents = rag_engine.search_similar_documents(q, limit)
        
        # Format documents
        formatted_docs = []
        for doc in documents:
            metadata = doc.get("metadata", {})
            formatted_doc = {
                "text": doc["text"][:200] + "..." if len(doc["text"]) > 200 else doc["text"],
                "source": metadata.get("source", "unknown"),
                "type": metadata.get("type", "document"),
                "title": metadata.get("title"),
                "author": metadata.get("author"),
                "url": metadata.get("url"),
                "similarity_score": doc.get("similarity_score"),
                "metadata": metadata
            }
            formatted_docs.append(formatted_doc)
        
        return {
            "query": q,
            "results": formatted_docs,
            "total_found": len(formatted_docs)
        }
    
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Search failed: {str(e)}")

# Development server runner
def run_dev_server():
    """Run development server"""
    try:
        import uvicorn
        print("🚀 Starting Weaver AI API server...")
        print(f"📍 API will be available at: http://{settings.API_HOST}:{settings.API_PORT}")
        print(f"📖 Documentation: http://{settings.API_HOST}:{settings.API_PORT}/docs")
        
        uvicorn.run(
            "backend.main:app",
            host=settings.API_HOST,
            port=settings.API_PORT,
            reload=True,
            log_level="info"
        )
    except ImportError:
        print("❌ Uvicorn not available. Install with: pip install uvicorn")
        print("💡 Or run manually: uvicorn backend.main:app --reload")

if __name__ == "__main__":
    run_dev_server()
