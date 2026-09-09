---
author: Kayra
pubDatetime: 2026-08-17T00:00:00Z
title: "Threat Modeling — Process, Methodologies, and Running the Session"
slug: "threat-modeling"
description: "What threat modeling is, the four questions it answers, how to decompose a system into a DFD with trust boundaries, the methodologies (STRIDE, LINDDUN, PASTA, attack trees, and the rest) and when each one is the right tool, how to rank and respond to what you find, and how to actually facilitate the session."
tags: ["security", "threat-modeling", "methodology"]
category: notes
draft: false
featured: true
---

## Introduction

Threat modeling is a structured way of asking what could go wrong with a system before someone shows you the answer in production. You take a design, break it into its moving parts, walk through each part looking for ways an attacker could abuse it, decide what to do about each one, and record the decision.

The value is entirely in the timing. A pentest finds the flaw in code that already shipped, where fixing it means a change request, a regression suite, and a release. Threat modeling finds the same flaw in a diagram, where fixing it means moving a box. It is the only security activity that can remove a vulnerability class from a system rather than patching an instance of it.

Two things it is not. It is not a vulnerability scan: you are reasoning about design, not enumerating CVEs. And it is not a document you produce once and file. A threat model that does not change when the system changes stops describing the system and starts describing a system that used to exist.

## The vocabulary, pinned down

Most confused threat modeling sessions are confused because people are using these five words for each other's meanings. Fix them first.

| Term | Definition | Example |
|---|---|---|
| **Asset** | Something of value worth protecting. Data, a capability, a reputation. | The customer PII table |
| **Threat actor** | Whoever might act against you, with their motive and capability. | A credential-stuffing bot, a disgruntled admin, a nation state |
| **Threat** | An action a threat actor could take to harm an asset. It exists whether or not you're vulnerable to it. | An attacker reads the PII table without authorization |
| **Vulnerability** | A weakness that lets a threat succeed. | The report endpoint concatenates user input into SQL |
| **Risk** | Likelihood that the threat is realized, multiplied by the impact if it is. | High: unauthenticated, trivially discoverable, 2M records |
| **Control** | What you put in the way. Also called a countermeasure or mitigation. | Parameterized queries, plus least-privilege DB roles |
| **Residual risk** | What is left after your controls, and the thing someone has to accept. | Low: an admin with DB credentials can still read it |

The distinction that matters in the room: **threats are properties of your design, vulnerabilities are properties of your implementation.** Threat modeling enumerates the first. If you find yourself arguing about whether a specific library version is patched, you have drifted out of the activity.

**Attack surface** is the sum of the points where an untrusted party can interact with the system. **Attack vector** is a specific path through it. **Trust boundary** is a line in the design where the level of trust changes, and it is the single most important concept in this whole post, because nearly every real threat lives on one.

## The four questions

Adam Shostack's framing is the spine of every methodology below, and it is what you should have written on the whiteboard during the session:

1. **What are we working on?** Build a shared model of the system.
2. **What can go wrong?** Enumerate threats against that model.
3. **What are we going to do about it?** Decide a response for each threat.
4. **Did we do a good enough job?** Validate the model, the coverage, and the follow-through.

Every one of them is required. Teams that skip question 1 argue past each other because they each hold a different mental model of the system. Teams that skip question 3 produce a list of scary things and change nothing. Teams that skip question 4 never find out that half the threats were never ticketed.

The Threat Modeling Manifesto (2020) adds the values that keep this from turning into paperwork. The ones worth remembering: *a culture of finding and fixing design issues over checkbox compliance*, *people and collaboration over processes, methodologies, and tools*, and *doing threat modeling over talking about it*. Its named anti-patterns are all real and all common:

- **Hero threat modeler** — believing it takes a special person, so one specialist does them all and nobody else learns.
- **Admiration for the problem** — analyzing deeper and deeper instead of acting on what you already found.
- **Tendency to overfocus** — burning the session on one component, or one threat class, while the rest of the system goes unexamined.
- **Perfect representation** — refusing to move until the diagram is exactly right. Several imperfect models beat one perfect one you never finished.

## When to do it

The default answer is *at design time, on every non-trivial change*. In practice, these are the triggers that should make someone open the model:

