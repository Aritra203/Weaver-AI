"""
Data processing script for Weaver AI
Processes raw data and creates vector embeddings for semantic search
"""

import json
import os
import sys
from datetime import datetime
from typing import Dict, List, Any, Optional, Tuple
import re

# Add the project root to the Python path
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from config.settings import get_settings

# Import dependencies with fallback for missing packages
try:
    import google.generativeai as genai
    GEMINI_AVAILABLE = True
except ImportError:
    GEMINI_AVAILABLE = False
    print("⚠️ Google Generative AI package not available. Install with: pip install google-generativeai")

try:
    import chromadb
    from chromadb.config import Settings as ChromaSettings
    CHROMADB_AVAILABLE = True
except ImportError:
    CHROMADB_AVAILABLE = False
    print("⚠️ ChromaDB package not available. Install with: pip install chromadb")

try:
    import tiktoken
    TIKTOKEN_AVAILABLE = True
except ImportError:
    TIKTOKEN_AVAILABLE = False
    print("⚠️ Tiktoken package not available. Install with: pip install tiktoken")

settings = get_settings()

class TextProcessor:
    """Handles text cleaning, chunking, and processing"""
    
    def __init__(self):
        """Initialize text processor"""
        self.chunk_size = settings.CHUNK_SIZE
        self.chunk_overlap = settings.CHUNK_OVERLAP
        
        # Initialize tokenizer if available
        if TIKTOKEN_AVAILABLE:
            try:
                import tiktoken
                self.tokenizer = tiktoken.get_encoding("cl100k_base")
            except Exception:
                self.tokenizer = None
                print("⚠️ Could not initialize tokenizer, using character-based chunking")
        else:
            self.tokenizer = None
    
    def clean_text(self, text: str) -> str:
        """Clean and normalize text"""
        if not text:
            return ""
        
        # Remove excessive whitespace
        text = re.sub(r'\s+', ' ', text)
        
        # Remove markdown-style formatting that might interfere
        text = re.sub(r'```[\s\S]*?```', '[CODE_BLOCK]', text)  # Code blocks
        text = re.sub(r'`([^`]+)`', r'[\1]', text)  # Inline code
        
        # Clean up common artifacts
        text = text.replace('\r\n', '\n').replace('\r', '\n')
        text = re.sub(r'\n\s*\n\s*\n+', '\n\n', text)  # Multiple newlines
        
        return text.strip()
    
    def count_tokens(self, text: str) -> int:
        """Count tokens in text"""
        if self.tokenizer:
            return len(self.tokenizer.encode(text))
        else:
            # Fallback: rough estimation (1 token ≈ 4 characters)
            return len(text) // 4
    
    def chunk_text(self, text: str, metadata: Dict[str, Any]) -> List[Dict[str, Any]]:
        """Split text into semantic chunks"""
        if not text or not text.strip():
            return []
        
        cleaned_text = self.clean_text(text)
        
        # If text is shorter than chunk size, return as single chunk
        if self.count_tokens(cleaned_text) <= self.chunk_size:
            return [{
                "text": cleaned_text,
                "metadata": metadata,
                "chunk_index": 0,
                "total_chunks": 1
            }]
        
        # Split into chunks
        chunks = []
        chunk_index = 0
        
        # Simple paragraph-based chunking
        paragraphs = cleaned_text.split('\n\n')
        current_chunk = ""
        
        for paragraph in paragraphs:
            paragraph = paragraph.strip()
            if not paragraph:
                continue
            
            # Check if adding this paragraph would exceed chunk size
            test_chunk = current_chunk + ("\n\n" if current_chunk else "") + paragraph
            
            if self.count_tokens(test_chunk) <= self.chunk_size:
                current_chunk = test_chunk
            else:
                # Save current chunk if it has content
                if current_chunk:
                    chunk_metadata = metadata.copy()
                    chunk_metadata.update({
                        "chunk_index": chunk_index,
                        "chunk_type": "paragraph_group"
                    })
                    
                    chunks.append({
                        "text": current_chunk,
                        "metadata": chunk_metadata
                    })
                    chunk_index += 1
                
                # Start new chunk with current paragraph
                # If paragraph itself is too long, split it further
                if self.count_tokens(paragraph) > self.chunk_size:
                    # Split by sentences
                    sentences = re.split(r'[.!?]+', paragraph)
                    current_chunk = ""
                    
                    for sentence in sentences:
                        sentence = sentence.strip()
                        if not sentence:
                            continue
                        
                        test_chunk = current_chunk + (" " if current_chunk else "") + sentence + "."
                        
                        if self.count_tokens(test_chunk) <= self.chunk_size:
                            current_chunk = test_chunk
                        else:
                            # Save current chunk
                            if current_chunk:
                                chunk_metadata = metadata.copy()
                                chunk_metadata.update({
                                    "chunk_index": chunk_index,
                                    "chunk_type": "sentence_group"
                                })
                                
                                chunks.append({
                                    "text": current_chunk,
                                    "metadata": chunk_metadata
                                })
                                chunk_index += 1
                            
                            current_chunk = sentence + "."
                else:
                    current_chunk = paragraph
        
        # Don't forget the last chunk
        if current_chunk:
            chunk_metadata = metadata.copy()
            chunk_metadata.update({
                "chunk_index": chunk_index,
                "chunk_type": "paragraph_group"
            })
            
            chunks.append({
                "text": current_chunk,
                "metadata": chunk_metadata
            })
        
        # Update total chunks count
        for chunk in chunks:
            chunk["metadata"]["total_chunks"] = len(chunks)
        
        return chunks

