"""
RAG (Retrieval-Augmented Generation) engine for Weaver AI
Handles semantic search and AI-powered answer generation
"""

import os
import sys
from typing import List, Dict, Any, Optional, Tuple
import time

# Add the project root to the Python path
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from config.settings import get_settings

# Import dependencies with fallback
try:
    import google.generativeai as genai
    GEMINI_AVAILABLE = True
except ImportError:
    GEMINI_AVAILABLE = False

# Handle ChromaDB and SQLite compatibility
try:
    # Try to fix SQLite version issue first
    import sys
    __import__('pysqlite3')
    sys.modules['sqlite3'] = sys.modules.pop('pysqlite3')
except ImportError:
    pass

try:
    import chromadb
    CHROMADB_AVAILABLE = True
except (ImportError, RuntimeError) as e:
    CHROMADB_AVAILABLE = False
    print(f"⚠️ ChromaDB not available: {str(e)}")
    print("💡 App will work with limited functionality (no persistent vector storage)")

settings = get_settings()

class RAGEngine:
    """Retrieval-Augmented Generation engine"""
    
    def __init__(self):
        """Initialize RAG engine components"""
        self.gemini_client = None
        self.vector_db = None
        self.collection = None
        
        # Initialize Gemini client
        if GEMINI_AVAILABLE and settings.GOOGLE_API_KEY:
            import google.generativeai as genai
            genai.configure(api_key=settings.GOOGLE_API_KEY)
            self.gemini_client = genai
            print("✅ Gemini client initialized")
        else:
            print("⚠️ Gemini not available - responses will be limited")
        
        # Initialize vector database
        if CHROMADB_AVAILABLE:
            try:
                import chromadb
                self.vector_db = chromadb.PersistentClient(path=settings.VECTOR_DB_PATH)
                self.collection = self.vector_db.get_collection(name="weaver_knowledge")
                print(f"✅ Vector database connected: {self.collection.count()} documents")
            except Exception as e:
                print(f"⚠️ Vector database not available: {str(e)}")
        else:
            print("⚠️ ChromaDB not available - semantic search disabled")
    
    def is_ready(self) -> bool:
        """Check if RAG engine is ready to process queries"""
        return (self.gemini_client is not None and 
                self.vector_db is not None and 
                self.collection is not None)
    
    def get_status(self) -> Dict[str, str]:
        """Get component status"""
        return {
            "gemini": "ready" if self.gemini_client else "unavailable",
            "vector_db": "ready" if self.collection else "unavailable",
            "overall": "ready" if self.is_ready() else "partial"
        }
    
    def generate_query_embedding(self, query: str) -> List[float]:
        """Generate embedding for user query"""
        if not self.gemini_client:
            raise Exception("Gemini client not available")
        
        try:
            result = self.gemini_client.embed_content(
                model=settings.EMBEDDING_MODEL,
                content=query,
                task_type="retrieval_query"
            )
            return result['embedding']
        except Exception as e:
            raise Exception(f"Failed to generate query embedding: {str(e)}")
    
    def search_similar_documents(self, query: str, max_results: int = 5) -> List[Dict[str, Any]]:
        """Search for documents similar to the query"""
        if not self.collection:
            raise Exception("Vector database not available")
        
        # Generate query embedding
        query_embedding = self.generate_query_embedding(query)
        
        # Search vector database
        try:
            results = self.collection.query(
                query_embeddings=[query_embedding],
                n_results=max_results,
                include=['documents', 'metadatas', 'distances']
            )
            
            # Format results safely
            documents = []
            if results and isinstance(results, dict):
                docs_list = results.get('documents')
                if docs_list and len(docs_list) > 0 and docs_list[0]:
                    docs = docs_list[0]
                    metadatas_list = results.get('metadatas', [[]])
                    metadatas = metadatas_list[0] if metadatas_list and len(metadatas_list) > 0 else []
                    distances_list = results.get('distances', [[]])
                    distances = distances_list[0] if distances_list and len(distances_list) > 0 else []
                    
                    for i in range(len(docs)):
                        doc = {
                            "text": docs[i],
                            "metadata": metadatas[i] if i < len(metadatas) else {},
                            "similarity_score": 1 - distances[i] if i < len(distances) else 0.0,  # Convert distance to similarity
                        }
                        documents.append(doc)
            
            return documents
            
        except Exception as e:
            raise Exception(f"Failed to search documents: {str(e)}")
    
    def format_sources_for_prompt(self, documents: List[Dict[str, Any]]) -> str:
        """Format retrieved documents for inclusion in the prompt"""
        if not documents:
            return "No relevant documents found in the knowledge base."
        
        formatted_sources = []
        for i, doc in enumerate(documents, 1):
            metadata = doc.get("metadata", {})
            
            # Create source header
            source_type = metadata.get("type", "document")
            source = metadata.get("source", "unknown")
            title = metadata.get("title", "")
            author = metadata.get("author", "")
            url = metadata.get("url", "")
            
            header_parts = [f"Source {i} ({source} {source_type})"]
            if title:
                header_parts.append(f"Title: {title}")
            if author:
                header_parts.append(f"Author: {author}")
            if url:
                header_parts.append(f"URL: {url}")
            
            header = " | ".join(header_parts)
            
            # Add content
            content = doc["text"]
            
            formatted_source = f"{header}\n{'-' * 50}\n{content}\n"
            formatted_sources.append(formatted_source)
        
        return "\n".join(formatted_sources)
    
    def generate_answer(self, query: str, context_documents: List[Dict[str, Any]]) -> str:
        """Generate answer using retrieved context"""
        if not self.gemini_client:
            return self._generate_fallback_answer(query, context_documents)
        
        # Format context
        context = self.format_sources_for_prompt(context_documents)
        
        # Create system prompt
        system_prompt = """You are Weaver AI, an intelligent assistant that helps answer questions about software projects based on their GitHub repositories and Slack conversations.

Your task is to provide helpful, accurate answers based ONLY on the provided context from the project's knowledge base. Follow these guidelines:

1. ONLY use information from the provided sources
2. If the sources don't contain enough information to answer the question, say so clearly
3. Always cite your sources by referencing "Source X" when possible
4. Be concise but thorough
5. If multiple sources contain relevant information, synthesize them coherently
6. Maintain a helpful, professional tone

Remember: You are helping team members understand their own project better by surfacing relevant information from their existing discussions and documentation."""
        
        # Create user prompt
        user_prompt = f"""Question: {query}

Context from project knowledge base:
{context}

Please provide a helpful answer based on the above context. If the context doesn't contain enough information to answer the question, please say so and suggest what kind of information would be needed."""
        
        try:
            model = self.gemini_client.GenerativeModel(settings.CHAT_MODEL)
            
            # Combine system and user prompts for Gemini
            full_prompt = f"{system_prompt}\n\n{user_prompt}"
            
            response = model.generate_content(
                full_prompt,
                generation_config=self.gemini_client.types.GenerationConfig(
                    max_output_tokens=settings.MAX_TOKENS,
                    temperature=settings.TEMPERATURE,
                )
            )
            
            content = response.text
            return content.strip() if content else "I apologize, but I couldn't generate a response."
            
        except Exception as e:
            print(f"⚠️ Failed to generate AI answer: {str(e)}")
            return self._generate_fallback_answer(query, context_documents)
    
    def _generate_fallback_answer(self, query: str, context_documents: List[Dict[str, Any]]) -> str:
        """Generate a simple fallback answer when AI is not available"""
        if not context_documents:
            return f"I couldn't find any relevant information in the knowledge base to answer your question: '{query}'. Please try rephrasing your question or check if the relevant data has been ingested."
        
        # Simple extraction-based answer
        answer_parts = [
            f"Based on the available information in the knowledge base, here are the most relevant findings for your question: '{query}'\n"
        ]
        
        for i, doc in enumerate(context_documents[:3], 1):  # Limit to top 3
            metadata = doc.get("metadata", {})
            source_info = f"Source {i}"
            
            if metadata.get("title"):
                source_info += f" - {metadata['title']}"
            if metadata.get("source"):
                source_info += f" ({metadata['source']})"
            
            # Extract first few sentences
            text = doc["text"]
            sentences = text.split('. ')
            excerpt = '. '.join(sentences[:2])
            if len(sentences) > 2:
                excerpt += "..."
            
            answer_parts.append(f"{source_info}:\n{excerpt}\n")
        
        answer_parts.append("Note: This is a basic information retrieval. For more sophisticated analysis, please ensure Gemini integration is configured.")
        
        return "\n".join(answer_parts)
    
    def process_query(self, query: str, max_results: int = 5) -> Tuple[str, List[Dict[str, Any]], float]:
        """Process a complete query: search + generate answer"""
        start_time = time.time()
        
        try:
            # Search for relevant documents
            documents = self.search_similar_documents(query, max_results)
            
            # Generate answer
            answer = self.generate_answer(query, documents)
            
            processing_time = time.time() - start_time
            
            return answer, documents, processing_time
            
        except Exception as e:
            processing_time = time.time() - start_time
            error_answer = f"I encountered an error while processing your question: {str(e)}"
            return error_answer, [], processing_time
    
    def get_stats(self) -> Dict[str, Any]:
        """Get knowledge base statistics"""
        stats = {
            "total_documents": 0,
            "sources": {},
            "last_updated": None,
            "vector_db_path": settings.VECTOR_DB_PATH
        }
        
        if self.collection:
            try:
                # Get total count
                stats["total_documents"] = self.collection.count()
                
                # Get source breakdown (sample a subset to avoid performance issues)
                sample_size = min(1000, stats["total_documents"])
                if sample_size > 0:
                    sample_results = self.collection.get(limit=sample_size, include=['metadatas'])
                    source_counts = {}
                    
                    metadatas = sample_results.get('metadatas', []) if sample_results else []
                    if metadatas:
                        for metadata in metadatas:
                            if metadata:  # Check metadata is not None
                                source = metadata.get('source', 'unknown')
                                source_counts[source] = source_counts.get(source, 0) + 1
                    
                    # Scale up to estimate total distribution
                    if source_counts:
                        scale_factor = stats["total_documents"] / sample_size
                        stats["sources"] = {
                            source: int(count * scale_factor) 
                            for source, count in source_counts.items()
                        }
                
            except Exception as e:
                print(f"⚠️ Error getting stats: {str(e)}")
        
        return stats

