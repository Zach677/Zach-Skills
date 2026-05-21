# Vouch GitHub App Permissions

Create a private GitHub App owned by the repo owner or organization.
Webhook delivery is not required because GitHub Actions triggers the
workflows.

## Repository permissions

| Permission | Access | Why |
| ---------- | ------ | --- |
| Metadata | Read-only | Required by GitHub for all apps. |
| Contents | Read and write | Commit `.github/VOUCHED.td` updates. |
| Issues | Read and write | Comment on, close, and lock unvouched issues. |
| Pull requests | Read and write | Create, close, and immediately merge vouch PRs. |
| Discussions | Read and write | Read Vouch Request discussions and approval comments. |

## Installation

- Choose **Only on this account** unless the app must be shared across
  organizations.
- Install only on selected repositories.
- For Zach's default flow, install on the target open-source repo only.

## Repository secrets

Write these secrets into the target repo:

```bash
gh secret set VOUCH_APP_ID --repo OWNER/REPO
gh secret set VOUCH_APP_PRIVATE_KEY --repo OWNER/REPO
```

Do not commit the private key or print it in logs.
