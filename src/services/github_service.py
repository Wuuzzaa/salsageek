import os
import time
import yaml
try:
    from github import Github, GithubException, Auth
except ImportError:
    Github = None
    GithubException = Exception
    Auth = None
from pathlib import Path
from typing import Optional, Dict, Any, List

class GithubService:
    """
    Service for interacting with GitHub to create PRs for new elements.
    """
    def __init__(self, token: Optional[str] = None, repo_name: Optional[str] = None):
        self.token = token or os.environ.get("GITHUB_TOKEN")
        self.repo_name = repo_name or os.environ.get("GITHUB_REPO")
        
        # New Auth style for PyGithub 2.x, fallback to old style for older versions
        auth = None
        if self.token and Auth:
            try:
                auth = Auth.Token(self.token)
            except Exception:
                auth = self.token
        else:
            auth = self.token
            
        self.gh = Github(auth=auth) if (auth and Github) else None

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
        file_path = f"data/elements/{element_id}.yaml"
        yaml_content = yaml.dump({"elements": [element_data]}, allow_unicode=True, sort_keys=False)
        commit_message = f"Add new salsa element: {element_data.get('name', element_id)}"
        pr_title = f"New Salsa Element: {element_data.get('name', element_id)}"
        pr_body = f"Automatic PR created for a new salsa element added via the web editor.\n\nElement ID: {element_id}"
        
        return self._create_pull_request(
            file_path=file_path,
            yaml_content=yaml_content,
            commit_message=commit_message,
            pr_title=pr_title,
            pr_body=pr_body,
            branch_prefix=f"add-element-{element_id}"
        )

    def create_pull_request_for_figure(self, figure_id: str, figure_data: Dict[str, Any]) -> Optional[str]:
        """
        Creates a new branch, commits the figure YAML, and opens a PR.
        Returns the PR URL if successful, else None.
        """
        file_path = f"data/figures/{figure_id}.yaml"
        yaml_content = yaml.dump({"figures": [figure_data]}, allow_unicode=True, sort_keys=False)
        commit_message = f"Add new salsa figure: {figure_data.get('name', figure_id)}"
        pr_title = f"New Salsa Figure: {figure_data.get('name', figure_id)}"
        pr_body = f"Automatic PR created for a new salsa figure added via the builder.\n\nFigure ID: {figure_id}"
        
        return self._create_pull_request(
            file_path=file_path,
            yaml_content=yaml_content,
            commit_message=commit_message,
            pr_title=pr_title,
            pr_body=pr_body,
            branch_prefix=f"add-figure-{figure_id}"
        )

    def _create_pull_request(self, file_path: str, yaml_content: str, commit_message: str, 
                             pr_title: str, pr_body: str, branch_prefix: str) -> Optional[str]:
        """
        Internal generic method to create a PR.
        """
        if not self.is_configured():
            print("GithubService: Not configured (GITHUB_TOKEN or GITHUB_REPO missing).")
            return None

        try:
            repo = self.gh.get_repo(self.repo_name)
            main_branch = repo.get_branch(repo.default_branch)
            
            # Create a unique branch name
            timestamp = int(time.time())
            branch_name = f"{branch_prefix}-{timestamp}"
            
            # Create branch from main
            repo.create_git_ref(ref=f"refs/heads/{branch_name}", sha=main_branch.commit.sha)
            
            # Check if file exists to get SHA for update
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
