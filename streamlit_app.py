"""
Streamlit web interface for Weaver AI
Multi-user application with authentication and individual knowledge bases
"""

import os
import sys
import json
import shutil
from datetime import datetime
from typing import Dict, List, Any, Optional, Union

# SQLite compatibility fix for ChromaDB on Streamlit Cloud
try:
    __import__('pysqlite3')
    import sys
    # Only replace if pysqlite3 is actually in sys.modules
    if 'pysqlite3' in sys.modules:
        sys.modules['sqlite3'] = sys.modules.pop('pysqlite3')
except ImportError:
    # pysqlite3 not available, use default sqlite3
    pass

# Add the project root to the Python path
project_root = os.path.dirname(os.path.abspath(__file__))
if project_root not in sys.path:
    sys.path.insert(0, project_root)

# Import dependencies with fallback
try:
    import streamlit as st
    STREAMLIT_AVAILABLE = True
except ImportError:
    STREAMLIT_AVAILABLE = False
    print("❌ Streamlit not available. Install with: pip install streamlit")
    sys.exit(1)

# Import settings with fallback
SETTINGS_AVAILABLE = True

# Create a compatible fallback class first
class MockSettings:
    def __init__(self):
        self.api_base_url = ""
        self.database_url = ""

try:
    from config.settings import get_settings  # type: ignore
except ImportError as e:
    print(f"Settings import failed: {e}")
    SETTINGS_AVAILABLE = False
    
    def get_settings():  # type: ignore
        return MockSettings()

# Import authentication modules
try:
    from auth.user_auth import AuthUI, UserManager
    from auth.user_database import UserDataManager
    from auth.user_rag import UserRAGEngine
    AUTH_AVAILABLE = True
except ImportError as e:
    print(f"Authentication modules import failed: {e}")
    AUTH_AVAILABLE = False
    AuthUI = UserManager = UserDataManager = UserRAGEngine = None

# Import RAG engine directly for cloud deployment
RAG_AVAILABLE = AUTH_AVAILABLE  # RAG is available if auth is available

# Import data connectors for direct integration
try:
    from scripts.github_connector import GitHubConnector
    GITHUB_AVAILABLE = True
except ImportError as e:
    print(f"GitHub connector import failed: {e}")
    GITHUB_AVAILABLE = False
    GitHubConnector = None

try:
    from scripts.slack_connector import SlackConnector
    SLACK_AVAILABLE = True
except ImportError as e:
    print(f"Slack connector import failed: {e}")
    SLACK_AVAILABLE = False
    SlackConnector = None

try:
    from scripts.process_data import DataProcessor, VectorDatabase, EmbeddingGenerator
    PROCESSING_AVAILABLE = True
except ImportError as e:
    print(f"Data processing import failed: {e}")
    PROCESSING_AVAILABLE = False
    DataProcessor = VectorDatabase = EmbeddingGenerator = None

settings = get_settings()

# Page configuration
st.set_page_config(
    page_title="Weaver AI - Multi-User",
    page_icon="🧠",
    layout="wide",
    initial_sidebar_state="expanded"
)

