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
                    st.subheader("📂 Data Sources")
                    for source, count in sources.items():
                        st.write(f"**{source.title()}**: {count}")
                
                # Database info
                if stats.get("vector_db_path"):
                    st.write(f"**Database**: {os.path.basename(stats['vector_db_path'])}")
                    
                # Show data sources
                if st.button("🔄 Refresh Data Sources"):
                    self.show_data_sources()
            else:
                st.info("No statistics available")
                if st.button("Load Stats"):
                    self.get_stats()
                    st.rerun()
            
            st.divider()
            
            # Data Ingestion Section
            st.header("📥 Data Ingestion")
            
            # GitHub Repository Section
            with st.expander("🔗 Add GitHub Repository", expanded=False):
                repo_name = st.text_input(
                    "Repository (owner/repo)",
                    placeholder="e.g., microsoft/vscode",
                    help="Enter the GitHub repository in format: owner/repository"
                )
                
                col1, col2 = st.columns(2)
                with col1:
                    include_issues = st.checkbox("Include Issues", value=True)
                    max_items = st.number_input("Max Items", min_value=10, max_value=100, value=30, 
                                              help="Recommended: 20-30 for quick processing. Higher values may timeout.")
                with col2:
                    include_prs = st.checkbox("Include PRs", value=True)
                
                # Warning for large repositories
                if max_items > 50:
                    st.warning("⚠️ Values > 50 may cause timeouts for large repositories")
                
                if st.button("🚀 Ingest Repository", disabled=not repo_name):
                    self.ingest_github_repo(repo_name, include_issues, include_prs, max_items)
                
                # Quick test button
                if repo_name and st.button("⚡ Quick Test (10 items)", disabled=not repo_name):
                    self.ingest_github_repo(repo_name, include_issues, include_prs, 10)
            
            # Slack Channels Section
            with st.expander("💬 Add Slack Channels", expanded=False):
                channels_input = st.text_area(
                    "Channel Names",
                    placeholder="general\nrandom\ndev-team",
                    help="Enter channel names, one per line"
                )
                
                col1, col2 = st.columns(2)
                with col1:
                    days_back = st.number_input("Days Back", min_value=1, max_value=90, value=30)
                with col2:
                    max_messages = st.number_input("Max Messages", min_value=50, max_value=2000, value=1000)
                
                if st.button("💬 Ingest Channels", disabled=not channels_input.strip()):
                    channels = [ch.strip() for ch in channels_input.split('\n') if ch.strip()]
                    self.ingest_slack_channels(channels, days_back, max_messages)
            
            # Repository Browser
            with st.expander("📚 Browse Available Repos", expanded=False):
                if st.button("🔍 Load My Repositories"):
                    self.load_available_repositories()
                
                if "available_repos" in st.session_state:
                    repos = st.session_state.available_repos
                    if repos:
                        selected_repo = st.selectbox(
                            "Select Repository",
                            options=[repo["full_name"] for repo in repos],
                            format_func=lambda x: f"{x} ⭐{next(r['stars'] for r in repos if r['full_name'] == x)}"
                        )
                        
                        if selected_repo and st.button(f"🚀 Ingest {selected_repo}"):
                            self.ingest_github_repo(selected_repo, True, True, 100)
            
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
            
            # Knowledge Base Management
            st.subheader("🗑️ Knowledge Base")
            if st.button("🗂️ View Data Sources"):
                self.show_data_sources()
            
            # Clear knowledge base with confirmation
            if stats.get("total_documents", 0) > 0:
                st.warning(f"⚠️ Current KB contains {stats.get('total_documents', 0)} documents")
                if st.button("🗑️ Clear Knowledge Base", type="secondary"):
                    if st.session_state.get("confirm_clear", False):
                        self.clear_knowledge_base()
                        st.session_state.confirm_clear = False
                    else:
                        st.session_state.confirm_clear = True
                        st.rerun()
                
                if st.session_state.get("confirm_clear", False):
                    st.error("⚠️ Are you sure? This will delete ALL data!")
                    col1, col2 = st.columns(2)
                    with col1:
                        if st.button("✅ Yes, Clear All"):
                            self.clear_knowledge_base()
                            st.session_state.confirm_clear = False
                    with col2:
                        if st.button("❌ Cancel"):
                            st.session_state.confirm_clear = False
                            st.rerun()
            else:
                st.info("Knowledge base is empty")
            
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
            - Auto-fetch from GitHub/Slack
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
            
            I'm your intelligent project assistant powered by semantic search and AI. I can help you find information from your:
            - 🐙 **GitHub repositories** (issues, PRs, comments) - *Auto-fetch available!*
            - 💬 **Slack channels** (conversations, discussions) - *Auto-fetch available!*
            
            **🚀 Quick Start:**
            1. Use the sidebar to add your GitHub repositories or Slack channels
            2. Choose from your available repositories or enter any public repo
            3. Let me automatically fetch and process the data with semantic embeddings
            4. Ask questions and get AI-powered answers with source citations!
            
            **Try asking me:**
            - "What are the recent bug reports?"
            - "How do I set up the development environment?"
            - "What did the team discuss about authentication?"
            - "Show me open issues related to performance"
            - "Summarize the latest pull requests"
            
            **✨ Features:**
            - Semantic search finds relevant information even with different keywords
            - Smart chunking preserves context for better answers
            - Real-time repository selection and ingestion
            - Source citations with clickable links
            
            Start by adding data sources in the sidebar, then ask away! 🚀
            """)
    
    def ingest_github_repo(self, repo_name: str, include_issues: bool, include_prs: bool, max_items: int):
        """Ingest data from a GitHub repository"""
        try:
            # Limit max_items for UI to prevent timeouts
            safe_max_items = min(max_items, 50)
            if max_items > 50:
                st.warning(f"⚠️ Limiting to {safe_max_items} items to prevent timeouts. For larger ingestion, use the manual scripts.")
            
            with st.spinner(f"🚀 Ingesting data from {repo_name} (max {safe_max_items} items)..."):
                payload = {
                    "repo_name": repo_name,
                    "include_issues": include_issues,
                    "include_prs": include_prs,
                    "max_items": safe_max_items
                }
                
                # Increased timeout for larger repositories
                response = requests.post(
                    f"{self.api_base_url}/ingest/github",
                    json=payload,
                    timeout=180  # 3 minutes
                )
                
                if response.status_code == 200:
                    result = response.json()
                    st.success(f"✅ {result['message']}")
                    
                    # Show detailed results
                    col1, col2, col3 = st.columns(3)
                    with col1:
                        st.metric("Items Fetched", result.get('items_fetched', 0))
                    with col2:
                        st.metric("Chunks Processed", result.get('chunks_processed', 0))
                    with col3:
                        st.metric("Chunks Stored", result.get('chunks_stored', 0))
                    
                    if result.get('note'):
                        st.info(f"ℹ️ {result['note']}")
                    
                    # Refresh stats
                    self.get_stats()
                    st.rerun()
                    
                elif response.status_code == 408:
                    error_data = response.json() if response.content else {"detail": "Request timed out"}
                    st.error(f"⏰ {error_data.get('detail', 'Request timed out')}")
                    st.info("💡 **Tips to avoid timeouts:**\n- Reduce the max items (try 20-30)\n- Use manual processing for large repositories\n- Process issues and PRs separately")
                else:
                    error_data = response.json() if response.content else {"detail": "Unknown error"}
                    st.error(f"❌ Failed to ingest repository: {error_data.get('detail', 'Unknown error')}")
                    
        except requests.exceptions.Timeout:
            st.error("⏰ **Request timed out.** Large repositories take time to process.")
            st.info("""
            💡 **What you can try:**
            - Reduce the 'Max Items' to 20-30
            - Uncheck either Issues or PRs to process less data
            - For full repository ingestion, use the manual approach:
              1. `python scripts/ingest_data.py`
              2. `python scripts/process_data.py`
            """)
        except Exception as e:
            st.error(f"❌ Error: {str(e)}")
            st.info("💡 If this persists, try the manual data processing approach from the terminal.")
    
    def ingest_slack_channels(self, channels: List[str], days_back: int, max_messages: int):
        """Ingest data from Slack channels"""
        try:
            with st.spinner(f"💬 Ingesting data from {len(channels)} Slack channels..."):
                payload = {
                    "channels": channels,
                    "days_back": days_back,
                    "max_messages": max_messages
                }
                
                response = requests.post(
                    f"{self.api_base_url}/ingest/slack",
                    json=payload,
                    timeout=120
                )
                
                if response.status_code == 200:
                    result = response.json()
                    st.success(f"✅ {result['message']}")
                    st.info(f"📊 Processed {result['chunks_processed']} chunks from {result['messages_fetched']} messages")
                    
                    # Refresh stats
                    self.get_stats()
                    st.rerun()
                else:
                    error_data = response.json() if response.content else {"detail": "Unknown error"}
                    st.error(f"❌ Failed to ingest Slack data: {error_data.get('detail', 'Unknown error')}")
                    
        except requests.exceptions.Timeout:
            st.error("⏰ Request timed out. Large channel histories may take longer to process.")
        except Exception as e:
            st.error(f"❌ Error: {str(e)}")
    
    def load_available_repositories(self):
        """Load available repositories from GitHub"""
        try:
            with st.spinner("🔍 Loading your repositories..."):
                response = requests.get(f"{self.api_base_url}/repositories", timeout=30)
                
                if response.status_code == 200:
                    data = response.json()
                    repositories = data.get("repositories", [])
                    
                    # Sort by stars descending
                    repositories.sort(key=lambda x: x.get("stars", 0), reverse=True)
                    
                    st.session_state.available_repos = repositories
                    st.success(f"✅ Found {len(repositories)} repositories")
                else:
                    error_data = response.json() if response.content else {"detail": "Unknown error"}
                    st.error(f"❌ Failed to load repositories: {error_data.get('detail', 'Unknown error')}")
                    
        except requests.exceptions.Timeout:
            st.error("⏰ Request timed out while loading repositories.")
        except Exception as e:
            st.error(f"❌ Error: {str(e)}")
    
    def show_data_sources(self):
        """Show detailed information about current data sources"""
        try:
            response = requests.get(f"{self.api_base_url}/data/sources", timeout=10)
            
            if response.status_code == 200:
                data = response.json()
                sources = data.get("sources", [])
                
                if sources:
                    st.subheader("📋 Detailed Data Sources")
                    for source in sources:
                        with st.expander(f"{source['type'].title()}: {source['name']} ({source['count']} chunks)"):
                            st.write(f"**Type**: {source['type']}")
                            st.write(f"**Name**: {source['name']}")
                            st.write(f"**Document Count**: {source['count']}")
                            if source.get('last_updated'):
                                st.write(f"**Last Updated**: {source['last_updated']}")
                else:
                    st.info("No data sources found. Add some repositories or Slack channels!")
                    
                # Refresh stats too
                self.get_stats()
            else:
                st.error("Failed to load data sources")
                
        except Exception as e:
            st.error(f"Error loading data sources: {str(e)}")

    def clear_knowledge_base(self):
        """Clear all documents from the knowledge base"""
        try:
            with st.spinner("🗑️ Clearing knowledge base..."):
                response = requests.delete(f"{self.api_base_url}/clear", timeout=30)
                
                if response.status_code == 200:
                    result = response.json()
                    st.success(f"✅ Knowledge base cleared successfully!")
                    st.info(f"Removed {result.get('documents_removed', 0)} documents")
                    
                    # Refresh stats
                    self.get_stats()
                    st.rerun()
                else:
                    st.error(f"❌ Failed to clear knowledge base: {response.text}")
                    
        except requests.exceptions.Timeout:
            st.error("⏰ Request timed out while clearing knowledge base.")
        except Exception as e:
            st.error(f"❌ Error clearing knowledge base: {str(e)}")

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
