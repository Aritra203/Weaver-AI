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

# Import data connectors for direct integration
try:
    from scripts.github_connector import GitHubConnector
    GITHUB_AVAILABLE = True
except ImportError as e:
    GITHUB_AVAILABLE = False

try:
    from scripts.slack_connector import SlackConnector
    SLACK_AVAILABLE = True
except ImportError as e:
    SLACK_AVAILABLE = False

try:
    from scripts.process_data import DataProcessor, VectorDatabase
    PROCESS_DATA_AVAILABLE = True
except ImportError as e:
    PROCESS_DATA_AVAILABLE = False

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
    
    def ingest_github_repo(self, repo_name: str, include_issues: bool = True, include_prs: bool = True, max_items: int = 30):
        """Ingest data from a GitHub repository directly"""
        if not GITHUB_AVAILABLE:
            st.error("❌ GitHub connector not available. Please install required dependencies.")
            return
            
        try:
            # Initialize progress tracking
            progress_bar = st.progress(0)
            status_text = st.empty()
            
            with st.spinner(f"🚀 Ingesting data from {repo_name}..."):
                # Step 1: Initialize GitHub connector
                status_text.text("🔗 Connecting to GitHub...")
                progress_bar.progress(20)
                
                from scripts.github_connector import GitHubConnector
                github = GitHubConnector()
                repo = github.get_repository(repo_name)
                
                # Step 2: Fetch basic repository data
                status_text.text("📥 Fetching repository data...")
                progress_bar.progress(50)
                
                # Fetch issues and PRs separately with limits
                issues = []
                prs = []
                
                if include_issues:
                    issues = github.fetch_issues(repo, limit=max_items//2 if include_prs else max_items)
                
                if include_prs:
                    prs = github.fetch_pull_requests(repo, limit=max_items//2 if include_issues else max_items)
                
                # Step 3: Save raw data
                status_text.text("💾 Saving raw data...")
                progress_bar.progress(70)
                
                import json
                import os
                from datetime import datetime
                
                # Create data structure
                data = {
                    "repository": repo_name,
                    "timestamp": datetime.now().isoformat(),
                    "items": issues + prs,
                    "metadata": {
                        "issues_count": len(issues),
                        "prs_count": len(prs),
                        "total_items": len(issues) + len(prs)
                    }
                }
                
                # Save to data/raw directory
                os.makedirs("data/raw", exist_ok=True)
                filename = f"github_{repo_name.replace('/', '_')}_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
                filepath = os.path.join("data/raw", filename)
                
                with open(filepath, 'w', encoding='utf-8') as f:
                    json.dump(data, f, indent=2, ensure_ascii=False)
                
                progress_bar.progress(100)
                status_text.text("✅ Ingestion complete!")
                
                # Show results
                total_items = len(issues) + len(prs)
                
                col1, col2, col3 = st.columns(3)
                with col1:
                    st.metric("Issues", len(issues))
                with col2:
                    st.metric("Pull Requests", len(prs))
                with col3:
                    st.metric("Total Items", total_items)
                
                st.success(f"✅ Successfully ingested {total_items} items from {repo_name}")
                st.info("💡 Data saved to raw format. Process it using the data processing scripts to add to knowledge base.")
                
        except Exception as e:
            st.error(f"❌ Error ingesting GitHub repository: {str(e)}")
            st.info("💡 Make sure your GitHub token is properly configured in secrets.")
    
    def ingest_slack_channels(self, channels: List[str], days_back: int = 30, max_messages: int = 1000):
        """Ingest data from Slack channels directly"""
        if not SLACK_AVAILABLE:
            st.error("❌ Slack connector not available. Please install required dependencies.")
            return
            
        try:
            # Initialize progress tracking
            progress_bar = st.progress(0)
            status_text = st.empty()
            
            with st.spinner(f"💬 Ingesting data from {len(channels)} Slack channels..."):
                # Step 1: Initialize Slack connector
                status_text.text("🔗 Connecting to Slack...")
                progress_bar.progress(20)
                
                from scripts.slack_connector import SlackConnector
                slack = SlackConnector()
                slack.test_connection()
                
                # Step 2: Get available channels and find matching ones
                status_text.text("🔍 Finding channels...")
                progress_bar.progress(40)
                
                available_channels = slack.get_channels()
                channel_map = {ch['name']: ch['id'] for ch in available_channels}
                
                # Step 3: Fetch channel messages
                status_text.text("📥 Fetching channel messages...")
                progress_bar.progress(50)
                
                all_messages = []
                channel_info = []
                
                for channel_name in channels:
                    try:
                        if channel_name not in channel_map:
                            st.warning(f"⚠️ Channel '{channel_name}' not found or not accessible")
                            continue
                            
                        channel_id = channel_map[channel_name]
                        messages = slack.fetch_channel_messages(
                            channel_id=channel_id,
                            limit=max_messages // len(channels)
                        )
                        
                        # Add channel name to each message for context
                        for msg in messages:
                            msg['channel_name'] = channel_name
                            
                        all_messages.extend(messages)
                        channel_info.append({
                            "channel": channel_name,
                            "channel_id": channel_id,
                            "message_count": len(messages)
                        })
                    except Exception as e:
                        st.warning(f"⚠️ Failed to fetch from channel '{channel_name}': {e}")
                
                # Step 3: Save raw data
                status_text.text("� Saving raw data...")
                progress_bar.progress(80)
                
                import json
                import os
                from datetime import datetime
                
                # Create data structure
                data = {
                    "channels": channel_info,
                    "messages": all_messages,
                    "timestamp": datetime.now().isoformat(),
                    "metadata": {
                        "total_messages": len(all_messages),
                        "channels_processed": len([c for c in channel_info if c["message_count"] > 0]),
                        "days_back": days_back
                    }
                }
                
                # Save to data/raw directory
                os.makedirs("data/raw", exist_ok=True)
                filename = f"slack_{'_'.join(channels)}_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
                filepath = os.path.join("data/raw", filename)
                
                with open(filepath, 'w', encoding='utf-8') as f:
                    json.dump(data, f, indent=2, ensure_ascii=False)
                
                progress_bar.progress(100)
                status_text.text("✅ Ingestion complete!")
                
                # Show results
                col1, col2, col3 = st.columns(3)
                with col1:
                    st.metric("Messages", len(all_messages))
                with col2:
                    st.metric("Channels", len([c for c in channel_info if c["message_count"] > 0]))
                with col3:
                    st.metric("Days Back", days_back)
                
                st.success(f"✅ Successfully ingested {len(all_messages)} messages from {len(channels)} channels")
                st.info("💡 Data saved to raw format. Process it using the data processing scripts to add to knowledge base.")
                
        except Exception as e:
            st.error(f"❌ Error ingesting Slack channels: {str(e)}")
            st.info("💡 Make sure your Slack bot token is properly configured in secrets.")
    
    def load_available_repositories(self):
        """Load available repositories from GitHub"""
        if not GITHUB_AVAILABLE:
            st.error("❌ GitHub connector not available. Please install required dependencies.")
            return
            
        try:
            with st.spinner("🔍 Loading your repositories..."):
                from scripts.github_connector import GitHubConnector
                github = GitHubConnector()
                
                # Get user's repositories
                user = github.client.get_user()
                repos = []
                
                # Limit to first 50 repos to avoid rate limits
                for repo in list(user.get_repos())[:50]:
                    repos.append({
                        "full_name": repo.full_name,
                        "name": repo.name,
                        "stars": repo.stargazers_count,
                        "description": repo.description or "No description",
                        "language": repo.language or "Unknown",
                        "private": repo.private
                    })
                
                # Sort by stars descending
                repos.sort(key=lambda x: x.get("stars", 0), reverse=True)
                
                st.session_state.available_repos = repos
                st.success(f"✅ Found {len(repos)} repositories")
                
        except Exception as e:
            st.error(f"❌ Error loading repositories: {str(e)}")
            st.info("💡 Make sure your GitHub token is properly configured.")
    
    def clear_knowledge_base(self):
        """Clear all documents from the knowledge base"""
        try:
            with st.spinner("🗑️ Clearing knowledge base..."):
                # Clear raw data files
                import os
                import shutil
                
                raw_data_path = "data/raw"
                processed_data_path = "data/processed"
                vector_db_path = "data/vector_db"
                
                paths_to_clear = [raw_data_path, processed_data_path, vector_db_path]
                
                for path in paths_to_clear:
                    if os.path.exists(path):
                        shutil.rmtree(path)
                        os.makedirs(path, exist_ok=True)
                
                # Reinitialize RAG engine if available
                if RAG_AVAILABLE and RAGEngine:
                    try:
                        self.rag_engine = RAGEngine()
                    except:
                        pass  # Ignore errors during reinitialization
                
                st.success("✅ Knowledge base cleared successfully!")
                
                # Refresh stats
                self.get_stats()
                st.rerun()
                    
        except Exception as e:
            st.error(f"❌ Error clearing knowledge base: {str(e)}")
    
    def show_data_sources(self):
        """Show detailed information about current data sources"""
        try:
            import os
            import json
            
            raw_data_path = "data/raw"
            processed_data_path = "data/processed"
            
            if not os.path.exists(raw_data_path):
                st.info("📭 No data sources found. Add some repositories or Slack channels!")
                return
            
            st.subheader("📋 Data Sources Overview")
            
            # Count raw data files
            raw_files = []
            if os.path.exists(raw_data_path):
                for filename in os.listdir(raw_data_path):
                    if filename.endswith('.json'):
                        filepath = os.path.join(raw_data_path, filename)
                        try:
                            with open(filepath, 'r', encoding='utf-8') as f:
                                data = json.load(f)
                                
                            if 'github' in filename:
                                raw_files.append({
                                    "type": "GitHub",
                                    "name": data.get("repository", filename),
                                    "items": len(data.get("items", [])),
                                    "file": filename
                                })
                            elif 'slack' in filename:
                                raw_files.append({
                                    "type": "Slack",
                                    "name": f"{len(data.get('channels', []))} channels",
                                    "items": len(data.get("messages", [])),
                                    "file": filename
                                })
                        except:
                            continue
            
            if raw_files:
                for source in raw_files:
                    with st.expander(f"{source['type']}: {source['name']} ({source['items']} items)"):
                        st.write(f"**Type**: {source['type']}")
                        st.write(f"**Items**: {source['items']}")
                        st.write(f"**File**: {source['file']}")
            else:
                st.info("📭 No data sources found. Add some repositories or Slack channels!")
                
        except Exception as e:
            st.error(f"❌ Error loading data sources: {str(e)}")
    
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
            
            # Data Ingestion Section
            st.header("� Data Ingestion")
            
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
                    if GITHUB_AVAILABLE:
                        self.ingest_github_repo(repo_name, include_issues, include_prs, max_items)
                    else:
                        st.error("❌ GitHub connector not available. Check your installation.")
                
                # Quick test button
                if repo_name and st.button("⚡ Quick Test (10 items)", disabled=not repo_name):
                    if GITHUB_AVAILABLE:
                        self.ingest_github_repo(repo_name, include_issues, include_prs, 10)
                    else:
                        st.error("❌ GitHub connector not available. Check your installation.")
            
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
                    if SLACK_AVAILABLE:
                        channels = [ch.strip() for ch in channels_input.split('\n') if ch.strip()]
                        self.ingest_slack_channels(channels, days_back, max_messages)
                    else:
                        st.error("❌ Slack connector not available. Check your installation.")
            
            # Repository Browser
            with st.expander("📚 Browse Available Repos", expanded=False):
                if st.button("🔍 Load My Repositories"):
                    if GITHUB_AVAILABLE:
                        self.load_available_repositories()
                    else:
                        st.error("❌ GitHub connector not available. Check your installation.")
                
                if "available_repos" in st.session_state:
                    repos = st.session_state.available_repos
                    if repos:
                        selected_repo = st.selectbox(
                            "Select Repository",
                            options=[repo["full_name"] for repo in repos],
                            format_func=lambda x: f"{x} ⭐{next(r['stars'] for r in repos if r['full_name'] == x)}"
                        )
                        
                        if selected_repo and st.button(f"� Ingest {selected_repo}"):
                            if GITHUB_AVAILABLE:
                                self.ingest_github_repo(selected_repo, True, True, 30)
                            else:
                                st.error("❌ GitHub connector not available. Check your installation.")
            
            st.divider()
            
            # Knowledge Base Management
            st.header("🗑️ Knowledge Base")
            if st.button("�️ View Data Sources"):
                self.show_data_sources()
            
            # Clear knowledge base with confirmation
            if stats and stats.get("total_documents", 0) > 0:
                st.warning(f"⚠️ Current KB contains {stats.get('total_documents', 0)} documents")
                if st.button("�️ Clear Knowledge Base", type="secondary"):
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
