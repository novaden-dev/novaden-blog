---
author: Kayra
pubDatetime: 2026-05-27T00:00:00Z
title: DevSecOps Foundations
slug: devsecops-foundations
featured: false
draft: false
tags: ["devsecops", "security"]
category: notes
description: What DevOps and DevSecOps actually are, why CI/CD matters, the tool categories you stitch together, and how SCA, SAST, DAST, IaC, CaC, and vulnerability management fit into a pipeline.
---

## Introduction

DevOps is the integration and automation of software development, security and quality testing, and operations. The goal is to shrink the time between committing a change and shipping it to production. It is a mix of practices, culture, and tooling, and its motivations come straight out of Agile.

DevSecOps is DevOps with security folded into every phase of that lifecycle, not bolted on at the end. The promise is the same as DevOps (speed and reliability) plus security checks running inside the same workflows that build and deploy the code.

## CI/CD: the Core of DevOps

Two ideas sit at the centre of DevOps:

- **Continuous Integration (CI)**: small changes merged into a main branch frequently, with automated builds and tests running on every merge.
- **Continuous Delivery (CD)**: producing release-ready software in short cycles. The build is always in a deployable state, even if a human still clicks the button.
- **Continuous Deployment (also CD)**: the strict form, where every change that passes the pipeline is rolled out to production automatically.

CI/CD is what actually bridges development and operations.

### Benefits of DevOps

- **Accelerate time to market**: continuous deployment, automation, and tighter collaboration cut the lag between an idea and a shipped feature.
- **Adapt to the market and competition**: short release cycles let teams react to customer feedback and competitive pressure instead of being locked into a quarterly plan.
- **Maintain system stability and reliability**: continuous improvement, automated tests, and safe-deployment practices reduce failures and the blast radius of the ones that get through.
- **Improve mean time to recovery (MTTR)**: when something does break, automation and observability shrink the gap between "we noticed" and "we fixed it".

### Benefits of DevSecOps

- **Speed and security together**: security checks run inside the same pipeline as builds and tests, so neither slows the other down once tuned.
- **Faster vulnerability management**: scanning and patching are part of the release cycle, shrinking the window an attacker has against a known issue in production.
- **Simplified compliance**: controls are codified and continuously evaluated, so projects don't have to be retrofitted for compliance at the end.
- **Shared responsibility**: application and infrastructure security become a shared concern of dev, sec, and ops, rather than the sole job of an isolated security team.

"Shift left", automation, and continuous monitoring are the **practices** that deliver those benefits, not benefits in themselves.

## The Tool Categories

DevOps is not one tool; it's a set of categories you wire together.

| Category | What it does | Common tools |
| --- | --- | --- |
| **Source Code Management (SCM/VCS)** | Track and record changes to the codebase, collaborate on a structured history. | Git, GitHub, GitLab |
| **CI/CD** | Run defined stages and jobs against the code (build, test, deploy). | GitHub Actions, GitLab CI/CD, Jenkins, Travis |
| **Artifact Manager** | Store, organise, and distribute binaries, packages, and container images produced by the build. | Docker Registry, JFrog Artifactory, Nexus |
| **Platform** | On-demand compute, storage, and network. | AWS, Azure, GCP |
| **Infrastructure as Code (IaC)** | Provision and manage infrastructure with code instead of clicks. | Terraform, Ansible |
| **Containers** | Package the app and its runtime so it runs the same everywhere. | Docker |
| **Monitoring** | Watch the system in production: performance, resource usage, logs. | ELK stack (Elasticsearch, Logstash, Kibana), Prometheus, Grafana |

The mental model for images, containers, registries, networking, and volumes lives in [Docker Foundations](/posts/docker-foundations).

## The DevSecOps Maturity Model (DSOMM)

DSOMM is an OWASP project that measures how mature a DevSecOps practice actually is. The current model is structured as **5 dimensions, 18 sub-dimensions, and 167 activities**, with **5 maturity levels** per sub-dimension. Not every sub-dimension defines all five levels; the model only includes a level where it's meaningful for that topic.

The five top-level dimensions:

