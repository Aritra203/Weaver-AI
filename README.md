# Weaver AI - Intelligent Project Knowledge Assistant

Weaver AI is a Retrieval-Augmented Generation (RAG) system that transforms your GitHub repositories and Slack channels into an intelligent, queryable knowledge base.

## 🚀 Features

- **Data Ingestion**: Automatically pulls data from GitHub (issues, PRs, comments) and Slack channels
- **Intelligent Processing**: Converts text into semantic embeddings for smart search
- **RAG Pipeline**: Retrieves relevant context and generates AI-powered answers
- **User-Friendly Interface**: Simple web UI for asking questions about your project

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
- **AI Service**: OpenAI GPT-4 & Embeddings
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

1. **Data Ingestion**: `python scripts/ingest_data.py`
2. **Process Data**: `python scripts/process_data.py`
3. **Start Backend**: `uvicorn backend.main:app --reload`
4. **Launch UI**: `streamlit run ui/app.py`

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
OPENAI_API_KEY=your_openai_api_key
```

## 📄 License

MIT License - Feel free to use this for your hackathon projects!
