"""
User-specific RAG (Retrieval-Augmented Generation) engine
"""

import time
from typing import List, Tuple, Dict, Any, Optional
from auth.user_database import UserVectorDatabase


class UserRAGEngine:
    """User-specific RAG engine for querying knowledge base"""
    
    def __init__(self, username: str):
        """Initialize user-specific RAG engine"""
        self.username = username
        self.vector_db = UserVectorDatabase(username)
        
        # Initialize embedding generator and LLM
        try:
            from scripts.process_data import EmbeddingGenerator
            self.embeddings_gen = EmbeddingGenerator()
        except ImportError:
            self.embeddings_gen = None
        
        # Initialize Gemini for response generation
        try:
            import google.generativeai as genai
            import streamlit as st
            
            # Get API key from secrets
            api_key = st.secrets.get("GOOGLE_API_KEY")
            if api_key:
                genai.configure(api_key=api_key)
                self.model = genai.GenerativeModel('gemini-1.5-flash')
            else:
                self.model = None
        except Exception as e:
            self.model = None
    
    def process_query(self, query: str, max_results: int = 5) -> Tuple[str, List[Dict], float]:
        """
        Process a query and return answer with sources
        
        Returns:
            Tuple of (answer, sources, processing_time)
        """
        start_time = time.time()
        
        try:
            if not self.embeddings_gen:
                return "❌ Embedding generator not available", [], time.time() - start_time
            
            if not self.model:
                return "❌ AI model not available. Please configure GOOGLE_API_KEY", [], time.time() - start_time
            
            # Generate query embedding
            query_embedding = self.embeddings_gen.generate_embedding(query)
            
            # Search for similar documents
            similar_docs = self.vector_db.search_similar_documents(query_embedding, max_results)
            
            if not similar_docs:
                return "I couldn't find any relevant information in your knowledge base. Please add some repositories or documents first.", [], time.time() - start_time
            
            # Prepare context from similar documents
            context_parts = []
            for i, doc in enumerate(similar_docs):
                context_parts.append(f"Source {i+1}: {doc['text']}")
            
            context = "\n\n".join(context_parts)
            
            # Generate response using Gemini
            prompt = f"""
            You are Weaver AI, an intelligent assistant for {self.username}'s project knowledge base.
            
            Based on the following context from the user's knowledge base, please answer the question comprehensively and accurately.
            
            Context:
            {context}
            
            Question: {query}
            
            Please provide a helpful and detailed answer based on the context. If the context doesn't fully answer the question, mention what information is available and what might be missing.
            
            Answer:
            """
            
            response = self.model.generate_content(prompt)
            answer = response.text if response else "I'm sorry, I couldn't generate a response at this time."
            
            processing_time = time.time() - start_time
            return answer, similar_docs, processing_time
            
        except Exception as e:
            processing_time = time.time() - start_time
            return f"❌ Error processing query: {str(e)}", [], processing_time
    
    def search_similar_documents(self, query: str, max_results: int = 10) -> List[Dict]:
        """Search for similar documents without generating a response"""
        try:
            if not self.embeddings_gen:
                return []
            
            # Generate query embedding
            query_embedding = self.embeddings_gen.generate_embedding(query)
            
            # Search for similar documents
            similar_docs = self.vector_db.search_similar_documents(query_embedding, max_results)
            
            return similar_docs
            
        except Exception as e:
            print(f"Error searching documents: {e}")
            return []
    
    def get_stats(self) -> Dict[str, Any]:
        """Get statistics about the user's RAG engine"""
        try:
            vector_stats = self.vector_db.get_stats()
            
            stats = {
                "user": self.username,
                "embedding_generator": "Available" if self.embeddings_gen else "Not Available",
                "ai_model": "Available" if self.model else "Not Available",
                **vector_stats
            }
            
            return stats
        except Exception as e:
            return {
                "user": self.username,
                "error": str(e),
                "total_documents": 0,
                "database_status": "Error"
            }
    
    def add_documents(self, documents: List[Dict], embeddings: List[List[float]]) -> bool:
        """Add documents to user's knowledge base"""
        try:
            return self.vector_db.add_documents(documents, embeddings)
        except Exception as e:
            print(f"Error adding documents: {e}")
            return False
    
    def clear_knowledge_base(self) -> bool:
        """Clear user's knowledge base"""
        try:
            return self.vector_db.clear_database()
        except Exception as e:
            print(f"Error clearing knowledge base: {e}")
            return False
