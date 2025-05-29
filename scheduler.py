import json
import os
import requests

# Load GitHub Token from environment
GITHUB_TOKEN = os.environ.get("GITHUB_TOKEN")
if not GITHUB_TOKEN:
    raise EnvironmentError("GITHUB_TOKEN not found in environment variables.")

# Identify event type (scheduled vs. manual dispatch)
GITHUB_EVENT_NAME = os.environ.get("GITHUB_EVENT_NAME", "")

EVENT_TYPE = "scheduler"
HEADERS = {
    "Content-Type": "application/json",
    "Authorization": f"Bearer {GITHUB_TOKEN}",
    "Accept": "application/vnd.github+json"
}

SCAN_FILE = "scan_results.json"

# Load previous scan results
if os.path.exists(SCAN_FILE):
    with open(SCAN_FILE, "r") as f:
        previous_results = json.load(f)
else:
    previous_results = {}

# New scan result object
scan_results = {}

# Read schedule_list.json
with open("schedule_list.json", "r") as file:
    schedule_list = json.load(file)

# Prepare markdown table header
summary_lines = [
    "## 🚀 Scheduler Summary\n",
    "| Repository | Branch | Status | Details |",
    "|------------|--------|--------|---------|"
]

for item in schedule_list:
    repo_name = item["repo_name"]
    branch = item["branch"]
    key = f"{repo_name}@{branch}"

    should_trigger = True
    # If this is a manual run and previous run succeeded, skip
    if GITHUB_EVENT_NAME == "workflow_dispatch":
        previous = previous_results.get(key)
        if previous and previous.get("status") == "success":
            should_trigger = False
            summary_lines.append(
                f"| `{repo_name}` | `{branch}` | ✅ Skipped | 💥 Previously successful |"
            )

    if not should_trigger:
        continue

    url = f"https://api.github.com/repos/{repo_name}/dispatches"
    payload = {
        "event_type": EVENT_TYPE,
        "client_payload": {"branch": branch}
    }

    response = requests.post(url, headers=HEADERS, json=payload)
    if response.status_code == 204:
        previous_results[key] = {"status": "success"}
        summary_lines.append(
            f"| `{repo_name}` | `{branch}` | ✅ Success | 🚀 Triggered |"
        )
    else:
        error_detail = response.text.strip().replace('\n', ' ')
        previous_results[key] = {"status": "failed", "error": error_detail}
        summary_lines.append(
            f"| `{repo_name}` | `{branch}` | ❌ Failed ({response.status_code}) | `{error_detail}` |"
        )

# Define the sorting key function
def sort_key(line):
    if "Success" in line or "Failed" in line:
        priority = 0
    else:
        priority = 1
    # You could extract repo name to sort alphabetically within priority
    repo = line.split('|')[1].strip()
    return (priority, repo)

# Save current scan results
with open(SCAN_FILE, "w") as f:
    json.dump(previous_results, f, indent=2)


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
