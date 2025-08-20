"""
Debug version of streamlit app to fix authentication issues
"""

import streamlit as st
import os
import sys

# Set up page config first
st.set_page_config(
    page_title="Weaver AI - Debug",
    page_icon="🔍",
    layout="wide"
)

def test_authentication():
    """Test authentication step by step"""
    st.title("🔍 Authentication Debug")
    
    # Show debug info
    col1, col2 = st.columns(2)
    
    with col1:
        st.subheader("System Status")
        
        try:
            # Test imports
            from auth.user_auth import AuthUI, UserManager
            st.success("✅ Auth modules imported")
            
            # Test UserManager
            user_mgr = UserManager()
            st.success("✅ UserManager initialized")
            
            # Test AuthUI
            auth_ui = AuthUI()
            st.success("✅ AuthUI initialized")
            
            # Show session state
            st.write("Session State:")
            st.json(dict(st.session_state))
            
        except Exception as e:
            st.error(f"❌ Import/Init error: {e}")
            st.stop()
    
    with col2:
        st.subheader("Authentication")
        
        # Test authentication
        try:
            user_info = auth_ui.render_auth_forms()
            
            if user_info:
                st.success(f"✅ Authenticated as: {user_info['username']}")
                
                # Test user components
                try:
                    from auth.user_database import UserDataManager
                    from auth.user_rag import UserRAGEngine
                    
                    st.write("Initializing user components...")
                    user_data_mgr = UserDataManager(user_info['username'])
                    user_rag_engine = UserRAGEngine(user_info['username'])
                    
                    st.success("✅ User components initialized")
                    
                    # Show stats
                    stats = user_rag_engine.get_stats()
                    st.write("User RAG Stats:")
                    st.json(stats)
                    
                except Exception as e:
                    st.error(f"❌ User component error: {e}")
                    import traceback
                    st.code(traceback.format_exc())
            
        except Exception as e:
            st.error(f"❌ Auth error: {e}")
            import traceback
            st.code(traceback.format_exc())

if __name__ == "__main__":
    test_authentication()
