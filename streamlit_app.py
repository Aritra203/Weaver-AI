#!/usr/bin/env python3
"""
Streamlit Cloud Deployment Version of Weaver AI
This version combines the backend functionality with the Streamlit UI
for seamless deployment on Streamlit Cloud.
"""

import streamlit as st
import os
import sys
import json
import requests
from datetime import datetime
from pathlib import Path

# Add project root to path for imports
project_root = Path(__file__).parent
sys.path.append(str(project_root))

# Import your existing modules
try:
    from backend.rag_engine import RAGEngine
    from scripts.github_connector import GitHubConnector
    from scripts.slack_connector import SlackConnector
    from scripts.process_data import DataProcessor
    from config.settings import get_settings
except ImportError as e:
    st.error(f"Import error: {e}")
    st.error("Please ensure all required packages are installed.")
    st.stop()

# Page configuration
st.set_page_config(
    page_title="Weaver AI - Knowledge Assistant",
    page_icon="🧠",
    layout="wide",
    initial_sidebar_state="expanded"
)

class StreamlitWeaverAI:
    """Streamlit Cloud version of Weaver AI"""
    
    def __init__(self):
        """Initialize the application"""
        self.settings = get_settings()
        self.init_session_state()
        self.init_components()
    
    def init_session_state(self):
        """Initialize Streamlit session state"""
        if "messages" not in st.session_state:
            st.session_state.messages = []
        if "rag_engine" not in st.session_state:
            st.session_state.rag_engine = None
        if "stats" not in st.session_state:
            st.session_state.stats = {}
        if "initialized" not in st.session_state:
            st.session_state.initialized = False
    
    def init_components(self):
        """Initialize RAG engine and other components"""
        if not st.session_state.initialized:
            try:
                with st.spinner("🔄 Initializing Weaver AI..."):
                    st.session_state.rag_engine = RAGEngine()
                    st.session_state.initialized = True
                    self.get_stats()
            except Exception as e:
                st.error(f"❌ Failed to initialize: {str(e)}")
                st.error("Please check your API keys in Streamlit secrets.")
    
    def get_stats(self):
        """Get knowledge base statistics"""
        if st.session_state.rag_engine:
            try:
                stats = st.session_state.rag_engine.get_stats()
                st.session_state.stats = stats
            except Exception as e:
                st.error(f"Error getting stats: {str(e)}")
    
    def render_header(self):
        """Render the main header"""
        st.title("🧠 Weaver AI - Knowledge Assistant")
        st.markdown("*Transform your repositories into intelligent, queryable knowledge*")
        
        # Status indicator
        if st.session_state.rag_engine and st.session_state.rag_engine.is_ready():
            st.success("✅ System Ready")
        else:
            st.warning("⚠️ System Initializing...")
    
    def render_sidebar(self):
        """Render the sidebar"""
        with st.sidebar:
            st.header("📊 Knowledge Base")
            
            # Stats
            stats = st.session_state.stats
            if stats:
                st.metric("Total Documents", stats.get("total_documents", 0))
                
                sources = stats.get("sources", {})
                if sources:
                    st.subheader("📂 Data Sources")
                    for source, count in sources.items():
                        st.write(f"**{source.title()}**: {count}")
            
            st.divider()
            
            # Data Ingestion
            st.header("📥 Data Ingestion")
            
            with st.expander("🔗 Add GitHub Repository"):
                self.render_github_section()
            
            with st.expander("💬 Add Slack Channels"):
                self.render_slack_section()
            
            st.divider()
            
            # Management
            st.header("⚙️ Management")
            
            if st.button("🔄 Refresh Stats"):
                self.get_stats()
                st.rerun()
            
            if stats.get("total_documents", 0) > 0:
                if st.button("🗑️ Clear Knowledge Base"):
                    self.clear_knowledge_base()
    
    def render_github_section(self):
        """Render GitHub ingestion section"""
        repo_name = st.text_input(
            "Repository (owner/repo)",
            placeholder="e.g., microsoft/vscode"
        )
        
        col1, col2 = st.columns(2)
        with col1:
            include_issues = st.checkbox("Include Issues", value=True)
        with col2:
            include_prs = st.checkbox("Include PRs", value=True)
        
        max_items = st.number_input("Max Items", min_value=5, max_value=50, value=20)
        
        if st.button("🚀 Ingest Repository", disabled=not repo_name):
            self.ingest_github_repo(repo_name, include_issues, include_prs, max_items)
    
    def render_slack_section(self):
        """Render Slack ingestion section"""
        channels_input = st.text_area(
            "Channel Names",
            placeholder="general\\nrandom\\ndev-team"
        )
        
        col1, col2 = st.columns(2)
        with col1:
            days_back = st.number_input("Days Back", min_value=1, max_value=30, value=7)
        with col2:
            max_messages = st.number_input("Max Messages", min_value=50, max_value=500, value=200)
        
        if st.button("💬 Ingest Channels", disabled=not channels_input.strip()):
            channels = [ch.strip() for ch in channels_input.split('\\n') if ch.strip()]
            self.ingest_slack_channels(channels, days_back, max_messages)
    
    def ingest_github_repo(self, repo_name, include_issues, include_prs, max_items):
        """Ingest GitHub repository data"""
        try:
            with st.spinner(f"🔄 Ingesting {repo_name}..."):
                # Initialize connectors
                github_connector = GitHubConnector()
                data_processor = DataProcessor()
                
                # Fetch data
                repo = github_connector.get_repository(repo_name)
                all_data = []
                
                if include_issues:
                    issues = github_connector.fetch_issues(repo, limit=max_items//2)
                    all_data.extend(issues)
                
                if include_prs:
                    prs = github_connector.fetch_pull_requests(repo, limit=max_items//2)
                    all_data.extend(prs)
                
                if all_data:
                    # Process data
                    github_data = {
                        "type": "github",
                        "repository": repo_name,
                        "items": all_data,
                        "fetched_at": datetime.now().isoformat()
                    }
                    
                    processed_chunks = data_processor.process_github_data(github_data)
                    
                    # Store in RAG engine
                    stored_count = self.store_chunks(processed_chunks, repo_name)
                    
                    st.success(f"✅ Successfully ingested {len(all_data)} items, stored {stored_count} chunks")
                    self.get_stats()
                else:
                    st.warning("No data found in repository")
                    
        except Exception as e:
            st.error(f"❌ Error ingesting repository: {str(e)}")
    
    def ingest_slack_channels(self, channels, days_back, max_messages):
        """Ingest Slack channel data"""
        try:
            with st.spinner(f"🔄 Ingesting {len(channels)} Slack channels..."):
                slack_connector = SlackConnector()
                data_processor = DataProcessor()
                
                # Get all channels and create name to ID mapping
                all_channels = slack_connector.get_channels()
                channel_map = {ch["name"]: ch["id"] for ch in all_channels}
                
                all_messages = []
                
                for channel_name in channels:
                    if channel_name in channel_map:
                        channel_id = channel_map[channel_name]
                        messages = slack_connector.fetch_channel_messages(
                            channel_id=channel_id,
                            limit=max_messages//len(channels)
                        )
                        all_messages.extend(messages)
                    else:
                        st.warning(f"Channel '{channel_name}' not found or not accessible")
                
                if all_messages:
                    slack_data = {
                        "type": "slack",
                        "channels": channels,
                        "messages": all_messages,
                        "fetched_at": datetime.now().isoformat()
                    }
                    
                    processed_chunks = data_processor.process_slack_data(slack_data)
                    stored_count = self.store_chunks(processed_chunks, f"slack-{'-'.join(channels)}")
                    
                    st.success(f"✅ Successfully ingested {len(all_messages)} messages, stored {stored_count} chunks")
                    self.get_stats()
                else:
                    st.warning("No messages found in channels")
                    
        except Exception as e:
            st.error(f"❌ Error ingesting Slack data: {str(e)}")
    
    def store_chunks(self, chunks, source_name):
        """Store processed chunks in the RAG engine"""
        stored_count = 0
        
        if st.session_state.rag_engine and st.session_state.rag_engine.collection and chunks:
            try:
                from scripts.process_data import EmbeddingGenerator
                embedding_generator = EmbeddingGenerator()
                
                for i, chunk in enumerate(chunks):
                    try:
                        chunk_text = chunk["text"]
                        metadata = chunk["metadata"]
                        metadata["source_name"] = source_name
                        
                        # Generate unique ID
                        chunk_id = f"{source_name}_{metadata.get('type', 'unknown')}_{metadata.get('id', 'unknown')}_{i}"
                        chunk_id = chunk_id.replace("/", "_").replace(" ", "_")
                        
                        # Generate embedding
                        embedding = embedding_generator.generate_embedding(chunk_text)
                        
                        # Store in vector database
                        st.session_state.rag_engine.collection.add(
                            ids=[chunk_id],
                            embeddings=[embedding],
                            documents=[chunk_text],
                            metadatas=[metadata]
                        )
                        stored_count += 1
                        
                    except Exception as e:
                        st.error(f"Error storing chunk {i}: {str(e)}")
                        
            except Exception as e:
                st.error(f"Error in storage process: {str(e)}")
        
        return stored_count
    
    def clear_knowledge_base(self):
        """Clear all documents from knowledge base"""
        try:
            if st.session_state.rag_engine and st.session_state.rag_engine.collection:
                current_count = st.session_state.rag_engine.collection.count()
                
                if current_count > 0:
                    all_docs = st.session_state.rag_engine.collection.get(include=[])
                    if all_docs and 'ids' in all_docs and all_docs['ids']:
                        st.session_state.rag_engine.collection.delete(ids=all_docs['ids'])
                
                st.success(f"✅ Cleared {current_count} documents")
                self.get_stats()
                st.rerun()
                
        except Exception as e:
            st.error(f"❌ Error clearing knowledge base: {str(e)}")
    
    def render_chat_interface(self):
        """Render the main chat interface"""
        st.header("💬 Ask Your Questions")
        
        # Display chat messages
        for message in st.session_state.messages:
            with st.chat_message(message["role"]):
                st.markdown(message["content"])
                if "sources" in message and message["sources"]:
                    with st.expander(f"📚 Sources ({len(message['sources'])})"):
                        for i, source in enumerate(message["sources"], 1):
                            st.write(f"**{i}.** {source.get('type', 'unknown')} - {source.get('title', 'No title')}")
        
        # Chat input
        if prompt := st.chat_input("Ask me anything about your repositories..."):
            # Add user message
            st.session_state.messages.append({"role": "user", "content": prompt})
            
            with st.chat_message("user"):
                st.markdown(prompt)
            
            # Generate response
            with st.chat_message("assistant"):
                with st.spinner("🤔 Thinking..."):
                    try:
                        if st.session_state.rag_engine and st.session_state.rag_engine.is_ready():
                            answer, sources, _ = st.session_state.rag_engine.process_query(prompt)
                            
                            st.markdown(answer)
                            
                            # Store assistant message
                            st.session_state.messages.append({
                                "role": "assistant", 
                                "content": answer,
                                "sources": sources
                            })
                            
                            # Show sources
                            if sources:
                                with st.expander(f"📚 Sources ({len(sources)})"):
                                    for i, source in enumerate(sources, 1):
                                        metadata = source.get("metadata", {})
                                        st.write(f"**{i}.** {metadata.get('type', 'unknown')} - {metadata.get('title', 'No title')}")
                                        st.write(f"   Similarity: {source.get('similarity_score', 0):.3f}")
                        else:
                            error_msg = "❌ System not ready. Please check your configuration and try again."
                            st.error(error_msg)
                            st.session_state.messages.append({"role": "assistant", "content": error_msg})
                            
                    except Exception as e:
                        error_msg = f"❌ Error processing question: {str(e)}"
                        st.error(error_msg)
                        st.session_state.messages.append({"role": "assistant", "content": error_msg})
    
    def run(self):
        """Main application entry point"""
        self.render_header()
        
        # Check if system is ready
        if not st.session_state.initialized:
            st.warning("⚠️ System is initializing. Please wait...")
            self.init_components()
        
        # Create layout
        col1, col2 = st.columns([2, 1])
        
        with col1:
            self.render_chat_interface()
        
        with col2:
            self.render_sidebar()

# Run the application
if __name__ == "__main__":
    app = StreamlitWeaverAI()
    app.run()
