# Contributing to {{PROJECT_NAME}}

This document explains how to contribute to {{PROJECT_NAME}}. It applies
to discussions, issues, and pull requests. If you plan to make code changes,
also read [Developing {{PROJECT_NAME}}](HACKING.md).

> [!NOTE]
>
> Please read this before opening a contribution. {{PROJECT_NAME}} is
> maintained by people with limited review time, so the process below keeps
> issues actionable and keeps reviews focused on work that is ready to land.

## The Critical Rule

**You must understand your contribution.** If you cannot explain what your
change does, why it is correct, and how it affects the rest of the project
without relying on an AI tool to answer for you, do not submit it.

AI assistance is allowed only when there is a real human in the loop. Read
the [AI Usage Policy](AI_POLICY.md) before opening any contribution.

## AI Usage

{{PROJECT_NAME}} has strict AI usage rules. See the
[AI Usage Policy](AI_POLICY.md). This policy is part of the contribution
process, not optional background reading.

## First-Time Contributors

First-time contributors must be vouched before opening pull requests:

1. Open a
   [Vouch Request](https://github.com/{{OWNER}}/{{REPO}}/discussions/new?category={{VOUCH_REQUEST_CATEGORY_SLUG}})
   discussion describing what you want to change and why.
2. Keep the request concise.
3. Write it in your own voice. Do not ask AI to write it for you.
4. A maintainer will comment `!vouch` if the request is approved.
5. After approval, you may open pull requests.

If you are not vouched, pull requests you open may be closed automatically.
This exists because modern AI tools make it too easy to create plausible
looking contributions that the author does not understand.

## Contributors Prior to the Vouch System

If you contributed before this vouch system was introduced and want to keep
contributing, check whether your handle is listed in
[`.github/VOUCHED.td`](.github/VOUCHED.td). If it is not listed, use the same
Vouch Request process as any other first-time contributor.

## Denouncement System

Contributors who repeatedly ignore this document, submit low-quality work, or
abuse AI assistance may be denounced. A denounced user is added to the public
vouch list with a negative entry, and future issues or pull requests from that
account may be closed automatically.

The denouncement list is public so other projects can choose to reuse it if
they trust this project's maintainer judgment.

## Quick Guide

### I'd like to contribute

[All issues are actionable](#issues-are-actionable). Pick an open issue and
work from the scope described there. If you need clarification, comment on
the issue. Issues labeled
["contributor friendly"](https://github.com/{{OWNER}}/{{REPO}}/issues?q=is%3Aissue%20is%3Aopen%20label%3A%22contributor%20friendly%22)
are expected to be approachable for new contributors.

<!--
### I'd like to translate {{PROJECT_NAME}} to my language

Translation guidance is intentionally commented out for template projects.
When this project needs translations, replace this block with a translator
guide link and explain whether translation pull requests bypass normal issue
triage.
-->

### I have a bug or something is not working

Search open and closed issues first, then search discussions. If your report
has not already been covered, open an
[Issue Triage](https://github.com/{{OWNER}}/{{REPO}}/discussions/new?category={{ISSUE_TRIAGE_CATEGORY_SLUG}})
discussion and fill in the template completely.

Please do not open a GitHub issue directly. Issues are created only after a
discussion has become actionable.

### I have an idea for a feature

Search issues and discussions first. If the idea has not already been raised,
open a
[Feature Request](https://github.com/{{OWNER}}/{{REPO}}/discussions/new?category={{FEATURE_REQUEST_CATEGORY_SLUG}})
discussion. Feature design belongs in discussions, not in pull requests.

### I've implemented a feature

1. If there is an accepted issue for the feature, open a pull request that
   implements that issue.
2. If there is not an accepted issue, open a discussion and link to your
   branch or prototype.
3. Pull requests for undiscussed features may be closed or left stale.

### I have a question

Open a
[Q&A discussion](https://github.com/{{OWNER}}/{{REPO}}/discussions/new?category={{QA_CATEGORY_SLUG}})
unless the question is really a bug report or feature request. Use the Issue
Triage or Feature Request categories for those.

## General Patterns

### Issues are Actionable

The issue tracker is for work that is already understood and ready to be
implemented. General discussion, support, and feature design happen in GitHub
Discussions first. When a discussion reaches a clear actionable outcome, a
maintainer can move it into the issue tracker.

This keeps every open issue useful for contributors looking for work.

### Pull Requests Implement Accepted Issues

Pull requests should implement a previously accepted issue. If you open a
pull request for work that has not been discussed and accepted, it may be
closed or remain stale.

Pull requests are not the place to design a feature. Use a discussion for
design work, then open a pull request after the scope is accepted.