- A new feature or service is being designed.
- A **new trust boundary** appears, or an existing one moves. A new third-party integration, a new public endpoint, a component moving from internal to internet-facing.
- The **authentication or authorization** model changes.
- A **new class of data** enters the system: PII, payment data, health data, credentials, secrets.
- The **deployment topology** changes: new cloud provider, new region, containers where there were VMs.
- After a security incident, to find the assumption that turned out to be wrong.
- Before a pentest, to focus the scope on where the design says the risk lives.

The cost argument is the one that convinces management: a design flaw caught on a whiteboard costs a conversation, the same flaw caught in QA costs a sprint, and caught in production it costs a sprint plus an incident response plus whatever the disclosure costs.

---

# Question 1 — What are we working on?

You cannot enumerate threats against a system nobody has described. This phase produces a model that everyone in the room agrees is accurate, and the shared understanding is at least half the value of the whole exercise.

## Scope first

Before any diagram, write down four things:

- **In scope.** The specific service, feature, or flow. One at a time. "The whole platform" is not a scope, it is an excuse for a session that achieves nothing.
- **Out of scope.** Explicit. "We are not modeling the corporate network today."
- **Assumptions.** Everything you are taking on faith. "We assume the platform team's Kubernetes cluster is hardened." "We assume TLS is terminated at the ALB." Every assumption is a threat you have chosen to defer, and writing them down is what makes that a decision instead of an oversight.
- **What you're protecting.** The assets, and what property of each matters — confidentiality, integrity, availability, or some mix. "Session tokens: confidentiality and integrity." "Audit log: integrity and availability, confidentiality is secondary."

## Data flow diagrams

The DFD is the standard model because it makes trust boundaries visible. It has five element types and no more:

| Element | Drawn as | What it is |
|---|---|---|
| **External entity** | Rectangle | An actor outside your control: a user, a browser, a third-party API, another team's service |
| **Process** | Circle | Something that acts on data: a service, a function, a worker, a lambda |
| **Data store** | Two parallel lines | Something that holds data at rest: a database, a bucket, a queue, a log file, a cache |
| **Data flow** | Arrow | Data moving between the above, labeled with what moves and over what protocol |
| **Trust boundary** | Dashed line | Where the trust level changes |

Draw the boundaries last and draw them honestly. A trust boundary sits anywhere that data crosses from a place with one set of guarantees to a place with another: internet to DMZ, DMZ to internal network, your process to another team's process, application to database, host to container, user space to kernel, your code to a third-party SDK. **A boundary crossing is where you check things.** If a flow crosses a boundary and nothing validates, authenticates, or authorizes it there, you have found a threat before you even start enumerating.

Keep the level of detail honest to the decision you're making. Level 0 (context) is the system as one process with its external entities, and is where you start. Level 1 breaks that into the major services and stores, and is where most sessions live and most value is found. Level 2 decomposes a single service internally, and is worth doing only for the components that Level 1 flagged as high risk. Going deeper than that usually means you have started designing rather than modeling.

## Everything else you need on the board

The diagram alone leaves gaps. Alongside it, capture:

- **Entry points**, meaning every place input enters: endpoints, webhooks, file uploads, queue consumers, CLI flags, environment variables, config files.
- **Actors and roles**, with what each is allowed to do. Anonymous, authenticated user, org admin, support agent, service account, CI runner, platform SRE.
- **Data classification** on each store and flow. It drives impact scoring later.
- **Existing controls**, drawn or annotated. You cannot judge residual risk without them, and half the room will not know they exist.
- **Dependencies**: libraries, base images, SaaS providers, identity providers.

> Do not spend the session making the diagram beautiful. A whiteboard photo with legible boxes is a finished model. The tool comes after, if at all.

---

# Question 2 — What can go wrong?

This is where the methodologies live. They exist because unstructured brainstorming finds the threats the loudest person in the room already knows about, and misses whole categories systematically. A methodology's real job is to force coverage.

## STRIDE

STRIDE (Microsoft, 1999) is the default, and if you learn one methodology, learn this one. It is a mnemonic for six threat categories, each the negation of a security property you want.

