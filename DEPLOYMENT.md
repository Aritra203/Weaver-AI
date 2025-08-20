# 🚀 Streamlit Cloud Deployment Guide

## Prerequisites
1. GitHub account
2. Streamlit Cloud account (sign up at share.streamlit.io)
3. Your API keys ready

## Deployment Steps

### 1. Push to GitHub
```bash
# Initialize git repository (if not done)
git init
git add .
git commit -m "Initial commit - Weaver AI"
git branch -M main
git remote add origin https://github.com/yourusername/weaver-ai.git
git push -u origin main
```

### 2. Deploy on Streamlit Cloud

1. **Go to [share.streamlit.io](https://share.streamlit.io)**
2. **Sign in** with your GitHub account
3. **Click "New app"**
4. **Select your repository**: `yourusername/weaver-ai`
5. **Set main file path**: `streamlit_app.py`
6. **Click "Deploy!"**

### 3. Configure Secrets

In your Streamlit Cloud app dashboard:

1. **Go to "Manage app" > "Secrets"**
2. **Add your secrets** in TOML format:

```toml
# API Keys
GITHUB_TOKEN = "your_actual_github_token"
SLACK_BOT_TOKEN = "your_actual_slack_token"
GOOGLE_API_KEY = "your_actual_gemini_api_key"

# Database Settings
VECTOR_DB_PATH = "./data/vector_db"
CHUNK_SIZE = 500
CHUNK_OVERLAP = 50

# API Settings
API_HOST = "127.0.0.1"
API_PORT = 8000
```

### 4. Advanced Configuration (Optional)

#### Custom Domain
- Go to "Manage app" > "Settings"
- Add your custom domain if you have one

#### Resource Settings
- Streamlit Cloud provides sufficient resources for most use cases
- Monitor usage in the dashboard

## Files Created for Deployment

✅ `streamlit_app.py` - Main Streamlit app (combines UI + backend)
✅ `.streamlit/config.toml` - Streamlit configuration
✅ `.streamlit/secrets.toml` - Secrets template (local only)
✅ `packages.txt` - System dependencies
✅ Updated `.gitignore` - Excludes sensitive files

## Local Testing

Test the Streamlit-only version locally:

```bash
# Activate your environment
weaver-env\Scripts\activate

# Run the streamlit app
streamlit run streamlit_app.py
```

## Differences from Local Version

**Streamlit Cloud Version:**
- Combines backend and frontend in one app
- Uses Streamlit secrets instead of .env
- Optimized for cloud deployment
- Single process architecture

**Local Development Version:**
- Separate FastAPI backend + Streamlit frontend
- Uses .env file for configuration
- Multi-process architecture

## Troubleshooting

### Common Issues:

1. **Dependency Conflicts (Python 3.13)**
   - Streamlit Cloud uses Python 3.13 which has stricter compatibility
   - Solution: Use `requirements-cloud.txt` instead of `requirements.txt`
   - Alternative: Use `requirements-minimal.txt` for bare minimum setup

2. **Import Errors**
   - Check all dependencies are in requirements.txt
   - Verify Python version compatibility (3.13)
   - Try using version ranges (>=) instead of pinned versions (==)

3. **ChromaDB Installation Issues**
   - ChromaDB may have compilation issues on some cloud platforms
   - Fallback: The app will work without ChromaDB but with limited functionality
   - Alternative: Use requirements-minimal.txt to skip ChromaDB

4. **API Key Issues**
   - Double-check secrets configuration
   - Ensure keys have proper permissions

5. **Memory Issues**
   - Reduce batch sizes in data processing
   - Limit concurrent operations

6. **Vector DB Issues**
   - Vector database persists in Streamlit Cloud
   - Use "Clear Knowledge Base" to reset

### Dependency Solutions:

**Option 1: Full Features (Recommended)**
```bash
# Use the updated requirements.txt
git push origin main
```

**Option 2: Cloud Optimized**
```bash
# Rename requirements-cloud.txt to requirements.txt in your repo
mv requirements-cloud.txt requirements.txt
git add requirements.txt
git commit -m "Use cloud-optimized dependencies"
git push origin main
```

**Option 3: Minimal Setup**
```bash
# Rename requirements-minimal.txt to requirements.txt in your repo  
mv requirements-minimal.txt requirements.txt
git add requirements.txt
git commit -m "Use minimal dependencies for compatibility"
git push origin main
```

## Support

- **Streamlit Docs**: [docs.streamlit.io](https://docs.streamlit.io)
- **Community**: [discuss.streamlit.io](https://discuss.streamlit.io)
- **Status**: [status.streamlit.io](https://status.streamlit.io)

## Security Notes

🔒 **Never commit API keys to GitHub**
🔒 **Use Streamlit Cloud secrets for sensitive data**
🔒 **Keep .env files in .gitignore**
🔒 **Rotate keys if accidentally exposed**
