import os
import requests
import base64
import time
from datetime import datetime, timezone

GITHUB_TOKEN = os.environ["GH_TOKEN"]
ORG = "modeln"
HEADERS = {
    "Authorization": f"token {GITHUB_TOKEN}",
    "Accept": "application/vnd.github.v3+json",
}
REPO_TYPE = "all" # Default: all , Can be one of: all, public, private, forks, sources, member 
WORKFLOW_PATH = ".github/workflows/appsec.yaml"
WORKFLOW_FILE = "appsec.yaml"
DEFAULT_BRANCH = "main"  # Fallback if default_branch not found via API

with open("pr_description.md", "r") as f:
    PR_DESCRIPTION = f.read()

def get_repos():
    url = f"https://api.github.com/orgs/{ORG}/repos?type={REPO_TYPE}&per_page=100"
    repos = []
    while url:
        res = requests.get(url, headers=HEADERS)
        res.raise_for_status()
        repos += res.json()
        url = res.links.get("next", {}).get("url")
    return [r["full_name"] for r in repos]

def get_default_branch(repo):
    url = f"https://api.github.com/repos/{repo}"
    res = requests.get(url, headers=HEADERS)
    res.raise_for_status()
    return res.json().get("default_branch", DEFAULT_BRANCH)

def file_exists(repo, branch):
    url = f"https://api.github.com/repos/{repo}/contents/{WORKFLOW_PATH}?ref={branch}"
    return requests.get(url, headers=HEADERS).status_code == 200

def branch_exists(repo, branch):
    url = f"https://api.github.com/repos/{repo}/git/ref/heads/{branch}"
    return requests.get(url, headers=HEADERS).status_code == 200

def pr_exists(repo, branch):
    url = f"https://api.github.com/repos/{repo}/pulls?head={ORG}:{branch}&state=all"
    res = requests.get(url, headers=HEADERS)
    res.raise_for_status()
    return len(res.json()) > 0

def create_branch(repo, base_branch, new_branch):
    url = f"https://api.github.com/repos/{repo}/git/ref/heads/{base_branch}"
    sha = requests.get(url, headers=HEADERS).json()["object"]["sha"]
    url = f"https://api.github.com/repos/{repo}/git/refs"
    data = {"ref": f"refs/heads/{new_branch}", "sha": sha}
    res = requests.post(url, headers=HEADERS, json=data)
    res.raise_for_status()

def commit_file(repo, branch):
    with open(WORKFLOW_FILE, "rb") as f:
        content = base64.b64encode(f.read()).decode()
    url = f"https://api.github.com/repos/{repo}/contents/{WORKFLOW_PATH}"
    data = {
        "message": "Add AppSec workflow",
        "content": content,
        "branch": branch,
    }
    res = requests.put(url, headers=HEADERS, json=data)
    res.raise_for_status()

def create_pr(repo, head, base):
    url = f"https://api.github.com/repos/{repo}/pulls"
    data = {
        "title": "Add AppSec GitHub Workflow",
        "head": head,
        "base": base,
        "body": PR_DESCRIPTION,
    }
    res = requests.post(url, headers=HEADERS, json=data)
    res.raise_for_status()
    print(f"PR created: {repo} -> {head}")

def generate_unique_branch(base_name="add-appsec-workflow"):
    timestamp = datetime.now(timezone.utc).strftime("%Y%m%d%H%M%S")
    return f"{base_name}-{timestamp}"

def onboard_repo(repo, single_repo_mode=False):
    default_branch = get_default_branch(repo)
    base_branch = "add-appsec-workflow"

    if file_exists(repo, default_branch):
        print(f"[{repo}] Workflow already exists. Skipping.")
        return

    if not branch_exists(repo, base_branch):
        branch_to_use = base_branch
        create_branch(repo, default_branch, branch_to_use)

    else:
        if pr_exists(repo, base_branch):
            if single_repo_mode:
                branch_to_use = generate_unique_branch()
                create_branch(repo, default_branch, branch_to_use)
            else:
                print(f"[{repo}] PR already exists for base branch. Skipping.")
                return
        else:
            branch_to_use = base_branch

    commit_file(repo, branch_to_use)
    create_pr(repo, branch_to_use, default_branch)


def main():
    input_repo = os.environ.get("REPO_NAME")
    if input_repo == None:
        print("Input is missing..")
        return
    if input_repo.lower() != "all":
        onboard_repo(input_repo, single_repo_mode=True)
    else:
        for repo in get_repos():
            try:
                onboard_repo(repo, single_repo_mode=False)
            except Exception as e:
                print(f"Failed for {repo}: {e}")

if __name__ == "__main__":
    main()
