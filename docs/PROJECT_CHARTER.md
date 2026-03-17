# PROJECT CHARTER
## LeanAI Platform — Version 2.5
Last updated: 2026-03-11

---

## Purpose
LeanAI Platform is a modular platform for building applications for associations and small organizations.

The platform enables organizations to manage members, events, communication and lightweight commerce in a structured and maintainable way.

LeanAI Platform is designed to support multiple organizations using the same core platform modules.

---

## Owner
- **Name:** Ello van Gelderen
- **Email:** ello.van.gelderen@gmail.com
- **Context:** Software factory helping associations and small businesses gain insight and optimize their operations through AI-assisted development
- **Goal:** Build reusable, professional applications with AI assistance

---

## Core Philosophy
LeanAI Platform follows three guiding principles:

### 1. Simple
Solutions must remain easy to understand, easy to maintain and easy to extend.
Avoid unnecessary abstraction, over-engineering or complex frameworks.

### 2. Stable
Reliability and predictability are more important than rapid change.
New functionality must not destabilize existing modules.

### 3. First Time Right
Features should be designed carefully before implementation.

Agents must:
- think before coding
- validate architecture before implementing
- avoid quick fixes
- avoid rewriting code multiple times

The goal is to produce correct and maintainable solutions the first time, reducing rework and AI token usage.

---

## Target Users
LeanAI Platform is designed for:
- sports clubs and cycling clubs
- hobby organizations and community associations
- small membership organizations
- small businesses (MKB)

---

## Development Workflow
All development follows this workflow — **no steps may be skipped:**

```
Model → PM → Requirement → Architecture → Build → Release
```

1. Model Agent: business exploration, HTML mockups, BACKLOG_INIT.md
2. PM Agent: BACKLOG.md creation and maintenance
3. Requirement definition
4. Architecture validation
5. Implementation + unit tests
6. Release: review, integration tests, security check, deploy + PM update

---

## Agent Model
LeanAI Platform uses 5 agents — lean and focused:

| Agent | Responsibility |
|-------|---------------|
| **Model Agent** | Business intake, value chains, HTML mockups, BACKLOG_INIT.md |
| **PM Agent** | Backlog management, progress monitoring, reporting |
| **Architect Agent** | Requirements, design, orchestration, quality |
| **Builder Agent** | Implementation, frontend, backend, data, unit tests |
| **Release Agent** | Review, integration tests, security, deploy + PM update |

---

## Platform Strategy
LeanAI Platform is a platform with reusable modules, not individual custom applications.

New projects extend the platform instead of creating separate codebases.

The component library (`leanai-components` on GitHub) stores all reusable modules. Before building anything new, check if a module already exists.

---

## AI Development Principles
AI agents are used as engineering assistants, not autonomous developers.

Agents must:
- respect architecture
- keep solutions simple
- produce maintainable code
- generate tests alongside implementation
- never skip workflow steps

AI cost efficiency is an explicit design goal. Clear structure = less context = lower costs.

---

## Current Projects

| Project | Client | Status | Stack | Hosting |
|---------|--------|--------|-------|---------|
| WVAmsterdam | WV Amsterdam | Live | Python + FastAPI | Antagonist |
| WVA Digitaal Clubhuis | WV Amsterdam | Model phase | Python + FastAPI | Antagonist |
| Aardappelboer App | Farm client | Planned | TBD | TBD |

---

## Long-Term Vision
LeanAI Platform becomes a stable and reusable platform that allows organizations to deploy reliable applications quickly with minimal complexity.