def main():
    """Test the RAG engine"""
    print("🧠 Testing Weaver AI RAG Engine")
    print("=" * 50)
    
    try:
        rag = RAGEngine()
        
        # Check status
        status = rag.get_status()
        print(f"Status: {status}")
        
        if not rag.is_ready():
            print("❌ RAG engine not ready. Please ensure:")
            print("  - Vector database is created (run process_data.py)")
            print("  - Google API key is configured")
            return
        
        # Get stats
        stats = rag.get_stats()
        print(f"📊 Knowledge base: {stats['total_documents']} documents")
        
        # Test query
        test_query = input("\nEnter a test question (or press Enter to skip): ").strip()
        if test_query:
            print(f"\n🔍 Processing query: '{test_query}'")
            answer, sources, processing_time = rag.process_query(test_query)
            
            print(f"\n📝 Answer ({processing_time:.2f}s):")
            print(answer)
            
            print(f"\n📚 Sources ({len(sources)}):")
            for i, source in enumerate(sources, 1):
                metadata = source.get("metadata", {})
                print(f"  {i}. {metadata.get('type', 'unknown')} from {metadata.get('source', 'unknown')}")
                if metadata.get('title'):
                    print(f"     Title: {metadata['title']}")
                print(f"     Similarity: {source.get('similarity_score', 0):.3f}")
        
        print("\n✅ RAG engine test completed!")
        
    except Exception as e:
        print(f"❌ Error: {str(e)}")

if __name__ == "__main__":
    main()