- **Build and Deployment**: how the pipeline itself is structured.
- **Culture and Organization**: training, ownership, security champions.
- **Implementation**: hardening, secrets handling, secure defaults.
- **Information Gathering**: logging, monitoring, attack surface inventory.
- **Test and Verification**: the security scans and what they cover.

Inside "Test and Verification", the sub-dimensions most often cited when talking about scan coverage are:

- **Dynamic depth**: how deep dynamic scans (DAST) reach into the running app.
- **Static depth**: how deep static analysis (SAST/SCA) reaches into the source.
- **Test intensity**: how often the scans run.
- **Consolidation**: how findings are handled (deduplicated, triaged, tracked).

A rough sketch of what the five maturity levels mean in practice:

- **Level 1**: the tool is running, with no real tuning. Findings exist somewhere.
- **Level 2**: minimal tweaks, basic rules applied, results visible to the team.
- **Level 3**: tuned to the codebase, false positives managed, results actioned in a regular cadence.
- **Level 4**: integrated with vulnerability management, gating on severity, ownership defined.
- **Level 5**: continuous metrics, SLOs around MTTR, the practice is self-improving and benchmarked.

The point of DSOMM isn't the exact rubric; it's to give a team a shared way to say "we're a Level 1 SCA shop, let's get to Level 2 next quarter" instead of arguing about whether security is "good". For the full activity catalogue, see [dsomm.owasp.org](https://dsomm.owasp.org).

## How a Pipeline Actually Works

A **pipeline** is a system of stages that continuously integrates, delivers, or deploys software.

- A **stage** is a group of **jobs** that share a goal (build, test, deploy).
- Jobs in a stage run **in parallel**. When all jobs in a stage succeed, the pipeline moves to the next stage.
- If a job fails, the next stage is usually skipped. GitHub Actions defaults to "resume on failure", GitLab CI defaults to "stop". Configurable on both.
- Success and failure are determined by **exit codes**. `0` means success; anything else is a failure. The job typically inherits the exit code of its last command.
- **Tags** decide which branches or runners a job is allowed to use.
- Jobs can be marked as **non-blocking**, so they run but don't break the pipeline. The keyword differs by tool: GitLab CI uses `allow_failure: true` (and marks the pipeline green), GitHub Actions uses `continue-on-error: true` (and still marks the workflow red, but proceeds), Jenkins handles it through `catchError` or `unstable` post conditions.
- Jobs can require **manual approval** before they run (useful for prod deploys).
- **YAML** (YAML Ain't Markup Language) is what almost every CI system uses to describe pipelines.
- **Rules** decide whether a job runs at all (e.g. only when a specific file changes, only on the main branch).

### Engineering Hygiene for Pipelines

These aren't security-specific, but they're what makes a pipeline survive contact with a real team:

- **Budget the time**: any single job that takes more than ~15 minutes is a bad fit for the per-commit pipeline. Move it to a scheduled job (nightly, hourly) so commits don't queue behind it.
- **One concern per job**: failures are easier to debug when one job does one thing.
- **Roll new tools out in phases**: start as non-blocking and informational, then promote to gating once the signal is trustworthy.
- **Gate on severity, not noise**: fail on critical/high, warn on the rest. Otherwise the build turns red constantly and people learn to ignore it.
- **Test locally first**: CI is not a debugger. Give every job a documented `docker run` equivalent a developer can reproduce.

### Securing the Pipeline Itself

The pipeline is part of the attack surface. The authoritative guidance lives in a few places:

- **OWASP Top 10 CI/CD Security Risks**: insufficient flow control, poisoned pipeline execution, insufficient credential hygiene, insecure system configuration, ungoverned plugin usage, and the rest.
- **NIST SP 800-204D**: software supply chain security controls mapped to DevSecOps. Calls for artifact integrity checks, continuous SBOM generation, provenance validation.
- **SLSA framework**: tiered levels for protecting build systems against tampering.

The shared themes:

- **Secrets in a vault**, not in environment variables in plain text. HashiCorp Vault, AWS/GCP/Azure secret managers. Rotate.
- **RBAC on the pipeline**, with separation between who can approve a release and who can deploy it.
- **Sign and verify artifacts**: produce an SBOM, sign images, verify signatures at deploy.
- **Pin pipeline plugins and actions to commit SHAs**, not floating tags.
- **Treat the runner as hostile**: short-lived, network-restricted, no long-lived secrets on disk.

## Picking a Security Tool

Most of the criteria for choosing between two scanners are the same regardless of whether the scanner is SCA, SAST, DAST, or something else. Pick on:

- **Language and stack support**: covers the languages, package managers, and frameworks you actually use.
- **Output format**: emits a structured report (JSON, XML, SARIF) you can pipe into a vulnerability manager. Plain-text or PDF-only output is a dead end.
- **API support**: results can be fetched or uploaded programmatically.
- **Ignore and allowlist**: lets you suppress confirmed false positives without editing source. Per-finding and per-file granularity.
- **Severity gating**: can fail the build on critical/high and only warn on lower. Don't accept "fail or pass" as the only modes.
- **Local execution**: can be run on a developer laptop before push, not just in CI. Otherwise developers learn from the pipeline instead of fixing pre-push.
- **Pricing model**: free, open-source, per-developer, per-scan. Some "free" tools cap private repos or rate-limit aggressively.
- **False positive rate**: the single biggest predictor of whether a team will actually keep the tool turned on. The work of confirming that a finding isn't a real issue is called **False Positive Analysis (FPA)**; every tool generates some, and a noisy one can quietly consume more engineer-hours than the bugs it would have caught.
- **Speed**: under the ~15-minute per-commit budget. If a scan is slower than that, schedule it as a nightly job instead of running it on every commit.


## Security in the Pipeline

Most DevSecOps tooling falls into a handful of well-known categories. Each gets its own job in the pipeline.

### Software Component Analysis (SCA)

SCA is a static technique for finding security vulnerabilities in **third-party components**: npm packages, Python wheels, Go modules, OS packages, container base image layers. It does not look at your own source; it looks at what you imported.

It works by comparing the dependency manifest (`package-lock.json`, `requirements.txt`, `go.sum`, etc.) against vulnerability databases (NVD, GitHub Advisory Database, OSV). A match means a CVE has been published for a version you're pulling in.

**Use cases:**

- Block PRs that introduce a known critical CVE in a transitive dependency.
- Nightly scan of the main-branch lockfile to catch CVEs published *after* you merged.
- Pre-build scan of base container images so an Alpine release with a kernel CVE isn't shipped silently.
- License compliance, when the same tool maps package licenses to a policy.

**Benefits:**

- Cheap to run, fast, language-aware.
- Low false-positive rate compared with SAST/DAST because the result is "this version of this package has CVE-X" — verifiable.
- Catches issues in code you'd never read yourself (deep transitive deps).

**Shortcomings:**

- Only finds **known** vulnerabilities. Zero-days are invisible until disclosed.
- Transitive dependency noise can drown the signal. A direct dep pulls in 200 transitives, and one of them has a "medium" finding nobody can reach from your code.
- "Reachability" is rarely answered: the CVE may exist in a function you never call.
- Different databases disagree on severity. Treat the vendor's CVSS as a starting point, not a verdict.

**Common tools:** `safety`, `RetireJS`, `OWASP Dependency-Check`, `Snyk`, `npm audit`, `bundler-audit`, `Composer Audit`, `Renovate`, `Dependabot`, `OSV-Scanner`, `OSV-Scalibr`, `Semgrep` (with rule packs), `Trivy`, `Sandworm`, `pip-licenses` (license-focused).

### Static Application Security Testing (SAST)

SAST analyses **your own source code** for security vulnerabilities without running it. It walks the AST, follows variable flow, and matches against patterns (SQL string concatenation, unsafe deserialization, command injection sinks).

**Secrets scanning** is a sub-category of SAST. It runs on the same source tree but targets credentials specifically, using two detection strategies:

- **Regex**: match against known formats (AWS keys, GitHub tokens, Stripe keys).
- **Entropy**: flag strings random enough to look like a key or password, even if no format is recognised.

**Use cases:**

- Run on every PR, ideally against the diff only for speed.
- Pre-commit hook for secrets (cheaper to catch them before they ever leave the laptop).
- Language- or framework-specific scans on dedicated paths (`bandit` against Python services, `gosec` against Go services, `hadolint` against Dockerfiles).

**Benefits:**

- Catches code-level patterns no runtime test would surface.
- Runs without a deployed environment.
- Cheap to integrate per-language.

**Shortcomings:**

- **High false-positive rate** is the defining problem. Industry write-ups consistently put out-of-the-box rates at 60–90%, dropping to 10–20% only after serious tuning. The cause is **taint analysis**: the scanner tries to follow untrusted data from where it enters the program (a "source", like an HTTP parameter) to where it could do damage (a "sink", like an SQL query). Without running the code, that flow has to be approximated across function calls, classes, virtual dispatch, and framework conventions. Where the approximation breaks, the scanner either invents bugs (false positive) or misses real ones (false negative).
- **Blind to runtime and environment** issues. A wide-open S3 bucket, a missing security header, a misconfigured reverse proxy — none of those are visible in the source.
- **Blind to business logic and authorisation bugs**. SAST can spot SQL injection in a query string, but it cannot tell you that a normal user shouldn't be able to call `/admin/delete-account`.
- **Slow on large monorepos** unless scoped to the diff.
- Secrets scanners flag plenty of high-entropy strings that aren't secrets (UUIDs, hashes, base64-encoded test fixtures).

**Common tools (security-focused):** `TruffleHog`, `detect-secrets`, `Talisman`, `Gitleaks`, `Kingfisher` (secrets); `Bandit` (Python), `Brakeman` (Ruby/Rails), `gosec` (Go), `hadolint` (Dockerfile), `FindSecBugs` / `SpotBugs` (Java), `njsscan` (Node.js), `Semgrep`, `SonarQube`, `Bearer` (data-flow / PII).

### Dynamic Application Security Testing (DAST)

DAST exercises a **running** application to find security vulnerabilities. It probes the app like an attacker would, with no source-code knowledge required. The scanner crawls the routes, fuzzes inputs, and observes responses.

**Use cases:**

- Nightly baseline scan against staging.
- Post-deploy smoke scan after a release.
- Authenticated scan against a long-lived test environment to cover paths behind login.
- TLS configuration audit of a public endpoint (a narrow but useful slice of DAST).

**Benefits:**

- Tests the system as it actually runs, including config and infrastructure issues SAST can't see (open CORS, missing security headers, weak TLS, misrouted ports).
- Language-agnostic. The scanner doesn't care if the backend is Go, Python, or PHP.
- Low false-positive rate on the issues it can actually confirm (it observed the response).

**Shortcomings:**

- **Late in the lifecycle**: by definition, DAST needs a deployed application. Issues caught here are more expensive to fix than the same issues caught at SAST time, because the change has already passed code review, been merged, and been deployed.
- **Coverage is bounded by what the crawler can reach**. State-heavy flows, multi-step forms, SPA routes, and pages behind unusual auth get skipped without manual help. Whatever the crawler doesn't reach, the scanner doesn't scan.
- **Misses business logic bugs**. DAST sees that an endpoint responds; it doesn't know that the response shouldn't include another user's order details.
- **Misses code-level bugs that never surface through HTTP**, like a buggy CLI tool, a worker that processes a queue, or a library function called only from internal services.
- **Active scans can mutate data**. Run against staging or an ephemeral environment, never prod, unless the scan is explicitly read-only.

**Common tools (by purpose):**

- **General web DAST**: `OWASP ZAP`, `Dastardly` (PortSwigger), `Nikto`.
- **Template-driven scanning**: `Nuclei` (with `Katana` as the upstream crawler that feeds it).
- **TLS-specific**: `SSLyze`, `testssl.sh`.
- **Network/service discovery**: `Nmap` (more recon than DAST, but commonly slotted in).
- **Pipeline-friendly orchestration**: `Gauntlt`.

## Infrastructure as Code (IaC)

IaC is the practice of creating, managing, and destroying infrastructure as if it were code, by applying software-development practices (review, version control, testing) to operations work.

Three concerns make up the IaC stack:

- **Platform**: the underlying compute, storage, and network. AWS, GCP, Azure.
- **Infrastructure definition**: the files that declare what infra should exist on that platform. Terraform, OpenTofu, CloudFormation, Pulumi.
- **Configuration tools**: the tools that tweak the infrastructure once provisioned, applying configs, images, and settings. Ansible, Chef, Puppet.

**Use cases:**

- Stand up a new environment (staging, prod, per-PR ephemeral) from scratch in minutes.
- Tear down ephemeral environments cleanly when a PR closes.
- Codify hardening baselines (CIS, NIST) and apply them uniformly.
- Reproduce a prod-shaped lab for debugging or load testing.

**Benefits:**

- Repeatable and diffable: the change to your network is a Git PR like any other.
- Drift-detectable: you can ask "does prod still match the code?".
- Faster recovery: lose a region, terraform-apply elsewhere.

**Shortcomings:**

- **State** is fragile. Terraform's state file is the source of truth for what *exists*; if it diverges from reality, every plan lies.
- **Blast radius** is huge. One bad `apply` can wipe a VPC. Strict review and plan output is non-negotiable.
- **Tool lock-in**: switching IaC tools is expensive once you have hundreds of resources.
- Security mistakes scale too: an over-permissive IAM role written once gets replicated everywhere.

### Terraform

Terraform (and its open-source fork **OpenTofu**) is the most common infrastructure-definition tool. It is **declarative**: you describe the desired state, Terraform diffs it against reality and produces a plan to reach it.

Key pieces:

- **Providers**: plugins that know how to talk to a specific API (AWS, GCP, GitHub, Cloudflare, Kubernetes). Hundreds exist.
- **Resources**: declarations of what you want to exist (`aws_vpc`, `aws_instance`). The unit of management.
- **Data sources**: read-only lookups into existing infrastructure.
- **Variables and outputs**: parameterise modules and expose values.
- **Modules**: reusable bundles of resources you can call with inputs. The Terraform equivalent of a function.
- **State**: a JSON record mapping declarations to real resource IDs. Stored locally by default, but for any team you push it to a remote backend (S3 + DynamoDB lock, Terraform Cloud, GitLab-managed state) so two engineers don't apply at the same time.
- **`plan` and `apply`**: `plan` shows the diff between code and reality; `apply` executes it. Always review the plan output; never apply unreviewed.

> **Gotcha:** Terraform plans look harmless until you read them. A line that says `- aws_db_instance.main` (note the minus sign) means a database is about to be **destroyed**. Add `prevent_destroy = true` to stateful resources, and keep state and credentials behind tight access controls.

### Ansible

Ansible is **agentless**: it pushes changes over SSH (or WinRM on Windows) instead of running a daemon on every target. Where Terraform shines at provisioning infrastructure, Ansible shines at configuring what's inside it: installing packages, writing config files, restarting services, applying hardening.

Its core pieces:

- **Modules**: executable code (libraries) that run on target nodes. Modules are the units of work that touch files, services, packages.
- **Tasks**: the smallest executable units in Ansible. One module invocation with arguments.
- **Roles**: groupings of related tasks, files, templates, and variables. Distributable via Ansible Galaxy.
- **Playbooks**: YAML files describing which tasks/roles to apply to which hosts, in what order. The thing you actually run.
- **Inventory**: the list of servers Ansible should manage, grouped by purpose (`[web]`, `[db]`, `[prod]`).

Before connecting to a new host you'll typically populate the SSH known-hosts file so Ansible doesn't get blocked at the first connection:

```bash
ssh-keyscan -H prod-host staging-host build-host >> ~/.ssh/known_hosts
echo "StrictHostKeyChecking accept-new" >> ~/.ssh/config
```

## Compliance as Code (CaC)

CaC is the technique of automating compliance and managing it as code. The same logic as IaC: instead of a PDF checklist, you have a machine-readable specification of "this host must look like X" that runs on a schedule.

A CaC tool defines **controls** (e.g. "SSH password authentication must be disabled"), executes them against a target, and emits structured pass/fail results. The same controls can be run pre-deploy as a gate, nightly as drift detection, and on demand as evidence for an auditor.

**Use cases:**

- Nightly drift detection against prod hosts: did anyone change something out-of-band?
- Pre-deploy gate that fails the pipeline if the target host doesn't meet a baseline.
- Audit evidence: produce a dated, signed JSON report instead of taking screenshots.
- Comparing two environments (prod vs staging) for parity.

**Benefits:**

- Continuous evidence instead of point-in-time audits.
- Findings are machine-readable, so they go into the same vulnerability manager as scanner output.
- Same tool, same baseline runs against every host, every time.

**Shortcomings:**

- Controls drift behind reality: a new TLS cipher gets standardised and your baseline still flags it.
- False positives on hardening rules are common (a host has a justified exception that the baseline doesn't know about).
- Doesn't replace human review for nuanced requirements (data-handling policies, retention).
- Authoring custom controls is a real investment; off-the-shelf baselines rarely fit exactly.

**Common tools:** **InSpec** (now Chef Inspec) and **CinC Auditor** (its open-source fork) are the usual choices. The `dev-sec` community baselines (Linux, Windows, SSH, MySQL, Nginx) are a good starting point.

## Vulnerability Management

Pipelines generate findings. A lot of them, from different tools, in different formats, across products and environments. Vulnerability management is the discipline (and the tool that supports it) of getting from "raw scanner output" to "the right person fixing the right thing at the right time".

A good vuln-management system does the following:

- **Ingest** structured reports from every scanner (SCA, SAST, DAST, secrets, CaC) via API or parser.
- **Deduplicate** the same finding reported by multiple tools or multiple runs.
- **Map** each finding to a product, an engagement (a scope of work), an environment, and an owner.
- **Triage**: mark findings as confirmed, false positive, accepted risk, or duplicate.
- **Track over time**: when did this finding first appear, when did it close, what was the time-to-fix?
- **Push** to an issue tracker (Jira, GitLab, GitHub Issues) so engineers see findings where they already work.
- **Report** on metrics: open findings by severity, MTTR by severity, scanner coverage per product.

**Use cases:**

- Single pane of glass for security and engineering leads.
- Reduce duplicate noise when SCA, SAST, and a container scanner all flag the same upstream CVE.
- Produce evidence for compliance frameworks (SOC 2, ISO 27001): "here are all open criticals, here is MTTR over 90 days".
- Enforce SLOs: criticals fixed within 7 days, highs within 30, etc.

**Benefits:**

- Findings stop dying in CI job logs.
- Same workflow, regardless of which scanner produced the finding.
- Auditable history of who decided what and when.

**Shortcomings:**

- **The "vulnerability backlog" problem**: the average enterprise runs dozens of security tools, each generating findings faster than engineers can close them. A vuln manager surfaces the scale of the backlog, it doesn't shrink it on its own.
- **Prioritisation by raw CVSS is broken**. A "Critical" finding on an isolated test host isn't the same risk as a "High" on a payment gateway. Effective use requires layering business context (asset criticality, reachability, exposure) on top of the scanner-reported severity, and most teams underinvest in that work.
- **Garbage in, garbage out**: if scanner output is noisy, the vuln manager is just a louder mirror. Tuning the upstream scanners matters more than the manager itself.
- **Triage culture matters more than the tool**. Without explicit ownership and SLOs, findings accumulate indefinitely regardless of how good the dashboard looks.

**Common tools:** **DefectDojo** (open-source, the most common pick), **Dependency-Track** (specifically for SCA/SBOM workflows), and a long tail of commercial platforms (Snyk, Veracode, GitHub Advanced Security, GitLab Ultimate's vulnerability reports).

The pattern in a pipeline is the same regardless of which tool you pick:

1. Every scanner job emits a structured report (JSON, XML, SARIF).
2. An upload step pushes the report into the vulnerability manager via API, tagged with product, engagement, environment, and a lead.
3. The manager deduplicates against existing findings and surfaces only what's new.
4. Tickets get created (or not) based on severity rules.

> **Quick reference:** the pipeline YAML, Docker-based scanner snippets, and DefectDojo upload patterns live in the [DevSecOps Cheat Sheet](/posts/devsecops-cheatsheet).
