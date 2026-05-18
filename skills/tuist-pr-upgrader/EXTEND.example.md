# Tuist PR Upgrader Preferences
#
# Copy this file to one of:
# - .zach-skills/tuist-pr-upgrader/EXTEND.md
# - ${XDG_CONFIG_HOME:-$HOME/.config}/zach-skills/tuist-pr-upgrader/EXTEND.md
# - ~/.zach-skills/tuist-pr-upgrader/EXTEND.md
#
# Non-secret settings only.
# Keep the fenced `toml` block intact; the runtime reads config from this Markdown file.

```toml
scan_roots = ["/path/to/repos"]
include_repos = []
exclude_repos = []
allow_push = false
allow_pr = false

[repos.mitori]
path = "/path/to/repos/mitori"
verify_commands = ["mise run test-macos"]
base_branch = "main"
```
