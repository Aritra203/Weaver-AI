"""
Main data ingestion script for Weaver AI
Orchestrates data collection from GitHub and Slack
"""

import sys
import os
from typing import Dict, List, Optional

# Add the project root to the Python path
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from config.settings import get_settings
from scripts.github_connector import GitHubConnector
from scripts.slack_connector import SlackConnector

settings = get_settings()

class DataIngestionOrchestrator:
    """Orchestrates data collection from multiple sources"""
    
    def __init__(self):
        """Initialize connectors"""
        self.github_connector = None
        self.slack_connector = None
        self.results = {}
    
    def validate_setup(self) -> Dict[str, bool]:
        """Validate that API keys and configuration are present"""
        print("🔍 Validating setup...")
        
        validation_results = {
            "github_token": bool(settings.GITHUB_TOKEN),
            "slack_token": bool(settings.SLACK_BOT_TOKEN),
            "openai_key": bool(settings.OPENAI_API_KEY),
            "github_repo": bool(settings.GITHUB_REPO),
            "slack_channels": bool(settings.SLACK_CHANNELS)
        }
        
        print(f"📊 Configuration Status:")
        for key, status in validation_results.items():
            status_icon = "✅" if status else "❌"
            print(f"  {status_icon} {key}: {'Configured' if status else 'Missing'}")
        
        # Check for missing required API keys
        missing_keys = settings.validate_api_keys()
        if missing_keys:
            print(f"\n⚠️ Missing required API keys: {', '.join(missing_keys)}")
            print("   Please set these in your .env file before proceeding.")
            return validation_results
        
        print("✅ Basic validation passed!")
        return validation_results
    
    def ingest_github_data(self, repo_name: Optional[str] = None) -> Dict[str, str]:
        """Ingest data from GitHub"""
        print("\n" + "="*50)
        print("🐙 GITHUB DATA INGESTION")
        print("="*50)
        
        try:
            # Initialize GitHub connector
            self.github_connector = GitHubConnector()
            
            # Use provided repo or setting
            target_repo = repo_name or settings.GITHUB_REPO
            if not target_repo:
                target_repo = input("Enter GitHub repository (format: owner/repo): ").strip()
            
            if not target_repo:
                print("❌ No GitHub repository specified, skipping GitHub ingestion")
                return {}
            
            # Fetch data
            files = self.github_connector.fetch_repository_data(target_repo)
            self.results['github'] = files
            
            return files
            
        except Exception as e:
            print(f"❌ GitHub ingestion failed: {str(e)}")
            return {}
    
    def ingest_slack_data(self, channel_ids: Optional[List[str]] = None) -> Dict[str, str]:
        """Ingest data from Slack"""
        print("\n" + "="*50)
        print("💬 SLACK DATA INGESTION")
        print("="*50)
        
        try:
            # Initialize Slack connector
            self.slack_connector = SlackConnector()
            
            # Fetch data
            files = self.slack_connector.fetch_workspace_data(channel_ids)
            self.results['slack'] = files
            
            return files
            
        except Exception as e:
            print(f"❌ Slack ingestion failed: {str(e)}")
            return {}
    
    def run_full_ingestion(self, 
                          github_repo: Optional[str] = None,
                          slack_channels: Optional[List[str]] = None,
                          skip_github: bool = False,
                          skip_slack: bool = False) -> Dict[str, Dict[str, str]]:
        """Run complete data ingestion from all sources"""
        print("🚀 Starting Weaver AI Data Ingestion")
        print("="*60)
        
        # Validate setup
        validation = self.validate_setup()
        
        # GitHub ingestion
        if not skip_github and validation['github_token']:
            github_files = self.ingest_github_data(github_repo)
        else:
            print("\n⏭️ Skipping GitHub ingestion")
            github_files = {}
        
        # Slack ingestion
        if not skip_slack and validation['slack_token']:
            slack_files = self.ingest_slack_data(slack_channels)
        else:
            print("\n⏭️ Skipping Slack ingestion")
            slack_files = {}
        
        # Summary
        self.print_summary()
        
        return {
            "github": github_files,
            "slack": slack_files
        }
    
    def print_summary(self):
        """Print ingestion summary"""
        print("\n" + "="*60)
        print("📊 INGESTION SUMMARY")
        print("="*60)
        
        total_files = 0
        for source, files in self.results.items():
            file_count = len(files)
            total_files += file_count
            print(f"📁 {source.upper()}: {file_count} files")
            for file_type, filepath in files.items():
                print(f"   - {file_type}: {os.path.basename(filepath)}")
        
        if total_files > 0:
            print(f"\n🎉 Successfully ingested data into {total_files} files")
            print(f"📂 All files saved to: {settings.RAW_DATA_PATH}")
            print(f"\n💡 Next step: Run 'python scripts/process_data.py' to process this data")
        else:
            print("⚠️ No data was ingested. Check your configuration and try again.")

def main():
    """Main entry point"""
    import argparse
    
    parser = argparse.ArgumentParser(description="Weaver AI Data Ingestion")
    parser.add_argument("--github-repo", help="GitHub repository (owner/repo)")
    parser.add_argument("--slack-channels", nargs="+", help="Slack channel IDs")
    parser.add_argument("--skip-github", action="store_true", help="Skip GitHub ingestion")
    parser.add_argument("--skip-slack", action="store_true", help="Skip Slack ingestion")
    parser.add_argument("--validate-only", action="store_true", help="Only validate configuration")
    
    args = parser.parse_args()
    
    try:
        orchestrator = DataIngestionOrchestrator()
        
        if args.validate_only:
            orchestrator.validate_setup()
            return
        
        # Run ingestion
        results = orchestrator.run_full_ingestion(
            github_repo=args.github_repo,
            slack_channels=args.slack_channels,
            skip_github=args.skip_github,
            skip_slack=args.skip_slack
        )
        
        # Exit with appropriate code
        total_files = sum(len(files) for files in results.values())
        sys.exit(0 if total_files > 0 else 1)
        
    except KeyboardInterrupt:
        print("\n\n⏹️ Ingestion cancelled by user")
        sys.exit(1)
    except Exception as e:
        print(f"\n❌ Fatal error: {str(e)}")
        sys.exit(1)

if __name__ == "__main__":
    main()
