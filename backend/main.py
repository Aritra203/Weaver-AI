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
from scripts.github_connector import GitHubConnector
from scripts.slack_connector import SlackConnector
from scripts.process_data import DataProcessor, EmbeddingGenerator

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

@app.delete("/clear", summary="Clear Knowledge Base")
async def clear_knowledge_base():
    """Clear all documents from the knowledge base"""
    
    if not rag_engine.collection:
        raise HTTPException(
            status_code=503, 
            detail="Vector database not available"
        )
    
    try:
        # Get current count before clearing
        current_count = rag_engine.collection.count()
        
        # Delete all documents from the collection
        if current_count > 0:
            # Get all document IDs
            all_docs = rag_engine.collection.get(include=[])
            if all_docs and 'ids' in all_docs and all_docs['ids']:
                rag_engine.collection.delete(ids=all_docs['ids'])
        
        return {
            "status": "success",
            "message": f"Knowledge base cleared successfully",
            "documents_removed": current_count,
            "current_documents": rag_engine.collection.count()
        }
        
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Failed to clear knowledge base: {str(e)}"
        )

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
            detail="Service temporarily unavailable. Please ensure the knowledge base is loaded and Gemini is configured."
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
            "model_used": settings.CHAT_MODEL if rag_engine.gemini_client else "fallback",
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

