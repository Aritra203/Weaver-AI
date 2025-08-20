"""
Fix for vector database initialization issues
"""

def fix_vector_db_issues():
    """Clear corrupted vector databases and restart fresh"""
    import os
    import shutil
    
    print("🔧 Fixing vector database issues...")
    
    # Clear all user vector databases
    users_path = "data/users"
    if os.path.exists(users_path):
        for username in os.listdir(users_path):
            user_path = os.path.join(users_path, username)
            if os.path.isdir(user_path):
                vector_db_path = os.path.join(user_path, "vector_db")
                if os.path.exists(vector_db_path):
                    try:
                        shutil.rmtree(vector_db_path)
                        os.makedirs(vector_db_path)
                        print(f"✅ Cleared vector DB for user: {username}")
                    except Exception as e:
                        print(f"⚠️ Could not clear vector DB for {username}: {e}")
    
    # Clear global vector database
    global_vector_path = "data/vector_db"
    if os.path.exists(global_vector_path):
        try:
            shutil.rmtree(global_vector_path)
            os.makedirs(global_vector_path)
            print("✅ Cleared global vector DB")
        except Exception as e:
            print(f"⚠️ Could not clear global vector DB: {e}")

def test_vector_db_init():
    """Test vector database initialization"""
    print("\n🧪 Testing vector database initialization...")
    
    try:
        from auth.user_database import UserVectorDatabase
        
        # Test with a clean user
        test_user = "test_vectordb_user"
        user_vdb = UserVectorDatabase(test_user)
        
        stats = user_vdb.get_stats()
        print(f"✅ Vector DB initialized: {stats}")
        
        # Clean up test user
        import os
        import shutil
        test_path = f"data/users/{test_user}"
        if os.path.exists(test_path):
            shutil.rmtree(test_path)
            print("✅ Test user cleaned up")
            
    except Exception as e:
        print(f"❌ Vector DB test failed: {e}")
        import traceback
        traceback.print_exc()

def test_auth_system():
    """Test authentication system"""
    print("\n🔐 Testing authentication system...")
    
    try:
        from auth.user_auth import UserManager, AuthUI
        
        user_mgr = UserManager()
        print("✅ UserManager initialized")
        
        auth_ui = AuthUI()
        print("✅ AuthUI initialized")
        
        print("✅ Authentication system working")
        
    except Exception as e:
        print(f"❌ Auth test failed: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    fix_vector_db_issues()
    test_vector_db_init()
    test_auth_system()
    print("\n🎉 Fix completed! Try running the Streamlit app again.")