class EmbeddingGenerator:
    """Handles embedding generation using Google Gemini API"""
    
    def __init__(self):
        """Initialize embedding generator"""
        if not GEMINI_AVAILABLE:
            raise Exception("Google Generative AI package is required for embedding generation")
        
        if not settings.GOOGLE_API_KEY:
            raise Exception("GOOGLE_API_KEY is required")
        
        import google.generativeai as genai
        genai.configure(api_key=settings.GOOGLE_API_KEY)
        self.client = genai
        self.model = settings.EMBEDDING_MODEL
    
    def generate_embedding(self, text: str) -> List[float]:
        """Generate embedding for a single text"""
        try:
            result = self.client.embed_content(
                model=self.model,
                content=text,
                task_type="retrieval_document"
            )
            return result['embedding']
        except Exception as e:
            raise Exception(f"Failed to generate embedding: {str(e)}")
    
    def generate_embeddings_batch(self, texts: List[str]) -> List[List[float]]:
        """Generate embeddings for multiple texts"""
        embeddings = []
        batch_size = 50  # Gemini API is more conservative
        
        for i in range(0, len(texts), batch_size):
            batch = texts[i:i + batch_size]
            print(f"  🔢 Processing embedding batch {i//batch_size + 1}/{(len(texts)-1)//batch_size + 1}")
            
            try:
                # Gemini processes one at a time in a batch
                batch_embeddings = []
                for text in batch:
                    result = self.client.embed_content(
                        model=self.model,
                        content=text,
                        task_type="retrieval_document"
                    )
                    batch_embeddings.append(result['embedding'])
                embeddings.extend(batch_embeddings)
            except Exception as e:
                print(f"⚠️ Warning: Failed to generate embeddings for batch {i//batch_size + 1}: {str(e)}")
                # Add placeholder embeddings (Gemini embeddings are 768 dimensions)
                embeddings.extend([[0.0] * 768] * len(batch))
        
        return embeddings

