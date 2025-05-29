import os
import requests
import base64
import time
from datetime import datetime, timezone

GITHUB_TOKEN = os.environ["GH_TOKEN"]
ORG = "appsec-gis"
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

def pr_exists(repo, base_branch, head_branch):
    url = f"https://api.github.com/repos/{repo}/pulls?head={ORG}:{head_branch}&base={base_branch}&state=all"
    res = requests.get(url, headers=HEADERS)
    res.raise_for_status()
    pr_list = res.json()
    return pr_list

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
    head_branch = "add-appsec-workflow"

    if file_exists(repo, default_branch):
        print(f"[{repo}] Workflow already exists. Skipping.")
        summary_lines.append(
            f"| `{repo}` | `{default_branch}` | ✅ Skipped | 💥 appsec.yaml found |"
        )
        return

    if not branch_exists(repo, head_branch):
        branch_to_use = head_branch
        create_branch(repo, default_branch, branch_to_use)

    else:
        prlist = pr_exists(repo, default_branch, head_branch)
        if prlist:
            if single_repo_mode:
                branch_to_use = generate_unique_branch()
                create_branch(repo, default_branch, branch_to_use)
            else:
                print(f"[{repo}] PR already exists for base branch. Skipping.")
                open_pr = False
                closed_pr_number = ''
                pr_number = ''
                for pr in prlist:
                    if pr["state"] == "open":
                        open_pr = True
                        pr_number = pr["number"]
                    if pr["state"] == "closed" and not closed_pr_number:
                        closed_pr_number = pr["number"]

                summary_lines.append(
                    f"| `{repo}` | `{default_branch}` | ✅ Skipped | 💥 {f'Open PR Found:{pr_number}' if open_pr else f'PR already closed:{closed_pr_number}'} |"
                )
                return
        else:
            branch_to_use = head_branch

    commit_file(repo, branch_to_use)
    create_pr(repo, branch_to_use, default_branch)
    summary_lines.append(
        f"| `{repo}` | `{default_branch}` | ✅ Created | PR {'forcefully' if single_repo_mode else ''} Created |"
    )


def main():
    input_repos = os.environ.get("REPO_NAMES")
    single_repo_mode = False
    if input_repos == None:
        print("Input is missing..")
        return
    if input_repos.lower() != "all":
        repos = input_repos.replace(' ', '').split(',')

        if len(repos) == 1:
            single_repo_mode = True
    else:
        repos = get_repos()
    
    for repo in repos:
        try:
            onboard_repo(repo, single_repo_mode=single_repo_mode)
        except Exception as e:
            print(f"Failed for {repo}: {e}")
            summary_lines.append(
                f"| `{repo}` | - | ❌ Exception | {e} |"
            )

# Prepare markdown table header
summary_lines = [
    "## 🚀 Scheduler Summary\n",
    "| Repository | Branch | Status | Details |",
    "|------------|--------|--------|---------|"
]

# Define the sorting key function
def sort_key(line):
    if "Created" in line or "Exception" in line:
        priority = 0
    else:
        priority = 1
    # You could extract repo name to sort alphabetically within priority
    repo = line.split('|')[1].strip()
    return (priority, repo)

if __name__ == "__main__":
    main()
    header = summary_lines[:3]
    data_lines = summary_lines[3:]
    sorted_data = sorted(data_lines, key=sort_key)
    final_summary = header + sorted_data
    # Write markdown summary to GitHub Actions job summary
    summary_path = os.environ.get("GITHUB_STEP_SUMMARY")
    if summary_path:
        with open(summary_path, "w") as summary_file:
            summary_file.write("\n".join(final_summary))
    else:
        print("GITHUB_STEP_SUMMARY not set. Printing summary instead:")
        print("\n".join(final_summary))