class WeaverAIInterface:
    """Multi-user interface class for Weaver AI"""
    
    def __init__(self):
        """Initialize the interface"""
        if AUTH_AVAILABLE and AuthUI is not None:
            self.auth_ui = AuthUI()
        else:
            self.auth_ui = None
            
        self.current_user = None
        self.user_rag_engine = None
        self.user_data_manager = None
        
        self.session_state_keys = [
            "messages", "rag_connected", "stats", "last_check", "user_session", "current_authenticated_user"
        ]
        self.init_session_state()
    
    def init_session_state(self):
        """Initialize Streamlit session state"""
        for key in self.session_state_keys:
            if key not in st.session_state:
                if key == "messages":
                    st.session_state[key] = []
                elif key == "rag_connected":
                    st.session_state[key] = False
                elif key == "stats":
                    st.session_state[key] = {}
                else:
                    st.session_state[key] = None
    
    def init_user_components(self, username: str):
        """Initialize user-specific components"""
        if not AUTH_AVAILABLE or UserRAGEngine is None or UserDataManager is None:
            return False
            
        try:
            self.user_rag_engine = UserRAGEngine(username)
            self.user_data_manager = UserDataManager(username)
            self.current_user = username
            st.session_state.rag_connected = True
            st.session_state.last_check = datetime.now()
            return True
        except Exception as e:
            st.error(f"❌ Failed to initialize user components: {e}")
            st.session_state.rag_connected = False
            return False
    
    def check_authentication(self) -> Optional[Dict[str, Any]]:
        """Check if user is authenticated"""
        if not AUTH_AVAILABLE or self.auth_ui is None:
            st.error("❌ Authentication system not available")
            return None
            
        return self.auth_ui.render_auth_forms()
    
    def get_stats(self) -> Optional[Dict[str, Any]]:
        """Get user-specific knowledge base statistics"""
        if not self.user_rag_engine or not self.user_data_manager:
            return None
            
        try:
            rag_stats = self.user_rag_engine.get_stats()
            user_stats = self.user_data_manager.get_user_stats()
            
            stats = {
                "status": "Connected" if st.session_state.rag_connected else "Disconnected",
                "engine_type": "User-Specific RAG Engine",
                "vector_db": "ChromaDB (User-Isolated)",
                "last_updated": datetime.now().isoformat(),
                "user": self.current_user
            }
            
            # Merge with RAG engine and user stats
            if rag_stats:
                stats.update(rag_stats)
            if user_stats:
                stats.update(user_stats)
            
            st.session_state.stats = stats
            return stats
        except Exception as e:
            return {"error": str(e), "user": self.current_user}
    
    def ask_question(self, question: str, max_results: int = 5) -> Optional[Dict[str, Any]]:
        """Ask question using the user's RAG engine"""
        if not self.user_rag_engine:
            st.error("❌ User RAG engine not available")
            return None
            
        try:
            with st.spinner("🤔 Thinking..."):
                answer, sources, processing_time = self.user_rag_engine.process_query(
                    query=question,
                    max_results=max_results
                )
                
                return {
                    "response": answer,
                    "sources": sources,
                    "metadata": {
                        "query": question,
                        "results_count": len(sources),
                        "processing_time": processing_time,
                        "user": self.current_user
                    }
                }
                
        except Exception as e:
            st.error(f"❌ Error processing question: {str(e)}")
            return None
    
    def ingest_github_repo(self, repo_name: str, include_issues: bool = True, include_prs: bool = True, max_items: int = 30):
        """Ingest data from a GitHub repository for current user"""
        if not GITHUB_AVAILABLE:
            st.error("❌ GitHub connector not available. Please install required dependencies.")
            return
            
        if not self.user_data_manager:
            st.error("❌ User not properly initialized")
            return
            
        try:
            # Initialize progress tracking
            progress_bar = st.progress(0)
            status_text = st.empty()
            
            with st.spinner(f"🚀 Ingesting data from {repo_name} for {self.current_user}..."):
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
                
                # Step 3: Save raw data to user's directory
                status_text.text("💾 Saving raw data...")
                progress_bar.progress(70)
                
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
                
                # Save to user's data directory
                filepath = self.user_data_manager.save_raw_data(data, "github", repo_name)
                
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
                
                st.success(f"✅ Successfully ingested {total_items} items from {repo_name} to {self.current_user}'s knowledge base")
                
                # Auto-process the data into vector database
                st.info("🔄 Processing data into your knowledge base...")
                self.process_raw_data_to_vector_db()
                
        except Exception as e:
            st.error(f"❌ Error ingesting GitHub repository: {str(e)}")
            st.info("💡 Make sure your GitHub token is properly configured in secrets.")
    
    def clear_knowledge_base(self):
        """Clear user's knowledge base"""
        if not self.user_data_manager or not self.user_rag_engine:
            st.error("❌ User components not available")
            return
            
        try:
            with st.spinner("🗑️ Clearing your knowledge base..."):
                # Clear user data
                data_cleared = self.user_data_manager.clear_all_data()
                kb_cleared = self.user_rag_engine.clear_knowledge_base()
                
                if data_cleared and kb_cleared:
                    st.success("✅ Your knowledge base has been cleared successfully!")
                    
                    # Refresh stats
                    self.get_stats()
                    st.rerun()
                else:
                    st.warning("⚠️ Some data may not have been cleared completely")
                    
        except Exception as e:
            st.error(f"❌ Error clearing knowledge base: {str(e)}")
    
    def process_raw_data_to_vector_db(self):
        """Process user's raw data files and add them to their vector database"""
        if not self.user_data_manager or not self.user_rag_engine:
            st.error("❌ User components not available")
            return
            
        try:
            with st.spinner("🔄 Processing your raw data into knowledge base..."):
                # Initialize data processor if available
                if not PROCESSING_AVAILABLE:
                    st.error("❌ Data processing components not available")
                    return
                
                from scripts.process_data import DataProcessor, EmbeddingGenerator
                
                processor = DataProcessor()
                embeddings_gen = EmbeddingGenerator()
                
                processed_count = 0
                
                # Get user's raw data files
                raw_files = self.user_data_manager.get_raw_data_files()
                
                for file_info in raw_files:
                    try:
                        with open(file_info['filepath'], 'r', encoding='utf-8') as f:
                            data = json.load(f)
                        
                        chunks = []
                        
                        # Process based on data type
                        filename = file_info['filename'].lower()
                        if 'github' in filename:
                            chunks = processor.process_github_data(data)
                        elif 'slack' in filename:
                            chunks = processor.process_slack_data(data)
                        
                        if chunks:
                            # Generate embeddings
                            texts = [chunk['text'] for chunk in chunks]
                            embeddings = embeddings_gen.generate_embeddings_batch(texts)
                            
                            # Add to user's vector database
                            if self.user_rag_engine.add_documents(chunks, embeddings):
                                processed_count += len(chunks)
                    
                    except Exception as e:
                        st.warning(f"⚠️ Failed to process {file_info['filename']}: {e}")
                        continue
                
                if processed_count > 0:
                    st.success(f"✅ Processed {processed_count} chunks into your knowledge base!")
                    
                    # Refresh stats
                    self.get_stats()
                else:
                    st.warning("No data chunks were generated from your raw files.")
                    
        except Exception as e:
            st.error(f"❌ Error processing raw data: {str(e)}")
    
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
                status_text.text("💾 Saving raw data...")
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
                
                # Auto-process the data into vector database
                st.info("🔄 Processing data into knowledge base...")
                self.process_raw_data_to_vector_db()
                
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
    
    def show_data_sources(self):
        """Show detailed information about current user's data sources"""
        if not self.user_data_manager:
            st.error("❌ User components not available")
            return
            
        try:
            st.subheader(f"📋 {self.current_user}'s Data Sources")
            
            # Get user's raw data files
            raw_files = self.user_data_manager.get_raw_data_files()
            
            if not raw_files:
                st.info("📭 No data sources found. Add some repositories or Slack channels!")
                return
            
            # Process and display files
            processed_files = []
            for file_info in raw_files:
                try:
                    with open(file_info['filepath'], 'r', encoding='utf-8') as f:
                        data = json.load(f)
                    
                    filename = file_info['filename']
                    if 'github' in filename:
                        processed_files.append({
                            "type": "GitHub",
                            "name": data.get("repository", filename),
                            "items": len(data.get("items", [])),
                            "file": filename,
                            "size": file_info['size']
                        })
                    elif 'slack' in filename:
                        processed_files.append({
                            "type": "Slack",
                            "name": f"{len(data.get('channels', []))} channels",
                            "items": len(data.get("messages", [])),
                            "file": filename,
                            "size": file_info['size']
                        })
                except:
                    continue
            
            if processed_files:
                for source in processed_files:
                    with st.expander(f"{source['type']}: {source['name']} ({source['items']} items)"):
                        st.write(f"**Type**: {source['type']}")
                        st.write(f"**Items**: {source['items']}")
                        st.write(f"**File**: {source['file']}")
                        st.write(f"**Size**: {source['size']} bytes")
            else:
                st.info("📭 No valid data sources found.")
                
        except Exception as e:
            st.error(f"❌ Error loading data sources: {str(e)}")
            return
            
        try:
            st.subheader(f"📋 {self.current_user}'s Data Sources")
            
            # Get user's raw data files
            raw_files = self.user_data_manager.get_raw_data_files()
            
            if not raw_files:
                st.info("📭 No data sources found. Add some repositories or Slack channels!")
                return
            
            # Process and display files
            processed_files = []
            for file_info in raw_files:
                try:
                    with open(file_info['filepath'], 'r', encoding='utf-8') as f:
                        data = json.load(f)
                    
                    filename = file_info['filename']
                    if 'github' in filename:
                        processed_files.append({
                            "type": "GitHub",
                            "name": data.get("repository", filename),
                            "items": len(data.get("items", [])),
                            "file": filename,
                            "size": file_info['size']
                        })
                    elif 'slack' in filename:
                        processed_files.append({
                            "type": "Slack",
                            "name": f"{len(data.get('channels', []))} channels",
                            "items": len(data.get("messages", [])),
                            "file": filename,
                            "size": file_info['size']
                        })
                except:
                    continue
            
            if processed_files:
                for source in processed_files:
                    with st.expander(f"{source['type']}: {source['name']} ({source['items']} items)"):
                        st.write(f"**Type**: {source['type']}")
                        st.write(f"**Items**: {source['items']}")
                        st.write(f"**File**: {source['file']}")
                        st.write(f"**Size**: {source['size']} bytes")
            else:
                st.info("📭 No valid data sources found.")
                
        except Exception as e:
            st.error(f"❌ Error loading data sources: {str(e)}")
    
    def render_header(self):
        """Render the application header"""
        st.title("🧠 Weaver AI - Multi-User")
        if self.current_user:
            st.markdown(f"*Welcome back, **{self.current_user}**! Your intelligent project knowledge assistant*")
        else:
            st.markdown("*Your intelligent project knowledge assistant*")
        
        if self.current_user:
            # Connection status
            col1, col2, col3 = st.columns([2, 1, 1])
            
            with col1:
                if st.session_state.rag_connected:
                    st.success("🟢 Your Knowledge Base Ready")
                else:
                    st.error("🔴 Knowledge Base not available")
            
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
                        
                        if selected_repo and st.button(f"📥 Ingest {selected_repo}"):
                            if GITHUB_AVAILABLE:
                                self.ingest_github_repo(selected_repo, True, True, 30)
                            else:
                                st.error("❌ GitHub connector not available. Check your installation.")
            
            st.divider()
            
            # Knowledge Base Management
            st.header("🗑️ Knowledge Base")
            if st.button("🗂️ View Data Sources"):
                self.show_data_sources()
            
            # Process existing raw data
            if st.button("🔄 Process Raw Data"):
                self.process_raw_data_to_vector_db()
            
            # Clear knowledge base with confirmation
            if stats and stats.get("total_documents", 0) > 0:
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
                    # Try to reinitialize user components
                    if self.current_user:
                        self.init_user_components(self.current_user)
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
                                # Fix: Use 'text' field instead of 'content'
                                content = source.get('text', source.get('content', 'N/A'))
                                st.markdown(f"- **Content**: {content[:200]}...")
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
                                    # Fix: Use 'text' field instead of 'content'
                                    content = source.get('text', source.get('content', 'N/A'))
                                    st.markdown(f"- **Content**: {content[:200]}...")
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
        """Main application entry point with authentication"""
        if not AUTH_AVAILABLE:
            st.error("❌ Authentication system not available. Please check your installation.")
            return
        
        # Check authentication first
        user_info = self.check_authentication()
        
        if not user_info:
            # User not authenticated, auth forms are shown
            return
        
        # User is authenticated, initialize user components if needed
        current_session_user = st.session_state.get("current_authenticated_user")
        
        if not self.current_user or self.current_user != user_info["username"] or current_session_user != user_info["username"]:
            if self.init_user_components(user_info["username"]):
                st.session_state.current_authenticated_user = user_info["username"]
                st.success(f"✅ Welcome back, {user_info['username']}!")
                st.rerun()
            else:
                st.error("❌ Failed to initialize user components")
                return
        
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
            # Show user info and render sidebar
            if self.auth_ui:  # type: ignore
                self.auth_ui.render_user_info(user_info)
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