class VectorDatabase:
    """Handles vector database operations using ChromaDB"""
    
    def __init__(self, db_path: Optional[str] = None):
        """Initialize vector database"""
        if not CHROMADB_AVAILABLE:
            raise Exception("ChromaDB package is required")
        
        self.db_path = db_path or settings.VECTOR_DB_PATH
        os.makedirs(os.path.dirname(self.db_path), exist_ok=True)
        
        # Initialize ChromaDB client
        import chromadb
        self.client = chromadb.PersistentClient(path=self.db_path)
        self.collection_name = "weaver_knowledge"
        
        # Get or create collection
        try:
            self.collection = self.client.get_collection(name=self.collection_name)
            print(f"📚 Connected to existing collection: {self.collection_name}")
        except Exception:
            self.collection = self.client.create_collection(
                name=self.collection_name,
                metadata={"description": "Weaver AI knowledge base"}
            )
            print(f"📚 Created new collection: {self.collection_name}")
    
    def add_documents(self, chunks: List[Dict[str, Any]], embeddings: List[List[float]]):
        """Add documents to vector database"""
        if not chunks or not embeddings:
            return
        
        if len(chunks) != len(embeddings):
            raise ValueError("Number of chunks and embeddings must match")
        
        # Prepare data for ChromaDB
        documents = []
        metadatas = []
        ids = []
        
        for i, chunk in enumerate(chunks):
            # Create unique ID
            source = chunk["metadata"].get("source", "unknown")
            chunk_id = f"{source}_{chunk['metadata'].get('id', i)}_{chunk['metadata'].get('chunk_index', 0)}"
            ids.append(chunk_id)
            
            # Add document text
            documents.append(chunk["text"])
            
            # Prepare metadata (ChromaDB requires string values)
            metadata = {}
            for key, value in chunk["metadata"].items():
                if value is not None:
                    metadata[key] = str(value)
            metadatas.append(metadata)
        
        # Add to collection
        try:
            # Ensure embeddings is a list of lists of floats
            embeddings_list = []
            for emb in embeddings:
                if isinstance(emb, list):
                    embeddings_list.append([float(x) for x in emb])
                else:
                    embeddings_list.append(emb)
            
            self.collection.add(
                embeddings=embeddings_list,
                documents=documents,
                metadatas=metadatas,
                ids=ids
            )
            print(f"✅ Added {len(chunks)} documents to vector database")
        except Exception as e:
            print(f"❌ Failed to add documents to vector database: {str(e)}")
            raise
    
    def get_stats(self) -> Dict[str, Any]:
        """Get database statistics"""
        count = self.collection.count()
        return {
            "document_count": count,
            "collection_name": self.collection_name,
            "db_path": self.db_path
        }

