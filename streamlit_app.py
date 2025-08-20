"""
Streamlit web interface for Weaver AI
Provides an intuitive chat-like interface for querying the knowledge base
"""

import os
import sys
import json
from datetime import datetime
from typing import Dict, List, Any, Optional

# SQLite compatibility fix for ChromaDB on Streamlit Cloud
try:
    __import__('pysqlite3')
    import sys
    sys.modules['sqlite3'] = sys.modules.pop('pysqlite3')
except ImportError:
    pass

# Add the project root to the Python path
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

# Import dependencies with fallback
try:
    import streamlit as st
    STREAMLIT_AVAILABLE = True
except ImportError:
    STREAMLIT_AVAILABLE = False
    print("❌ Streamlit not available. Install with: pip install streamlit")
    sys.exit(1)

from config.settings import get_settings

# Import RAG engine directly for cloud deployment
try:
    from backend.rag_engine import RAGEngine
    RAG_AVAILABLE = True
except ImportError as e:
    RAG_AVAILABLE = False
    RAGEngine = None  # Define RAGEngine as None when not available

settings = get_settings()

# Page configuration
st.set_page_config(
    page_title="Weaver AI",
    page_icon="🧠",
    layout="wide",
    initial_sidebar_state="expanded"
)

class WeaverAIInterface:
    """Main interface class for Weaver AI"""
    
    def __init__(self):
        """Initialize the interface"""
        self.rag_engine = None
        self.session_state_keys = [
            "messages", "rag_connected", "stats", "last_check"
        ]
        self.init_session_state()
        self.init_rag_engine()
    
    def init_rag_engine(self):
        """Initialize the RAG engine"""
        if not RAG_AVAILABLE or RAGEngine is None:
            st.session_state.rag_connected = False
            st.error("❌ RAG engine not available. Please check your installation.")
            return
            
        try:
            with st.spinner("🔄 Initializing knowledge base..."):
                self.rag_engine = RAGEngine()
                st.session_state.rag_connected = True
                st.session_state.last_check = datetime.now()
        except Exception as e:
            st.session_state.rag_connected = False
            st.error(f"❌ Failed to initialize RAG engine: {e}")
            st.info("💡 The knowledge base may need to be populated with data first.")
    
    def init_session_state(self):
        """Initialize Streamlit session state"""
        if "messages" not in st.session_state:
            st.session_state.messages = []
        
        if "rag_connected" not in st.session_state:
            st.session_state.rag_connected = False
        
        if "stats" not in st.session_state:
            st.session_state.stats = {}
        
        if "last_check" not in st.session_state:
            st.session_state.last_check = None
    
    def check_api_connection(self) -> bool:
        """Check if the RAG engine is available"""
        if not RAG_AVAILABLE:
            return False
            
        try:
            if self.rag_engine is None:
                self.init_rag_engine()
            
            if self.rag_engine:
                st.session_state.rag_connected = True
                st.session_state.last_check = datetime.now()
                return True
            else:
                st.session_state.rag_connected = False
                return False
        except Exception as e:
            st.session_state.rag_connected = False
            return False
    
    def get_stats(self) -> Optional[Dict[str, Any]]:
        """Get knowledge base statistics"""
        if not self.rag_engine:
            return None
            
        try:
            # Get stats from the RAG engine
            rag_stats = self.rag_engine.get_stats()
            
            stats = {
                "status": "Connected" if st.session_state.rag_connected else "Disconnected",
                "engine_type": "Direct RAG Engine",
                "vector_db": "ChromaDB",
                "last_updated": datetime.now().isoformat()
            }
            
            # Merge with RAG engine stats
            if rag_stats:
                stats.update(rag_stats)
            
            st.session_state.stats = stats
            return stats
        except Exception as e:
            return {"error": str(e)}
    
    def ask_question(self, question: str, max_results: int = 5) -> Optional[Dict[str, Any]]:
        """Ask question using the RAG engine directly"""
        if not self.rag_engine:
            st.error("❌ RAG engine not available")
            return None
            
        try:
            with st.spinner("🤔 Thinking..."):
                # Use the process_query method which returns (answer, sources, processing_time)
                answer, sources, processing_time = self.rag_engine.process_query(
                    query=question,
                    max_results=max_results
                )
                
                return {
                    "response": answer,
                    "sources": sources,
                    "metadata": {
                        "query": question,
                        "results_count": len(sources),
                        "processing_time": processing_time
                    }
                }
                
        except Exception as e:
            st.error(f"❌ Error processing question: {str(e)}")
            return None
    
    def render_header(self):
        """Render the application header"""
        st.title("🧠 Weaver AI")
        st.markdown("*Your intelligent project knowledge assistant*")
        
        # Connection status
        col1, col2, col3 = st.columns([2, 1, 1])
        
        with col1:
            if st.session_state.rag_connected:
                st.success("🟢 RAG Engine Ready")
            else:
                st.error("🔴 RAG Engine not available")
                if st.button("🔄 Retry Connection"):
                    self.check_api_connection()
        
        with col2:
            if st.button("📊 Refresh Stats"):
                self.get_stats()
        
        with col3:
            if st.button("🗑️ Clear Chat"):
                st.session_state.messages = []
                st.rerun()
    
    def render_sidebar(self):
        """Render the sidebar with stats and settings"""
        with st.sidebar:
            st.header("📊 Knowledge Base")
            
            # Stats
            stats = st.session_state.stats
            if stats:
                st.metric("Status", stats.get("status", "Unknown"))
                st.write(f"**Engine**: {stats.get('engine_type', 'RAG Engine')}")
                st.write(f"**Vector DB**: {stats.get('vector_db', 'ChromaDB')}")
                
                # Show document count if available
                if stats.get("total_documents"):
                    st.metric("Documents", stats.get("total_documents", 0))
                
                # Show database info if available
                if stats.get("database_status"):
                    st.write(f"**DB Status**: {stats.get('database_status')}")
                
                if stats.get("last_updated"):
                    st.write(f"**Last Updated**: {stats.get('last_updated')[:19]}")
            else:
                st.info("No statistics available")
                if st.button("Load Stats"):
                    self.get_stats()
                    st.rerun()
            
            st.divider()
            
            # Info Section
            st.header("📖 About Weaver AI")
            st.markdown("""
            **Weaver AI** is your intelligent project knowledge assistant.
            
            Ask questions about:
            - 📁 Project documentation
            - 🔧 Code implementation
            - 🐛 Issues and solutions
            - 📊 Project insights
            
            Simply type your question below and get instant answers!
            """)
            
            st.divider()
            
            # Quick Tips
            st.header("💡 Quick Tips")
            st.markdown("""
            - **Be specific**: "How do I configure the database?" 
            - **Ask about code**: "Show me authentication examples"
            - **Explore features**: "What APIs are available?"
            - **Get help**: "How do I deploy this project?"
            """)
            
            if st.button("🔄 Refresh Knowledge Base"):
                if st.session_state.rag_connected:
                    self.get_stats()
                    st.success("✅ Knowledge base refreshed!")
                else:
                    self.check_api_connection()
                    st.rerun()
    
    def render_welcome_message(self):
        """Render welcome message when no messages exist"""
        if not st.session_state.messages:
            st.markdown("""
            ### 👋 Welcome to Weaver AI!
            
            I'm your intelligent project knowledge assistant. I can help you find information,
            understand code, and answer questions about your project.
            
            **What you can ask me:**
            - 🔍 "How does authentication work in this project?"
            - 📝 "Show me examples of API usage"
            - 🐛 "What are common issues and their solutions?"
            - 🚀 "How do I deploy this application?"
            
            Start by asking questions about the knowledge base! 🚀
            """)
    
    def render_chat_interface(self):
        """Render the main chat interface"""
        # Display chat messages
        for message in st.session_state.messages:
            with st.chat_message(message["role"]):
                if message["role"] == "assistant":
                    st.markdown(message["content"])
                    
                    # Show sources if available
                    if message.get("sources"):
                        with st.expander("📚 Sources", expanded=False):
                            for i, source in enumerate(message["sources"], 1):
                                st.markdown(f"**Source {i}:**")
                                st.markdown(f"- **Content**: {source.get('content', 'N/A')[:200]}...")
                                if source.get('metadata'):
                                    metadata = source['metadata']
                                    if metadata.get('source_type'):
                                        st.markdown(f"- **Type**: {metadata['source_type']}")
                                    if metadata.get('source_name'):
                                        st.markdown(f"- **Source**: {metadata['source_name']}")
                                st.divider()
                else:
                    st.markdown(message["content"])
        
        # Chat input
        if prompt := st.chat_input("Ask me anything about the project..."):
            # Add user message
            st.session_state.messages.append({"role": "user", "content": prompt})
            
            # Display user message
            with st.chat_message("user"):
                st.markdown(prompt)
            
            # Get assistant response
            with st.chat_message("assistant"):
                if not st.session_state.rag_connected:
                    response = "❌ RAG engine is not connected. Please check the connection status above."
                    st.markdown(response)
                    st.session_state.messages.append({"role": "assistant", "content": response})
                else:
                    result = self.ask_question(prompt)
                    
                    if result:
                        response = result["response"]
                        sources = result.get("sources", [])
                        
                        st.markdown(response)
                        
                        # Show sources
                        if sources:
                            with st.expander("📚 Sources", expanded=False):
                                for i, source in enumerate(sources, 1):
                                    st.markdown(f"**Source {i}:**")
                                    st.markdown(f"- **Content**: {source.get('content', 'N/A')[:200]}...")
                                    if source.get('metadata'):
                                        metadata = source['metadata']
                                        if metadata.get('source_type'):
                                            st.markdown(f"- **Type**: {metadata['source_type']}")
                                        if metadata.get('source_name'):
                                            st.markdown(f"- **Source**: {metadata['source_name']}")
                                    st.divider()
                        
                        # Add to session state
                        st.session_state.messages.append({
                            "role": "assistant", 
                            "content": response,
                            "sources": sources
                        })
                    else:
                        error_response = "❌ I encountered an error while processing your question. Please try again."
                        st.markdown(error_response)
                        st.session_state.messages.append({"role": "assistant", "content": error_response})

    def run(self):
        """Main application entry point"""
        # Check RAG connection on startup
        if not st.session_state.rag_connected:
            with st.spinner("🔄 Connecting to RAG engine..."):
                self.check_api_connection()
        
        # Load stats if connected
        if st.session_state.rag_connected and not st.session_state.stats:
            self.get_stats()
        
        # Render UI components
        self.render_header()
        
        # Main layout
        col1, col2 = st.columns([3, 1])
        
        with col1:
            self.render_welcome_message()
            self.render_chat_interface()
        
        with col2:
            self.render_sidebar()

def main():
    """Main entry point"""
    try:
        # Create and run the interface
        interface = WeaverAIInterface()
        interface.run()
        
    except Exception as e:
        st.error(f"❌ Application error: {str(e)}")
        st.info("Please check your configuration and try refreshing the page.")

if __name__ == "__main__":
    main()
