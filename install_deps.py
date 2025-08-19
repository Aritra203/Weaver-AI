"""
Dependency checker and installer for Weaver AI
This script helps install dependencies incrementally
"""

import subprocess
import sys
import os
from typing import List, Dict, Tuple

def check_package(package_name: str) -> bool:
    """Check if a package is installed"""
    try:
        # Handle package name variations
        import_name = package_name.replace("-", "_")
        if package_name == "PyGithub":
            import_name = "github"
        elif package_name == "slack-sdk":
            import_name = "slack_sdk"
        elif package_name == "python-dotenv":
            import_name = "dotenv"
        elif package_name.startswith("uvicorn"):
            import_name = "uvicorn"
        
        __import__(import_name)
        return True
    except ImportError:
        return False

def install_package(package_name: str) -> bool:
    """Install a single package"""
    try:
        print(f"Installing {package_name}...")
        subprocess.check_call([sys.executable, "-m", "pip", "install", package_name])
        return True
    except subprocess.CalledProcessError:
        print(f"Failed to install {package_name}")
        return False

def get_package_groups() -> Dict[str, List[str]]:
    """Get packages organized by functionality"""
    return {
        "core": [
            "python-dotenv",
            "requests",
            "pydantic"
        ],
        "data_apis": [
            "PyGithub",
            "slack-sdk"
        ],
        "ai_processing": [
            "openai",
            "tiktoken",
            "chromadb"
        ],
        "web_framework": [
            "fastapi",
            "uvicorn[standard]"
        ],
        "ui": [
            "streamlit"
        ],
        "data_processing": [
            "pandas",
            "numpy"
        ]
    }

def main():
    """Main installation process"""
    print("🔧 Weaver AI Dependency Manager")
    print("=" * 50)
    
    package_groups = get_package_groups()
    
    # Check current status
    print("\n📋 Current Package Status:")
    all_packages = []
    for group_name, packages in package_groups.items():
        print(f"\n{group_name.upper()}:")
        for package in packages:
            # Clean package name for checking
            check_name = package.split('[')[0]  # Remove extras like [standard]
            installed = check_package(check_name)
            status = "✅" if installed else "❌"
            print(f"  {status} {package}")
            all_packages.append((package, installed))
    
    # Count installed packages
    installed_count = sum(1 for _, installed in all_packages if installed)
    total_count = len(all_packages)
    
    print(f"\n📊 Summary: {installed_count}/{total_count} packages installed")
    
    if installed_count == total_count:
        print("🎉 All packages are installed!")
        return
    
    # Interactive installation
    print(f"\n🚀 Installation Options:")
    print("1. Install all missing packages")
    print("2. Install by group")
    print("3. Install individual packages")
    print("4. Exit")
    
    choice = input("\nEnter your choice (1-4): ").strip()
    
    if choice == "1":
        print("\n📦 Installing all missing packages...")
        for package, installed in all_packages:
            if not installed:
                install_package(package)
    
    elif choice == "2":
        print("\n📂 Available groups:")
        for i, (group_name, packages) in enumerate(package_groups.items(), 1):
            missing = [p for p in packages if not check_package(p.split('[')[0])]
            print(f"{i}. {group_name} ({len(missing)} missing)")
        
        try:
            group_choice = int(input("Select group number: ")) - 1
            group_names = list(package_groups.keys())
            if 0 <= group_choice < len(group_names):
                selected_group = group_names[group_choice]
                packages = package_groups[selected_group]
                print(f"\n📦 Installing {selected_group} packages...")
                for package in packages:
                    if not check_package(package.split('[')[0]):
                        install_package(package)
        except (ValueError, IndexError):
            print("Invalid selection")
    
    elif choice == "3":
        missing_packages = [p for p, installed in all_packages if not installed]
        if missing_packages:
            print("\n📦 Missing packages:")
            for i, package in enumerate(missing_packages, 1):
                print(f"{i}. {package}")
            
            try:
                pkg_choice = int(input("Select package number: ")) - 1
                if 0 <= pkg_choice < len(missing_packages):
                    install_package(missing_packages[pkg_choice])
            except (ValueError, IndexError):
                print("Invalid selection")
    
    elif choice == "4":
        print("👋 Goodbye!")
    
    else:
        print("Invalid choice")

if __name__ == "__main__":
    main()