| Letter | Threat | Property violated | The question to ask | Typical controls |
|---|---|---|---|---|
| **S** | **Spoofing** | Authentication | Can someone pretend to be another user, service, or machine? | Strong authN, MFA, mTLS, signed tokens, DNSSEC |
| **T** | **Tampering** | Integrity | Can someone modify data in transit, at rest, or in memory? | TLS, signatures/MACs, input validation, ACLs, checksums |
| **R** | **Repudiation** | Non-repudiation | Can someone deny doing something, and can we prove otherwise? | Tamper-evident audit logs, signed transactions, time sync |
| **I** | **Information disclosure** | Confidentiality | Can someone read what they shouldn't? | Encryption at rest/in transit, authZ checks, minimal error output |
| **D** | **Denial of service** | Availability | Can someone degrade or stop the service? | Rate limits, quotas, timeouts, autoscaling, circuit breakers |
| **E** | **Elevation of privilege** | Authorization | Can someone do something they're not permitted to? | Least privilege, server-side authZ on every request, sandboxing |

Two ways to apply it systematically.

**STRIDE-per-element** walks every element on the diagram and asks only the categories that can apply to that element type. This is the fast, thorough default:

| Element type | S | T | R | I | D | E |
|---|:-:|:-:|:-:|:-:|:-:|:-:|
| External entity | ✓ | | ✓ | | | |
| Process | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ |
| Data flow | | ✓ | | ✓ | ✓ | |
| Data store | | ✓ | (✓) | ✓ | ✓ | |

The parenthesized R on a data store applies when the store *is* the audit log — tampering with the log is how repudiation is achieved.

**STRIDE-per-interaction** walks every (source, flow, destination) triple instead of every element. It produces fewer and more concrete threats because a threat against "the API" is vague while a threat against "browser sends session cookie to API over the internet boundary" writes itself. Use it when the element-based pass is generating too much noise.

The mechanical version of the session: for each element or interaction, read the applicable letters aloud, and for each one either state a concrete threat or state why it doesn't apply. Say the "doesn't apply" out loud — that is the part that catches wrong assumptions.

### Writing a usable threat statement

"XSS" is not a threat, it is a category. A threat statement someone can act on has five parts:

> **[Actor]** can **[action]** by **[means]**, because **[weakness]**, resulting in **[impact]**.

*"An unauthenticated internet user can read any other tenant's documents by changing the `docId` path parameter, because the document service authorizes on document existence rather than ownership, resulting in a cross-tenant confidentiality breach across all customers."*

That statement contains its own test case, its own fix, and its own impact score. The one-word version contains none of them.

## LINDDUN — the privacy counterpart

STRIDE finds security threats and is close to blind to privacy ones. A system can be perfectly authenticated, encrypted, and authorized while still over-collecting, over-retaining, and enabling users to be tracked across contexts. If your system handles personal data, or you have GDPR-type obligations, run LINDDUN over the same DFD.

| Letter | Threat | What it means |
|---|---|---|
| **L** | Linking | Associating two data items or actions as belonging to the same person |
| **I** | Identifying | Learning the real identity behind data that was supposed to be anonymous |
| **N** | Non-repudiation | The user *cannot* deny an action — here it's a threat, not a goal (whistleblowers, sensitive queries) |
| **D** | Detecting | Inferring something from the mere existence of data or a message, without reading it |
| **D** | Data disclosure | Excessive or unauthorized processing and exposure of personal data |
| **U** | Unawareness & unintervenability | The user doesn't know what's collected, or can't access, correct, or delete it |
| **N** | Non-compliance | Processing that breaches regulation, policy, or the notice you gave |

Note that non-repudiation flips sign between the two frameworks. In STRIDE you want it; in LINDDUN, for some systems, it is the harm. **LINDDUN GO** is a card-deck variant that works well as a workshop format if you want a lighter-weight run.

## PASTA — risk-centric, seven stages

PASTA (Process for Attack Simulation and Threat Analysis) is the heavyweight. Where STRIDE starts from the design, PASTA starts from the business and ends with a costed mitigation strategy. It is a program, not a 90-minute meeting.

| Stage | Name | What it produces |
|---|---|---|
| I | Define objectives | Business objectives, compliance requirements, a business impact analysis |
| II | Define technical scope | Boundaries, assets, infrastructure, dependencies |
| III | Application decomposition | Actors, use cases, data flows, trust boundaries |
| IV | Threat analysis | Real threat intel: who actually attacks systems like this, and how |
| V | Vulnerability & weakness analysis | Existing weaknesses (CWE/CVE) correlated to the assets and threats |
| VI | Attack modeling | Attack trees, attack surface analysis, threat-to-vulnerability paths |
| VII | Risk & impact analysis | Residual risk, countermeasures, a prioritized mitigation strategy |

