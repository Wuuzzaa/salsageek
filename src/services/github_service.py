import os
import time
import yaml
try:
    from github import Github, GithubException
except ImportError:
    Github = None
    GithubException = Exception
from pathlib import Path
from typing import Optional, Dict, Any, List

class GithubService:
    """
    Service for interacting with GitHub to create PRs for new elements.
    """
    def __init__(self, token: Optional[str] = None, repo_name: Optional[str] = None):
        self.token = token or os.environ.get("GITHUB_TOKEN")
        self.repo_name = repo_name or os.environ.get("GITHUB_REPO")
        self.gh = Github(self.token) if (self.token and Github) else None

    def is_configured(self) -> bool:
        if not Github:
            print("GithubService: PyGithub ist nicht installiert.")
            return False
        if not self.token:
            print("GithubService: GITHUB_TOKEN fehlt.")
        if not self.repo_name:
            print("GithubService: GITHUB_REPO fehlt.")
        return bool(self.gh and self.repo_name)

    def create_pull_request_for_element(self, element_id: str, element_data: Dict[str, Any]) -> Optional[str]:
        """
        Creates a new branch, commits the element YAML, and opens a PR.
        Returns the PR URL if successful, else None.
        """
        if not self.is_configured():
            print("GithubService: Not configured (GITHUB_TOKEN or GITHUB_REPO missing).")
            return None

        try:
            repo = self.gh.get_repo(self.repo_name)
            main_branch = repo.get_branch(repo.default_branch)
            
            # Create a unique branch name
            timestamp = int(time.time())
            branch_name = f"add-element-{element_id}-{timestamp}"
            
            # Create branch from main
            repo.create_git_ref(ref=f"refs/heads/{branch_name}", sha=main_branch.commit.sha)
            
            # Prepare file path and content
            file_path = f"data/custom_elements/{element_id}.yaml"
            yaml_content = yaml.dump({"elements": [element_data]}, allow_unicode=True, sort_keys=False)
            
            # Create/Update file in the new branch
            commit_message = f"Add new salsa element: {element_data.get('name', element_id)}"
            
            # Check if file exists to get SHA for update (though usually new)
            sha = None
            try:
                contents = repo.get_contents(file_path, ref=branch_name)
                sha = contents.sha
            except GithubException:
                pass # File doesn't exist yet

            if sha:
                repo.update_file(file_path, commit_message, yaml_content, sha, branch=branch_name)
            else:
                repo.create_file(file_path, commit_message, yaml_content, branch=branch_name)
                
            # Create Pull Request
            pr_title = f"New Salsa Element: {element_data.get('name', element_id)}"
            pr_body = f"Automatic PR created for a new salsa element added via the web editor.\n\nElement ID: {element_id}"
            
            pr = repo.create_pull(
                title=pr_title,
                body=pr_body,
                head=branch_name,
                base=repo.default_branch
            )
            
            return pr.html_url
            
        except Exception as e:
            print(f"GithubService Error: {e}")
            return None
