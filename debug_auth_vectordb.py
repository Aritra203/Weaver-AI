"""
Debug authentication and vector database issues
"""

def test_auth_system():
    """Test the authentication system"""
    print("🔐 Testing Authentication System")
    print("=" * 40)
    
    try:
        from auth.user_auth import UserManager
        user_mgr = UserManager()
        print("✅ UserManager initialized successfully")
        
        # Check users database
        import sqlite3
        import os
        
        db_path = 'data/users/users.db'
        if os.path.exists(db_path):
            print("✅ Users database exists")
            
            # Check tables
            conn = sqlite3.connect(db_path)
            cursor = conn.cursor()
            cursor.execute("SELECT name FROM sqlite_master WHERE type='table'")
            tables = cursor.fetchall()
            print("Database tables:", [table[0] for table in tables])
            
            # Check if tables have correct structure
            for table_name in ['users', 'sessions']:
                try:
                    cursor.execute(f"PRAGMA table_info({table_name})")
                    columns = cursor.fetchall()
                    print(f"✅ Table '{table_name}' structure: {len(columns)} columns")
                except Exception as e:
                    print(f"❌ Table '{table_name}' issue: {e}")
            
            conn.close()
        else:
            print("❌ Users database does not exist")
            
    except Exception as e:
        print(f"❌ Auth system error: {e}")
        import traceback
        traceback.print_exc()

def test_vector_db():
    """Test vector database initialization"""
    print("\n🗄️ Testing Vector Database")
    print("=" * 40)
    
    try:
        import chromadb
        print(f"✅ ChromaDB version: {chromadb.__version__}")
        
        # Test ChromaDB client
        client = chromadb.PersistentClient(path="data/vector_db")
        print("✅ ChromaDB client created")
        
        # List existing collections
        collections = client.list_collections()
        print(f"📋 Existing collections: {len(collections)}")
        for collection in collections:
            print(f"   - {collection.name}")
        
        # Test creating a new collection
        try:
            test_collection = client.get_or_create_collection("test_collection")
            print("✅ Test collection created/retrieved")
            
            # Clean up test collection
            client.delete_collection("test_collection")
            print("✅ Test collection cleaned up")
            
        except Exception as e:
            print(f"❌ Collection test failed: {e}")
            
    except Exception as e:
        print(f"❌ Vector DB error: {e}")
        import traceback
        traceback.print_exc()

def test_user_vector_db():
    """Test user-specific vector database"""
    print("\n👤 Testing User Vector Database")
    print("=" * 40)
    
    try:
        from auth.user_database import UserVectorDatabase
        
        # Test with a fake user
        test_username = "test_user"
        user_vdb = UserVectorDatabase(test_username)
        print("✅ UserVectorDatabase initialized")
        
        # Test basic operations
        stats = user_vdb.get_stats()
        print(f"✅ User vector DB stats: {stats}")
        
    except Exception as e:
        print(f"❌ User vector DB error: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    test_auth_system()
    test_vector_db()
    test_user_vector_db()