@app.post("/ingest/github", summary="Ingest GitHub Repository Data")
async def ingest_github_data(request: Dict[str, Any]):
    """Automatically fetch and ingest data from a GitHub repository"""
    
    repo_name = request.get("repo_name", "")
    include_issues = request.get("include_issues", True)
    include_prs = request.get("include_prs", True)
    max_items = request.get("max_items", 100)
    
    if not repo_name:
        raise HTTPException(status_code=400, detail="Repository name is required (format: owner/repo)")
    
    try:
        # Initialize GitHub connector and data processor
        github_connector = GitHubConnector()
        data_processor = DataProcessor()
        
        # Fetch repository data with limits to prevent timeouts
        repo = github_connector.get_repository(repo_name)
        
        # Collect data with reasonable limits
        all_data = []
        items_limit = min(max_items, 50)  # Limit to prevent timeouts
        
        # Fetch issues (limited)
        if include_issues:
            issues = github_connector.fetch_issues(repo, limit=items_limit//2)
            recent_issues = issues  # Already limited in the connector
            all_data.extend(recent_issues)
        
        # Fetch pull requests (limited)
        if include_prs:
            prs = github_connector.fetch_pull_requests(repo, limit=items_limit//2)
            recent_prs = prs  # Already limited in the connector
            all_data.extend(recent_prs)
        
        if not all_data:
            return {
                "status": "success",
                "repo_name": repo_name,
                "items_fetched": 0,
                "chunks_processed": 0,
                "message": f"No data found in {repo_name} or repository is empty"
            }
        
        # Create GitHub data structure for processing
        github_data = {
            "type": "github",
            "repository": repo_name,
            "items": all_data,
            "fetched_at": datetime.now().isoformat()
        }
        
        # Process the data in smaller batches
        processed_chunks = data_processor.process_github_data(github_data)
        
        # Generate embeddings and store in vector database (batch processing)
        total_stored = 0
        if rag_engine.collection and processed_chunks:
            embedding_generator = EmbeddingGenerator()
            
            # Process in batches to prevent memory issues
            batch_size = 10
            
            for i in range(0, len(processed_chunks), batch_size):
                batch = processed_chunks[i:i + batch_size]
                
                for chunk_idx, chunk in enumerate(batch):
                    try:
                        chunk_text = chunk["text"]
                        metadata = chunk["metadata"]
                        metadata["repo_name"] = repo_name
                        
                        # Generate unique ID for chunk
                        chunk_id = f"{repo_name}_{metadata.get('type', 'unknown')}_{metadata.get('id', 'unknown')}_{chunk.get('chunk_index', chunk_idx)}"
                        chunk_id = chunk_id.replace("/", "_").replace(" ", "_")
                        
                        # Generate embedding
                        embedding = embedding_generator.generate_embedding(chunk_text)
                        
                        # Store in vector database
                        rag_engine.collection.add(
                            ids=[chunk_id],
                            embeddings=[embedding],
                            documents=[chunk_text],
                            metadatas=[metadata]
                        )
                        total_stored += 1
                        
                    except Exception as e:
                        print(f"Warning: Failed to process chunk {chunk.get('id', 'unknown')}: {str(e)}")
                        continue
        
        return {
            "status": "success",
            "repo_name": repo_name,
            "items_fetched": len(all_data),
            "chunks_processed": len(processed_chunks),
            "chunks_stored": total_stored,
            "message": f"Successfully ingested data from {repo_name} (limited to {items_limit} most recent items)",
            "note": f"Processed {len(all_data)} items out of potentially more available. For full ingestion, use the manual scripts."
        }
    
    except Exception as e:
        error_msg = str(e)
        if "timeout" in error_msg.lower() or "time" in error_msg.lower():
            raise HTTPException(
                status_code=408, 
                detail=f"Request timed out while processing {repo_name}. Try reducing max_items or use manual processing for large repositories."
            )
        else:
            raise HTTPException(status_code=500, detail=f"Failed to ingest GitHub data: {error_msg}")

@app.post("/ingest/slack", summary="Ingest Slack Channel Data")
async def ingest_slack_data(request: Dict[str, Any]):
    """Automatically fetch and ingest data from Slack channels"""
    
    channels = request.get("channels", [])
    days_back = request.get("days_back", 30)
    max_messages = request.get("max_messages", 1000)
    
    if not channels:
        raise HTTPException(status_code=400, detail="At least one channel is required")
    
    try:
        # Initialize Slack connector and data processor
        slack_connector = SlackConnector()
        data_processor = DataProcessor()
        
        # Get channel IDs
        all_channels = slack_connector.get_channels()
        channel_map = {ch["name"]: ch["id"] for ch in all_channels}
        
        all_messages = []
        
        for channel_name in channels:
            if channel_name in channel_map:
                channel_id = channel_map[channel_name]
                messages = slack_connector.fetch_channel_messages(
                    channel_id=channel_id,
                    limit=max_messages//len(channels)
                )
                all_messages.extend(messages)
        
        # Create Slack data structure for processing
        slack_data = {
            "type": "slack",
            "channels": channels,
            "messages": all_messages,
            "fetched_at": datetime.now().isoformat()
        }
        
        # Process the data
        processed_chunks = data_processor.process_slack_data(slack_data)
        
        # Generate embeddings and store in vector database
        if rag_engine.collection:
            embedding_generator = EmbeddingGenerator()
            
            for chunk in processed_chunks:
                chunk_text = chunk["text"]
                metadata = chunk["metadata"]
                
                # Generate embedding
                embedding = embedding_generator.generate_embedding(chunk_text)
                
                # Store in vector database
                rag_engine.collection.add(
                    ids=[chunk["id"]],
                    embeddings=[embedding],
                    documents=[chunk_text],
                    metadatas=[metadata]
                )
        
        return {
            "status": "success",
            "channels": channels,
            "messages_fetched": len(all_messages),
            "chunks_processed": len(processed_chunks),
            "message": f"Successfully ingested data from {len(channels)} Slack channels"
        }
    
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to ingest Slack data: {str(e)}")

@app.get("/repositories", summary="List Available Repositories")
async def list_repositories():
    """Get list of repositories that can be ingested"""
    try:
        github_connector = GitHubConnector()
        
        # Get user's repositories
        user = github_connector.client.get_user()
        repos = []
        
        for repo in user.get_repos():
            repos.append({
                "full_name": repo.full_name,
                "name": repo.name,
                "description": repo.description,
                "private": repo.private,
                "language": repo.language,
                "updated_at": repo.updated_at.isoformat() if repo.updated_at else None,
                "stars": repo.stargazers_count,
                "url": repo.html_url
            })
        
        return {
            "repositories": repos,
            "total": len(repos)
        }
    
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to fetch repositories: {str(e)}")

@app.get("/data/sources", summary="Get Data Sources")
async def get_data_sources():
    """Get information about current data sources in the knowledge base"""
    try:
        if not rag_engine.collection:
            return {"sources": [], "total": 0}
        
        # Get all documents and analyze sources
        results = rag_engine.collection.get()
        sources = {}
        
        if results and "metadatas" in results and results["metadatas"]:
            for metadata in results["metadatas"]:
                if metadata:
                    source_type = metadata.get("type", "unknown")
                    source_name = metadata.get("source", "unknown")
                    
                    key = f"{source_type}:{source_name}"
                    if key not in sources:
                        sources[key] = {
                            "type": source_type,
                            "name": source_name,
                            "count": 0,
                            "last_updated": metadata.get("created_at") or metadata.get("timestamp")
                        }
                    sources[key]["count"] += 1
        
        return {
            "sources": list(sources.values()),
            "total": len(results.get("ids", []))
        }
    
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to get data sources: {str(e)}")

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
