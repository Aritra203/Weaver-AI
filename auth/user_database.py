"""
User-specific database and vector store management
"""

import os
import sqlite3
import shutil
from typing import Dict, Any, Optional
import chromadb
from chromadb.config import Settings

class UserVectorDatabase:
    """User-specific vector database management"""
    
    def __init__(self, username: str):
        """Initialize user-specific vector database"""
        self.username = username
        self.user_data_path = f"data/users/{username}"
        self.vector_db_path = f"{self.user_data_path}/vector_db"
        self.collection_name = f"weaver_kb_{username}"
        
        # Ensure directories exist
        os.makedirs(self.vector_db_path, exist_ok=True)
        
        # SQLite compatibility fix for ChromaDB
        try:
            __import__('pysqlite3')
            import sys
            if 'pysqlite3' in sys.modules:
                sys.modules['sqlite3'] = sys.modules.pop('pysqlite3')
        except ImportError:
            pass
        
        # Initialize ChromaDB client
        self.client = chromadb.PersistentClient(
            path=self.vector_db_path,
            settings=Settings(
                anonymized_telemetry=False,
                allow_reset=True
            )
        )
        
        # Get or create collection
        try:
            self.collection = self.client.get_collection(name=self.collection_name)
        except:
            self.collection = self.client.create_collection(
                name=self.collection_name,
                metadata={"description": f"Knowledge base for user {username}"}
            )
    
    def add_documents(self, documents: list, embeddings: list):
        """Add documents to user's vector database"""
        try:
            # Prepare data for ChromaDB
            ids = []
            texts = []
            metadatas = []
            
            for i, doc in enumerate(documents):
                # Create unique ID for this user's document
                doc_id = f"{self.username}_{doc.get('id', f'doc_{i}')}"
                ids.append(doc_id)
                texts.append(doc.get('text', ''))
                
                # Ensure metadata is a dictionary
                metadata = doc.get('metadata', {})
                if not isinstance(metadata, dict):
                    metadata = {}
                metadata['user'] = self.username
                metadatas.append(metadata)
            
            # Add to collection
            self.collection.add(
                ids=ids,
                documents=texts,
                embeddings=embeddings,
                metadatas=metadatas
            )
            
            return True
        except Exception as e:
            print(f"Error adding documents: {e}")
            return False
    
    def search_similar_documents(self, query_embedding: list, max_results: int = 5):
        """Search for similar documents in user's vector database"""
        try:
            results = self.collection.query(
                query_embeddings=[query_embedding],
                n_results=max_results,
                include=['documents', 'metadatas', 'distances']
            )
            
            # Format results
            formatted_results = []
            if results['documents'] and results['documents'][0]:
                for i in range(len(results['documents'][0])):
                    formatted_results.append({
                        'text': results['documents'][0][i],
                        'metadata': results['metadatas'][0][i] if results['metadatas'] else {},
                        'score': 1 - results['distances'][0][i] if results['distances'] else 0  # Convert distance to similarity
                    })
            
            return formatted_results
        except Exception as e:
            print(f"Error searching documents: {e}")
            return []
    
    def get_stats(self) -> Dict[str, Any]:
        """Get statistics about user's vector database"""
        try:
            count = self.collection.count()
            return {
                "total_documents": count,
                "database_status": "Connected",
                "collection_name": self.collection_name,
                "user": self.username
            }
        except Exception as e:
            return {
                "total_documents": 0,
                "database_status": f"Error: {str(e)}",
                "collection_name": self.collection_name,
                "user": self.username
            }
    
    def clear_database(self):
        """Clear user's vector database"""
        try:
            # Delete the collection
            self.client.delete_collection(name=self.collection_name)
            
            # Recreate empty collection
            self.collection = self.client.create_collection(
                name=self.collection_name,
                metadata={"description": f"Knowledge base for user {self.username}"}
            )
            
            return True
        except Exception as e:
            print(f"Error clearing database: {e}")
            return False


class UserDataManager:
    """Manages user-specific data operations"""
    
    def __init__(self, username: str):
        """Initialize user data manager"""
        self.username = username
        self.user_data_path = f"data/users/{username}"
        self.raw_data_path = f"{self.user_data_path}/raw"
        self.processed_data_path = f"{self.user_data_path}/processed"
        
        # Ensure directories exist
        for path in [self.raw_data_path, self.processed_data_path]:
            os.makedirs(path, exist_ok=True)
    
    def save_raw_data(self, data: Dict[str, Any], source_type: str, source_name: str) -> str:
        """Save raw data for user"""
        try:
            import json
            from datetime import datetime
            
            # Create filename
            timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
            filename = f"{source_type}_{source_name.replace('/', '_')}_{timestamp}.json"
            filepath = os.path.join(self.raw_data_path, filename)
            
            # Add user metadata
            data['user'] = self.username
            data['created_at'] = datetime.now().isoformat()
            
            # Save file
            with open(filepath, 'w', encoding='utf-8') as f:
                json.dump(data, f, indent=2, ensure_ascii=False)
            
            return filepath
        except Exception as e:
            print(f"Error saving raw data: {e}")
            return ""
    
    def get_raw_data_files(self) -> list:
        """Get list of user's raw data files"""
        try:
            if not os.path.exists(self.raw_data_path):
                return []
            
            files = []
            for filename in os.listdir(self.raw_data_path):
                if filename.endswith('.json'):
                    filepath = os.path.join(self.raw_data_path, filename)
                    files.append({
                        'filename': filename,
                        'filepath': filepath,
                        'size': os.path.getsize(filepath),
                        'modified': os.path.getmtime(filepath)
                    })
            
            # Sort by modification time (newest first)
            files.sort(key=lambda x: x['modified'], reverse=True)
            return files
        except Exception as e:
            print(f"Error getting raw data files: {e}")
            return []
    
    def clear_all_data(self):
        """Clear all user data"""
        try:
            paths_to_clear = [self.raw_data_path, self.processed_data_path]
            
            for path in paths_to_clear:
                if os.path.exists(path):
                    shutil.rmtree(path)
                    os.makedirs(path, exist_ok=True)
            
            return True
        except Exception as e:
            print(f"Error clearing user data: {e}")
            return False
    
    def get_user_stats(self) -> Dict[str, Any]:
        """Get user's data statistics"""
        try:
            raw_files = self.get_raw_data_files()
            
            # Count processed files
            processed_count = 0
            if os.path.exists(self.processed_data_path):
                processed_count = len([f for f in os.listdir(self.processed_data_path) if f.endswith('.json')])
            
            # Calculate total size
            total_size = sum(f['size'] for f in raw_files)
            
            return {
                'raw_files_count': len(raw_files),
                'processed_files_count': processed_count,
                'total_data_size': total_size,
                'user': self.username
            }
        except Exception as e:
            return {
                'raw_files_count': 0,
                'processed_files_count': 0,
                'total_data_size': 0,
                'user': self.username,
                'error': str(e)
            }