Its distinguishing feature is stage IV: threats come from evidence about actual adversaries rather than from a mnemonic. That makes the output far more defensible to a business audience and far more expensive to produce. Reach for it on a crown-jewel system or when you need to justify a security budget, not for a sprint feature.

## Attack trees

An attack tree inverts the perspective. Instead of walking your design, you start from the attacker's goal and decompose it.

The root is a goal: *"read another tenant's documents."* Children are the ways to reach it, joined by **OR** (any one suffices) or **AND** (all are required). You keep decomposing until the leaves are concrete actions. Then annotate the leaves with cost, required skill, detectability, or probability, and propagate upward — the cheapest complete path is the one an attacker takes, and it is the one to cut.

```text
GOAL: Read another tenant's documents
├── OR  Abuse the application's authorization
│   ├── OR  IDOR on GET /documents/{id}
│   └── OR  Tenant ID accepted from a client-supplied header
├── OR  Steal a valid session
│   ├── AND Find stored XSS in the comment field
│   └── AND Session cookie readable from JS (no HttpOnly)
└── OR  Reach the storage layer directly
    ├── OR  Bucket policy allows public list
    └── OR  Compromise a service account with over-broad IAM
```

Attack trees are the right tool for the two or three threats that came out of STRIDE as "high, and we're not sure our control actually holds." They go deep on one goal; they are not a way to get coverage.

## Kill chains and MITRE ATT&CK

The Lockheed Martin **Cyber Kill Chain** (reconnaissance → weaponization → delivery → exploitation → installation → command and control → actions on objectives) models an intrusion as a sequence, which is useful because breaking any link breaks the chain. Its weakness is that it is malware-and-perimeter shaped, and describes an external intrusion better than an insider or a cloud identity attack.

**MITRE ATT&CK** is the modern successor in practice: a matrix of adversary tactics (the goal) and techniques (the method), grounded in observed real-world behaviour. In a threat model it has two good uses. First, in question 2, to ask "which ATT&CK techniques apply to this component" as a sanity check on the STRIDE pass, particularly for infrastructure and identity threats that DFD-based modeling under-serves. Second, in question 4, to map your detections against the techniques you claim to cover and find the gaps.

Related reference sets worth knowing by name: **CAPEC** for attack patterns, **CWE** for weakness types, **CVE** for specific vulnerable versions. A mature threat table cites CAPEC or CWE IDs on each threat so the mitigation links to known guidance.

## The rest of the field

You need to be able to name these and say when they apply. You will rarely run them.

