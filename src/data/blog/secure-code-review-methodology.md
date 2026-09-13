---
author: Kayra
pubDatetime: 2026-08-21T00:00:00Z
title: "Secure Code Review: Process and Methodology"
slug: "secure-code-review-methodology"
description: "Running a secure code review end to end: scoping and intake before the environment is provisioned, getting an analyser working on a network with no internet, which code to read when you cannot read all of it, and the coverage statement that makes a time-boxed review defensible."
tags: ["security", "devsecops", "methodology", "owasp"]
category: notes
draft: true
featured: false
---

## Introduction

A secure code review is a white-box assessment of an application's source, looking for security defects that a black-box test would either miss entirely or only see the symptom of. It is not a code quality review, it is not a pentest with the source attached, and it is not the output of a scanner.

This note covers the process: scoping, environment, recon, automation, manual review, validation, reporting. It is deliberately stack-agnostic. The per-ecosystem detail (which build manifests to read, whether the analyser needs a compile, what to grep for in each language) lives in [Secure Code Review by Stack](/posts/secure-code-review-by-stack).

The reference for the technical half is the [OWASP Code Review Guide v2](https://owasp.org/www-project-code-review-guide/), with one caveat. It was written mostly for a development organisation reviewing its own code inside an S-SDLC, with access to the developers, the architects, and the design documents. A time-boxed external activity is a different shape. The technical content transfers directly. The process content needs adapting, and that adaptation is most of what follows.

## What the Activity Actually Is

### Code review against pentest

The two find different things, and the difference is not "one has the source".

| | Pentest | Code review |
|---|---|---|
| Sees | The running system's responses | Every branch, including ones no request reaches |
| Misses | Logic that never surfaces in a response | Runtime, deployment, and infrastructure behaviour |
| Proves | Exploitability | Presence of a defect |
| Coverage | Whatever the tester reached | Whatever the reviewer read |
| Best at | SSRF, injection you can trigger, misconfigured hosts | Crypto misuse, authorization gaps, dead-but-reachable code, hardcoded secrets, error handling |

The value a code review adds over a pentest is **certainty about absence**. A pentest that finds no IDOR tells you the tester did not find one. A code review that reads the data access layer and confirms every query filters on the caller's tenant tells you something stronger. That certainty only exists for the code you actually read, which is why the coverage statement at the end is not optional paperwork.

### The confidence tax

Code review has an inversion that catches people out. **A finding you cannot prove exploitable is still a finding**, but it is worth much less if you cannot say what happens when it fires. Reading a raw SQL call built by string concatenation is a real defect. Reading it, tracing the parameter back to a request-bound property, and confirming nothing sanitises it in between is a report-grade finding. The gap between those two is where the time goes.

### What automated analysis cannot see

Static analysis is good at what a pattern or a taint trace can reach, and structurally blind to the rest. Knowing the shape of the blind spot is what tells you where to spend the manual hours:

- **Broken access control**: an endpoint with no authorization check, or a query that filters by ID but not by owner. No analyser knows which endpoints are supposed to be admin-only. This is the most common serious finding in a business application and it is invisible to SAST.
- **Business logic**: a refund path that allows a negative amount, a voucher that can be applied twice, a workflow whose state machine can be skipped.
- **Insecure design**: the right primitive used the wrong way. AES with a hardcoded IV, a password hash with 1,000 iterations, a session token that is a GUID.
- **Multi-tenancy leaks**: correct code that queries the wrong tenant context.
- **Trust boundary errors**: validation done in the client and nowhere else.
- **Configuration the tool does not model**: token validation flags, CORS policy, cookie attributes, middleware ordering.

Scanner output is a lead, not a verdict. Treat every finding as a question about the code rather than a statement about it.

> **Check the tool's edition before planning around it.** In several commercial analysers, including SonarQube, cross-file taint analysis (the part that actually traces a source to a sink) is a paid-tier feature. On the free tier the output is rule-pattern matches and hotspots, with much less of the injection detection the plan probably assumed.

## Time Budget and Run Order

Exhaustive reading is not on the table at any realistic budget. Deep line-by-line reading runs at roughly 100 to 200 lines an hour once you include following call chains and checking the other end, so a week of review buys a few thousand lines against a codebase of hundreds of thousands. The job is not to read everything. It is to **choose which few thousand lines**, deliberately, and record the choice.

Whatever the duration, the proportions hold:

| Phase | Share | What happens |
|---|---|---|
| Intake and environment | 15% | Toolchain, build, first successful scan |
| Recon and comprehension | 15% | Map the app, read the config, build the review list |
| Automated pass | 10% | Scan runs, secrets sweep, dependency inventory |
| Manual targeted review | 40% | The findings live here |
| Validation and evidence | 10% | Prove each one, kill the false positives |
| Reporting | 10% | Write-up plus coverage statement |

The run order that keeps the scans off the critical path:

1. **Intake before provisioning.** Get the build manifests, derive the exact toolchain, request everything in one message.
2. **Build the environment and get one green scan** on the smallest component in scope, even a hello-world, to prove the pipeline works before you fight the real codebase.
3. **Kick off the full analysis in the background.** It takes a while on a large codebase and you do not need to watch it.
4. **Do recon while it runs.** Project structure, entry points, auth model, config files.
5. **Secrets and dependency sweeps**, which are fast and need no build.
6. **Manual review**, the bulk of the time, guided by the recon output.
7. **Triage the scanner output** once, in a single pass, near the end.
8. **Reporting and coverage.**

> **Note:** step 7 is deliberate. Triaging first anchors you to what the tool noticed. Doing recon first means you arrive at the tool's output already knowing which of its findings sit on a path that matters.

## Phase 0: Intake, Before Anyone Touches a Laptop

This phase decides whether the activity runs smoothly or bleeds days. The failure mode is **serial discovery**: request a runtime, find the version is wrong, request the right one, request the scanners, receive the source, find it does not build, request the build toolchain, find you need to know which version first. On a network with no internet egress every round trip costs at least a day, because each missing prerequisite has to be sourced, approved, and moved across by someone else.

The fix is one insight.

### Ask for the build manifests, not the source

You do not need the source code to size the environment. You need the files that describe how it is built, and those are small enough to send in an email or read over a screen share.

| Ecosystem | Manifests to request |
|---|---|
| .NET | `*.sln`, `*.csproj`, `global.json`, `Directory.Build.props`, `nuget.config` |
| Java | `pom.xml`, `build.gradle`, `gradle.properties`, `settings.xml` |
| Node and frontend | `package.json`, the lockfile, `.npmrc`, `tsconfig.json`, framework config |
| PHP | `composer.json`, `composer.lock` |
| Python | `requirements*.txt`, `pyproject.toml`, the lockfile, `.python-version` |
| Ruby | `Gemfile`, `Gemfile.lock`, `.ruby-version` |
| Go | `go.mod`, `go.sum` |

Ask for these before anything is provisioned. Ten minutes reading them yields every version number you are about to request, and it turns four provisioning rounds into one. The per-ecosystem commands for reading them are in [Secure Code Review by Stack](/posts/secure-code-review-by-stack).

### The intake sheet

Send this as a single list. Phrase it as "here is everything the activity needs", not as a series of questions.

**Scope and access**

- Repository list, with the exact commit or tag under review.
- Source delivered as a **repository, not a zip**. History is evidence: deleted secrets, security-relevant commit messages, and the churn signal that tells you which modules to prioritise.
- Line count per repository and per language, so the time estimate is grounded.
- A named developer or architect available for questions. This is the highest-value item on the sheet and the one most often dropped. The OWASP guide is blunt about it: a whiteboard session with the lead architect is the fastest way into an unfamiliar codebase.
- Whether a running instance is reachable from the review network. Even a dev instance turns unprovable findings into proven ones.

**Documentation**

- Architecture or data flow diagrams, however rough.
- Authentication and authorization model: the roles, and what each one is allowed to do. Without this you cannot assess access control at all, only guess.
- API specification, if one exists.
- Previous pentest or code review reports, and the current risk register.
- Any secure coding standard the organisation holds the developers to.

**Build environment, the part that gets forgotten**

- Exact OS for the review workstation, and whether you have local administrator rights.
- Whether an **internal package mirror** (Nexus, Artifactory, Azure Artifacts, a proxying registry) is reachable from the review network. Ask this first, because if the answer is yes most of the offline problem disappears in one config line.
- If there is no mirror, an offline dependency bundle produced on a connected machine.
- How files reach the review machine: an internal file share, a jump host, or removable media, and what approval each route needs.
- Whether anything may be taken **out**, including dependency lists. On some engagements exporting a manifest for an online vulnerability lookup is prohibited, and you need to know that before you plan the dependency work.

**Tooling**

- Analyser version and edition, and who administers it.
- How you get a project token.

### The analyser's own runtime

Do not overlook that the tool has prerequisites of its own, separate from the code it analyses. SonarQube and most Java-based analysers need a JDK, and the required version is dictated by the analyser version, not by preference. There are usually three separate places it matters: the server, the scanner on your workstation, and any language-specific scanner wrapper, which often needs the JDK *and* the language runtime on top of it.

Pin it from the version you were actually given rather than guessing:

```bash
curl -s http://<analyser-host>:9000/api/server/version
```

Then read that exact version's prerequisites in the bundled documentation before requesting a runtime. Requesting the wrong JDK is one of the easiest round trips to waste.

> **Tip:** some scanner distributions ship with a bundled JRE. If you get to choose the download, take that one and the workstation runtime question disappears.

## Phase 1: Building the Environment

### Why some languages need a build and others do not

This is the part that feels arbitrary until you see the mechanism, and it decides most of the environment work.

For compiled languages, security rules typically run **as analyzer plugins inside the compiler**. The workflow is: a `begin` step injects hooks into the build, the build runs and the rules execute during compilation, and an `end` step collects the results. Without the build there is no **semantic model**: no type resolution, no symbol binding, no knowledge of which overload a call resolves to. Most useful rules for those languages need that, which is why the good analysers refuse to offer a "just point at the files" mode rather than silently under-reporting.

| Ecosystem | What the analyser needs | Why |
|---|---|---|
| C#, Java, Kotlin, Go, C/C++ | A successful build | Rules run against a semantic model built by the compiler |
| TypeScript | Source plus resolved dependencies | Types come from declaration files that have to resolve |
| JavaScript, PHP, Python, Ruby | Source only | The analyser parses directly; there is no compile step to ride |

The rule of thumb: **if the language has a compiler, the analyser probably rides along inside it.** The consequence is that dependency resolution has to work, and dependency resolution is the thing that wants a network.

An interpreted backend paired with a compiled one (a common shape) means half the codebase scans immediately and half needs the build fought for. Scan the easy half first so something is running while you work on the other.

### Getting dependencies without internet access

In order of preference.

**Option 1: an internal package mirror.** If a proxying registry is reachable from the review network, this is a config-file fix, and it is by far the most likely to already exist. Point the package manager at it and clear the default public source, so a failed lookup fails fast instead of stalling on a timeout to an unreachable host. That stall is worth knowing about, because the resulting error usually looks like a package problem rather than a network one.

**Option 2: an offline dependency bundle.** Have someone run the normal restore on a connected machine that can already build the project, then move the resulting package folder or cache across and point the review machine at it. Every ecosystem has a verb for this.

**Option 3: the client's own pipeline.** If restore cannot be made to work, ask them to run the analyser in their existing build pipeline against the commit under review and give you access to the resulting project. You lose nothing analytically, you just did not press the button yourself.

**Option 4: build-free analysis**, below.

### If the build cannot be made to work

Do not let this block the activity. Degrade in this order and say so in the report:

- **Pattern-based SAST that needs no build**, such as Semgrep. Fetch the rule packs on a connected machine, move them across, and run fully offline. More noise than a taint engine, and it reads compiled languages without compiling them.
- **Build-free modes in heavier tools.** Some analysers now offer a buildless mode for languages that normally require compilation. Worth the setup only on a longer engagement.
- **Grep sweeps** using the sink lists for the stack. Crude, and genuinely effective on a codebase you have already mapped.
- **The manual pass**, which was always going to produce the important findings anyway.

Scan whatever half of the codebase does not need a build regardless.

### Verification checklist

Confirm each of these before declaring the environment ready:

- The analyser's runtime matches what its version requires.
- Every language runtime and SDK in scope is installed, at the versions the manifests specify. Where a project pins a toolchain version, an unmatched pin fails the build even when a newer version is installed.
- Where several versions are in scope, all of them are installed. Side-by-side installation is usually supported and removes the question.
- The analyser host is reachable from the review machine.
- The project **builds** and dependencies **restore**, confirmed on their own, before the analyser is involved at all.

> **Watch out:** get one complete scan cycle to succeed on the smallest component in scope before pointing the analyser at the real codebase. A failure at the collection step after a twenty-minute build tells you very little about which of the twenty things you changed was wrong.

Two failure modes worth naming because they produce a scan that looks fine and is not. **Incremental builds** skip projects, skipped projects never invoke the analyzer, and coverage silently drops. Force a full rebuild for an analysis run. **Unresolved dependencies** in typed languages degrade type resolution, so type-aware rules quietly produce less. A suspiciously clean result on a large codebase is usually one of these two, not good code.

## Phase 2: Reconnaissance

You now have a codebase you have never seen and a fraction of it you can afford to read. This phase decides which fraction.

### Size it

```bash
cloc --by-file-by-lang .          # or scc, or tokei
git log --oneline | wc -l
git log --since='1 year ago' --name-only --pretty=format: | sort | uniq -c | sort -rn | head -40
```

That last command is the most useful one here. It ranks files by how often they changed in the last year. Churn concentrates in the code that is actively worked on, which is where recently introduced defects are, and it is a better prioritisation signal than directory names.

### Map the application

Build a one-page map before reading any logic. Whatever the stack, you want the same six things:

1. **The entry points.** Every route, endpoint, handler, message consumer, and scheduled job. This is your inventory and your coverage denominator.
2. **The composition root.** The file where middleware, authentication, dependency injection, and framework configuration are wired. It is short and it is the highest-yield reading per line in the codebase.
3. **Every configuration file**, including per-environment overrides. Misconfiguration lives here, and so do secrets.
4. **The data access layer**, and which technology it uses. That decides which injection rules apply and where ownership checks would have to live.
5. **The authentication mechanism**, and where the identity comes from on each request.
6. **The client-side surface**, if there is one: routes, guards, and every call it makes to the backend.

The per-stack commands for each of these are in [Secure Code Review by Stack](/posts/secure-code-review-by-stack).

Then write down, in prose: what the app does, who its users are, what the roles are, where the sensitive data lives, and what the trust boundaries are. The OWASP guide calls this the "context", and everything downstream depends on it. Without it you can find that a method is missing an authorization check but not whether that matters.

### Rebuild the threat model

If they gave you a threat model, read it and check it against the code. If they did not, spend an hour building a light one: assets, actors, entry points, trust boundaries. This is what turns "which few thousand lines" from a guess into a decision. Detail on running that session is in [Threat Modeling](/posts/threat-modeling).

The output you want is a ranked review list, something like:

1. Authentication and token or session issuance.
2. Authorization enforcement across all entry points.
3. Anything handling money, entitlements, or personal data.
4. File upload and download.
5. Admin functionality.
6. Third-party integrations and outbound calls.
7. Cryptography and secret handling.
8. Everything else, sampled.

## Phase 3: The Automated Pass

### Secrets

Fast, needs no build, no network, and produces findings on most codebases:

```bash
gitleaks detect --source . --report-path gitleaks.json
trufflehog filesystem . --no-verification
```

Run these against the **repository history**, not just the working tree. A credential removed in a later commit is still in the repository and still needs rotating, and this is one of the strongest arguments for asking for a repository rather than a zip during intake.

Then read the configuration files by hand anyway. Connection strings with embedded passwords, API keys in committed environment files, and signing keys checked in as plain strings are common, and the automated tools miss the ones that do not look like credentials.

### Dependencies

This is the part no internal mirror solves, because every vulnerability database lives on the internet. The package manager's own audit command queries a live feed and will simply fail.

The workable approaches:

- **Pre-seeded local databases.** Trivy, OSV-Scanner, and OWASP Dependency-Check can all run offline if their database is downloaded on a connected machine and moved across. Request this in intake, since it needs planning.
- **Export the inventory, check it outside.** Produce the dependency list on the review machine, take it out, look it up on a connected machine. **Confirm in intake that taking the list out is permitted**, because on some engagements it is not.

If neither is possible, say so plainly in the report. "Dependency vulnerability analysis was not performed because no vulnerability database was reachable from the review environment" is a legitimate scope limitation. Quietly omitting the section is not.

## Phase 4: The Manual Review

Three techniques, run in this order. The first two are the OWASP guide's "crawling code" idea split into its two directions.

### Technique 1: the entry point walk (top down)

Take the entry point inventory from recon and walk it. For each one, answer six questions. Keep the answers in a spreadsheet, because that spreadsheet becomes your coverage evidence.

1. **Is authentication required?** Check the framework's default. If unannotated handlers are public by default rather than denied by default, then every handler someone forgot to annotate is anonymous, and that is easy to do by accident.
2. **Is authorization enforced, and at what granularity?** An authentication check alone only proves the caller is *someone*. A role check proves they are the right kind of someone. Neither proves they own the object being addressed.
3. **Is object ownership checked?** This is the big one. Follow the identifier parameter into the data access layer. Does the query filter on the caller's identity, or only on the identifier from the request? A lookup by ID with no owner predicate is an IDOR, and no scanner will tell you.
4. **How is the request body bound?** If the handler binds directly to a persistence model rather than an explicit input type, every field on that model is settable by the caller, including the ones that decide privilege or price. This is mass assignment and it is a privilege escalation in one line.
5. **What comes back?** Serialising a persistence model straight to the response returns every column, including the password hash, the internal notes, and the soft-delete flag.
6. **What happens on error?** Is the exception caught, and does the caller see the message?

You will not do all six for two hundred endpoints. Do all six for the entry points your threat model ranked, and do questions one and three for **every** entry point, because those two are cheap and catch the worst findings.

### Technique 2: the sink sweep (bottom up)

Grep for dangerous APIs, then trace each hit backwards to see whether attacker-controlled data reaches it. Most hits will be safe. The point is that the ones that are not are found in minutes rather than by chance.

The categories are the same in every language, and only the spelling changes:

- **Query construction**: anything that builds a query from a string rather than binding parameters.
- **Command execution**: process spawning, shell invocation.
- **Deserialization**: any decoder that can instantiate arbitrary types from input.
- **XML parsing**: external entity resolution left enabled.
- **File path handling**: paths joined from request data.
- **Outbound requests**: URLs taken from input, and disabled certificate validation.
- **Template and HTML output**: anything that marks a string as trusted or escapes-by-default being turned off.
- **Cryptography and randomness**: broken primitives, hardcoded keys and IVs, general-purpose random used for security values.
- **Redirects**: destinations taken from request data.

The per-language patterns for each category are in [Secure Code Review by Stack](/posts/secure-code-review-by-stack).

### Technique 3: client to server control mapping

This applies to any architecture where a client enforces something the server also has to.

Client-side route guards, hidden menu items, and disabled form fields are **user interface convenience, not security**. They run in code the user controls. Each one is therefore a claim the developer made about who should reach something, and the server is the only place that claim can be enforced.

So: list every guarded client route or conditionally rendered privileged control, find the endpoints behind it, and check whether the server enforces the same restriction.

Every mismatch is a finding. A client route restricted to an admin role whose backing endpoint carries only a generic authentication check means any authenticated user can call the admin function directly. This is broken function level authorization, it is common, and it is invisible to a scanner looking at either project on its own. It is also the clearest argument for reviewing frontend and backend as one system rather than two.

### Cross-cutting configuration review

Read these completely, top to bottom. They are short, dense, and per line the highest-yield reading in the whole activity.

- **The composition root.** Middleware order is security-relevant: an authorization filter that runs before authentication populates the identity checks an empty identity. Error-detail middleware outside an environment guard leaks stack traces in production. Check whether the default is deny or allow.
- **Token and session validation.** Every validation flag, individually. Issuer, audience, expiry, and signature validation each disabled independently, and each one is a finding on its own. A signing key read from a committed config file is both a validation weakness and a hardcoded secret.
- **CORS.** The dangerous pattern is rarely a literal wildcard, because most frameworks reject wildcard-plus-credentials at runtime. It is a predicate that reflects any origin while allowing credentials.
- **Cookies and CSRF.** The `HttpOnly`, `Secure`, and `SameSite` attributes on session cookies, and whether state-changing handlers carry antiforgery protection. If the API is purely token-authenticated, note that CSRF does not apply and say why, rather than leaving it unaddressed. Background in [Cross-Site Request Forgery](/posts/cross-site-request-forgery).
- **Environment overrides.** Compare the base configuration against the production one and note what the override does, or fails to do. Debug flags and detailed errors surviving into production are common.

## Phase 5: Validating Findings

### Triaging the scanner output

Filter before you read. On a large codebase the tool will produce thousands of issues, and the great majority are maintainability findings that are not yours to report.

- Filter to security categories using the tool's own type filter rather than reading the issue list.
- Treat every "hotspot" or equivalent as a **question, not a finding**. That is what the category means: code that needs a human decision, not code that is wrong.
- For each candidate, open the file and trace the flow yourself. Confirm the source is genuinely attacker-controlled, confirm nothing between the source and the sink neutralises it, and confirm the code is reachable.
- Look for **rule clusters**. Forty instances of the same rule in the same module is usually one design decision, not forty findings. Report it once, list the instances in an appendix, and describe the pattern rather than the occurrences.

Discard aggressively and keep a note of what you discarded and why. "1,847 issues raised, 1,203 maintainability and excluded from scope, 644 reviewed, 12 confirmed" is a sentence worth putting in the report, because it shows the triage happened.

> **Danger:** never copy a scanner finding into a report unverified. The first client developer who opens the file and shows you the sanitiser you did not read costs you the credibility of every other finding in the document.

### What a finding needs

- **Location**: file path and line number, plus the commit hash. Without the commit, line numbers are meaningless in three weeks.
- **The code**, quoted, with enough surrounding context to be readable.
- **The data flow**: where the untrusted value enters, the path it takes, the sink it reaches. This is what separates a code review finding from a linter warning.
- **Why the existing controls do not cover it.** Pre-empt the developer's first objection, because they will have one.
- **Impact in the application's own terms.** Not "SQL injection" but "any authenticated user can read the full customer table via the order search parameter".
- **A fix**, at the code level, in their idiom and their framework.
- **A severity**, using the client's scale or CVSS, applied consistently.

Where a running instance is available, confirm the finding against it. A code review finding backed by a working request is much harder to defer.

## Phase 6: Reporting

### The coverage statement

This is the section that matters most on a time-boxed review and the one most often left out. State plainly:

- Which repositories and which commits were reviewed.
- Total lines of code, and which modules received deep manual review against which were covered by automation only.
- Which items from the Phase 2 review list were completed and which were not reached.
- What could not be assessed, and why: no dependency database reachable, a component that could not be built, no running instance to confirm against, no developer access for questions.

Two reasons to write it. Professionally it is the honest description of what the client bought, and it protects you when something is later found in a module you never opened. Practically it is the strongest argument for the next engagement, because a client reading "authentication and payment modules received full manual review, the reporting module was covered by automated analysis only" can see exactly what more time would buy.

### Structure

Separate the two streams so the reader can see where each finding came from:

1. Executive summary, written for someone who will not read past page two.
2. Scope, methodology, and the coverage statement.
3. Findings from manual review, ordered by severity.
4. Findings from automated analysis, confirmed and triaged, ordered by severity.
5. Observations and hardening notes: things that are not vulnerabilities but should change.
6. Appendices: full tool output, dependency inventory, the entry point coverage spreadsheet.

Putting the manual findings first is not vanity. It is where the serious issues are, and it sets the reader's expectation that this was a review rather than a scan.

## Condensed Intake Checklist

Before provisioning, in order:

1. Request the build manifests for every ecosystem in scope.
2. Derive from them: every runtime and SDK version, and whether any component needs a build the review machine cannot perform.
3. Get the analyser version and **edition**, and derive its runtime requirement from that version.
4. Ask whether an internal package mirror is reachable. If yes, most of the offline problem disappears.
5. If no mirror, request an offline dependency bundle produced from the exact commit under review.
6. Request in the same message: the scanner archives, a developer contact, the authorization model, and confirmation on how files move in and out.
7. Verify the toolchain, then get one green scan on the smallest component before touching the real codebase.
8. Start the full scan in the background, and begin recon while it runs.

The pattern underneath all of it: **every question you answer before provisioning saves a day, and every question you discover afterwards costs one.**

> The per-ecosystem manifests and sink patterns are in [Secure Code Review by Stack](/posts/secure-code-review-by-stack).
