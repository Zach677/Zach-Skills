# Bootstrap Tuist Mobile Project Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Build a reusable `bootstrap-tuist-mobile-project` skill in `Zach-Skills` that interviews the user, creates a new local or GitHub-backed mobile project from a public Tuist template, initializes project-specific names and IDs through a CLI, and optionally wires Tuist Cloud plus Xcode cache.

**Architecture:** The system is split into three layers. Public template repos hold the source skeletons and placeholders. `bin/zach-mobile-init` is a deterministic initializer that materializes one chosen template with concrete project values. The `bootstrap-tuist-mobile-project` skill is a thin orchestrator that detects capabilities, asks questions, requires confirmation before side effects, and invokes GitHub, Tuist, and the initializer in the right order.

**Tech Stack:** Python 3 stdlib (`argparse`, `dataclasses`, `json`, `pathlib`, `re`, `shutil`, `subprocess`, `tempfile`, `textwrap`, `unittest`), Git, GitHub CLI, Tuist CLI, `mise`

---

### Task 1: Scaffold The Bootstrap Skill Shell

**Files:**
- Create: `/Users/star/Developer/zach-repo/Zach-Skills/skills/bootstrap-tuist-mobile-project/SKILL.md`
- Create: `/Users/star/Developer/zach-repo/Zach-Skills/skills/bootstrap-tuist-mobile-project/README.md`
- Create: `/Users/star/Developer/zach-repo/Zach-Skills/skills/bootstrap-tuist-mobile-project/references/flow.md`
- Create: `/Users/star/Developer/zach-repo/Zach-Skills/skills/bootstrap-tuist-mobile-project/scripts/bootstrap_mobile_project.py`
- Create: `/Users/star/Developer/zach-repo/Zach-Skills/skills/bootstrap-tuist-mobile-project/agents/openai.yaml`
- Modify: `/Users/star/Developer/zach-repo/Zach-Skills/README.md`

- [ ] **Step 1: Scaffold the new skill directory**

Run:

```bash
cd /Users/star/Developer/zach-repo/Zach-Skills
python3 scripts/new_skill.py "Bootstrap Tuist Mobile Project" \
  --description "Use when creating a new Tuist iOS or iOS plus Catalyst project from a public template with interactive setup." \
  --with-agent
```

Expected: `skills/bootstrap-tuist-mobile-project/` exists with scaffold files.

- [ ] **Step 2: Verify the scaffold output before rewriting it**

Run:

```bash
find /Users/star/Developer/zach-repo/Zach-Skills/skills/bootstrap-tuist-mobile-project -maxdepth 3 -type f | sort
```

Expected: scaffolded `SKILL.md`, `README.md`, optional `agents/openai.yaml`, and reference/script placeholders are present.

- [ ] **Step 3: Rewrite the skill shell to match the approved architecture**

Document:

- trigger conditions
- capability detection requirements
- confirmation rules
- mode selection flow
- invocation of `bin/zach-mobile-init`
- no-silent-downgrade guardrail

The skill body should treat the CLI as the deterministic executor and keep the skill focused on orchestration only.

- [ ] **Step 4: Add a root README entry for the new skill**

Add one row that explains that `bootstrap-tuist-mobile-project` creates local-only, GitHub-backed, or Tuist-Cloud-backed mobile projects from public templates.

- [ ] **Step 5: Commit the skill-shell slice**

Run:

```bash
cd /Users/star/Developer/zach-repo/Zach-Skills
git add README.md skills/bootstrap-tuist-mobile-project
git commit -m "feat: scaffold mobile project bootstrap skill"
```

Expected: one commit containing only the new skill shell plus root README update.

### Task 2: Implement The Shared Initializer CLI

