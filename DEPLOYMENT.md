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

1. **Import Errors**
   - Check all dependencies are in requirements.txt
   - Verify Python version compatibility

2. **API Key Issues**
   - Double-check secrets configuration
   - Ensure keys have proper permissions

3. **Memory Issues**
   - Reduce batch sizes in data processing
   - Limit concurrent operations

4. **Vector DB Issues**
   - Vector database persists in Streamlit Cloud
   - Use "Clear Knowledge Base" to reset

## Support

- **Streamlit Docs**: [docs.streamlit.io](https://docs.streamlit.io)
- **Community**: [discuss.streamlit.io](https://discuss.streamlit.io)
- **Status**: [status.streamlit.io](https://status.streamlit.io)

## Security Notes

🔒 **Never commit API keys to GitHub**
🔒 **Use Streamlit Cloud secrets for sensitive data**
🔒 **Keep .env files in .gitignore**
🔒 **Rotate keys if accidentally exposed**
