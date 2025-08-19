"""
GitHub API connector for Weaver AI
Fetches issues, pull requests, and comments from GitHub repositories
"""

import json
import os
from datetime import datetime
from typing import Dict, List, Any, Optional
from github import Github, Repository
from config.settings import get_settings

settings = get_settings()

class GitHubConnector:
    """Handles GitHub API interactions and data fetching"""
    
    def __init__(self, token: Optional[str] = None):
        """Initialize GitHub client with authentication token"""
        self.token = token or settings.GITHUB_TOKEN
        if not self.token:
            raise ValueError("GitHub token is required. Set GITHUB_TOKEN environment variable.")
        
        self.client = Github(self.token)
        self.rate_limit_info = None
    
    def get_repository(self, repo_name: str) -> Repository.Repository:
        """Get repository object by name (format: owner/repo)"""
        try:
            repo = self.client.get_repo(repo_name)
            print(f"✅ Connected to repository: {repo.full_name}")
            return repo
        except Exception as e:
            raise Exception(f"Failed to access repository {repo_name}: {str(e)}")
    
    def check_rate_limit(self) -> Dict[str, Any]:
        """Check current API rate limit status"""
        try:
            rate_limit = self.client.get_rate_limit()
            # Access rate limit data safely
            core_rate = getattr(rate_limit, 'core', None)
            search_rate = getattr(rate_limit, 'search', None)
            
            self.rate_limit_info = {
                "core": {
                    "limit": getattr(core_rate, 'limit', 5000),
                    "remaining": getattr(core_rate, 'remaining', 5000),
                    "reset": getattr(core_rate, 'reset', datetime.now()).strftime("%Y-%m-%d %H:%M:%S")
                },
                "search": {
                    "limit": getattr(search_rate, 'limit', 30),
                    "remaining": getattr(search_rate, 'remaining', 30),
                    "reset": getattr(search_rate, 'reset', datetime.now()).strftime("%Y-%m-%d %H:%M:%S")
                }
            }
        except Exception as e:
            print(f"⚠️ Could not check rate limit: {e}")
            self.rate_limit_info = {
                "core": {"limit": 5000, "remaining": 5000, "reset": "Unknown"},
                "search": {"limit": 30, "remaining": 30, "reset": "Unknown"}
            }
        return self.rate_limit_info
    
    def fetch_issues(self, repo: Repository.Repository, state: str = "all") -> List[Dict[str, Any]]:
        """Fetch all issues from repository"""
        print(f"📥 Fetching issues (state: {state})...")
        
        issues_data = []
        issues = repo.get_issues(state=state, sort="updated", direction="desc")
        
        for issue in issues:
            # Skip pull requests (they appear in issues API)
            if issue.pull_request:
                continue
            
            issue_data = {
                "id": issue.id,
                "number": issue.number,
                "title": issue.title,
                "body": issue.body or "",
                "state": issue.state,
                "author": issue.user.login if issue.user else "unknown",
                "created_at": issue.created_at.isoformat() if issue.created_at else None,
                "updated_at": issue.updated_at.isoformat() if issue.updated_at else None,
                "url": issue.html_url,
                "labels": [label.name for label in issue.labels],
                "comments_count": issue.comments,
                "comments": []
            }
            
            # Fetch comments for this issue
            if issue.comments > 0:
                print(f"  📝 Fetching {issue.comments} comments for issue #{issue.number}")
                for comment in issue.get_comments():
                    comment_data = {
                        "id": comment.id,
                        "body": comment.body,
                        "author": comment.user.login if comment.user else "unknown",
                        "created_at": comment.created_at.isoformat() if comment.created_at else None,
                        "updated_at": comment.updated_at.isoformat() if comment.updated_at else None,
                        "url": comment.html_url
                    }
                    issue_data["comments"].append(comment_data)
            
            issues_data.append(issue_data)
        
        print(f"✅ Fetched {len(issues_data)} issues")
        return issues_data
    
    def fetch_pull_requests(self, repo: Repository.Repository, state: str = "all") -> List[Dict[str, Any]]:
        """Fetch all pull requests from repository"""
        print(f"📥 Fetching pull requests (state: {state})...")
        
        prs_data = []
        pulls = repo.get_pulls(state=state, sort="updated", direction="desc")
        
        for pr in pulls:
            pr_data = {
                "id": pr.id,
                "number": pr.number,
                "title": pr.title,
                "body": pr.body or "",
                "state": pr.state,
                "author": pr.user.login if pr.user else "unknown",
                "created_at": pr.created_at.isoformat() if pr.created_at else None,
                "updated_at": pr.updated_at.isoformat() if pr.updated_at else None,
                "merged_at": pr.merged_at.isoformat() if pr.merged_at else None,
                "url": pr.html_url,
                "base_branch": pr.base.ref,
                "head_branch": pr.head.ref,
                "comments_count": pr.comments,
                "review_comments_count": pr.review_comments,
                "comments": []
            }
            
            # Fetch issue comments (general PR comments)
            if pr.comments > 0:
                print(f"  💬 Fetching {pr.comments} comments for PR #{pr.number}")
                for comment in pr.get_issue_comments():
                    comment_data = {
                        "id": comment.id,
                        "type": "issue_comment",
                        "body": comment.body,
                        "author": comment.user.login if comment.user else "unknown",
                        "created_at": comment.created_at.isoformat() if comment.created_at else None,
                        "updated_at": comment.updated_at.isoformat() if comment.updated_at else None,
                        "url": comment.html_url
                    }
                    pr_data["comments"].append(comment_data)
            
            # Fetch review comments (code-specific comments)
            if pr.review_comments > 0:
                print(f"  🔍 Fetching {pr.review_comments} review comments for PR #{pr.number}")
                for comment in pr.get_review_comments():
                    comment_data = {
                        "id": comment.id,
                        "type": "review_comment",
                        "body": comment.body,
                        "author": comment.user.login if comment.user else "unknown",
                        "created_at": comment.created_at.isoformat() if comment.created_at else None,
                        "updated_at": comment.updated_at.isoformat() if comment.updated_at else None,
                        "url": comment.html_url,
                        "path": comment.path,
                        "line": getattr(comment, 'position', None) or getattr(comment, 'original_position', None)
                    }
                    pr_data["comments"].append(comment_data)
            
            prs_data.append(pr_data)
        
        print(f"✅ Fetched {len(prs_data)} pull requests")
        return prs_data
    
    def save_data(self, data: Dict[str, Any], filename: str) -> str:
        """Save data to JSON file in raw data directory"""
        os.makedirs(settings.RAW_DATA_PATH, exist_ok=True)
        filepath = os.path.join(settings.RAW_DATA_PATH, filename)
        
        # Add metadata
        data_with_metadata = {
            "metadata": {
                "fetched_at": datetime.now().isoformat(),
                "source": "github",
                "rate_limit": self.rate_limit_info
            },
            "data": data
        }
        
        with open(filepath, 'w', encoding='utf-8') as f:
            json.dump(data_with_metadata, f, indent=2, ensure_ascii=False)
        
        print(f"💾 Saved data to {filepath}")
        return filepath
    
    def fetch_repository_data(self, repo_name: str) -> Dict[str, str]:
        """Fetch all data from a repository and save to files"""
        print(f"🚀 Starting data fetch for repository: {repo_name}")
        
        # Check rate limit
        rate_limit = self.check_rate_limit()
        print(f"📊 Rate limit - Core: {rate_limit['core']['remaining']}/{rate_limit['core']['limit']}")
        
        repo = self.get_repository(repo_name)
        
        # Generate timestamp for file naming
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        repo_safe_name = repo_name.replace("/", "_")
        
        # Fetch and save issues
        issues = self.fetch_issues(repo)
        issues_file = self.save_data(
            {"repository": repo_name, "issues": issues},
            f"github_issues_{repo_safe_name}_{timestamp}.json"
        )
        
        # Fetch and save pull requests
        prs = self.fetch_pull_requests(repo)
        prs_file = self.save_data(
            {"repository": repo_name, "pull_requests": prs},
            f"github_prs_{repo_safe_name}_{timestamp}.json"
        )
        
        print(f"🎉 Completed data fetch for {repo_name}")
        print(f"📈 Summary: {len(issues)} issues, {len(prs)} pull requests")
        
        return {
            "issues_file": issues_file,
            "prs_file": prs_file
        }

def main():
    """Main function for testing the GitHub connector"""
    try:
        connector = GitHubConnector()
        
        # Use repository from settings or prompt user
        repo_name = settings.GITHUB_REPO
        if not repo_name:
            repo_name = input("Enter GitHub repository (format: owner/repo): ").strip()
        
        if not repo_name:
            print("❌ No repository specified")
            return
        
        # Fetch data
        files = connector.fetch_repository_data(repo_name)
        print(f"\n✅ Data ingestion complete!")
        print(f"📁 Files saved:")
        for file_type, filepath in files.items():
            print(f"  - {file_type}: {filepath}")
        
    except Exception as e:
        print(f"❌ Error: {str(e)}")

if __name__ == "__main__":
    main()
