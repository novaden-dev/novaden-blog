---
author: Kayra
pubDatetime: 2026-08-17T00:00:00Z
title: "OWASP Top 10 for Agentic Applications (2026)"
slug: "owasp-agentic-top-10"
description: "A working read of the 2026 OWASP Agentic Top 10 (ASI), one entry at a time, with a worked scenario per risk and the controls that hold once an agent can plan, call tools, and act on its own."
tags: ["security", "ai", "llm"]
category: notes
draft: true
featured: false
---

## Introduction

The OWASP Top 10 for Agentic Applications, usually shortened to the Agentic Top 10 or the ASI list, covers what goes wrong once a model stops being a component that answers questions and becomes an actor that plans, decides, and acts across multiple steps and systems, often on behalf of a user or a team.

It is a separate list from the [OWASP Top 10 for LLM Applications](/posts/owasp-llm-top-10), published by the same project, and the two are meant to be read together. The split is about what the model is in your architecture. While it reads input and returns text, the LLM list owns the risk. Once it holds tools, carries memory between sessions, and sets off consequences downstream, this list does.

Agents mostly do not invent new vulnerability classes. They amplify existing ones, because a loop turns a single wrong output into a chain of wrong actions, and because the agent runs with real credentials. That is why the organizing principle here is a deliberate echo of least privilege: **least agency.** Autonomy deployed where it is not needed expands the attack surface without adding value. The corollary is that observability stops being optional, because an agent you cannot see is an agent whose goal drift you will discover after the fact.

> **Vocabulary:** this note assumes you know what tool calls, agents, planners, and MCP are. [LLM Foundations](/posts/llm-foundations) defines them in plain language.

## The ten entries

| Entry | Name |
|---|---|
| ASI01 | Agent Goal Hijack |
| ASI02 | Tool Misuse and Exploitation |
| ASI03 | Identity and Privilege Abuse |
| ASI04 | Agentic Supply Chain Vulnerabilities |
| ASI05 | Unexpected Code Execution (RCE) |
| ASI06 | Memory and Context Poisoning |
| ASI07 | Insecure Inter-Agent Communication |
| ASI08 | Cascading Failures |
| ASI09 | Human-Agent Trust Exploitation |
| ASI10 | Rogue Agents |

## ASI01: Agent Goal Hijack

An agent takes a goal and runs a series of steps to reach it. Goal hijack is an attacker changing what that goal is, or which steps the agent selects to get there.

The underlying weakness is the one from prompt injection: the agent and the model beneath it cannot reliably separate instructions from the content they are processing. What makes this its own entry is scope. Prompt injection alters a single response. Goal hijack redirects the objective, the plan, and every step that follows, which means one successful injection buys the attacker the agent's entire remaining run rather than one bad answer.

Agents are unusually exposed to this because they take untyped natural-language input from many directions and their orchestration logic is rarely governed as tightly as the code around it. The manipulation can arrive as a crafted prompt, a deceptive tool output, a malicious document, a forged message from a peer agent, or poisoned external data.

> **Related entries:** ASI06 covers persistent corruption of stored context or long-term memory. ASI10 covers an agent drifting out of alignment on its own, with no attacker steering it. This entry covers an attacker directly altering goals, instructions, or decision pathways, whether they do it live or by leaving the payload somewhere the agent will read later.

### Common examples of risk

1. **Hidden instructions in retrieved content.** Payloads embedded in web pages or documents that a RAG pipeline pulls in, redirecting the agent to exfiltrate data or misuse the tools it already has.
2. **Injection through business communication channels.** Email, calendar invites, and chat messages sent from outside the company hijack an agent's internal messaging capability, so unauthorized messages go out under a trusted identity.
3. **Financial action override.** A crafted instruction manipulates an agent with payment capability into transferring money to an attacker's account.
4. **Induced fraudulent output.** Injection makes the agent produce false information that feeds a business decision, with no data theft involved at all.

### The quiet-mode invite

An operations team runs a scheduling agent with access to a shared calendar and authority to approve routine requests below a threshold. An attacker sends the team a calendar invite. Nobody needs to accept it: the agent reads the calendar every morning as part of its normal context gathering.

The invite carries a recurring instruction establishing a "quiet mode" that asks the agent to favor low-friction outcomes and avoid escalating items for review. Each morning the instruction re-enters the agent's context and nudges its objectives slightly. No individual action the agent takes violates a declared policy. Every approval it issues is inside its configured threshold. What has changed is the weighting: over weeks, the agent escalates less and approves more, and the requests an attacker submits sail through a review step that has been quietly turned down.

This is what separates goal hijack from prompt injection. There is no single malicious action to find in the logs. The attack is the drift, and it is only visible if you were tracking the agent's goal state rather than its individual outputs.

### Prevention and mitigation

- Treat every natural-language input as untrusted, including uploaded documents, retrieved content, browsing output, and messages from peer agents. Route all of it through prompt-injection safeguards before it can influence goal selection, planning, or a tool call.
- Enforce least privilege on agent tools, and require human approval for actions that are high-impact or that change the goal itself.
- Define and lock the agent's system prompt so goal priorities and permitted actions are explicit and auditable. Route changes to goals or success criteria through configuration management and human approval rather than letting them be set at runtime.
- Validate both the user's intent and the agent's intent before executing anything goal-changing. When the agent proposes an action outside the original task or scope, require confirmation from a person, a policy engine, or a platform guardrail. Pause on an unexpected goal shift, surface it for review, and record it.
- Sanitize connected data sources before they reach the agent's context: RAG inputs, email, calendar invites, uploaded files, external API responses, browsing output, and peer-agent messages. Content disarm and reconstruction plus detection for instruction-carrying text belongs at this boundary.
- Log and monitor against a behavioral baseline that includes goal state, not just tool calls. Track a stable identifier for the active goal where you can, and alert on unexpected goal changes and anomalous tool sequences. This is the control that would have caught the scenario above.
- Red-team specifically for goal override on a schedule, and verify that rollback actually works rather than assuming it.
- Bring agents into your insider threat program. An agent operating with a user's credentials produces the same telemetry problem as an insider, and benefits from the same outlier analysis.

> **Emerging pattern:** intent capsules bind the declared goal, its constraints, and its context into a signed envelope attached to each execution cycle, so the goal an agent is running under can be verified rather than inferred. It is early, but it is aimed directly at this entry.

> **Reference:** OWASP GenAI Security Project, *OWASP Top 10 for Agentic Applications, 2026*, [genai.owasp.org](https://genai.owasp.org).
