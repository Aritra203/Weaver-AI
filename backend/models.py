"""
Data models for Weaver AI backend
Defines request/response schemas and data structures
"""

from datetime import datetime
from typing import List, Optional, Dict, Any
from pydantic import BaseModel, Field

class QueryRequest(BaseModel):
    """Request model for asking questions"""
    question: str = Field(..., description="The question to ask", min_length=1, max_length=1000)
    max_results: Optional[int] = Field(5, description="Maximum number of source documents to retrieve", ge=1, le=20)
    include_metadata: Optional[bool] = Field(True, description="Whether to include source metadata in response")

class SourceDocument(BaseModel):
    """Model for source document information"""
    text: str = Field(..., description="The relevant text content")
    source: str = Field(..., description="Source type (github/slack)")
    type: str = Field(..., description="Document type (issue, pr, message, etc.)")
    url: Optional[str] = Field(None, description="URL to original content")
    title: Optional[str] = Field(None, description="Title or subject")
    author: Optional[str] = Field(None, description="Author or creator")
    created_at: Optional[str] = Field(None, description="Creation timestamp")
    similarity_score: Optional[float] = Field(None, description="Semantic similarity score")
    metadata: Optional[Dict[str, Any]] = Field(None, description="Additional metadata")

class QueryResponse(BaseModel):
    """Response model for question answers"""
    answer: str = Field(..., description="The generated answer")
    sources: List[SourceDocument] = Field(..., description="Source documents used to generate the answer")
    query: str = Field(..., description="The original question")
    timestamp: datetime = Field(default_factory=datetime.now, description="Response timestamp")
    model_used: Optional[str] = Field(None, description="AI model used for generation")
    processing_time: Optional[float] = Field(None, description="Processing time in seconds")

class HealthResponse(BaseModel):
    """Health check response"""
    status: str = Field(..., description="Service status")
    timestamp: datetime = Field(default_factory=datetime.now)
    version: str = Field(..., description="API version")
    components: Dict[str, str] = Field(..., description="Component status")

class StatsResponse(BaseModel):
    """Statistics response"""
    total_documents: int = Field(..., description="Total number of documents in knowledge base")
    sources: Dict[str, int] = Field(..., description="Document count by source")
    last_updated: Optional[str] = Field(None, description="Last update timestamp")
    vector_db_path: Optional[str] = Field(None, description="Vector database path")

class ErrorResponse(BaseModel):
    """Error response model"""
    error: str = Field(..., description="Error message")
    detail: Optional[str] = Field(None, description="Detailed error information")
    timestamp: datetime = Field(default_factory=datetime.now)
    request_id: Optional[str] = Field(None, description="Request identifier for debugging")