- **Trike** — an open-source, risk-and-requirements-driven method. You build an actor–asset–action matrix (who may create, read, update, delete what, and under which rules), and threats fall out of it automatically as the cells that shouldn't be allowed. It recognizes only two threat types, elevation of privilege and denial of service. Strong on authorization completeness, weak elsewhere.
- **VAST** (Visual, Agile, and Simple Threat modeling) — the methodology behind the commercial ThreatModeler tool, designed for enterprise scale. Splits into *application* threat models built from process-flow diagrams for developers, and *operational* threat models built from DFDs from the attacker's view for infrastructure. Its selling point is that it scales to hundreds of models without a security expert in every room.
- **OCTAVE** (Operationally Critical Threat, Asset, and Vulnerability Evaluation, from CERT/SEI) — organizational risk assessment, not software design. Asset-driven, run by the business rather than by engineers. **OCTAVE Allegro** is the streamlined, information-asset-focused version. Use it for enterprise risk programs; it will not tell you your API has an IDOR.
- **hTMM** (hybrid Threat Modeling Method, SEI) — deliberately combines Security Cards for breadth of imagination, Persona non Grata for attacker realism, and STRIDE for systematic coverage, aiming for no false positives and no missed threats.
- **Security Cards** — a 42-card deck across four dimensions (human impact, adversary's motivations, adversary's resources, adversary's methods). Excellent at surfacing unusual threats that a checklist structurally cannot produce. Good as a 20-minute divergence exercise inside a longer session.
- **Persona non Grata** — write your attackers as personas with motivation, skill, resources, and goals, then reason about what *that specific person* would do. Catches "who would even bother" reasoning errors in both directions.
- **Abuse cases / evil user stories** — the same use-case format inverted: *"As an attacker, I want to submit a negative quantity so that I receive a refund."* The cheapest way to get threat thinking into a team that already writes user stories, and the format product owners understand without training.

## Choosing one

| Situation | Use |
|---|---|
| Default, a feature or service at design time | STRIDE (per-element, moving to per-interaction if noisy) |
| The system handles personal data | STRIDE **plus** LINDDUN |
| Crown-jewel system, need business-grade risk justification | PASTA |
| One specific high-risk threat you need to go deep on | Attack tree |
| Agile team, security embedded in the backlog | Abuse cases per story + a STRIDE pass per epic |
| Enterprise-wide, hundreds of applications | VAST or a tool-driven program (IriusRisk, ThreatModeler) |
| Organizational/business risk, not software | OCTAVE Allegro |
| The team is new to this and needs to loosen up | Security Cards, Elevation of Privilege card game, OWASP Cornucopia |

Pick one primary, and treat the others as supplements. Running two full methodologies over the same diagram in one session produces exhaustion, not coverage.

---

# Question 3 — What are we going to do about it?

Every threat gets exactly one of four responses, and every response gets a named owner. A threat with no response is not a threat model output, it is a note.

| Response | Meaning | Example |
|---|---|---|
| **Mitigate** | Reduce likelihood or impact with a control | Add server-side ownership checks on every document fetch |
| **Eliminate** | Remove the thing that creates the threat | Stop storing the full card number; store the last four |
| **Transfer** | Move the risk to someone contractually equipped to hold it | Use a PCI-compliant payment provider, insurance |
| **Accept** | Consciously live with it, with a named accepter and a review date | "Admins with prod DB access can read PII; covered by contract, logging, and access review" |

Acceptance is legitimate and necessary, but it has requirements: a named person with the authority to accept it, the residual risk written in business terms, and a date to revisit. "The team accepted it" is not acceptance, it is diffusion of responsibility.

The fifth option, ignoring the threat, is what happens by default when you don't do the other four. It is the outcome of most threat models that end at question 2.

STRIDE also gives you a starting point for *what kind* of control to reach for, since each category maps to a property and each property maps to a control family:

| Threat | Control family | Concrete examples |
|---|---|---|
| Spoofing | Authentication | MFA, mTLS between services, signed and audience-scoped tokens, no shared accounts |
| Tampering | Integrity | TLS everywhere, MACs/signatures, server-side validation, immutable infrastructure, WORM storage |
| Repudiation | Logging & non-repudiation | Append-only audit logs shipped off-host, synchronized clocks, per-actor identity in every log line |
| Information disclosure | Confidentiality | Encryption at rest and in transit, authorization on every read, generic error messages, no secrets in logs |
| Denial of service | Availability | Rate limiting per identity and per IP, request size and timeout limits, quotas, backpressure, autoscaling |
| Elevation of privilege | Authorization | Deny by default, least privilege, server-side checks on every request, no client-supplied role or tenant claims |

A control is only a control if it sits on the path. Rate limiting at the CDN does nothing for a threat that enters via the internal queue.

## Prioritizing: which threats first

You will finish enumeration with more threats than you can fix in the quarter. Rank them.

**Likelihood × impact matrix.** A 3×3 or 5×5 grid, scored by the room. Crude, fast, and what most real sessions use. Its weakness is that "likelihood" gets estimated differently by every participant, so define the anchors before you score: what does a "high likelihood" actually mean here — weekly? Requires no skill? Already happening to peers?

**DREAD.** Damage, Reproducibility, Exploitability, Affected users, Discoverability, each scored 1–10 and averaged. Microsoft deprecated it because the scores turned out to be inconsistent between people and between sessions, which is fatal for something whose only job is comparison. Discoverability is the worst of the five, because scoring it low is security through obscurity — if you use DREAD at all, pin Discoverability to 10 and treat it as DREA. Know it because you will be asked about it; prefer something else.

**OWASP Risk Rating Methodology.** Likelihood from threat-agent factors (skill level, motive, opportunity, size of the group) and vulnerability factors (ease of discovery, ease of exploit, awareness, intrusion detection), impact from technical factors (loss of confidentiality, integrity, availability, accountability) and business factors (financial damage, reputation, non-compliance, privacy violation). More structured than DREAD, with the same subjectivity problem but better-defined anchors. Good middle ground when you need to show your work.

**CVSS.** Built for scoring known vulnerabilities in shipped software, not design-stage threats. You often lack the information its vectors demand. Use it downstream, when a threat has become a specific finding.

**FAIR.** Quantitative: loss event frequency × loss magnitude, expressed in currency with distributions rather than a High/Medium/Low label. It is the right answer when you are talking to a CFO and the wrong answer when you have 90 minutes and a whiteboard.

**Bug bars.** Instead of scoring each threat, define severity classes up front ("any unauthenticated remote data access is Critical and blocks release"), and classify threats into them. Faster and far more consistent than per-threat scoring, and it removes the argument from the session, which is usually worth more than the precision you lose.

Whatever you pick, apply it consistently and record the reasoning, not just the number. The ranking exists to order the backlog, not to be correct to two decimal places.

---

# Question 4 — Did we do a good enough job?

The step everyone skips. It has four distinct checks:

- **Is the model accurate?** Does the diagram still match what was built? Walk the code or the infrastructure against it. A model that drifted is worse than no model, because it produces confidence.
- **Is the enumeration complete enough?** Did every element get every applicable STRIDE letter? Did you cover every trust boundary crossing? Were the assumptions all written down?
- **Did the mitigations get built, and do they work?** This is the hand-off to testing. Each mitigation should become a test case, a pentest scope item, or a detection rule. "We added rate limiting" is a claim until someone tries to exceed it.
- **Did anything actually change?** Count the tickets created, closed, and still open. A threat model program whose output backlog never drains is theatre, and the metric will tell you before the incident does.

The other half of question 4 is feeding what you learned back: threats you found here that generalize become standards, secure defaults, or paved-road platform features, so the next team doesn't have to find them again.

---

# Running the session

This is the part that determines whether you get an outcome or a meeting.

## Who is in the room

Four to eight people. More than that and the quiet ones stop talking.

- **A facilitator** who drives the process and does not need to be the deepest technical person in the room. Their job is to keep the room on the current element, park tangents, and make sure every STRIDE letter gets asked.
- **The architect or tech lead** who can answer "does it actually work that way."
- **Developers** who own the components in scope. They know where the shortcuts are.
- **A product owner** who knows what the data is worth and has the authority to accept risk.
- **Ops/SRE**, who knows the deployment reality, which is rarely what the diagram says.
- **QA or an SDET** if you have one, because they leave with test cases.

The security engineer is usually the facilitator, but the anti-pattern to avoid is the security team producing the model *for* the team. The team that builds the system must own the model, or it will not be maintained.

## Preparation

Send in advance: the scope statement, the current architecture diagram (however rough), the data classification of what's in play, and any existing threat model. Ask people to arrive knowing what the system does. Do not send a template to fill in — the collaboration is the point.

Have ready: a whiteboard or a shared canvas, the STRIDE table visible on a wall or screen, and a scribe who is not the facilitator.

## A 90-minute agenda

| Time | Activity |
|---|---|
| 0:00–0:10 | Scope, assets, assumptions, out-of-scope. Write them where everyone can see. |
| 0:10–0:30 | Draw the DFD together. Draw trust boundaries last. Stop when the room agrees it's accurate, not when it's pretty. |
| 0:30–1:05 | STRIDE sweep. Element by element, letter by letter. Scribe captures threats verbatim; no fixing yet. |
| 1:05–1:20 | Rank. Score each threat, agree the top handful. |
| 1:20–1:30 | Responses and owners. Every top threat gets one of the four responses and a name. Create tickets in the room. |

## Facilitation rules that make the difference

- **Separate enumeration from solutioning.** The instant someone proposes a fix, the room stops finding threats and starts designing. Park mitigations in a column and come back to them. This is the single most common way sessions fail.
- **Ask the questions out loud, in order.** "Data flow from the browser to the API: tampering?" The structure is doing the work; freeform "what could go wrong" reverts to whatever the room read about last week.
- **Record the negatives.** When a letter doesn't apply, capture *why* in one line. That line is what a future reader needs, and half the time saying it out loud reveals it does apply.
- **Write every assumption down the moment it's spoken.** "Well, that endpoint is internal-only" is an assumption, and it is wrong more often than anyone expects.
- **Assume any single control fails.** For each threat, ask what else stops it. That is defence in depth, tested cheaply.
- **Timebox each element.** Three to five minutes. The facilitator's job is to move on while someone is still talking.
- **Don't let the diagram grow.** Scope creep in a threat model shows up as new boxes. New boxes are a new session.

## What you leave with

The deliverable is small, and it is not a report:

1. The diagram, photographed or exported, dated.
2. The threat table.
3. The assumptions and out-of-scope list.
4. Tickets in the backlog, with owners, linked back to threat IDs.
5. A review trigger: the date or the change that brings the team back.

The threat table is the core artifact. These columns:

| ID | Element / interaction | Category | Threat statement | Existing controls | Likelihood | Impact | Risk | Response | Mitigation | Owner | Ticket |
|---|---|---|---|---|---|---|---|---|---|---|---|
| T-07 | Browser → API (internet boundary) | I | An attacker on a shared network reads session cookies because the cookie lacks `Secure` and the app answers on port 80 | HSTS on the apex domain only | Med | High | High | Mitigate | `Secure`, `HttpOnly`, `SameSite=Lax`; HSTS with `includeSubDomains`; redirect 80→443 | A. Ehab | SEC-412 |

---

# A worked example

A document-sharing service. Users upload files through a browser, a worker extracts text for search, files land in object storage, and a third-party API scans for malware.

## The model

```text
                    ┌─ INTERNET ──────────────────────────────┐
  [User Browser] ───┼──> (Web/API service) ─────┐             │
                    └───────────┬───────────────┼─────────────┘
                 TRUST BOUNDARY │               │  TRUST BOUNDARY
                    ┌─ APP VPC ─┴───────────────┼─────────────┐
                    │  (Auth service)           │             │
                    │        │                  v             │
                    │        │            [[ Upload queue ]]  │
                    │        │                  │             │
                    │        │                  v             │
                    │        │           (OCR/scan worker) ───┼──> {Malware scanning API}
                    │        v                  │             │        (third party)
                    │  [[ Postgres ]] <─────────┤             │
                    │  [[ S3 bucket ]] <────────┘             │
                    └─────────────────────────────────────────┘

  ( ) process     [ ] external entity     [[ ]] data store     { } third party
```

Four trust boundaries: internet→web tier, web tier→app VPC, app→data stores, app→third-party API.

## A slice of the STRIDE sweep

| Element | Cat | Threat | Response |
|---|---|---|---|
| Browser → API | **S** | An attacker replays a stolen session token from another device and IP | Mitigate: bind tokens to a device fingerprint, short TTL, re-auth for sensitive actions |
| Browser → API | **T** | A user modifies the `orgId` in the upload request to write into another tenant's space | Mitigate: derive `orgId` from the session server-side; never accept it from the client |
| Web/API service | **E** | The upload endpoint checks that the document exists but not that the caller owns it | Mitigate: centralized ownership check in middleware; add a negative test per endpoint |
| Web/API service | **D** | Unbounded file size and unlimited concurrent uploads exhaust the worker pool | Mitigate: size cap, per-user concurrency quota, queue depth limit with shed-load |
| Upload queue | **T** | A compromised web node enqueues a job pointing at an arbitrary internal URL, and the worker fetches it (SSRF) | Mitigate: workers accept storage keys only, never URLs; egress allowlist on the worker subnet |
| OCR/scan worker | **E** | A malicious document exploits the parsing library and the worker runs as root with broad IAM | Mitigate: sandbox parsing, drop privileges, scope the worker's IAM role to one prefix |
| Worker → third party | **I** | Documents containing customer PII are sent to the scanning vendor, outside the agreed processing region | Mitigate/transfer: hash-first submission, DPA and regional endpoint, or scan in-house |
| S3 bucket | **I** | A bucket policy or pre-signed URL lifetime allows access to objects beyond the requesting user's scope | Mitigate: per-object keys, 60s pre-signed URLs, block public access, access logging |
| Postgres | **R** | An admin deletes a document and the audit trail lives in the same database they control | Mitigate: ship audit events to append-only external storage |
| Auth service | **S** | Password spraying against the login endpoint, no lockout or rate limit | Mitigate: per-account and per-IP throttling, MFA, breached-password check |

Ten threats out of a partial pass, and every one of them is a design decision, not a code bug. That is the point: none of these are findable by a scanner, and all of them are cheaper to fix now than after launch.

---

# Keeping it alive

## In an agile process

A 90-minute session per quarter does not match a two-week release cadence. What works:

- **Per-epic threat model.** When an epic enters design, run a scoped session on it. Small model, small scope, 60 minutes.
- **Per-story abuse cases.** For stories that touch auth, data, or an external boundary, write one or two evil user stories in the story itself, and make them acceptance criteria. This is where most of the volume gets covered.
- **A trigger checklist in the definition of ready.** New trust boundary, new data class, new dependency, auth change, new entry point — any of these and the story doesn't start until someone has looked at the model.
- **A security champion on the team** who can run a small session without pulling in the security team, escalating only for the crown jewels.
- **Model in the repo.** Keep the diagram and the threat table as files next to the code, so they show up in pull-request diffs and go stale visibly rather than silently.

## Threat modeling as code

The tooling that supports the last point:

- **pytm** (OWASP) — describe the system in Python, get a DFD and a threat report generated from a threat library.
- **threagile** — describe the architecture in YAML, get generated diagrams plus a risk report; runs in CI as a container.
- **Threatspec** — annotations in ordinary source comments (`@threat`, `@mitigation`) that build a model out of the code itself.

The trade-off is real: as-code models version, diff, and run in CI, but they lose the collaborative conversation that is the main reason to do the activity. The strong pattern is a whiteboard session for discovery, then commit the result as code so it stays honest.

## Tooling

| Tool | Type | Notes |
|---|---|---|
| **OWASP Threat Dragon** | Free, open source | Diagramming plus STRIDE/LINDDUN/CIA prompts, web and desktop. The default starting point. |
| **Microsoft Threat Modeling Tool** | Free, Windows | DFD editor that auto-generates STRIDE threats from element types, with templates. Dated but effective. |
| **IriusRisk** | Commercial (community edition available) | Questionnaire-driven, generates threats and countermeasures from a library, integrates with Jira. Scales across many teams. |
| **ThreatModeler** | Commercial | The VAST methodology, aimed at enterprise automation. |
| **pytm / threagile / Threatspec** | Free, as-code | Model lives in the repo, runs in CI. |
| **Elevation of Privilege / Cornucopia** | Free card games | STRIDE and web-vulnerability card decks. The best way to teach a dev team the categories. |
| **draw.io, Excalidraw + a spreadsheet** | Free | Genuinely sufficient. Most successful programs run on exactly this. |

Do not choose a tool before you have run three sessions by hand. Tool selection is the most common way a threat modeling initiative spends six months producing nothing.

## Where it plugs into everything else

The threat model is an input to work you're already doing. It scopes the pentest, telling you which components deserve the days. It seeds abuse-case test suites. It defines what your detection rules need to catch, and a threat with no corresponding detection is a gap worth naming. It generates the security requirements that go into the backlog, and it justifies them, which is what gets them prioritized. And it is the artifact auditors ask for when a framework requires evidence of secure design.

Domain-specific overlays are worth knowing: for mobile, the threat model must include a hostile user on their own device, which is a different assumption from a web app. For LLM-backed systems, the model has to account for the fact that instructions and data share one channel — see [the OWASP Top 10 for LLM Applications](/posts/owasp-llm-top-10). For CI/CD, the pipeline is a production system with production credentials, and it deserves its own model.

---

# The one-page version

Bring this into the room.

**Scope.** One system. Write down what's in, what's out, what you assume, and what you're protecting.

**Model.** External entities, processes, data stores, data flows. Trust boundaries last. Level 1 detail.

**Enumerate.** Every element, every applicable letter, out loud.

| Letter | Threat → property to check |
|---|---|
| **S** | Spoofing → authentication |
| **T** | Tampering → integrity |
| **R** | Repudiation → non-repudiation |
| **I** | Information disclosure → confidentiality |
| **D** | Denial of service → availability |
| **E** | Elevation of privilege → authorization |

Element coverage: external entity = S, R. Process = all six. Data flow = T, I, D. Data store = T, I, D (+R for logs).

Threat statement: *[actor] can [action] by [means] because [weakness], resulting in [impact].*

**Rank.** Likelihood × impact, with the anchors defined before you score.

**Respond.** Mitigate, eliminate, transfer, or accept. Named owner, ticket, date. Acceptance needs someone with the authority to accept.

**Validate.** Does the model match reality, did every element get covered, did the mitigations get built and tested, did the backlog actually move?

**The three rules.** Don't solution during enumeration. Write down every assumption. Finish something imperfect rather than perfecting something unfinished.
