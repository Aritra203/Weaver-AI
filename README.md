# Weaver AI - Multi-User Intelligent Project Knowledge Assistant

Weaver AI is a Retrieval-Augmented Generation (RAG) system that transforms your GitHub repositories and Slack channels into an intelligent, queryable knowledge base. Now with **multi-user support and individual knowledge bases**.

## 🚀 Key Features

### 🔐 Multi-User Authentication
- **Secure User Registration & Login**: Create individual accounts with password protection
- **Session Management**: Secure token-based authentication with automatic expiry
- **Data Isolation**: Complete separation of user data and knowledge bases
- **Personal Workspaces**: Each user gets their own data directories and vector databases

### 📊 Individual Knowledge Bases
- **User-Specific Vector Databases**: ChromaDB collections isolated per user
- **Personal Data Storage**: Raw and processed data stored separately for each user
- **Individual RAG Engines**: Personalized AI responses based on user's own data
- **No Data Sharing**: Complete privacy - users can only access their own information

### 🔄 Intelligent Data Processing
- **Automatic Data Ingestion**: Pull data from GitHub (issues, PRs, comments) and Slack channels
- **Smart Processing**: Convert text into semantic embeddings using Google Gemini
- **RAG Pipeline**: Retrieve relevant context and generate AI-powered answers
- **Repository Browser**: Browse and select from your available GitHub repositories

### 🎯 User Experience
- **Clean Authentication UI**: Simple sign-up/sign-in interface with tabs
- **Personalized Dashboard**: User-specific statistics and data sources
- **Individual Controls**: Clear only your own knowledge base, view only your data
- **Real-time Processing**: Live feedback during data ingestion and processing

## 🏗️ Architecture

### Multi-User Structure
```
data/
├── users/
│   ├── users.db              # Central authentication database
│   └── {username}/           # Individual user directories
│       ├── raw/              # User's raw data files
│       ├── processed/        # User's processed chunks
│       ├── vector_db/        # User's ChromaDB collection
│       └── uploads/          # User's file uploads
```

### Authentication System
- **UserManager**: Handles registration, login, session management
- **AuthUI**: Streamlit components for authentication forms
- **UserDataManager**: Manages user-specific data operations
- **UserRAGEngine**: Personalized RAG processing per user

## 📋 Implementation Status

### ✅ Completed Features
- Multi-user authentication system with SQLite database
- Individual vector databases per user (ChromaDB)
- User-specific data ingestion and processing
- Personalized RAG engines and responses
- Secure session management with token expiry
- Complete data isolation between users
- User-specific GitHub repository ingestion
- Personal knowledge base management

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