**Files:**
- Create: `/Users/star/Developer/zach-repo/Zach-Skills/bin/zach-mobile-init`
- Create: `/Users/star/Developer/zach-repo/Zach-Skills/tests/test_zach_mobile_init.py`
- Modify: `/Users/star/Developer/zach-repo/Zach-Skills/skills/bootstrap-tuist-mobile-project/scripts/bootstrap_mobile_project.py`
- Modify: `/Users/star/Developer/zach-repo/Zach-Skills/skills/bootstrap-tuist-mobile-project/README.md`
- Modify: `/Users/star/Developer/zach-repo/Zach-Skills/skills/bootstrap-tuist-mobile-project/references/flow.md`

- [ ] **Step 1: Write failing tests for config parsing and placeholder replacement**

Add tests for:

- loading a JSON config file
- validating required fields
- rejecting unknown template names
- replacing placeholders in text files
- renaming project and workspace filenames
- normalizing executable bits on generated shell scripts
- failing when placeholders remain unresolved

Use temp directories and fake template contents such as:

```text
__PROJECT_NAME__
__BUNDLE_ID__
__FULL_HANDLE__
```

- [ ] **Step 2: Run the initializer tests and confirm they fail**

Run:

```bash
cd /Users/star/Developer/zach-repo/Zach-Skills
python3 -m unittest tests.test_zach_mobile_init -q
```

Expected: FAIL because `bin/zach-mobile-init` does not exist yet.

- [ ] **Step 3: Implement the minimal initializer**

Create `bin/zach-mobile-init` as a Python entrypoint with:

- `--config <path>`
- strict JSON validation
- template directory copy
- placeholder replacement
- file and directory renames
- executable permission normalization
- unresolved-placeholder detection

Keep the remote-resource logic out of this CLI.

- [ ] **Step 4: Re-run the initializer tests and make them pass**

Run:

```bash
cd /Users/star/Developer/zach-repo/Zach-Skills
python3 -m unittest tests.test_zach_mobile_init -q
```

Expected: PASS.

- [ ] **Step 5: Commit the initializer slice**

Run:

```bash
cd /Users/star/Developer/zach-repo/Zach-Skills
git add bin/zach-mobile-init tests/test_zach_mobile_init.py \
  skills/bootstrap-tuist-mobile-project/scripts/bootstrap_mobile_project.py \
  skills/bootstrap-tuist-mobile-project/README.md \
  skills/bootstrap-tuist-mobile-project/references/flow.md
git commit -m "feat: add mobile project initializer cli"
```

Expected: one commit for the CLI and its tests.

### Task 3: Create The Pure iOS Public Template Repository

**Files:**
- Create repo: `tuist-ios-starter` on GitHub
- Create in repo: `Project.swift`
- Create in repo: `Tuist.swift`
- Create in repo: `Workspace.swift` if needed
- Create in repo: `mise.toml`
- Create in repo: `.codex/environments/environment.toml`
- Create in repo: `.gitignore`
- Create in repo: `AGENTS.md`
- Create in repo: `README.md`
- Create in repo: `scripts/tuist-common.sh`
- Create in repo: `scripts/run-ios-sim.sh`
- Create in repo: `scripts/build-ios-sim.sh`
- Create in repo: `scripts/test-ios.sh`
- Create in repo: `scripts/share-ios-preview.sh`
- Create in repo: `scripts/warm-external-cache.sh`

- [ ] **Step 1: Create the template repo and mark it as a template**

Run:

```bash
gh repo create <owner>/tuist-ios-starter --public --clone --template=false
```

Then enable the GitHub template-repository setting manually or through the GitHub UI/API.

Expected: local repo exists and is empty except for base Git metadata.

- [ ] **Step 2: Add the placeholder-based iOS project skeleton**

Use the approved placeholder set:

- `__PROJECT_NAME__`
- `__PROJECT_NAME_LOWER__`
- `__REPO_NAME__`
- `__BUNDLE_ID__`
- `__FULL_HANDLE__`
- `__IOS_SIMULATOR_DEVICE__`
- `__APP_SCHEME__`
- `__TEST_SCHEME__`
- `__CACHE_SERVICE_SLUG__`

All generated scripts should already match the Kigen-style workflow:

