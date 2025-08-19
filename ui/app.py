"""
Streamlit web interface for Weaver AI
Provides an intuitive chat-like interface for querying the knowledge base
"""

import os
import sys
import json
from datetime import datetime
from typing import Dict, List, Any, Optional

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

try:
    import requests
    REQUESTS_AVAILABLE = True
except ImportError:
    REQUESTS_AVAILABLE = False
    print("❌ Requests not available. Install with: pip install requests")
    sys.exit(1)

from config.settings import get_settings

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
        self.api_base_url = f"http://{settings.API_HOST}:{settings.API_PORT}"
        self.session_state_keys = [
            "messages", "api_connected", "stats", "last_check"
        ]
        self.init_session_state()
    
    def init_session_state(self):
        """Initialize Streamlit session state"""
        if "messages" not in st.session_state:
            st.session_state.messages = []
        
        if "api_connected" not in st.session_state:
            st.session_state.api_connected = False
        
        if "stats" not in st.session_state:
            st.session_state.stats = {}
        
        if "last_check" not in st.session_state:
            st.session_state.last_check = None
    
    def check_api_connection(self) -> bool:
        """Check if the API backend is available"""
        try:
            response = requests.get(f"{self.api_base_url}/health", timeout=5)
            if response.status_code == 200:
                health_data = response.json()
                st.session_state.api_connected = True
                st.session_state.last_check = datetime.now()
                return True
            else:
                st.session_state.api_connected = False
                return False
        except Exception as e:
            st.session_state.api_connected = False
            return False
    
    def get_stats(self) -> Optional[Dict[str, Any]]:
        """Get knowledge base statistics"""
        try:
            response = requests.get(f"{self.api_base_url}/stats", timeout=10)
            if response.status_code == 200:
                stats = response.json()
                st.session_state.stats = stats
                return stats
            return None
        except Exception:
            return None
    
    def ask_question(self, question: str, max_results: int = 5) -> Optional[Dict[str, Any]]:
        """Send question to the API"""
        try:
            payload = {
                "question": question,
                "max_results": max_results,
                "include_metadata": True
            }
            
            response = requests.post(
                f"{self.api_base_url}/ask",
                json=payload,
                timeout=30
            )
            
            if response.status_code == 200:
                return response.json()
            else:
                error_detail = response.json().get("detail", "Unknown error")
                st.error(f"API Error: {error_detail}")
                return None
                
        except requests.exceptions.Timeout:
            st.error("⏰ Request timed out. The question might be too complex.")
            return None
        except Exception as e:
            st.error(f"❌ Error communicating with API: {str(e)}")
            return None
    
    def render_header(self):
        """Render the application header"""
        st.title("🧠 Weaver AI")
        st.markdown("*Your intelligent project knowledge assistant*")
        
        # Connection status
        col1, col2, col3 = st.columns([2, 1, 1])
        
        with col1:
            if st.session_state.api_connected:
                st.success("🟢 Connected to API")
            else:
                st.error("🔴 API not available")
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
                st.metric("Total Documents", stats.get("total_documents", 0))
                
                # Source breakdown
                sources = stats.get("sources", {})
                if sources:
                    st.subheader("📂 Sources")
                    for source, count in sources.items():
                        st.write(f"**{source.title()}**: {count}")
                
                # Database info
                if stats.get("vector_db_path"):
                    st.write(f"**Database**: {os.path.basename(stats['vector_db_path'])}")
            else:
                st.info("No statistics available")
                if st.button("Load Stats"):
                    self.get_stats()
                    st.rerun()
            
            st.divider()
            
            # Settings
            st.header("⚙️ Settings")
            
            # API endpoint
            api_endpoint = st.text_input(
                "API Endpoint",
                value=self.api_base_url,
                help="Backend API URL"
            )
            
            if api_endpoint != self.api_base_url:
                self.api_base_url = api_endpoint
                st.session_state.api_connected = False
            
            # Query settings
            max_results = st.slider(
                "Max Sources",
                min_value=1,
                max_value=10,
                value=5,
                help="Maximum number of source documents to retrieve"
            )
            
            st.session_state.max_results = max_results
            
            st.divider()
            
            # Help section
            st.header("💡 Tips")
            st.markdown("""
            **Good questions:**
            - "How do I configure the database?"
            - "What are the recent bug reports?"
            - "Show me discussions about authentication"
            
            **Features:**
            - Sources are clickable links
            - Chat history is preserved
            - Real-time API status
            """)
    
    def render_message(self, message: Dict[str, Any]):
        """Render a single message in the chat"""
        if message["role"] == "user":
            with st.chat_message("user"):
                st.write(message["content"])
        else:
            with st.chat_message("assistant"):
                # Main answer
                st.write(message["content"])
                
                # Sources
                if "sources" in message and message["sources"]:
                    with st.expander(f"📚 Sources ({len(message['sources'])})", expanded=False):
                        for i, source in enumerate(message["sources"], 1):
                            self.render_source(source, i)
                
                # Metadata
                if "metadata" in message:
                    metadata = message["metadata"]
                    col1, col2, col3 = st.columns(3)
                    
                    with col1:
                        if "processing_time" in metadata:
                            st.caption(f"⏱️ {metadata['processing_time']:.2f}s")
                    
                    with col2:
                        if "model_used" in metadata:
                            st.caption(f"🤖 {metadata['model_used']}")
                    
                    with col3:
                        if "timestamp" in metadata:
                            timestamp = metadata["timestamp"]
                            if isinstance(timestamp, str):
                                try:
                                    dt = datetime.fromisoformat(timestamp.replace('Z', '+00:00'))
                                    st.caption(f"🕒 {dt.strftime('%H:%M:%S')}")
                                except:
                                    st.caption(f"🕒 {timestamp}")
    
    def render_source(self, source: Dict[str, Any], index: int):
        """Render a source document"""
        # Source header
        source_type = source.get("type", "document")
        source_name = source.get("source", "unknown")
        title = source.get("title", "")
        author = source.get("author", "")
        
        header_parts = [f"**{index}. {source_name} {source_type}**"]
        if title:
            header_parts.append(f"*{title}*")
        
        st.markdown(" | ".join(header_parts))
        
        # Author and date
        info_parts = []
        if author:
            info_parts.append(f"👤 {author}")
        
        if source.get("created_at"):
            try:
                created_at = source["created_at"]
                if isinstance(created_at, str):
                    dt = datetime.fromisoformat(created_at.replace('Z', '+00:00'))
                    info_parts.append(f"📅 {dt.strftime('%Y-%m-%d')}")
            except:
                pass
        
        if source.get("similarity_score"):
            score = source["similarity_score"]
            info_parts.append(f"🎯 {score:.1%}")
        
        if info_parts:
            st.caption(" | ".join(info_parts))
        
        # Content
        content = source.get("text", "")
        if len(content) > 300:
            with st.expander("📖 Full content"):
                st.write(content)
            st.write(content[:300] + "...")
        else:
            st.write(content)
        
        # URL link
        if source.get("url"):
            st.markdown(f"🔗 [View original]({source['url']})")
        
        st.divider()
    
    def render_chat_interface(self):
        """Render the main chat interface"""
        # Display existing messages
        for message in st.session_state.messages:
            self.render_message(message)
        
        # Chat input
        if question := st.chat_input("Ask me anything about your project..."):
            if not st.session_state.api_connected:
                st.error("❌ Please connect to the API first")
                return
            
            # Add user message
            user_message = {"role": "user", "content": question}
            st.session_state.messages.append(user_message)
            
            # Display user message
            self.render_message(user_message)
            
            # Get response from API
            with st.chat_message("assistant"):
                with st.spinner("🧠 Thinking..."):
                    max_results = getattr(st.session_state, 'max_results', 5)
                    response = self.ask_question(question, max_results)
                
                if response:
                    # Display answer
                    answer = response.get("answer", "No answer received")
                    st.write(answer)
                    
                    # Display sources
                    sources = response.get("sources", [])
                    if sources:
                        with st.expander(f"📚 Sources ({len(sources)})", expanded=False):
                            for i, source in enumerate(sources, 1):
                                self.render_source(source, i)
                    
                    # Display metadata
                    metadata = {
                        "processing_time": response.get("processing_time"),
                        "model_used": response.get("model_used"),
                        "timestamp": response.get("timestamp")
                    }
                    
                    col1, col2, col3 = st.columns(3)
                    with col1:
                        if metadata["processing_time"]:
                            st.caption(f"⏱️ {metadata['processing_time']:.2f}s")
                    with col2:
                        if metadata["model_used"]:
                            st.caption(f"🤖 {metadata['model_used']}")
                    with col3:
                        if metadata["timestamp"]:
                            timestamp = metadata["timestamp"]
                            if isinstance(timestamp, str):
                                try:
                                    dt = datetime.fromisoformat(timestamp.replace('Z', '+00:00'))
                                    st.caption(f"🕒 {dt.strftime('%H:%M:%S')}")
                                except:
                                    st.caption(f"🕒 {timestamp}")
                    
                    # Add assistant message to session
                    assistant_message = {
                        "role": "assistant",
                        "content": answer,
                        "sources": sources,
                        "metadata": metadata
                    }
                    st.session_state.messages.append(assistant_message)
                    
                else:
                    st.error("❌ Failed to get response from API")
                    # Add error message to session
                    error_message = {
                        "role": "assistant",
                        "content": "I'm sorry, I couldn't process your question. Please try again.",
                        "sources": [],
                        "metadata": {}
                    }
                    st.session_state.messages.append(error_message)
            
            # Force rerun to update the interface
            st.rerun()
    
    def render_welcome_message(self):
        """Render welcome message when no chat history exists"""
        if not st.session_state.messages:
            st.info("""
            👋 **Welcome to Weaver AI!**
            
            I'm your intelligent project assistant. I can help you find information from your:
            - 🐙 GitHub issues and pull requests
            - 💬 Slack conversations and discussions
            
            **Try asking me:**
            - "What are the recent bug reports?"
            - "How do I set up the development environment?"
            - "What did the team discuss about authentication?"
            - "Show me open issues related to performance"
            
            Just type your question below to get started! 🚀
            """)
    
    def run(self):
        """Main application entry point"""
        # Check API connection on startup
        if not st.session_state.api_connected:
            with st.spinner("🔄 Connecting to API..."):
                self.check_api_connection()
        
        # Load stats if connected
        if st.session_state.api_connected and not st.session_state.stats:
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
