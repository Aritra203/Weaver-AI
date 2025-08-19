"""
Weaver AI Setup and Test Script
Validates installation and provides guided setup
"""

import os
import sys
import json
import subprocess
from typing import List, Dict, Any, Tuple

def print_header(title: str):
    """Print a formatted header"""
    print("\n" + "=" * 60)
    print(f"    {title}")
    print("=" * 60)

def print_status(message: str, status: bool):
    """Print status with appropriate icon"""
    icon = "✅" if status else "❌"
    print(f"{icon} {message}")

def check_python_version() -> bool:
    """Check if Python version is compatible"""
    version = sys.version_info
    required = (3, 8)
    
    if version >= required:
        print_status(f"Python {version.major}.{version.minor}.{version.micro}", True)
        return True
    else:
        print_status(f"Python {version.major}.{version.minor}.{version.micro} (requires 3.8+)", False)
        return False

def check_package_installation() -> Dict[str, bool]:
    """Check if required packages are installed"""
    packages = [
        "fastapi", "uvicorn", "streamlit", "requests", "python-dotenv",
        "pandas", "numpy", "PyGithub", "slack-sdk", "chromadb", 
        "openai", "tiktoken", "pydantic"
    ]
    
    results = {}
    for package in packages:
        try:
            __import__(package.replace("-", "_"))
            results[package] = True
        except ImportError:
            results[package] = False
    
    return results

def check_environment_file() -> Tuple[bool, List[str]]:
    """Check if .env file exists and has required keys"""
    env_path = ".env"
    required_keys = ["GITHUB_TOKEN", "SLACK_BOT_TOKEN", "OPENAI_API_KEY"]
    
    if not os.path.exists(env_path):
        return False, required_keys
    
    missing_keys = []
    try:
        with open(env_path, 'r') as f:
            content = f.read()
            for key in required_keys:
                if f"{key}=" not in content or f"{key}=your_" in content:
                    missing_keys.append(key)
    except Exception:
        return False, required_keys
    
    return len(missing_keys) == 0, missing_keys

def check_data_directories() -> Dict[str, bool]:
    """Check if required directories exist"""
    directories = [
        "data/raw",
        "data/processed", 
        "data/vector_db"
    ]
    
    results = {}
    for directory in directories:
        results[directory] = os.path.exists(directory)
    
    return results

def install_packages():
    """Install required packages"""
    print("📦 Installing packages...")
    try:
        subprocess.check_call([sys.executable, "-m", "pip", "install", "-r", "requirements.txt"])
        print_status("Package installation completed", True)
        return True
    except subprocess.CalledProcessError:
        print_status("Package installation failed", False)
        return False

def create_env_file():
    """Create .env file from template"""
    if os.path.exists(".env.example"):
        try:
            with open(".env.example", 'r') as src, open(".env", 'w') as dst:
                dst.write(src.read())
            print_status("Created .env file from template", True)
            return True
        except Exception:
            print_status("Failed to create .env file", False)
            return False
    else:
        print_status(".env.example not found", False)
        return False

def create_directories():
    """Create required directories"""
    directories = ["data/raw", "data/processed", "data/vector_db"]
    
    for directory in directories:
        try:
            os.makedirs(directory, exist_ok=True)
            print_status(f"Created directory: {directory}", True)
        except Exception:
            print_status(f"Failed to create directory: {directory}", False)

def test_imports():
    """Test critical imports"""
    print("\n🧪 Testing imports...")
    
    tests = [
        ("config.settings", "Configuration"),
        ("scripts.github_connector", "GitHub connector"),
        ("scripts.slack_connector", "Slack connector"),
        ("backend.rag_engine", "RAG engine"),
        ("backend.main", "FastAPI backend"),
    ]
    
    results = []
    for module, description in tests:
        try:
            __import__(module)
            print_status(f"{description}", True)
            results.append(True)
        except Exception as e:
            print_status(f"{description} - {str(e)}", False)
            results.append(False)
    
    return all(results)