- `warm-external-cache`
- `run-ios-sim`
- `build-ios-sim`
- `test-ios`
- `share-ios-preview`

- [ ] **Step 3: Add template README guidance**

Document:

- what the template includes
- that users should run the initializer instead of hand-editing placeholders
- how the template is intended to be consumed by the bootstrap skill

- [ ] **Step 4: Run a placeholder integrity check**

Run:

```bash
rg -n "__[A-Z0-9_]+__" /path/to/tuist-ios-starter
```

Expected: placeholders only exist where intentional and there are no stray real project names.

- [ ] **Step 5: Commit the iOS template**

Run:

```bash
git add .
git commit -m "feat: add pure iOS Tuist starter template"
```

Expected: one commit containing the full template skeleton.

### Task 4: Create The iOS Plus Catalyst Public Template Repository

**Files:**
- Create repo: `tuist-ios-catalyst-starter` on GitHub
- Create all pure iOS template files plus:
- Create in repo: `scripts/run-macos.sh`
- Create in repo: `scripts/test-macos.sh`

- [ ] **Step 1: Create the Catalyst template repo**

Run:

```bash
gh repo create <owner>/tuist-ios-catalyst-starter --public --clone --template=false
```

Expected: local repo exists and is ready for template content.

- [ ] **Step 2: Materialize the dual-platform skeleton**

Use the same placeholder vocabulary as the iOS template, but include:

- Catalyst run task
- Catalyst test task
- dual-platform Codex actions
- AGENTS guidance for both `run-macos` and `run-ios-sim`

- [ ] **Step 3: Verify the template can express both iOS and Catalyst flows without hard-coded names**

Run:

```bash
rg -n "SubPanda|Kigen|mitori|zach/" /path/to/tuist-ios-catalyst-starter
```

Expected: no leaked real project names or real handles remain.

- [ ] **Step 4: Commit the Catalyst template**

Run:

```bash
git add .
git commit -m "feat: add iOS Catalyst Tuist starter template"
```

Expected: one commit for the full Catalyst template skeleton.

### Task 5: Add The Skill Orchestrator Logic

**Files:**
- Modify: `/Users/star/Developer/zach-repo/Zach-Skills/skills/bootstrap-tuist-mobile-project/SKILL.md`
- Modify: `/Users/star/Developer/zach-repo/Zach-Skills/skills/bootstrap-tuist-mobile-project/scripts/bootstrap_mobile_project.py`
- Create: `/Users/star/Developer/zach-repo/Zach-Skills/tests/test_bootstrap_mobile_project.py`
- Modify: `/Users/star/Developer/zach-repo/Zach-Skills/skills/bootstrap-tuist-mobile-project/agents/openai.yaml`

- [ ] **Step 1: Write failing tests for capability detection and mode selection**

Add tests for:

- capability matrix generation
- blocked-mode messaging
- no-silent-downgrade behavior
- confirmation requirement before repo creation
- confirmation requirement before Tuist Cloud/cache setup
- handoff payload generation for `zach-mobile-init`

- [ ] **Step 2: Run the orchestrator tests and confirm they fail**

Run:

```bash
cd /Users/star/Developer/zach-repo/Zach-Skills
python3 -m unittest tests.test_bootstrap_mobile_project -q
```

Expected: FAIL because the orchestrator logic does not yet implement the tested flow.

- [ ] **Step 3: Implement capability detection and config assembly**

The orchestrator script should expose helpers for:

- `git` detection
- `gh` detection
- `gh auth status`
- `mise` detection
- `tuist` detection
- `tuist auth whoami`

It should also produce the exact JSON config payload expected by `zach-mobile-init`.

- [ ] **Step 4: Update the skill docs to match the executable flow**

Make sure the skill doc explicitly states:

- it asks first
- it never silently downgrades
- it can create local-only, GitHub-backed, or Tuist-Cloud-backed projects
- it calls `zach-mobile-init`

- [ ] **Step 5: Re-run orchestrator tests and make them pass**

Run:

