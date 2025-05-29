## 🔒 AppSec GitHub Workflow
 
This PR introduces the **AppSec Scans** GitHub Actions workflow that will run security scans on code changes.
 
---
 
### 📌 Developer Instructions
 
Update the workflow file (`.github/workflows/appsec.yaml`) to include your branch patterns under `push` and `pull_request` specific to your workflow:
 
```yaml
on:
  push:
    branches: [ "main", "release/*", "your-protected-branch" ]
  pull_request:
    branches: [ "main", "release/*", "your-protected-branch" ]
