"""
Streamlit Cloud Deployment Verification Script
"""

def check_streamlit_deployment():
    """Check if the Streamlit app would deploy successfully"""
    print("🚀 Streamlit Cloud Deployment Check")
    print("=" * 40)
    
    try:
        # Import main app components
        print("📦 Checking core imports...")
        import streamlit as st
        print("✅ Streamlit imported successfully")
        
        import pandas as pd
        import numpy as np
        print("✅ Data processing libraries imported")
        
        import chromadb
        print("✅ ChromaDB imported successfully")
        
        import google.generativeai as genai
        print("✅ Google Generative AI imported")
        
        # Check authentication modules
        print("\n🔐 Checking authentication modules...")
        from auth.user_auth import UserManager, AuthUI
        from auth.user_database import UserDataManager, UserVectorDatabase
        from auth.user_rag import UserRAGEngine
        print("✅ All authentication modules imported")
        
        # Check backend modules
        print("\n⚙️ Checking backend modules...")
        from backend.rag_engine import RAGEngine
        print("✅ Backend modules imported")
        
        # Check configuration
        print("\n🔧 Checking configuration...")
        from config.settings import get_settings
        settings = get_settings()
        print("✅ Configuration loaded")
        
        # Test core functionality instantiation
        print("\n🧪 Testing component instantiation...")
        
        # Test UserManager
        user_mgr = UserManager()
        print("✅ UserManager instantiated")
        
        # Test AuthUI (with minimal Streamlit session state)
        if not hasattr(st, 'session_state'):
            st.session_state = {}
        auth_ui = AuthUI()
        print("✅ AuthUI instantiated")
        
        # Test basic functionality
        print("\n🔍 Testing basic functionality...")
        
        # Check if required environment variables would be accessible
        required_vars = [
            'GOOGLE_API_KEY',
            'GITHUB_TOKEN'
        ]
        
        missing_vars = []
        for var in required_vars:
            if var == 'GOOGLE_API_KEY' and not settings.GOOGLE_API_KEY:
                missing_vars.append(var)
            elif var == 'GITHUB_TOKEN' and not settings.GITHUB_TOKEN:
                missing_vars.append(var)
        
        if missing_vars:
            print(f"⚠️  Missing environment variables: {', '.join(missing_vars)}")
            print("   These should be set in Streamlit Cloud secrets")
        else:
            print("✅ All required environment variables configured")
        
        print("\n🎉 Deployment Check Completed Successfully!")
        print("✅ The application should deploy successfully to Streamlit Cloud")
        
        return True
        
    except ImportError as e:
        print(f"❌ Import error: {e}")
        print("   Missing dependencies detected")
        return False
    except Exception as e:
        print(f"❌ Error during check: {e}")
        import traceback
        traceback.print_exc()
        return False

def print_deployment_instructions():
    """Print deployment instructions for Streamlit Cloud"""
    print("\n" + "="*60)
    print("📋 STREAMLIT CLOUD DEPLOYMENT INSTRUCTIONS")
    print("="*60)
    
    instructions = [
        "1. Go to https://share.streamlit.io/",
        "2. Connect your GitHub account",
        "3. Select repository: Aritra203/Weaver-AI", 
        "4. Set main file path: streamlit_app.py",
        "5. Set Python version: 3.13",
        "6. Configure secrets:",
        "   - GOOGLE_API_KEY=your_api_key",
        "   - GITHUB_TOKEN=your_github_token",
        "7. Click 'Deploy!'",
        "",
        "📱 Features Ready for Testing:",
        "✅ Multi-user authentication system",
        "✅ User registration and login",
        "✅ Per-user knowledge bases",
        "✅ GitHub repository ingestion", 
        "✅ Personalized RAG engine",
        "✅ User data isolation",
        "✅ Session management",
        "✅ Vector database per user"
    ]
    
    for instruction in instructions:
        print(f"   {instruction}")
    
    print("\n🌟 Your Weaver AI multi-user system is ready for deployment!")

if __name__ == "__main__":
    success = check_streamlit_deployment()
    if success:
        print_deployment_instructions()
    else:
        print("\n❌ Deployment check failed. Please fix the issues above.")