def test_api_endpoints():
    """Test if API endpoints are accessible"""
    print("\n🌐 Testing API (start backend first)...")
    
    try:
        import requests
        
        base_url = "http://localhost:8000"
        endpoints = [
            ("/", "Root endpoint"),
            ("/health", "Health check"),
            ("/stats", "Statistics")
        ]
        
        for endpoint, description in endpoints:
            try:
                response = requests.get(f"{base_url}{endpoint}", timeout=5)
                success = response.status_code == 200
                print_status(f"{description} ({endpoint})", success)
            except requests.exceptions.ConnectionError:
                print_status(f"{description} - Backend not running", False)
            except Exception as e:
                print_status(f"{description} - {str(e)}", False)
    
    except ImportError:
        print_status("Requests package not available", False)

def run_full_diagnostic():
    """Run complete diagnostic"""
    print_header("WEAVER AI DIAGNOSTIC")
    
    # Python version
    print("\n🐍 Python Environment:")
    python_ok = check_python_version()
    
    # Package installation
    print("\n📦 Package Installation:")
    packages = check_package_installation()
    all_packages_ok = True
    
    for package, installed in packages.items():
        print_status(package, installed)
        if not installed:
            all_packages_ok = False
    
    # Environment configuration
    print("\n⚙️ Environment Configuration:")
    env_exists, missing_keys = check_environment_file()
    print_status(".env file exists", env_exists)
    
    if missing_keys:
        print("   Missing or incomplete keys:")
        for key in missing_keys:
            print(f"     - {key}")
    
    # Directory structure
    print("\n📁 Directory Structure:")
    directories = check_data_directories()
    for directory, exists in directories.items():
        print_status(directory, exists)
    
    # Import tests
    imports_ok = test_imports()
    
    # Summary
    print_header("SUMMARY")
    
    overall_status = (
        python_ok and 
        all_packages_ok and 
        env_exists and 
        all(directories.values()) and
        imports_ok
    )
    
    if overall_status:
        print("🎉 All checks passed! Weaver AI is ready to use.")
        print("\n📋 Next steps:")
        print("1. Configure your API keys in .env")
        print("2. Run: python scripts/ingest_data.py")
        print("3. Run: python scripts/process_data.py")
        print("4. Run: python backend/main.py")
        print("5. Run: streamlit run ui/app.py")
    else:
        print("⚠️ Some issues found. Please address them before proceeding.")
        
        if not all_packages_ok:
            print("\n💡 To install packages: pip install -r requirements.txt")
        
        if not env_exists:
            print("\n💡 To create .env: copy .env.example .env")
        
        if not all(directories.values()):
            print("\n💡 To create directories: mkdir -p data/{raw,processed,vector_db}")

def interactive_setup():
    """Interactive setup wizard"""
    print_header("WEAVER AI SETUP WIZARD")
    
    # Check Python
    if not check_python_version():
        print("❌ Python 3.8+ is required. Please upgrade and try again.")
        return
    
    # Install packages
    packages = check_package_installation()
    if not all(packages.values()):
        print(f"\n📦 {sum(not v for v in packages.values())} packages need to be installed.")
        install = input("Install missing packages? (y/N): ").lower().strip()
        
        if install in ['y', 'yes']:
            if not install_packages():
                print("❌ Package installation failed. Please check your internet connection and try again.")
                return
        else:
            print("⏭️ Skipping package installation")
    
    # Create .env file
    env_exists, missing_keys = check_environment_file()
    if not env_exists:
        print("\n⚙️ Environment file (.env) not found.")
        create = input("Create .env file from template? (y/N): ").lower().strip()
        
        if create in ['y', 'yes']:
            if create_env_file():
                print("✅ Created .env file. Please edit it with your API keys.")
            else:
                print("❌ Failed to create .env file")
        else:
            print("⏭️ Skipping .env creation")
    
    # Create directories
    directories = check_data_directories()
    if not all(directories.values()):
        print("\n📁 Creating required directories...")
        create_directories()
    
    # Final check
    print("\n🏁 Setup complete! Running final diagnostic...")
    run_full_diagnostic()

def main():
    """Main entry point"""
    import argparse
    
    parser = argparse.ArgumentParser(description="Weaver AI Setup and Diagnostic Tool")
    parser.add_argument("--setup", action="store_true", help="Run interactive setup wizard")
    parser.add_argument("--diagnostic", action="store_true", help="Run diagnostic only")
    parser.add_argument("--test-api", action="store_true", help="Test API endpoints")
    
    args = parser.parse_args()
    
    if args.setup:
        interactive_setup()
    elif args.test_api:
        test_api_endpoints()
    else:
        run_full_diagnostic()

if __name__ == "__main__":
    main()
