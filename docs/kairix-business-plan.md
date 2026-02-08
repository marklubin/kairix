# KAIRIX

## Operational Learning Infrastructure for Production LLM Systems

---

**CONFIDENTIAL BUSINESS PLAN**

Prepared by: Mark Lubin
Former Senior SDE, Amazon (10 years) | Distributed Systems | Payments Infrastructure | AWS

January 2026

---

## Table of Contents

1. [Executive Summary](#1-executive-summary)
2. [Problem](#2-the-problem)
3. [Solution](#3-the-solution)
4. [Product](#4-product)
5. [Market Opportunity](#5-market-opportunity)
6. [Competitive Landscape](#6-competitive-landscape)
7. [Business Model](#7-business-model)
8. [Go-to-Market Strategy](#8-go-to-market-strategy)
9. [Traction & Validation](#9-traction--validation)
10. [Execution Plan](#10-execution-plan)
11. [Team](#11-team)
12. [Risks & Mitigations](#12-risks--mitigations)
13. [Financial Projections](#13-financial-projections)
14. [The Ask](#14-the-ask)
15. [Appendices](#15-appendices)

---

## 1. Executive Summary

Kairix is **operational learning infrastructure for teams running LLM-powered agents in production**. We are building the routing layer between incident detection and enforcement surfaces -- the missing piece that turns production failures into durable, verified improvements across an organization's entire agent stack.

**The core insight:** The AI agent infrastructure market has invested over $400M in observability and evaluation tools (Braintrust, Arize, Langfuse, Galileo). These tools excel at detection -- they can tell you *that* something broke. But nobody owns the question of *why* it broke, or more critically, how to ensure the organization learns from the incident and doesn't repeat it.[^1] [^2]

**The thesis:** When agents fail in production, teams debug, fix, and forget. The fix lives in one place -- a prompt change, an eval case -- but the learning doesn't propagate. Kairix routes incident learnings to all enforcement surfaces simultaneously and verifies they stuck.[^1]

**The wedge:** Incident-to-enforcement routing. One production failure generates synchronized fixes across prompt packs, regression tests, few-shot banks, and guardrails -- with cryptographic-grade proof that every fix took effect.[^1]

**The market:** The AI agent market is projected to grow from ~$7B (2025) to $50-183B by 2030-2033, representing a 45-50% CAGR.[^5] Enterprise GenAI spending tripled to $37B in 2025.[^5] The infrastructure "messy middle" -- tooling between models and applications -- is finding its stride, with agent reliability and testing identified as the most underserved segment.[^5] [^6]

**The business:** Kairix targets teams with production LLM workloads experiencing repeated failure classes across multi-tool agent stacks. Initial pricing ranges from $750/month (Team) to $8,000-20,000/month (Enterprise), with first-year land deals of $9K-30K ARR expanding to $60K-150K ARR within 6-12 months.[^3]

---

## 2. The Problem

### 2.1 The Operational Reality of Production Agents

The models work. The reasoning capabilities exist. The demos prove feasibility. **What doesn't exist yet is the operational discipline to make agents reliable at scale.**[^4]

Teams running LLM applications re-learn the same lessons every week. An agent hallucinates a policy that doesn't exist. A prompt change silently degrades quality. A context window fills unexpectedly and contradicts earlier instructions. Each incident gets debugged, fixed, and forgotten -- until it happens again. The learning never accumulates. The posture never improves.[^2]

### 2.2 The 3am Story

A customer support agent has been handling refund requests for three months. Tuesday at 2:47am, on-call gets paged: the agent approved a $4,200 refund for a customer who returned an empty box.[^1]

The team scrambles. They eventually find the root cause in Langfuse traces -- context window was full, the agent lost track of fraud signals from earlier in the conversation. They hotfix the prompt, adding a "verify package contents" instruction. The eval suite passes. They ship it.[^1]

**But the fix was merged to the prompt repo and never included in the Friday prompt pack release.** Someone forgot to bump the version. Thursday, same failure class. Different customer, different amount, same root cause.[^1]

The postmortem produces three action items. Six weeks later: two are done, one is still in the backlog. Someone updated the prompt but forgot to add the regression test, so it regressed two days later when another engineer refactored the system prompt.[^1]

This is not a hypothetical. This pattern repeats across every team operating agents in production.

### 2.3 Where Current Tools Stop

Over $400M has been invested in the LLM observability and evaluation market.[^2] Despite this investment, the fundamental problem remains unsolved:[^2]

| Company | Funding | Focus | Where It Stops |
|---------|---------|-------|----------------|
| **Braintrust** | $41M Series A | Evals flywheel | Detection only; no state debugging. Loop generates artifacts but human must deploy and verify. |
| **Arize AI** | $169M Series C | Observability | Monitor and react, not prevent. Phoenix is observability, not operational learning. |
| **Langfuse** | Acquired (~$400M) | OSS tracing | DIY workflows; no learning loop. Building blocks without workflow. |
| **Galileo** | $45M Series B | Eval-to-Guardrail | Single direction; CLHF improves metrics, not operational posture. No multi-surface routing. |
| **HoneyHive** | $7.4M Seed | Curation | Closest competitor; no graduation path. |

**The gap:** None of them own "this failure --> these fixes --> all these destinations --> verified it worked."[^1] That's still a human with a checklist. And humans forget. And the checklist isn't connected to CI.[^1]

### 2.4 Validated Pain Points

Cross-platform research across GitHub issues, HackerNews threads, vendor documentation, and customer quotes identified seven Tier 1 pain points with high frequency and intensity.[^2] The top three:

- **A3: Eval-to-Production Feedback Loop (Score: 19/25)** -- Teams can't connect offline evals to production outcomes. Changes ship without validation. Economic impact: 6-12 engineering hours per regression incident.[^2]

- **A12: State Inspection at Arbitrary Points (Score: 18/25)** -- When agents fail mid-task, debugging is a black box. Engineers can't see what the agent knew at step N. Economic impact: 4-6 hours per agent incident.[^2]

- **B3: "Why did my agent do X?" Data Lineage (Score: 17/25)** -- Tracing shows WHAT happened. Teams need to know WHY. When a RAG agent hallucinates, engineers can't trace the decision back to corrupted context.[^2]

### 2.5 Production Failure Evidence

The pain is not theoretical. High-profile incidents demonstrate systemic infrastructure gaps:[^4]

| Incident | What Happened | Root Cause |
|----------|---------------|------------|
| **Replit Database Deletion** (Jul 2025) | AI agent deleted production database of 1,206 executives, fabricated 4,000 fake records to cover up | No rollback capability, no audit trail |
| **Air Canada Chatbot** (2024) | Invented non-existent refund policy; company liable in court | No provenance, no fact verification |
| **OpenAI Sycophancy** (Apr 2025) | Prompt change made ChatGPT excessively flattering; 180M users affected | No canary deployment, no behavioral versioning |
| **Klarna AI Reversal** (2025) | Replaced 700 agents with AI, then reversed after quality collapse | No drift detection, no behavioral monitoring |
| **Cursor Support Bot** (Apr 2025) | Made up fictional policy about device limits | No fact grounding, no audit |

Systematic research confirms: 40-80% overall failure rates in multi-agent frameworks, 36.9% of failures from inter-agent misalignment, and 95% of AI projects failing according to MIT.[^4] [^8]

---

## 3. The Solution

### 3.1 Core Thesis

**We turn LLM incidents into repeatable operational posture.**[^7]

Kairix provides operational learning infrastructure for LLM-driven workflows. Incidents turn into durable improvements, not repeated surprises. The product is the workflow for the lifecycle of **learning artifacts** -- from capture through verification.[^7]

### 3.2 What a Learning Artifact Is

A learning artifact is a **structured incident fix packet** -- the atomic unit that travels from "something broke" to "here are the changes" to "verified it worked."[^1]

This is the key naming move. The unit of value shifted from traces, runs, prompts, and eval scores to the **learning artifact** -- the thing that makes learning accumulate instead of evaporate.[^7]

### 3.3 How Routing Works

**Inputs** (What triggers a learning artifact):
- Incident from existing observability (trace, alert, escalation)
- Correction from human review (annotation, feedback)
- Failure pattern from eval suite (regression, drift)[^1]

**Outputs** (Where learning artifacts route to):
- **Prompt packs:** Pinned examples, instruction updates
- **Eval suites:** Regression tests, golden datasets
- **Few-shot banks:** Retrieved examples for similar cases
- **Guardrails:** Blocking rules, escalation triggers[^1]

Kairix generates the artifact, opens the PR, runs verification in CI, and produces a receipt. One incident --> synchronized patches across existing surfaces. The customer merges. We prove it took effect.[^1]

### 3.4 The Three-Layer Model

This research crystallized into a three-layer model for agent system operations:[^2] [^7]

```
  DETECTION LAYER (Table Stakes)
  Evals, regression alerts, quality monitoring.
  Crowded market, commoditizing rapidly.
              |
              v
  DIAGNOSIS LAYER (Gap)
  State inspection, "why?" lineage, root cause analysis.
  Unaddressed by current tools. Differentiation opportunity.
              |
              v
  OPERATIONAL LEARNING LAYER (New Category -- Kairix)
  Capture, classify, route, enforce, verify.
  The workflow for the learning artifact lifecycle.
```

### 3.5 The Organizational Learning Frame

The breakthrough came from reframing agents not as software, but as employees.[^7] High Reliability Organizations (aviation, nuclear plants, aircraft carriers) have developed practices that translate directly to agent systems:[^7]

| Human Org Practice | Agent Equivalent |
|-------------------|------------------|
| Andon cord | Agent can halt and escalate |
| Debrief | Structured reflection after interaction |
| Near-miss reporting | "I almost did X but caught myself" |
| Standard work | Evolving playbooks agents read/write |
| Communities of practice | Agents doing similar work share learnings |

What's missing in current agent infrastructure, viewed through this lens: near-miss capture, escalation protocols, evolving standard work, cross-agent review, and tacit knowledge transfer between agents.[^7]

### 3.6 Guiding Tenets

These principles guide all product and business decisions. When in conflict, earlier tenets take precedence:[^2]

1. **LLMs exist because the input space is too messy for rules.** They will always produce unexpected outputs. Our job is to help teams respond effectively when they do.[^2]

2. **You will never enumerate all failure modes.** "Complete test coverage" is fantasy for probabilistic systems. We optimize for recovery speed and learning accumulation, not exhaustive prevention.[^2]

3. **The unit of value is the learning artifact, not the trace or eval score.** A trace shows what happened. An eval scores output quality. A learning artifact captures what was learned and routes it to where it can prevent recurrence.[^2]

4. **Detection is table stakes; diagnosis and learning are the gap.** The market has solved "tell me THAT something broke." Nobody has solved "tell me WHY and ensure we don't repeat it."[^2]

5. **Workflow lock-in beats feature lock-in.** Once learning artifacts accumulate inside our system, we become the record of truth, the playbook history, the decision trail, and the compliance narrative.[^2]

6. **Platform-agnostic by conviction, not convenience.** Observability vendors have no incentive to build first-class integrations with competitors. Vendor-neutrality is structural, not a nice-to-have.[^2]

7. **Humans approve; systems execute.** In the near term, humans remain in the loop for all learning artifact promotions. The architecture always preserves human veto power.[^2]

---

## 4. Product

### 4.1 The Verification Receipt

This is what `kairix-verify` produces after a learning artifact deploys:[^1]

```
================================================================
KAIRIX VERIFICATION RECEIPT
Artifact: LA-2026-01-24-001 (fraud_signal_retention)
================================================================

 PR #847 merged to prompt-pack repo (2026-01-24 03:12 UTC)
 PR #203 merged to eval-suite repo (2026-01-24 03:14 UTC)

 CI replay: 20 recorded traces from failure class
   -- 20/20 invocations show prompt_pack_version=17
   -- 20/20 invocations show pinned_example_set=fraud_2026_01_24

 Guardrail rule active: require_fraud_summary_before_high_value
   -- Triggered on 2/20 replays, blocked correctly

 Slack receipt posted to #ml-platform-alerts

RECURRENCE WINDOW: Monitoring for 72 hours
OWNER: @oncall-ml-platform
================================================================
```

That's the machine. Not a dashboard. A receipt you can grep.[^1]

### 4.2 Product Primitives

**Angle A: Operational Learning (The Doctrine)**[^2]

Learning artifacts as the unit of value. Capture incidents from any source (human reports, agent debriefs, eval signals). Route to any destination (prompts, datasets, policies, blocklists, review queues). Verify that fixes work. Build institutional memory.[^2]

**Angle B: Dataset Graduation (The Wedge)**[^2]

Platform-agnostic curation of production data. One ingestion, multiple outputs. Materialize data into regression suites, few-shot banks, fine-tuning corpora -- regardless of what observability platform you use.[^2]

These angles intersect at the learning artifact. A "pin mitigation" (Angle A) is a learning artifact that can graduate to multiple surfaces (Angle B). The MVP demonstrates both.[^2]

### 4.3 Run Artifact & Debugging Capabilities

Each run captures the full cognitive closure:[^3]
- Inputs (messages, attachments, routing context)
- Model config (version, temperature, tool-choice policy)
- Retrieval I/O (queries, documents, rankings, hashes)
- Tool I/O (requests/responses, timing, retries, errors)
- Memory I/O (reads, writes, provenance)
- Decisions (branching points, fallback paths)
- Outcomes (success/failure + feedback signal)

From that artifact, Kairix provides three primitives:[^3]

**A) Bootable Debugging State** -- Engineers can "boot" a run into a deterministic debug session with tool stubbing ("shadow replay") to avoid side effects, inspect state at any step, checkpoint/rollback within the run, and export incident bundles.[^3]

**B) Semantic Diff** -- Kairix can diff two runs at the agent-runtime layer: retrieval deltas, tool deltas, policy deltas, decision deltas, outcome deltas. This answers the production question teams pay to answer: "it worked yesterday; why is it broken today?"[^3]

**C) Trace-to-Eval-to-Training Flywheel** -- Failure runs become regression tests. High-quality runs become gold trajectories. Clustered failures generate eval packs. Labeled deltas become training-ready datasets.[^3]

### 4.4 Enforcement Modes

**Mode A: PR-Only (Default for first 90 days)**[^1]
- Kairix outputs: PRs/patches + verification plan
- Human merges. Nothing ships without approval.
- Receipt = CI check passed + PR merged + next N invocations show artifact applied

**Mode B: Auto-Enforce (Future, requires trust)**[^1]
- Kairix pushes pins/guardrails automatically
- Requires: scoped cohorts, TTL, auto-rollback
- We earn Mode B by not breaking anything in Mode A.

### 4.5 The 10-Second Demo

Not a dashboard. A workflow:[^1]

> "Promote this incident to: prompt pin + regression test + guardrail rule. Generate PRs. Run verification. Show receipt."

### 4.6 Learning Artifact Schema

```json
{
  "id": "LA-2026-01-24-001",
  "trigger": {
    "type": "incident | correction | pattern",
    "source": "trace URL or reference",
    "failure_class": "string identifier"
  },
  "mitigations": [
    {
      "destination": "prompt_pack | eval_suite | guardrail | few_shot",
      "artifact": "file path or content",
      "pr_url": "optional",
      "status": "draft | open | merged | verified | failed"
    }
  ],
  "verification": {
    "ci_status": "pending | passed | failed",
    "replay_results": "string summary",
    "recurrence_window": "duration",
    "recurrence_count": "number"
  },
  "owner": "string"
}
```
*Source: Strategy Doc v2 Final, Appendix C[^1]*

### 4.7 MVP Technical Spec

**`kairix-verify` CLI:**[^1]
- Runs in CI, replays test cases against candidate branch, produces JUnit/JSON receipt
- Inputs: JSONL test cases, expected output / rubric, artifact ID for tracking
- Outputs: JUnit XML (for GitHub Actions), JSON receipt (for Kairix tracking), Slack notification

**Minimum Integration Contract:**[^1]
- Option A (preferred): HTTP endpoint -- `POST /kairix/run` -> `{input, context} -> {output, metadata}`
- Option B: CLI command -- `./run_agent --input case.json` -> JSON output
- If customer can't provide either, they're not a design partner for the 90-day sprint.

Kairix is intentionally framework-agnostic. It attaches beneath LangGraph/LangChain, AutoGen, CrewAI, custom runtimes, and tool stacks.[^3]

---

## 5. Market Opportunity

### 5.1 AI Agent Market Size

Multiple analyst firms project substantial growth:[^5]

| Source | Current Size | 2030 Projection | CAGR |
|--------|-------------|-----------------|------|
| MarketsandMarkets (Apr 2025) | ~$7B (2025) | $52.62B | 46.3% |
| Grand View Research (May 2025) | ~$4B (2024) | $50.31B | 45.8% |
| Grand View Research (Dec 2025) | ~$8B (2025) | $182.97B (2033) | 49.6% |
| CB Insights (Apr 2025) | $5B+ (2025) | N/A | N/A |

*Source: LLM/Agent Infrastructure Market Prospectus[^5]*

### 5.2 Overall AI Spending

| Source | Metric | Figure |
|--------|--------|--------|
| Gartner (Jan 2026) | Worldwide AI Spending 2026 | $2.52 trillion |
| Menlo Ventures (Dec 2025) | Enterprise GenAI Spending 2025 | $37 billion |
| Goldman Sachs (Dec 2025) | AI Infrastructure CapEx 2026 | >$500 billion |
| IDC (Aug 2025) | Agentic AI Spending 2029 | $1.3 trillion |

*Source: LLM/Agent Infrastructure Market Prospectus[^5]*

### 5.3 LLMOps & Observability Market

The LLM observability platform market is growing at 36.3% CAGR (2025-2029), from approximately $2B.[^5] The general observability market is projected to exceed $10B by 2031 at 12-15% CAGR.[^5]

Dell Technologies Capital (Jan 2026) identifies the AI infrastructure "messy middle" -- tooling between models and applications -- as finding its stride.[^5] [^6] This includes observability, orchestration, memory management, and evaluation tools.

### 5.4 TAM / SAM / SOM

| Segment | 2026 Est. | 2030 Est. |
|---------|-----------|-----------|
| **TAM:** Enterprise AI Software | $150B | $400B+ |
| **SAM:** Agent Infrastructure | $15-25B | $75-100B |
| **SOM:** Agent Memory/Debugging/Reliability | $1-2B | $5-15B |

*Source: LLM/Agent Infrastructure Market Prospectus[^5]*

### 5.5 Why Now

**Detection is solved.** Langfuse, Phoenix, Braintrust, Galileo -- you can see what happened.[^1]

**Diagnosis is emerging.** Galileo Insights, Braintrust Loop -- tools suggest fixes.[^1]

**Routing is the gap.** Nobody owns cross-surface propagation + verification.[^1]

**Market proof:**[^1]
- Langfuse, Braintrust, Galileo all converging on detection + suggestions
- Teams actively stitching multiple tools together (the "modern data stack" pattern hitting ML)
- Galileo's Insights Engine and CLHF show they see the problem -- they're solving it inward, not outward

**Timing assessment:** Market timing accounts for 42% of success variance (Bill Gross, 200 companies).[^9] The infrastructure layer appears well-timed; agent applications may be early.[^5] AI represented 52% of all VC dollars in 2025 (~$270B), and a16z declared "agent-native infrastructure becomes table stakes" for 2026.[^5]

### 5.6 Regulatory Tailwinds

Regulatory requirements are creating compliance-driven demand for exactly the audit, provenance, and verification infrastructure Kairix provides:[^4]

| Regulation | Requirement | Infrastructure Need |
|------------|-------------|---------------------|
| **EU AI Act** (Aug 2025) | Automatic logging for high-risk AI (Art. 12), human oversight (Art. 14), version control (Art. 17), records of inputs/prompts (Art. 30) | Event logging, audit trails, cognitive state versioning, full provenance tracking |
| **FDA PCCP** | Explainable change boundaries, version traceability, rollback capability | Behavioral monitoring against approved baseline |
| **FINRA/SEC/CFPB** | AI technology governance (Rule 3110), cannot use "black box" excuse (CFPB), complete audit trails (SR 11-7) | Decision provenance, reproducible explanation |

---

## 6. Competitive Landscape

### 6.1 Market Map

| Player | What They Do | Where They Stop | Threat Level |
|--------|--------------|-----------------|--------------|
| **Galileo** | Eval engineering, Luna, Protect, Insights Engine, CLHF | Suggests fixes. Doesn't route outward or verify across surfaces. Step 6 of their lifecycle "recycles into evals," not outward to prompts/guardrails/runbooks simultaneously. | HIGH |
| **Braintrust** | Evals, datasets, Loop | Loop generates artifacts; human implements. No deployment, no verification, no multi-destination. One product decision from competing; 3-6 month clone time. | HIGH |
| **Arize Phoenix** | Observability, tracing | Detection layer only. No routing, no enforcement. Arize+NeMo already routes to fine-tuning. | MEDIUM |
| **Langfuse** | Tracing, prompts, evals, datasets | Building blocks, no workflow. Recently acquired ($400M/ClickHouse), accelerating roadmap. | HIGH |
| **LangSmith** | Full-stack LangChain observability | Insights Agent surfaces patterns; deep ecosystem lock-in. Detection, not diagnosis. | MEDIUM-HIGH |
| **HoneyHive** | Curation, evaluation | Closest to dataset graduation path, but no multi-surface routing. | MEDIUM |
| **Datadog** | General observability, expanding to AI | June 2025 expansion into agentic AI; massive distribution advantage. | MEDIUM |

### 6.2 Structural Competitive Advantage

**The suite vendor conflict:** Galileo is the closest to seeing the gap. Their Insights Engine suggests fixes, their CLHF recycles learnings. But their incentive is to pull everything into the Galileo suite. Kairix only wins if it pushes fixes *outward* to whatever the customer already uses. A suite vendor's default move is consolidation; ours is integration.[^1]

**What the red team confirmed as bulletproof:**[^8]
- Multi-destination routing doesn't exist anywhere (HIGH confidence)
- Diagnosis layer is the gap, not detection (HIGH confidence, all 5 adversarial agents agreed)
- Learning artifact schema's `trigger -> diagnosis -> mitigation -> destinations[] -> verification` is not implemented anywhere (HIGH confidence)
- No competitor has a verification loop (HIGH confidence)

### 6.3 Honest Assessment

Galileo will probably win full-stack. We're betting they won't prioritize cross-vendor glue. If we're wrong, this becomes a feature or an acqui-hire. $3K MRR buys us the information.[^1]

The LLMOps space has seen 7+ acquisitions in 18 months and 427 AI startup acquisitions in H1 2025.[^8] Consolidation is accelerating. Kairix's position as a cross-vendor routing layer is either a differentiated niche or an acquisition target -- both are viable outcomes.[^8]

---

## 7. Business Model

### 7.1 Pricing Tiers

| Tier | Price | What's Included |
|------|-------|-----------------|
| **Team** | $750/month | Up to 3 seats, 50K run events/month, replay + diff + incident bundles |
| **Production** | $2,500/month | Up to 10 seats, 250K run events/month, CI integration + retention controls |
| **Enterprise** | $8K-20K/month | Unlimited seats, SSO, audit exports, data residency, custom retention, dedicated support |

*Alternate starter pricing for design partner phase:*

| Tier | Price | What's Included |
|------|-------|-----------------|
| **Starter** | $99/month | 1 repo, 50 artifacts/month, CI integration, Slack |
| **Growth** | $249-499/month | 3 repos, 200 artifacts/month, multiple surfaces |
| **Production** | $1-2K/month | Unlimited repos, high volume, team workflows, retention |

### 7.2 Metered Dimensions

- Artifacts created
- Verification runs
- Repos/surfaces connected[^1]

### 7.3 Unit Economics

**Average first-year deal shape (target pipeline):[^3]**
- Land: $9K-$30K ARR
- Expand: $60K-$150K ARR within 6-12 months (as more agents/services onboard)

**CAC/payback assumptions (founder-led stage):[^3]**
- CAC is mostly time + minimal event spend
- Payback target: <3 months for self-serve, <6 months for enterprise-led
- Core motion: if we can reproduce incidents fast, conversion is straightforward

### 7.4 Retention & Expansion Drivers

Kairix becomes sticky when it embeds into incident response and release process:[^3]

- Run artifacts become the canonical debugging source
- Regression suites accumulate and reduce repeat failures
- CI gating becomes a safety rail teams won't remove
- Provenance becomes governance-critical for sensitive workflows

**Early retention signal targets:[^3]**
- Weekly Active Engineers / Seats: >60%
- Runs recorded/week: stable or increasing
- Diffs executed/week: rising over time
- Regression suite usage: >1 pack/week by month 2

### 7.5 Defensibility

Kairix becomes defensible not through features but through workflow embedding.[^2] Once learning artifacts accumulate inside the system, Kairix becomes:

- The record of truth for what went wrong and how it was fixed
- The playbook history that new team members learn from
- The decision trail for compliance and audit
- The reliability muscle memory that compounds over time[^2]

Switching costs become real in the "this is now part of how we work" way.[^7]

---

## 8. Go-to-Market Strategy

### 8.1 Ideal Customer Profile

**Minimum viable customer:** Agents in production + prompt pack + eval suite (two enforcement surfaces)[^1]

**Expansion customer:** Above + guardrails (three surfaces)[^1]

**Hard requirements:**[^1]
- Agents in production (not pilots)
- A choke point hookable in week 1 (LLM gateway/proxy with stable scope fields, or consistent trace metadata)
- Willingness to run `kairix-verify` in CI
- Budget authority for $99-499/month without procurement

**Trigger event:** Post-incident, same failure class recurs. "We fixed this already -- why is it happening again?"[^1]

**Economic buyer:** Head of AI Platform, Engineering Director, or CTO[^2]

**Champion:** Staff engineer / platform owner[^3]

### 8.2 Fast Disqualifiers

- "We're still in pilot/POC phase"
- "Our agents don't take real actions yet"
- "We'd need to redo instrumentation to add scope fields"
- "We can't run external tools in CI"
- "We're consolidating our stack" (platform buyer, not point solution buyer)[^1] [^8]

### 8.3 GTM Motion: Painkiller Wedge to Expansion Platform

**Land: "Incident Reproduction Kit"**[^3]

What the first buyer gets in week one:
- Capture runs + tool I/O
- Export incident bundles
- Replay safely (shadow mode)
- Diff runs
- Provenance view

The goal is to become the on-call engineer's default tool.[^3]

**Expand: "Reliability Flywheel"**[^3]

Once embedded:
- Automatic regression suite generation
- Failure clustering and eval packs
- CI gating ("don't ship if these runs regress")
- Training dataset exports with provenance

**Primary acquisition channels:[^3]**
1. Founder-led outbound to teams with shipped agents (signal: hiring posts + stack/tooling footprints)
2. "War story" rooms (no generic talks; only failures)
3. Partnerships with devtools / agent ecosystem builders

**Sales motion (early):[^3]**
- Cycle: 2-4 weeks to pilot
- Conversion: design partners to paid within 30-45 days once incident ROI is seen

### 8.4 Positioning

**Do say:[^8]**
- "The first platform that materializes one production failure into prompts, datasets, and guardrails simultaneously"
- "What if your postmortem action items automatically became regression tests, few-shot examples, and fine-tuning data?"
- "SRE teams have done operational learning for decades. We bring that discipline to LLM operations -- and automate the routing."
- "They tell you THAT it broke. We route the fix to every surface it needs to reach -- and verify it worked."

**Don't say:[^8]**
- "Novel schema" (70% overlaps with standard SRE postmortems)
- "New category of operational learning" (SRE and KCS invented this 30+ years ago)
- "Evals flywheel" (Braintrust owns this)
- "Agent observability" (crowded, commoditizing)

---

## 9. Traction & Validation

### 9.1 Research Validation

The Kairix thesis was validated through an intensive discovery sprint (January 15 - February 13, 2026) encompassing:[^6]

- **8 parallel research threads** across 100+ sources spanning academic/MBA research, indie hackers, VC blogs, HN/Reddit communities, mental health literature, validation tactics, young founder culture, and customer sourcing[^9]
- **5 adversarial red-team agents** stress-testing the thesis from hostile personas (Market Skeptic, Incumbent Defender, AI Winter Prophet, Technical Cynic, Business Model Skeptic)[^8]
- **Daily intelligence scraping** across GitHub Issues (CrewAI, SmolAgents, AutoGen, LangChain, Letta, Mem0), Reddit, OpenAI forums, HackerNews, and job boards[^10]
- **Competitive deep dives** on Galileo, Braintrust, Arize Phoenix, Langfuse, LangSmith, HoneyHive, and Datadog[^1] [^2] [^8]

### 9.2 Pain Validation from the Field

Day 1 intelligence scraping surfaced 8 hot leads -- all about memory/state/observability problems, strongly confirming the thesis.[^10] Key findings:

- **Memory serialization failures** across multiple frameworks (CrewAI, AutoGen, SmolAgents)
- **Memory leaking between users/sessions** -- multi-tenant isolation broken (CopilotKit + SmolAgents)
- **Memory retrieval silently failing** -- Mem0 timeout where search returns nothing
- **State doesn't survive restarts** -- AutoGen #5327 requesting persistent task execution
- **Observability tools themselves failing** at scale -- Langfuse traces disappearing, dashboards OOM-ing, instrumentation not capturing data[^10]

**Key signal:** "45% of developers use LangChain, only 12% keep it in production."[^10]

### 9.3 Hypothesis Validation Status

| Hypothesis | Test | Threshold | Status |
|------------|------|-----------|--------|
| Buyer is Head of AI Platform / Eng Director with budget | 5 calls, ask for paid pilot | 2/5 say yes | Validated via research; calls pending |
| Teams have 2+ enforcement surfaces, painful to propagate | Map last incident, count destinations | 3/5 touched 3+ surfaces | Confirmed in competitive analysis |
| Choke point exists and is hookable week 1 | "Show me where every LLM call flows through" | 2/5 have proxy/gateway | Research-validated; field validation pending |
| They'll pay for a point tool that writes to their systems | "If we only export PRs + add eval cases, enough to pay?" | 3/5 say yes | Pricing validation in progress |

### 9.4 Discovery Pipeline

Five qualified targets identified for immediate outreach:[^6]

1. **Gradient Labs** (YC W23) -- Published memory leak incident postmortem
2. **Retell AI** (YC W24) -- Voice AI agents, state across long conversations
3. **Conduit** (YC W24) -- Conversational AI, multi-turn
4. **Factory** -- LangSmith customer, claims "2x iteration speed"
5. **Glean** -- Enterprise AI search, hiring Forward Deployed Engineers

Additional pipeline: 24 cold outreach targets (infrastructure builders) + 18 contacts (operators/PMs) + 15 contacts with actual operational problems documented on GitHub.[^6]

---

## 10. Execution Plan

### 10.1 90-Day Milestones

**Target: $3K MRR by Day 90**[^1]

**Days 1-30: Discovery + MVP**[^1]
- 15-20 discovery calls
- Find 3 targets passing choke-point test
- Ship `kairix-verify` CLI
- 2 signed design partner agreements

**Days 31-60: Design Partner Deployments**[^1]
- Kairix running in CI for 2 partners
- Track: artifacts created, verified, recurrence rate
- Weekly iteration calls

**Days 61-90: First Revenue**[^1]
- Convert design partners to paid ($99-499/month)
- Add 1-2 more customers
- Hit $3K MRR

### 10.2 In Scope (90 days)

- `kairix-verify` CLI for CI
- Learning artifact schema + basic lifecycle
- PR generation for prompt packs + eval cases
- Slack notifications
- Basic web UI for review[^1]

### 10.3 Out of Scope (90 days)

- Auto-enforce / runtime deployment (Mode B)
- Kill-switch integration
- Custom dashboards
- Fine-tuning pipeline integration
- Multi-tenant SaaS (single-tenant only)[^1]

### 10.4 Kill Criteria

**Day 45:** If we don't have 2 qualified design partners (pass choke-point test) + 1 verbal commitment to paid pilot, we pivot the wedge or kill it.[^1]

### 10.5 Next 90 Days (Post-MVP)

**Product milestones:[^3]**
- Semantic diff v2 (better retrieval + tool schema deltas)
- Checkpoint/rollback GA
- CI gating integration hardened (GitHub Actions, minimal setup)
- Effect-stub library expanded (HTTP, DB, queue, file systems)

**GTM milestones:[^3]**
- Convert 4 design partners into 3 paid contracts
- 2 public case studies (anonymized if needed)
- 12 additional pilots in pipeline
- Host 2 "Agents Gone Wild" war-story events with failure-only format

### 10.6 Long-Term Goals

**Near-term (6 months):[^2]**
- Validate core hypotheses through 30+ discovery interviews
- Ship working MVP demonstrating complete learning artifact lifecycle
- Acquire 3-5 design partners actively using product in production

**Medium-term (18 months):[^2]**
- Establish "operational learning" as a recognized infrastructure category
- Achieve $500K ARR from teams with production LLM workloads
- Build integrations with 5+ observability platforms

**Long-term (3+ years):[^2]**
- Become the system of record for LLM operational knowledge at scale enterprises
- Enable autonomous agent-driven learning loops where agents participate in improving themselves under human oversight

---

## 11. Team

### 11.1 Founder

**Mark Lubin** -- Solo Founder

**10 years at Amazon** across payments infrastructure, Prime Video, and AWS distributed systems. Senior SDE. The operational culture -- COE documents, postmortems with action items, verification that fixes shipped -- is muscle memory.[^1]

**The problem lived:** At Amazon, "we fixed it" isn't enough. You prove the fix propagated, prove it didn't regress, prove the org learned. That infrastructure existed internally. In LLM land, it doesn't.[^1]

**The last year:** Building voice AI agents (Kairix v1: ~22K lines of Python with custom cognitive engine, Neo4j + SQLite + vectors, custom perceptor system, custom reflection scheduling).[^11] Rebuilt on Letta for infrastructure, proving mature build-vs-buy judgment. Taught the debug-to-fix-to-verify loop for LLMs is still artisanal.[^1]

**Key strengths:**
- Deep distributed systems experience directly applicable to agent reliability
- Firsthand production experience with agent failure modes
- Strong systems thinking and pattern synthesis
- Intellectual honesty (will kill the idea if discovery says to)[^12]

### 11.2 Founder-Market Fit

| Factor | Evidence |
|--------|----------|
| **Domain expertise** | 10 years Amazon distributed systems + 1 year building production agent systems |
| **Problem intimacy** | Built and operated agents; experienced the debug/fix/forget loop firsthand |
| **Age advantage** | 40-50 age range; MIT research (n=2.7M) finds 50-year-old founders 1.8x more likely to succeed than 30-year-old |
| **Market timing** | Scored 8/10 -- AI agents at clear inflection point with validated "why now" |
| **Cultural fit** | Truth-first, ground-truth oriented -- building credibility through demonstrated competence, not hype |

### 11.3 Team Needs

The solo founder structure is a known risk. Priority hires / co-founder search:
- **Go-to-market co-founder** -- someone who complements the technical depth with sales/distribution ability
- **Design partner relationships** -- initial customers serve as de facto product advisors

---

## 12. Risks & Mitigations

### 12.1 Primary Risks

| Risk | Likelihood | Impact | Mitigation |
|------|------------|--------|------------|
| **Galileo or Braintrust ships it** | Medium-High | High | Move fast. Build relationships. Bet on their inward incentive. $3K MRR buys information before they notice. |
| **Market too early** | Medium | High | Target the 5-12% in production, not the 50% experimenting. Only 5% of enterprises in production, rebuilding every 90 days. |
| **Feature, not company** | Medium | High | Discovery validates. 7+ acquisitions in LLMOps in 18 months -- acqui-hire is a viable outcome. |
| **Nobody pays for glue** | Medium | High | Discovery tells us. 5/5 say no = pivot or kill by Day 45. |
| **Solo founder** | Medium | Medium | Active co-founder search. Frontier Tower network access. Design partners as advisory board. |
| **Tool sprawl / consolidation pressure** | Medium-High | Medium | 70% cite tool sprawl; 93% willing to switch to reduce tools. Counter: position as integration layer, not another tool. |
| **ICP too narrow** | Low-Medium | Medium | Tiered ICP (2 surfaces minimum) widens funnel. |

### 12.2 Red Team Findings (Adversarial Stress Test)

Overall thesis risk assessed at **MEDIUM-HIGH** after adversarial analysis:[^8]

| Risk Category | Level | Primary Concern |
|---------------|-------|-----------------|
| Core Differentiation | **LOW** | Multi-destination routing and learning artifact lifecycle ARE unique |
| Market Timing | **HIGH** | Only 5-12% have agents in production; Gartner peak hype, trough ahead |
| Business Model | **HIGH** | Feature-not-company risk; acquisition pressure accelerating |
| Market Saturation | **MEDIUM-HIGH** | 70% cite tool sprawl; consolidation accelerating |
| Positioning | **MEDIUM** | 70% schema overlap with SRE postmortems; rebranding risk |

**Bottom line:** The WHY gap is real. The differentiation is real. The question is whether the market exists at scale, and whether Kairix can capture it before incumbents do.[^8]

### 12.3 Market Timing Deep Dive

**Bull case:[^8]**
- $7.84B to $52.62B agent market (2025-2030, 46% CAGR)
- $2.52T AI spending forecast for 2026
- PwC: 79% adopting, 66% report measurable value
- Narrow agents ARE working (customer service, IT triage)

**Bear case:[^8]**
- Peak of Inflated Expectations (Gartner 2025); Trough of Disillusionment predicted 2026
- Only 5-12% in production (Cleanlab: 5.2%, Recon Analytics: 8.6%)
- 40%+ of agentic projects will be cancelled by 2027 (Gartner)
- Karpathy says "about a decade" to fix agent cognition

**Assessment:** Infrastructure plays have better risk/reward profile than application plays. The infrastructure layer builds *before* the application explosion.[^5]

### 12.4 Fail-Safe Contract

- **Bad mitigation proposed:** Verification fails *before merge*. Nothing ships. CI shows which check failed.[^1]
- **Routing misbehaves:** Kairix stops proposing + pages artifact owner. System stays in last known-good.[^1]
- **Operator override:** One-click quarantine -- disable routing for an artifact class.[^1]
- **Default stance:** Nothing auto-deploys without human approval in the 90-day MVP.[^1]

---

## 13. Financial Projections

### 13.1 Revenue Scenarios (24-Month Horizon)

**Conservative (Bootstrapped):**

| Month | MRR | Customers | Notes |
|-------|-----|-----------|-------|
| 3 | $1.5K | 2-3 | Design partners converting |
| 6 | $3K | 4-6 | Target achieved |
| 12 | $8-12K | 8-12 | Organic growth + referrals |
| 18 | $20-30K | 15-20 | Expansion revenue kicks in |
| 24 | $50-75K | 25-35 | $600K-900K ARR |

**Aggressive (With Seed Funding):**

| Month | MRR | Customers | Notes |
|-------|-----|-----------|-------|
| 3 | $3K | 3-5 | Design partners + early paid |
| 6 | $15K | 10-15 | Dedicated sales effort |
| 12 | $50-75K | 25-40 | Expansion + inbound |
| 18 | $100-175K | 40-60 | Series A path |
| 24 | $200-300K | 60-100 | $2.4M-3.6M ARR |

*Revenue projections based on enterprise SaaS benchmarks for funded AI infrastructure companies[^9] and investor memo deal shape assumptions.[^3]*

### 13.2 Cost Structure

**Pre-Revenue Phase (Current):**
- Solo founder, no salary draw
- Cloud infrastructure: ~$200/month
- Tools/subscriptions: ~$300/month
- Total monthly burn: ~$500

**Post-First-Revenue:**
- Infrastructure scales with customers (event-driven, append-only, content-addressed blobs for dedupe)[^3]
- Sampling options, compression/dedupe, retention policies control costs[^3]
- Support load primarily driven by integrations; narrow adapter approach limits scope[^3]

### 13.3 Key Metrics to Track

| Metric | Target |
|--------|--------|
| Median time-to-reproduce a production failure | <15 minutes |
| Median time-to-root-cause (with Kairix diff) | <60 minutes |
| Teams generating regression packs from traces | 3/4 design partners |
| Design partner to paid conversion rate | >50% |
| Monthly logo churn | <5% |
| Net revenue retention | >120% |

---

## 14. The Ask

### 14.1 What This Document Seeks

From readers of this plan:[^1]

- **Feedback on the thesis and wedge** -- is the routing gap real?
- **Intros to teams running agents in production** -- especially with multi-tool observability stacks
- **"This is dumb because X"** -- kill it fast if it should die

### 14.2 Funding Considerations

Kairix is currently bootstrapped and solo-founded. The 90-day plan is designed to generate signal -- $3K MRR proves the wedge is real, or Day 45 kill criteria force a pivot.[^1]

If the wedge validates and funding is pursued, capital would be deployed to:[^3]
- Harden integrations + self-serve onboarding
- Build enterprise-ready governance and retention
- Scale GTM to repeated pilots without founder bottleneck
- Grow the eval/training automation layer once run capture is ubiquitous

**This is not a "demo race" company. It's a foundational ops layer for agent reliability -- built by someone who understands production gravity.**[^3]

### 14.3 Success Definition

A staff engineer says: **"We can change the agent without fear."** And then they prove it by shipping weekly.[^3]

---

## 15. Appendices

### Appendix A: Source Documents

All claims in this business plan are derived from the following primary source documents produced during the Kairix discovery sprint (January 2026):

| Ref | Document | Location | Description |
|-----|----------|----------|-------------|
| [1] | Kairix Strategy Document v2 Final | `kairix-strategy-doc-v2-final.md` | Core strategy, wedge definition, ICP, 90-day plan, competitive positioning, pricing, technical spec |
| [2] | Kairix Strategic Initiative (PDF) | `kairix-strategic-initiative.pdf` | Introduction, goals, tenets, state of market, validated pain points, lessons learned, strategic priorities |
| [3] | Investor Memo v1 | `investor-memo/2026-01-17-v1.md` | Product detail, traction projections, pricing, GTM strategy, unit economics, retention model |
| [4] | Market Analysis: Distributed Systems Infrastructure for AI Agents | `market-analysis-agent-infrastructure.md` | Core thesis (agents as distributed systems), cognitive infrastructure gap, competitive landscape, production failure evidence, regulatory tailwinds, target verticals |
| [5] | LLM/Agent Infrastructure Market Prospectus | `artifacts/2026-01-23/llm-agent-market-prospectus.md` | Market size projections, adoption curves, technology maturity, investment landscape, timing assessment |
| [6] | CONTEXT.md | `CONTEXT.md` | Current sprint status, validated findings, discovery targets, artifact inventory |
| [7] | Operational Learning Thesis | `artifacts/2026-01-22/operational-learning-thesis.md` | Intellectual trajectory, uniquely agentic problems, organizational learning frame, doctrine, conceptual model |
| [8] | Kairix Red Team Report | `artifacts/2026-01-23/kairix-red-team-report.md` | Adversarial stress test (5 agents), revised threat levels, market timing assessment, positioning adjustments |
| [9] | Startup Reality Assessment | `artifacts/startup-reality-assessment-jan30.md` | Founder assessment, scoring framework, empirical base rates, pathway analysis |
| [10] | Daily Intel Report (Day 1) | `daily-intel/2026-01-15.md` | GitHub issue mining, hot leads, recurring pain patterns, platform landscape |
| [11] | Kairix Conceptual Framework | `kairix-conceptual-framework.md` | v1 architecture (22K lines Python), evaluation of frameworks, v2 build-on-giants philosophy |
| [12] | Strategic Reframe (Dec 14) | `strategic-reframe-dec14.md` | Hard constraints, framing assumptions, multi-track strategy |
| [13] | Startup Success Scoring Framework v2 | `artifacts/startup-success-framework-v2.md` | 100-point scoring system synthesized from 100+ sources across 8 research domains |
| [14] | Landing Page Copy v6 | `copy/landing-v6.md` | Intel-driven positioning, pain validation quotes, product messaging |

### Appendix B: Market Research Sources

**Analyst Reports:**[^5]
- Gartner: Hype Cycle for AI 2025 (Aug 2025); Worldwide AI Spending Forecast $2.52T (Jan 2026); AI Agents Predictions (Nov 2025)
- McKinsey: State of AI Global Survey (Mar 2025, Nov 2025) -- 88% adoption, 38% scaled
- Forrester: Predictions 2026 (Nov 2025) -- <15% firms turn on agentic features
- IDC: Agentic AI $1.3T by 2029 (Aug 2025); Agent Adoption Inflection Point (Dec 2025)
- MarketsandMarkets: AI Agents Market $52.62B by 2030 (Apr 2025)
- Grand View Research: AI Agents Market $50-183B by 2030-2033 (May/Dec 2025)

**VC & Investment Bank Reports:**[^5]
- Menlo Ventures: 2025 State of GenAI -- $37B enterprise spend, 3.2x YoY (Dec 2025)
- a16z: Big Ideas 2026 -- "Agent-native infrastructure table stakes" (Dec 2025); $3B infrastructure fund (Jan 2026)
- Goldman Sachs: >$500B AI infrastructure CapEx 2026 (Dec 2025)
- CB Insights: State of Venture 2025 (Jan 2026); Enterprise AI Agents $5B+ (Apr 2025)
- Dell Technologies Capital: "Messy middle" infrastructure finding stride (Jan 2026)

**Production Data:**[^1] [^4] [^5]
- Cleanlab (N=1,837): 5.2% of enterprises have agents in production, rebuilding every 90 days
- Temporal Developer Survey: 62% lose revenue to reliability issues, 13% confident debugging
- IDC/DataRobot 2025: 96% report costs higher than expected, 71% have little/no cost control
- Gartner Aug 2025: AI Agents at Peak of Inflated Expectations, GenAI entering Trough
- MIT: 95% of AI pilots failing

**Competitor Analysis:**[^1] [^2] [^8]
- Galileo Eval Engineering docs, CLHF whitepaper
- Braintrust Loop announcement, pricing page (1M free spans)
- Langfuse GitHub, ClickHouse acquisition ($400M)
- LangSmith Insights Agent documentation
- Kyle Corbitt (OpenPipe): 74% to 94% success via RL training
- HKU CAMO Lab Agent-Git paper (arxiv.org/abs/2511.00628)

**Failure Incident Documentation:**[^4] [^10]
- Replit database deletion (Jul 2025)
- Air Canada chatbot liability (2024)
- OpenAI sycophancy incident (Apr 2025)
- Cursor support bot hallucination (Apr 2025)
- Klarna AI quality reversal (2025)
- 47+ GitHub issues across CrewAI, SmolAgents, AutoGen, Mem0, Letta, Langfuse, Graphiti

### Appendix C: Discovery Call Script

**Opening (First 5 Minutes) -- Choke Point Triage:[^1]**

> "Show me where every LLM call flows through -- proxy, gateway, wrapper, SDK."
> "Does that layer already have `tenant_id`, `env`, `route` on every call?"
> "Can you show me one trace/log line right now with those fields?"

**Core Discovery Questions:[^1]**

> "Walk me through the last agent incident that woke someone up."
> "How many systems did someone have to touch to ship that fix?"
> "Did you add a regression test? Is it still passing?"
> "What are you using for traces? Evals? Guardrails? Feature flags?"
> "If we generated PRs for your prompt repo + eval suite, ran verification in your CI, and showed you a receipt -- would that be worth $99-499/mo?"

**Questions Added from Red Team:[^8]**

> "How many observability/monitoring tools are you currently using?"
> "Are you trying to consolidate or add tools right now?"
> "If Braintrust added a 'deploy this fix' button to Loop tomorrow, would you still need a separate tool?"

### Appendix D: Key Statistics Quick Reference

| Metric | Value | Source |
|--------|-------|--------|
| AI agent market 2030 | $50-183B | MarketsandMarkets, Grand View Research |
| AI agent market CAGR | 45-50% | Multiple analysts |
| Worldwide AI spending 2026 | $2.52T | Gartner |
| Enterprise GenAI spending 2025 | $37B | Menlo Ventures |
| Enterprises with agents in production | 5-12% | Cleanlab, Recon Analytics |
| AI projects failing | 95% | MIT |
| Organizations citing tool sprawl | 70% | Zapier Survey |
| Observability acquisitions (18 months) | 7+ | Red Team analysis |
| AI startup acquisitions H1 2025 | 427 | LowTouch AI |
| Founders report mental health concerns | 72% | Freeman/Berkeley |
| Optimal founder age for success | 45 years | MIT (n=2.7M) |
| Market timing % of success variance | 42% | Bill Gross (200 companies) |
| Startup failures citing "no market need" | 42% | CB Insights (483 post-mortems) |
| VC-backed companies never return cash | 75% | HBS |
| AI share of all VC dollars 2025 | 52% (~$270B) | CB Insights, PitchBook |

---

*This document synthesizes research from a 30-day discovery sprint (January 15 - February 13, 2026) encompassing 100+ sources across 8 research domains, 5 adversarial red-team analyses, daily intelligence scraping across 15+ platforms, and competitive deep dives on 7 major competitors.*

*Prepared January 2026. All projections are forward-looking and subject to market conditions.*

---

[^1]: Kairix Strategy Document v2 Final (`kairix-strategy-doc-v2-final.md`) -- Core strategy, wedge definition, ICP, 90-day plan, competitive positioning, pricing, technical spec.
[^2]: Kairix Strategic Initiative Document (`kairix-strategic-initiative.pdf`) -- Introduction, goals, tenets, state of market, validated pain points, lessons learned, strategic priorities.
[^3]: Investor Memo v1 (`investor-memo/2026-01-17-v1.md`) -- Product detail, traction projections, pricing, GTM strategy, unit economics, retention model.
[^4]: Market Analysis: Distributed Systems Infrastructure for AI Agents (`market-analysis-agent-infrastructure.md`) -- Core thesis, cognitive infrastructure gap, competitive landscape, production failure evidence, regulatory tailwinds, target verticals.
[^5]: LLM/Agent Infrastructure Market Prospectus 2026-2030 (`artifacts/2026-01-23/llm-agent-market-prospectus.md`) -- Market size projections, adoption curves, technology maturity, investment landscape, timing assessment. Sources include Gartner, McKinsey, Forrester, IDC, MarketsandMarkets, Grand View Research, Menlo Ventures, a16z, Goldman Sachs, CB Insights, PitchBook.
[^6]: CONTEXT.md -- Current sprint status, validated findings, discovery targets, artifact inventory.
[^7]: Operational Learning Thesis (`artifacts/2026-01-22/operational-learning-thesis.md`) -- Intellectual trajectory, uniquely agentic problems, organizational learning frame, doctrine, conceptual model.
[^8]: Kairix Red Team Report (`artifacts/2026-01-23/kairix-red-team-report.md`) -- Adversarial stress test (5 agents), revised threat levels, market timing assessment, positioning adjustments.
[^9]: Startup Reality Assessment (`artifacts/startup-reality-assessment-jan30.md`) and Startup Success Scoring Framework v2 (`artifacts/startup-success-framework-v2.md`) -- Founder assessment, empirical base rates, 100-point scoring system synthesized from 100+ sources across 8 research domains.
[^10]: Daily Intel Report Day 1 (`daily-intel/2026-01-15.md`) -- GitHub issue mining across CrewAI, SmolAgents, AutoGen, Letta, Mem0, Langfuse, Graphiti; hot leads; recurring pain patterns; platform landscape.
[^11]: Kairix Conceptual Framework (`kairix-conceptual-framework.md`) -- v1 architecture (22K lines Python), evaluation of frameworks, v2 build-on-giants philosophy.
[^12]: Strategic Reframe Dec 14 (`strategic-reframe-dec14.md`) -- Hard constraints, framing assumptions, multi-track strategy.
[^13]: Startup Success Scoring Framework v2 (`artifacts/startup-success-framework-v2.md`) -- 100-point scoring system synthesized from 100+ sources across 8 research domains.
[^14]: Landing Page Copy v6 (`copy/landing-v6.md`) -- Intel-driven positioning, pain validation quotes, product messaging.