```bash
cd /Users/star/Developer/zach-repo/Zach-Skills
python3 -m unittest tests.test_bootstrap_mobile_project -q
```

Expected: PASS.

- [ ] **Step 6: Commit the orchestration slice**

Run:

```bash
cd /Users/star/Developer/zach-repo/Zach-Skills
git add skills/bootstrap-tuist-mobile-project tests/test_bootstrap_mobile_project.py
git commit -m "feat: add mobile project bootstrap orchestration"
```

Expected: one commit covering the interactive orchestration logic.

### Task 6: Wire Real Side Effects Carefully

**Files:**
- Modify: `/Users/star/Developer/zach-repo/Zach-Skills/skills/bootstrap-tuist-mobile-project/scripts/bootstrap_mobile_project.py`
- Modify: `/Users/star/Developer/zach-repo/Zach-Skills/tests/test_bootstrap_mobile_project.py`
- Modify: `/Users/star/Developer/zach-repo/Zach-Skills/skills/bootstrap-tuist-mobile-project/README.md`

- [ ] **Step 1: Write failing tests for side-effect sequencing**

Cover these sequences:

- local-only
- github-backed
- github-and-tuist-cloud

Validate that:

- GitHub repo creation only happens after explicit confirmation
- `tuist project create` only happens when chosen
- `tuist setup cache` only happens when chosen
- `git push` only happens when chosen

- [ ] **Step 2: Run the tests and confirm the side-effect cases fail**

Run:

```bash
cd /Users/star/Developer/zach-repo/Zach-Skills
python3 -m unittest tests.test_bootstrap_mobile_project -q
```

Expected: FAIL on side-effect sequencing assertions.

- [ ] **Step 3: Implement the side-effect execution layer**

Add wrappers for:

- `gh repo create`
- `git init` or clone setup
- `tuist project create`
- `tuist setup cache`
- `mise run warm-external-cache`
- `git add`
- `git commit`
- `git push`

Keep each step explicit and tied to the confirmed mode.

- [ ] **Step 4: Re-run the test suite and make it green**

Run:

```bash
cd /Users/star/Developer/zach-repo/Zach-Skills
python3 -m unittest discover -s tests -q
```

Expected: PASS.

- [ ] **Step 5: Commit the side-effect integration**

Run:

```bash
cd /Users/star/Developer/zach-repo/Zach-Skills
git add skills/bootstrap-tuist-mobile-project tests
git commit -m "feat: wire mobile bootstrap side effects"
```

Expected: one commit for the remote and local execution flow.

### Task 7: End-To-End Manual Validation

**Files:**
- Modify if needed: `/Users/star/Developer/zach-repo/Zach-Skills/skills/bootstrap-tuist-mobile-project/README.md`
- Modify if needed: `/Users/star/Developer/zach-repo/Zach-Skills/skills/bootstrap-tuist-mobile-project/references/flow.md`

- [ ] **Step 1: Dry-run local-only creation**

Use a temporary destination and verify the generated project has:

- correct names
- correct bundle IDs
- correct Codex actions
- no unresolved placeholders

- [ ] **Step 2: Dry-run GitHub-backed creation**

Use a temporary test repo name and confirm:

- explicit confirmations are requested
- local repo and remote wiring are correct
- no silent downgrade happens when an optional capability is missing

- [ ] **Step 3: Dry-run GitHub plus Tuist Cloud creation**

Confirm:

- `fullHandle` lands in `Tuist.swift`
- `tuist setup cache` produces the expected build settings
- `mise run warm-external-cache` completes

- [ ] **Step 4: Update docs for any validation findings**

If the manual validation reveals friction, update the skill README and `references/flow.md` so the actual user flow matches reality.

- [ ] **Step 5: Commit the validation and doc-polish slice**

Run:

```bash
cd /Users/star/Developer/zach-repo/Zach-Skills
git add skills/bootstrap-tuist-mobile-project
git commit -m "docs: polish mobile bootstrap flow"
```

Expected: one small documentation-only commit after manual validation.