class DataProcessor:
    """Main data processing orchestrator"""
    
    def __init__(self):
        """Initialize data processor"""
        self.text_processor = TextProcessor()
        
        # Initialize components if dependencies are available
        self.embedding_generator = None
        self.vector_db = None
        
        if GEMINI_AVAILABLE and settings.GOOGLE_API_KEY:
            try:
                self.embedding_generator = EmbeddingGenerator()
                print("✅ Gemini embedding generator initialized")
            except Exception as e:
                print(f"⚠️ Failed to initialize embedding generator: {str(e)}")
        
        if CHROMADB_AVAILABLE:
            try:
                self.vector_db = VectorDatabase()
                print("✅ Vector database initialized")
            except Exception as e:
                print(f"⚠️ Failed to initialize vector database: {str(e)}")
    
    def load_raw_data(self) -> List[Dict[str, Any]]:
        """Load all raw data files"""
        raw_files = []
        
        if not os.path.exists(settings.RAW_DATA_PATH):
            print(f"❌ Raw data directory not found: {settings.RAW_DATA_PATH}")
            return raw_files
        
        for filename in os.listdir(settings.RAW_DATA_PATH):
            if filename.endswith('.json'):
                filepath = os.path.join(settings.RAW_DATA_PATH, filename)
                try:
                    with open(filepath, 'r', encoding='utf-8') as f:
                        data = json.load(f)
                        raw_files.append({
                            "filename": filename,
                            "filepath": filepath,
                            "data": data
                        })
                        print(f"📂 Loaded: {filename}")
                except Exception as e:
                    print(f"⚠️ Failed to load {filename}: {str(e)}")
        
        print(f"✅ Loaded {len(raw_files)} raw data files")
        return raw_files
    
    def process_github_data(self, data: Dict[str, Any]) -> List[Dict[str, Any]]:
        """Process GitHub data into chunks"""
        chunks = []
        
        # Handle the structure created by the backend: data["items"]
        items = data.get("items", [])
        
        for item in items:
            # Determine if this is an issue or PR by checking for 'merged_at' or other PR-specific fields
            is_pr = "merged_at" in item or "base" in item or "head" in item
            item_type = "pull_request" if is_pr else "issue"
            
            # Main item content
            item_text = f"{item_type.replace('_', ' ').title()}: {item['title']}\n\n{item.get('body', '')}"
            base_metadata = {
                "source": "github",
                "type": item_type,
                "id": str(item["id"]),
                "number": item["number"],
                "title": item["title"],
                "author": item.get("author", "unknown"),
                "url": item.get("url", ""),
                "created_at": item.get("created_at"),
                "state": item.get("state", "unknown"),
                "labels": ",".join(item.get("labels", [])),
                "repository": data.get("repository", "unknown")
            }
            
            # Add PR-specific metadata
            if is_pr:
                base_metadata.update({
                    "merged": item.get("merged", False),
                    "merged_at": item.get("merged_at"),
                    "base_branch": item.get("base", {}).get("ref", "unknown"),
                    "head_branch": item.get("head", {}).get("ref", "unknown")
                })
            
            item_chunks = self.text_processor.chunk_text(item_text, base_metadata)
            chunks.extend(item_chunks)
            
            # Process comments
            for comment in item.get("comments", []):
                if comment.get("body"):  # Only process comments with content
                    comment_text = comment["body"]
                    comment_metadata = base_metadata.copy()
                    comment_metadata.update({
                        "type": f"{item_type}_comment",
                        "comment_id": str(comment["id"]),
                        "comment_author": comment.get("author", "unknown"),
                        "comment_url": comment.get("url", ""),
                        "comment_created_at": comment.get("created_at")
                    })
                    
                    comment_chunks = self.text_processor.chunk_text(comment_text, comment_metadata)
                    chunks.extend(comment_chunks)
        
        print(f"📦 Processed {len(items)} items into {len(chunks)} chunks")
        return chunks

    def process_slack_data(self, data: Dict[str, Any]) -> List[Dict[str, Any]]:
        """Process Slack data into chunks"""
        chunks = []
        
        # Handle the structure created by the backend: data["messages"]
        messages = data.get("messages", [])
        
        for message in messages:
            # Skip empty messages
            if not message.get("text", "").strip():
                continue
            
            # Main message
            base_metadata = {
                "source": "slack",
                "type": "message",
                "channel_id": message.get("channel_id", ""),
                "channel_name": message.get("channel_name", ""),
                "message_ts": message.get("ts", ""),
                "author": message.get("user_name", "unknown"),
                "timestamp": message.get("timestamp", ""),
                "thread_ts": message.get("thread_ts", "")
            }
            
            message_chunks = self.text_processor.chunk_text(message["text"], base_metadata)
            chunks.extend(message_chunks)
            
            # Process thread replies
            for reply in message.get("replies", []):
                if reply.get("text", "").strip():
                    reply_metadata = base_metadata.copy()
                    reply_metadata.update({
                        "type": "thread_reply",
                        "reply_ts": reply.get("ts", ""),
                        "reply_author": reply.get("user_name", "unknown")
                    })
                    
                    reply_chunks = self.text_processor.chunk_text(reply["text"], reply_metadata)
                    chunks.extend(reply_chunks)
        
        print(f"📦 Processed {len(messages)} messages into {len(chunks)} chunks")
        return chunks

    def process_all_data(self) -> Tuple[List[Dict[str, Any]], Dict[str, Any]]:
        """Process all raw data and generate embeddings"""
        print("🚀 Starting data processing...")
        
        # Load raw data
        raw_files = self.load_raw_data()
        if not raw_files:
            print("❌ No raw data files found. Run data ingestion first.")
            return [], {}
        
        # Process each file
        all_chunks = []
        stats = {"files_processed": 0, "chunks_created": 0, "sources": {}}
        
        for file_info in raw_files:
            filename = file_info["filename"]
            data = file_info["data"]
            
            print(f"🔄 Processing {filename}...")
            
            try:
                if filename.startswith("github_"):
                    chunks = self.process_github_data(data)
                    source = "github"
                elif filename.startswith("slack_"):
                    chunks = self.process_slack_data(data)
                    source = "slack"
                else:
                    print(f"⚠️ Unknown file type: {filename}")
                    continue
                
                all_chunks.extend(chunks)
                stats["files_processed"] += 1
                stats["chunks_created"] += len(chunks)
                stats["sources"][source] = stats["sources"].get(source, 0) + len(chunks)
                
                print(f"  ✅ Created {len(chunks)} chunks from {filename}")
                
            except Exception as e:
                print(f"❌ Failed to process {filename}: {str(e)}")
                continue
        
        print(f"📊 Processing complete: {len(all_chunks)} total chunks created")
        
        # Save processed chunks
        self.save_processed_chunks(all_chunks)
        
        # Generate embeddings and store in vector database
        if self.embedding_generator and self.vector_db and all_chunks:
            print("🧠 Generating embeddings...")
            texts = [chunk["text"] for chunk in all_chunks]
            embeddings = self.embedding_generator.generate_embeddings_batch(texts)
            
            print("💾 Storing in vector database...")
            self.vector_db.add_documents(all_chunks, embeddings)
            
            # Get database stats
            db_stats = self.vector_db.get_stats()
            stats.update(db_stats)
        
        return all_chunks, stats
    
    def save_processed_chunks(self, chunks: List[Dict[str, Any]]):
        """Save processed chunks to file"""
        os.makedirs(settings.PROCESSED_DATA_PATH, exist_ok=True)
        
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        filename = f"processed_chunks_{timestamp}.json"
        filepath = os.path.join(settings.PROCESSED_DATA_PATH, filename)
        
        processed_data = {
            "metadata": {
                "processed_at": datetime.now().isoformat(),
                "total_chunks": len(chunks),
                "chunk_size": settings.CHUNK_SIZE,
                "chunk_overlap": settings.CHUNK_OVERLAP
            },
            "chunks": chunks
        }
        
        with open(filepath, 'w', encoding='utf-8') as f:
            json.dump(processed_data, f, indent=2, ensure_ascii=False)
        
        print(f"💾 Saved processed chunks to {filepath}")

