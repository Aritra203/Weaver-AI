# Weaver AI - Intelligent Project Knowledge Assistant

Weaver AI is a Retrieval-Augmented Generation (RAG) system that transforms your GitHub repositories and Slack channels into an intelligent, queryable knowledge base.

## 🚀 Features

- **Automatic Data Ingestion**: Automatically pulls data from GitHub (issues, PRs, comments) and Slack channels with repository selection
- **Intelligent Processing**: Converts text into semantic embeddings using Google Gemini for smart search
- **RAG Pipeline**: Retrieves relevant context and generates AI-powered answers using Gemini
- **User-Friendly Interface**: Simple web UI with integrated data source management and real-time ingestion
- **Repository Browser**: Browse and select from your available GitHub repositories
- **Smart Chunking**: Preserves context while breaking down large documents for better search

## 📋 Implementation Phases

### Phase 1: Setup and Data Ingestion ✅
- Project initialization with virtual environment
- API connectors for GitHub and Slack
- Raw data storage in JSON format

### Phase 2: Data Processing & Vectorization
- Text chunking and cleaning
- Embedding generation
- Vector database storage

### Phase 3: Backend API Development
- FastAPI server with RAG pipeline
- Query processing and answer generation

### Phase 4: User Interface Creation
- Streamlit web interface
- Interactive Q&A experience

## 🛠️ Tech Stack

- **Language**: Python 3.8+
- **APIs**: PyGithub, slack_sdk
- **Vector DB**: ChromaDB
- **AI Service**: Google Gemini & Embeddings
- **Backend**: FastAPI + Uvicorn
- **Frontend**: Streamlit
- **Environment**: python-venv, python-dotenv

## 📦 Installation

```bash
# Create virtual environment
python -m venv weaver-env
weaver-env\Scripts\activate  # Windows

# Install dependencies
pip install -r requirements.txt

# Set up environment variables
cp .env.example .env
# Edit .env with your API keys
```

## 🔧 Usage

### Option 1: Integrated Approach (Recommended)
1. **Start Backend**: `python backend/main.py`
2. **Launch UI**: `streamlit run ui/app.py`
3. **Add Data Sources**: Use the sidebar to select GitHub repositories and Slack channels
4. **Ask Questions**: Start querying your intelligent knowledge base!
5. **Manage Knowledge Base**: Use the clear option in the sidebar to reset the knowledge base when needed

### Option 2: Manual Data Processing
1. **Data Ingestion**: `python scripts/ingest_data.py`
2. **Process Data**: `python scripts/process_data.py`
3. **Start Backend**: `uvicorn backend.main:app --reload`
4. **Launch UI**: `streamlit run ui/app.py`

### Option 3: Streamlit Cloud Deployment
1. **Test Locally**: `streamlit run streamlit_app.py`
2. **Deploy**: Follow the guide in `DEPLOYMENT.md`
3. **Configure Secrets**: Add your API keys in Streamlit Cloud dashboard

### Knowledge Base Management
- **Clear All Data**: Use the "Clear Knowledge Base" button in the UI sidebar or call `DELETE /clear` endpoint
- **View Stats**: Check the sidebar for document counts and source breakdown
- **Data Sources**: View detailed information about ingested repositories and channels

## 📁 Project Structure

```
weaver-ai/
├── data/
│   ├── raw/           # Raw JSON data from APIs
│   └── processed/     # Processed and chunked data
├── scripts/
│   ├── github_connector.py
│   ├── slack_connector.py
│   ├── ingest_data.py
│   └── process_data.py
├── backend/
│   ├── main.py        # FastAPI application
│   ├── rag_engine.py  # RAG pipeline
│   └── models.py      # Data models
├── ui/
│   └── app.py         # Streamlit interface
├── config/
│   └── settings.py    # Configuration management
└── requirements.txt
```

## 🔑 Environment Variables

Create a `.env` file with:
```
GITHUB_TOKEN=your_github_token
SLACK_BOT_TOKEN=your_slack_bot_token
GOOGLE_API_KEY=your_google_gemini_api_key
```

## 📄 License

MIT License - Feel free to use this for your hackathon projects!
