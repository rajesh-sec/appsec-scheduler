import os
import base64
import requests
 
def create_appsec_pr():
    github_token = os.getenv("GH_TOKEN")
    repo = "appsec-scans/cxone-demo-1"
    base_branch = "main"
    new_branch = "add-appsec-workflow"
 
    headers = {
        "Authorization": f"Bearer {github_token}",
        "Accept": "application/vnd.github+json"
    }
 
    api_base = "https://api.github.com"
 
    # Get latest commit SHA
    r = requests.get(f"{api_base}/repos/{repo}/git/ref/heads/{base_branch}", headers=headers)
    r.raise_for_status()
    base_sha = r.json()["object"]["sha"]
 
    # Create new branch
    requests.post(f"{api_base}/repos/{repo}/git/refs", headers=headers, json={
        "ref": f"refs/heads/{new_branch}",
        "sha": base_sha
    })
 
    # Read content
    with open("appsec.yaml", "r") as f:
        workflow_content = f.read()
    with open("pr_description.md", "r") as f:
        pr_body = f.read()
 
    encoded_content = base64.b64encode(workflow_content.encode()).decode()
    workflow_path = ".github/workflows/appsec.yaml"
 
    # Upload workflow file
    r = requests.put(f"{api_base}/repos/{repo}/contents/{workflow_path}", headers=headers, json={
        "message": "Add AppSec GitHub workflow",
        "content": encoded_content,
        "branch": new_branch
    })
    r.raise_for_status()
 
    # Create PR
    r = requests.post(f"{api_base}/repos/{repo}/pulls", headers=headers, json={
        "title": "Add AppSec Workflow",
        "head": new_branch,
        "base": base_branch,
        "body": pr_body
    })
    r.raise_for_status()
 
    print("✅ Pull request created:", r.json()["html_url"])
 
if __name__ == "__main__":
    create_appsec_pr()