def main():
    """Main entry point"""
    import argparse
    
    parser = argparse.ArgumentParser(description="Weaver AI Data Processing")
    parser.add_argument("--skip-embeddings", action="store_true", help="Skip embedding generation")
    parser.add_argument("--chunk-size", type=int, help="Override chunk size")
    
    args = parser.parse_args()
    
    try:
        # Override settings if provided
        if args.chunk_size:
            settings.CHUNK_SIZE = args.chunk_size
        
        processor = DataProcessor()
        
        # Check if we can do full processing
        if args.skip_embeddings or not processor.embedding_generator or not processor.vector_db:
            print("ℹ️ Running in text processing only mode")
        
        # Process data
        chunks, stats = processor.process_all_data()
        
        # Print summary
        print("\n" + "="*60)
        print("📊 PROCESSING SUMMARY")
        print("="*60)
        print(f"📁 Files processed: {stats.get('files_processed', 0)}")
        print(f"📝 Chunks created: {stats.get('chunks_created', 0)}")
        
        for source, count in stats.get("sources", {}).items():
            print(f"  - {source}: {count} chunks")
        
        if "document_count" in stats:
            print(f"🗃️ Vector database: {stats['document_count']} documents")
            print(f"📂 Database path: {stats['db_path']}")
        
        if chunks:
            print(f"\n💡 Next step: Run 'python backend/main.py' to start the API server")
        else:
            print("\n⚠️ No chunks were created. Check your raw data and try again.")
            sys.exit(1)
        
    except KeyboardInterrupt:
        print("\n\n⏹️ Processing cancelled by user")
        sys.exit(1)
    except Exception as e:
        print(f"\n❌ Fatal error: {str(e)}")
        sys.exit(1)

if __name__ == "__main__":
    main()
