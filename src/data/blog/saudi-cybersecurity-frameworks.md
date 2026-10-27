---
author: Kayra
pubDatetime: 2026-10-27T00:00:00Z
title: "Saudi Cybersecurity Frameworks: NCA and SAMA"
slug: saudi-cybersecurity-frameworks
featured: false
draft: false
tags: ["compliance"]
category: notes
description: "The NCA and SAMA cybersecurity frameworks: who each applies to, how the ECC and SAMA CSF are structured, the control sets built on top of them, and what each requires for vulnerability assessment, penetration testing and code review."
---

## Introduction

Two regulators set most of the cybersecurity requirements in Saudi Arabia. The National Cybersecurity Authority (NCA) sets the national baseline, the Essential Cybersecurity Controls (ECC), plus extra control sets for specific contexts such as critical systems, cloud and OT. The Saudi Central Bank (SAMA) regulates banks, insurance companies, financing companies and other financial institutions, and sets their cybersecurity requirements through its Cyber Security Framework (SAMA CSF). An entity that falls under both has to meet both.

<figure class="diagram not-prose">
<div class="dg-pair">
<div class="dg-box"><b>NCA ECC</b><span>Government agencies, their affiliated companies and entities (inside and outside the Kingdom), and private sector entities that own, operate or host Critical National Infrastructure (CNI).</span></div>
<div class="dg-box"><b>SAMA CSF</b><span>SAMA-regulated entities: banks, insurance and reinsurance companies, financing companies, credit bureaus and the financial market infrastructure.</span></div>
</div>
<div class="dg-box dg-base" style="margin-top:0.5rem"><b>Both</b><span>An entity in both groups, such as a bank that owns or operates CNI, is assessed against the ECC and the SAMA CSF.</span></div>
<figcaption>Figure 1: Who each baseline applies to. Scope wording from ECC-2:2024 and SAMA CSF v1.0, section 1.4.</figcaption>
</figure>

## The two regulators

| Regulator | Scope | Frameworks |
|---|---|---|
| **NCA**, National Cybersecurity Authority | National: government entities and CNI operators | ECC, CSCC, CCC, DCC, OTCC, TCC, OSMACC, NCS |
| **SAMA**, Saudi Central Bank | Financial sector | Cyber Security Framework, IT Governance, Business Continuity, Threat Intelligence Principles, FEER, Counter-Fraud, Cyber Resilience Fundamental Requirements |

Other regulators have sector rules of their own: SDAIA and the NDMO (personal data and the PDPL), CST (telecom and ICT) and CMA (capital markets).

## NCA frameworks

### The Essential Cybersecurity Controls (ECC)

The ECC is the national minimum. Every other NCA control set assumes the entity already meets the ECC and adds controls for one context.

The current version is ECC-2:2024, which replaced ECC-1:2018:

| | ECC-1:2018 | ECC-2:2024 |
|---|---|---|
| Main domains | 5 | 4 |
| Subdomains | 29 | 28 |
| Controls | 114 | 108 main controls and 92 subcontrols |

The fifth domain in ECC-1, Industrial Control Systems, is gone from ECC-2. OT requirements now live in the OTCC. The subdomain numbers used for testing (1-6, 2-10, 2-11, 2-15) are the same in both versions.

| Domain | Subdomains |
|---|---|
| 1. Cybersecurity Governance | 1-1 Strategy, 1-2 Management, 1-3 Policies and Procedures, 1-4 Roles and Responsibilities, 1-5 Risk Management, 1-6 Cybersecurity in IT Project Management, 1-7 Compliance with Standards, Laws and Regulations, 1-8 Periodical Review and Audit, 1-9 Cybersecurity in Human Resources, 1-10 Awareness and Training |
| 2. Cybersecurity Defense | 2-1 Asset Management, 2-2 Identity and Access Management, 2-3 Information Systems and Processing Facilities Protection, 2-4 Email Protection, 2-5 Network Security, 2-6 Mobile Devices Security, 2-7 Data and Information Protection, 2-8 Cryptography, 2-9 Backup and Recovery, 2-10 Vulnerability Management, 2-11 Penetration Testing, 2-12 Event Logs and Monitoring, 2-13 Incident and Threat Management, 2-14 Physical Security, 2-15 Web Application Security |
| 3. Cybersecurity Resilience | 3-1 Cybersecurity Resilience Aspects of Business Continuity Management |
| 4. Third-Party and Cloud Computing Cybersecurity | 4-1 Third-Party Cybersecurity, 4-2 Cloud Computing and Hosting Cybersecurity |

Controls are numbered domain, subdomain, control, subcontrol: `2-11-3` is the third control in subdomain 2-11 (Penetration Testing), and `2-11-3-1` is its first subcontrol.

Two requirements shape how an entity organizes for the ECC:

- **Cybersecurity department**: it must be independent from the IT department (control 1-2-1). Reporting directly to the head of the entity is recommended.
- **Compliance assessment**: NCA evaluates compliance through self-assessment by the entity, periodic reports from its compliance tool, and field audits.

**Testing requirements**

The ECC sets what testing must exist but not how often: vulnerability assessment and penetration testing are required "periodically", and each entity sets the frequency in its own approved policy.

- **Vulnerability management (2-10-3)**: periodic vulnerability assessment and detection (2-10-3-1), classification by severity (2-10-3-2), remediation based on classification and risk (2-10-3-3), patch management with patches verified in a non-production environment first (2-10-3-4), and subscription to trusted sources for new vulnerabilities (2-10-3-5).
- **Penetration testing (2-11-3)**: the scope covers all services provided externally over the internet and their technical components: infrastructure, websites, web applications, smartphone and tablet applications, email and remote access (2-11-3-1). Tests are conducted periodically (2-11-3-2).
- **Projects and changes (1-6-2)**: vulnerability assessment and remediation, and a review of secure configuration, hardening and update packages before launch.
- **Software development (1-6-3)**: secure coding standards, trusted and licensed tools and libraries, compliance testing of software against cybersecurity requirements, secure integration between applications, and a hardening review before launch. Code review is not named explicitly.
- **Web applications (2-15-3)**: for external web applications, a web application firewall, a multi-tier architecture, secure protocols such as HTTPS, a secure usage policy for users, and authentication factors chosen by an impact assessment.

### Control sets built on the ECC

Each additional control set is an extension of the ECC: it covers one context and adds controls on top of the ECC. Most of them state that ECC compliance is a prerequisite for compliance with them, and most use the ECC's scope (government entities and CNI operators) and apply when the entity has the matching context, such as critical systems, cloud services or OT.

<figure class="diagram not-prose">
<div class="dg-grid">
<div class="dg-box"><b>CSCC</b><span>if you own or operate critical systems</span></div>
<div class="dg-box"><b>CCC</b><span>if you provide or use cloud services</span></div>
<div class="dg-box"><b>DCC</b><span>for your data, scaled by its classification</span></div>
<div class="dg-box"><b>OTCC</b><span>if you run ICS in critical facilities</span></div>
<div class="dg-box"><b>TCC</b><span>if staff work remotely</span></div>
<div class="dg-box"><b>OSMACC</b><span>if you run official social media accounts</span></div>
</div>
<div class="dg-box dg-base" style="margin-top:0.5rem"><b>ECC</b><span>applies to every entity in scope</span></div>
<div class="dg-box" style="margin-top:0.5rem"><b>NCS</b><span>the cryptography standard the other documents point to for algorithms and key lengths</span></div>
<figcaption>Figure 2: The NCA documents. The ECC is the base, each control set above it adds controls for one context, and the NCS sets the cryptography they rely on.</figcaption>
</figure>

| Document | Current version | Domains | Subdomains | Main controls | Subcontrols |
|---|---|---|---|---|---|
| **ECC**, Essential Cybersecurity Controls | ECC-2:2024 | 4 | 28 | 108 | 92 |
| **CSCC**, Critical Systems Cybersecurity Controls | CSCC-1:2019 | 4 | 21 | 32 | 73 |
| **CCC**, Cloud Cybersecurity Controls | CCC-2:2024 | 4 | 24 | 37 (CSP), 18 (CST) | 94 (CSP), 26 (CST) |
| **DCC**, Data Cybersecurity Controls | DCC-1:2022 | 3 | 11 | 19 | 47 |
| **OTCC**, Operational Technology Cybersecurity Controls | OTCC-1:2022 | 4 | 23 | 47 | 122 |
| **TCC**, Telework Cybersecurity Controls | TCC-1:2021 | 3 | 16 | 21 | 42 |
| **OSMACC**, Organizations' Social Media Accounts Cybersecurity Controls | OSMACC-1:2021 | 3 | 12 | 15 | 38 |

The **NCS** (National Cryptographic Standards, NCS-1:2020) lists the accepted algorithms, key lengths and protocols.

### Critical Systems Cybersecurity Controls (CSCC)

NCA defines a critical system as any system or network whose failure, unauthorized change, or unauthorized access to it or its data may affect the availability of the organization's services, or cause economic, financial, security or social harm at the national level.

A system is critical if its compromise could cause any one of these:

1. Negative impact on national security
2. Negative impact on the Kingdom's reputation and public image
3. Financial losses of more than 0.01% of GDP
4. Negative impact on services used by a large number of users (more than 5% of the population)
5. Loss of lives
6. Unauthorized disclosure of data classified Top Secret or Secret
7. Negative impact on the operations of one or more vital sectors

The organization that owns or operates a system identifies it as critical against these criteria. It must then meet the CSCC for those systems within the compliance period NCA sets, and stay compliant after it.

The CSCC lists these components of a critical system:

- **Network**: routers, switches, gateways, firewalls, IDS/IPS, APT protection devices
- **Platform**: databases, storage, middleware, servers and operating systems
- **Applications**
- **Supporting hardware**: encryption devices, printers, scanners
- **Non-technical**: users, privileged administrators, operators, service providers, and related documents

**Testing requirements**

The CSCC turns the ECC's "periodically" into fixed intervals for critical systems, and the scope covers every technical component listed above.

- **Vulnerability assessment (2-9-2)**: at least monthly on the technical components of critical systems, using trusted methods and tools (2-9-1-1).
- **Remediation (2-9-1-2, 2-9-1-3)**: at least monthly for external and internet-connected critical systems, at least every 3 months for internal ones, and immediately for critical vulnerabilities.
- **Penetration testing (2-10-1, 2-10-2)**: at least every 6 months, covering all technical components and all internal and external services, by a qualified team. The CSCC does not define what makes a team qualified.
- **Source code review (1-3-2-1)**: a security source code review before every release of a critical system, plus secured access to and storage of source code (1-3-2-2) and secured APIs (1-3-2-3).
- **Configuration and hardening (2-3-1-6, 2-3-1-7)**: reviewed at least every 6 months, with default configurations changed and hard-coded, backdoor and default passwords removed.
- **Security patches (2-3-1-3)**: at least monthly for external and internet-connected critical systems, and at least every 3 months for internal ones.
- **External web applications (2-12-1, 2-12-2)**: secure session management (session authenticity, lockout and timeout), the OWASP Top 10 as a minimum standard, and a multi-tier architecture with at least 3 tiers, on top of the ECC's 2-15.
- **Review of the CSCC itself (1-4-1, 1-4-2)**: by the cybersecurity function at least once a year, and by independent parties inside the organization but outside the cybersecurity function at least once every 3 years.

### Cloud Cybersecurity Controls (CCC)

The CCC applies to two parties. Cloud service providers (CSPs) are in scope when they serve in-scope customers. Cloud service tenants (CSTs) are government entities and CNI operators that use or plan to use cloud services. Each control is marked as a CSP control (`P` in the code, such as `2-10-P-1-1`) or a CST control (`T`, such as `2-9-T-1-1`). CCC-2:2024 replaced CCC-1:2020, and the testing controls kept the same numbers and frequencies.

Provider controls cover isolation of data, environments and guest systems, isolation of the cloud management and service delivery networks, and vetting of staff working inside the Kingdom.

**Testing requirements**

- **Provider vulnerability management (2-9-P-1-1)**: assess and remediate vulnerabilities on external components of the cloud technology stack at least monthly, and on internal components at least every 3 months. Providers also notify customers of vulnerabilities that may affect them (2-9-P-1-2).
- **Provider penetration testing (2-10-P-1-1)**: at least every 6 months, with a scope covering the cloud technology stack.
- **Customer vulnerability management (2-9-T-1-1)**: assess and remediate vulnerabilities in the cloud services used at least every 3 months, and manage the vulnerabilities the provider reports (2-9-T-1-2).
- **Customer penetration testing**: no CCC-specific requirement, so the ECC's 2-11 applies.

### Data Cybersecurity Controls (DCC)

The DCC covers data throughout its lifecycle, structured and unstructured, physical and digital. It has the same scope as the ECC, so it applies to all of an in-scope entity's data, and each control is marked with the classification levels it applies to: **Public, Confidential, Secret and Top Secret** (the classification scheme issued by SDAIA). Higher levels get more controls and shorter review cycles.

| Control | Public and Confidential | Secret and Top Secret |
|---|---|---|
| Security patches on systems handling the data (2-2-1-1) | At least monthly | Immediately |
| Configuration and hardening review (2-2-1-2) | At least annually | At least every 6 months |
| Review of privilege lists (2-1-3) | At least annually | At least every 3 months |
| Cryptography (2-5-1) | NCS moderate level (Confidential) | NCS advanced level |
| BYOD (2-3-1-2) | Allowed with MDM and remote wipe | Prohibited |

Other DCC controls include watermarking (Secret and above), DLP and rights management (Confidential and above), secure disposal with verification and records, printer and scanner controls, and approval before transferring data outside the Kingdom.

**Testing requirements**

The DCC adds no vulnerability assessment or penetration testing intervals, so the ECC's 2-10 and 2-11 apply. It does tighten the related controls by classification level:

- **Security patches (2-2-1-1)**: at least monthly for systems handling Public and Confidential data, immediately for Secret and Top Secret.
- **Configuration and hardening review (2-2-1-2)**: at least annually for Public and Confidential, at least every 6 months for Secret and Top Secret. Default configurations, such as default passwords, are reviewed and hardened at every level (2-2-1-3).
- **Test data (2-4-1-3)**: data from Confidential upwards cannot be used outside the production environment unless a risk assessment is done and controls such as data masking or scrambling are applied.

### Operational Technology Cybersecurity Controls (OTCC)

The OTCC applies to industrial control systems in critical facilities owned or operated by government entities or CNI operators. A facility is critical if its destruction or dysfunction may disrupt the organization's operation. A facility level identification tool places each facility at one of three levels, based on its impact on operations, on health, safety and environment, and on the economy or national security, and the level decides how many controls apply and how often testing runs:

| Facility level | Criticality | Controls that apply | VA and PT interval |
|---|---|---|---|
| Level 1 | High | 151 controls and subcontrols | 3 months |
| Level 2 | Moderate | 117 controls and subcontrols | 6 months |
| Level 3 | Low | 56 controls and subcontrols | 12 months |

**Testing requirements**

- **Vulnerability assessment (2-9-1-1, 2-9-1-3)**: every 3, 6 or 12 months by facility level, with scope and activities defined so they have limited or no impact on production. Critical vulnerabilities that pose significant risk are remediated in a timely manner (2-9-1-2).
- **Penetration testing (2-10-1)**: every 3, 6 or 12 months by facility level (2-10-1-3), by a qualified team, covering the OT/ICS environment and the networks connected to it (2-10-1-1). The OTCC does not define what makes a team qualified. Testing must have limited or no impact on production or run on an identical separate environment (2-10-1-2), and passive methods are used where production could be affected (2-10-1-4).
- **Acceptance testing (1-4-1-2)**: cybersecurity requirements are part of factory acceptance testing (FAT), site acceptance testing (SAT), commissioning, change and integration testing, and source code review.
- **Configuration and hardening (2-3-1-2)**: periodic security configuration review and hardening.

### Telework Cybersecurity Controls (TCC)

The TCC has the ECC's scope and covers the systems used for remote work, such as VPN and remote access.

**Testing requirements**

- **Vulnerability assessment (2-9-1-1)**: assess the technical components of telework systems and classify vulnerabilities by criticality at least every 3 months.
- **Remediation (2-9-1-2)**: at least every 3 months.
- **Penetration testing (2-10-1-1, 2-10-2)**: at least once a year, covering all technical components of telework systems.
- **Firewall rules (2-4-1-2)**: reviewed at least once a year.
- **Backup recovery (2-8-2)**: tested at least every 6 months.

### Organizations' Social Media Accounts Cybersecurity Controls (OSMACC)

OSMACC has the ECC's scope and covers the organization's official social media accounts. Accounts must belong to the organization rather than an individual, be registered with official information, and use a unique password and multi-factor authentication. Access is limited to specific, centrally managed devices, and every account needs a recovery plan.

**Testing requirements**

OSMACC adds no vulnerability assessment or penetration testing requirement, so the ECC applies. The related controls are:

- **Patches (2-3-1-1, 2-4-1-2)**: social media applications and the mobile devices used for the accounts are updated at least monthly.
- **Configuration and hardening (2-3-1-2, 2-3-1-3)**: the accounts and related technology assets are reviewed and hardened at least once a year, including default settings such as passwords and lockout.

### National Cryptographic Standards (NCS)

The NCS sets the minimum cryptography for protecting data in use, at rest and in transit for civilian and commercial purposes. It defines two strength levels:

- **MODERATE**: targets a 128-bit security level. For example, AES with 128 or 192-bit keys, and RSA with at least 3072-bit keys.
- **ADVANCED**: targets a 256-bit security level. For example, AES with 256-bit keys, and RSA is not accepted.

Each entity chooses the level based on the sensitivity of what it protects, and other NCA controls can require one: the DCC, for example, requires the advanced level for Secret and Top Secret data. The NCS also lists accepted schemes and protocols, PKI and key lifecycle management. For TLS, version 1.2 is accepted with the listed cipher suites and protection against downgrade, and TLS 1.3 is recommended for new applications.

**Testing requirements**

The NCS sets no testing requirement of its own. It is the reference that configuration reviews and penetration tests check cryptography against: protocol versions, cipher suites, key lengths and algorithms.

## SAMA frameworks

SAMA has issued seven frameworks that cover cybersecurity, IT and resilience for the financial sector. The CSF is the cybersecurity baseline. The IT Governance and Business Continuity frameworks are meant to be implemented together with it. The Threat Intelligence Principles and FEER set requirements for one activity each, the Counter-Fraud Framework covers fraud, and the Fundamental Requirements give new entities a smaller starting set.

<figure class="diagram not-prose">
<div class="dg-grid">
<div class="dg-box dg-base"><b>Cyber Security Framework</b><span>2017 · the cybersecurity baseline</span></div>
<div class="dg-box"><b>IT Governance Framework</b><span>2021 · IT controls beside the CSF</span></div>
<div class="dg-box"><b>Business Continuity Management</b><span>2017 · continuity and disaster recovery</span></div>
<div class="dg-box"><b>Cyber Threat Intelligence Principles</b><span>2022 · extends CSF 3.3.16 Threat Management</span></div>
<div class="dg-box"><b>FEER</b><span>2019 · regulated red teaming</span></div>
<div class="dg-box"><b>Counter-Fraud Framework</b><span>2022 · fraud governance, prevention, detection, response</span></div>
</div>
<div class="dg-box" style="margin-top:0.5rem"><b>Cyber Resilience Fundamental Requirements</b><span>2022 · a smaller set for sandbox entrants and licence applicants, before the CSF and BCM apply</span></div>
<figcaption>Figure 3: The SAMA frameworks. The highlighted CSF is the baseline the others build on or sit beside.</figcaption>
</figure>

| Framework | Version | Applies to | How compliance is checked | What counts as compliant |
|---|---|---|---|---|
| **Cyber Security Framework (CSF)** | 1.0, May 2017 | All SAMA member organizations | Periodic self-assessment questionnaire, reviewed and audited by SAMA | Maturity level 3 or higher |
| **IT Governance Framework (ITGF)** | 1.0, November 2021 | All SAMA member organizations | Periodic self-assessment questionnaire, reviewed and audited by SAMA | Maturity level 3 or higher |
| **Business Continuity Management Framework (BCMF)** | 1.0, February 2017 | Member organizations, banks and their subsidiaries | Gap assessment, roadmap and quarterly progress reports to SAMA, set by the issuing circular | Full compliance with the requirements |
| **Cyber Threat Intelligence Principles** | 1, February 2022 | All SAMA member organizations | Gap assessment and a board-approved roadmap, set by the issuing circular, with SAMA supervisory visits | Full compliance within 6 months, or 12 months for the strategic principles |
| **Financial Entities Ethical Red Teaming (FEER)** | 1.0, May 2019 | All SAMA member organizations | Not assessed: FEER is itself a test | A red teaming exercise at least every 3 years |
| **Counter-Fraud Framework** | 1.0, October 2022 | Member organizations that SAMA notifies | Periodic self-assessment questionnaire, reviewed and audited by SAMA | Maturity level 3 or higher |
| **Cyber Resilience Fundamental Requirements (CRFR)** | 1.0, January 2022 | Sandbox entrants and licence applicants | Self-assessment sent to SAMA, which can review it and audit at any time | Compliance, or SAMA can refuse sandbox graduation or a licence |

### Cyber Security Framework (CSF)

SAMA issued the Cyber Security Framework, version 1.0, in May 2017. It applies to all SAMA-regulated member organizations, as listed in the 2017 framework:

- All banks operating in Saudi Arabia
- All insurance and reinsurance companies
- All financing companies
- All credit bureaus
- The financial market infrastructure

All domains apply to banks. Other financial institutions are exempt from a few subdomains: 3.2.3 (compliance with industry standards, though PCI DSS and the SWIFT Customer Security Controls Framework still apply if they handle card data or SWIFT), 3.3.12 (payment systems) and 3.3.13 (electronic banking services, though customer-facing online services still need MFA).

The framework draws on NIST, ISF, ISO, Basel and PCI. Each subdomain states a **principle** (the required controls in summary), an **objective** (what they should achieve) and **control considerations** (the mandated controls themselves).

| Domain | Subdomains |
|---|---|
| 3.1 Leadership and Governance | 3.1.1 Governance, 3.1.2 Strategy, 3.1.3 Policy, 3.1.4 Roles and Responsibilities, 3.1.5 Cyber Security in Project Management, 3.1.6 Awareness, 3.1.7 Training |
| 3.2 Risk Management and Compliance | 3.2.1 Risk Management, 3.2.2 Regulatory Compliance, 3.2.3 Compliance with (inter)national industry standards, 3.2.4 Cyber Security Review, 3.2.5 Cyber Security Audits |
| 3.3 Operations and Technology | 3.3.1 Human Resources, 3.3.2 Physical Security, 3.3.3 Asset Management, 3.3.4 Architecture, 3.3.5 Identity and Access Management, 3.3.6 Application Security, 3.3.7 Change Management, 3.3.8 Infrastructure Security, 3.3.9 Cryptography, 3.3.10 BYOD, 3.3.11 Secure Disposal, 3.3.12 Payment Systems, 3.3.13 Electronic Banking Services, 3.3.14 Event Management, 3.3.15 Incident Management, 3.3.16 Threat Management, 3.3.17 Vulnerability Management |
| 3.4 Third Party Cyber Security | 3.4.1 Contract and Vendor Management, 3.4.2 Outsourcing, 3.4.3 Cloud Computing |

**Testing requirements**

- **Cyber security review (3.2.4)**: reviews periodically performed for critical information assets (3.2.4-1). Customer and internet facing services are subject to an annual review and penetration test (3.2.4-2). Each review is recorded with results, issues and recommended actions, reported to the business owner, and followed up until the issues are addressed (3.2.4-3 to 3.2.4-5).
- **Vulnerability management (3.3.17)**: the process covers all information assets, a risk-based scan frequency, classification of vulnerabilities, mitigation timelines per classification, prioritization for classified assets, and patch management.
- **Change management (3.3.7)**: security testing for a change includes, where applicable, penetration testing, code review of internally developed applications, code review of externally developed applications when the source code is available, and a code review report or independent assurance statement when it is not. Changes also need approval from the cyber security function before the Change Advisory Board, and a post-implementation review.
- **Application security (3.3.6)**: development follows an approved secure SDLC, and the application security standard includes secure coding standards, implemented controls (configuration parameters, logging, identity and access management), segregation of duties, data protection, vulnerability and patch management, and periodic compliance review.
- **Infrastructure security (3.3.8)**: security standards cover every type of infrastructure (operating systems, servers, virtual machines, firewalls, network devices, databases, workstations, mobile devices and others) in data centers, disaster recovery sites and offices, including configuration parameters.

### Maturity model

The CSF, the IT Governance Framework and the Counter-Fraud Framework share one maturity model. Each control is scored by maturity from 0 to 5, and member organizations must operate at **level 3 or higher**. A level counts only when all the criteria of the levels below it are also met. Assessment starts with a self-assessment questionnaire, which SAMA reviews and audits.

<figure class="diagram not-prose">
<div class="dg-rows">
<div class="dg-row" title="Level 0: no documentation, no awareness of the control"><span>0 Non-existent</span><span class="dg-track"><span class="dg-bar dim" style="width:13.4%"></span></span></div>
<div class="dg-row" title="Level 1: not or partially defined, performed inconsistently"><span>1 Ad-hoc</span><span class="dg-track"><span class="dg-bar dim" style="width:26.6%"></span></span></div>
<div class="dg-row" title="Level 2: practiced regularly but not formally defined or approved"><span>2 Repeatable but informal</span><span class="dg-track"><span class="dg-bar dim" style="width:40%"></span></span></div>
<div class="dg-row" title="Level 3: defined, approved and implemented; compliance monitored"><span>3 Structured and formalized</span><span class="dg-track"><span class="dg-bar" style="width:53.4%"></span><span>SAMA minimum</span></span></div>
<div class="dg-row" title="Level 4: effectiveness measured and periodically evaluated"><span>4 Managed and measurable</span><span class="dg-track"><span class="dg-bar" style="width:66.6%"></span></span></div>
<div class="dg-row" title="Level 5: continuous improvement, integrated with enterprise risk management"><span>5 Adaptive</span><span class="dg-track"><span class="dg-bar" style="width:80%"></span></span></div>
</div>
<figcaption>Figure 4: The SAMA maturity levels used by the CSF, IT Governance and Counter-Fraud frameworks. Levels 3 to 5 meet the requirement.</figcaption>
</figure>

| Level | Name | What it means |
|---|---|---|
| 0 | Non-existent | No documentation and no awareness of the control |
| 1 | Ad-hoc | Not or partially defined, performed inconsistently, varies by department or owner |
| 2 | Repeatable but informal | Practiced regularly, but not formally defined or approved |
| 3 | Structured and formalized | Defined, approved and implemented. Policies, standards and procedures exist, compliance with them is monitored, and KPIs track implementation |
| 4 | Managed and measurable | Effectiveness is measured and periodically evaluated, using key risk indicators and trend reporting, and results drive improvements |
| 5 | Adaptive | Continuous improvement, integrated with enterprise risk management, evaluated against peer and sector data |

### Financial Entities Ethical Red Teaming (FEER)

FEER, version 1.0 from May 2019, sets how SAMA-regulated entities run red teaming exercises against live production systems. Every member organization must be tested **at least once every three years**, and SAMA can also select an entity for a test based on the threat landscape.

A FEER exercise uses four teams:

- **Green Team**: SAMA's IT Risk supervision department. It appoints a Test Manager, approves the red teaming provider, and can add sector threat intelligence.
- **White Team**: a small group inside the entity, five people at most (for example the CISO), who know about the test and can stop it if it causes critical impact.
- **Blue Team**: the entity's SOC. It is never told about the test and follows its normal procedures.
- **Red Team**: an external certified provider that runs the attack scenarios and supplies the threat intelligence they are built on.

**Testing requirements**

- **Red teaming (1.6)**: at least once every three years per member organization, and when SAMA selects the entity.

### Cyber Threat Intelligence Principles

Issued in February 2022 as an extension of CSF subdomain 3.3.16 (Threat Management), the principles are mandatory for all member organizations, including those that outsource their threat intelligence. They are grouped into four domains and 19 principles:

| Domain | Principles | Purpose |
|---|---|---|
| Core CTI | 1 to 11 | The intelligence lifecycle: roles, collection requirements, sources, collection, SOPs, processing, analysis, sharing, delivery, improvement and integration |
| Strategic CTI | 12 to 14 | The objectives, motivations and intent of threat actors: threat landscape, strategic attack scenarios, requests for information |
| Operational CTI | 15 to 17 | How threat actors operate: attack chain, TTPs, malware and tools |
| Technical and Tactical CTI | 18 and 19 | Indicators of compromise and vulnerability monitoring |

The SAMA circular that issued the principles asked each entity for a gap assessment, then a roadmap to full compliance within six months for the core, operational and technical principles and twelve months for the strategic ones.

**Testing requirements**

None. Principle 19 (Monitor and Report Vulnerabilities) is the closest: entities monitor announcements of new vulnerabilities and zero-days exploited by threat actors, report them internally (for example to patch management), prioritize remediation with a risk rating that combines asset value, severity and threat actor activity, and use mitigating controls such as an IPS when a vulnerability cannot be patched.

### IT Governance Framework (ITGF)

Issued in November 2021, the ITGF covers IT controls the way the CSF covers cybersecurity, and SAMA says it should be implemented together with the CSF and the BCM framework. It uses the same maturity model, with level 3 as the target. It has four domains:

- **3.1 IT Governance and Leadership**: governance, strategy, enterprise architecture, policies, roles, regulatory compliance, internal IT audit, staff competence, performance management.
- **3.2 IT Risk Management**: managing IT risks, identification and analysis, treatment, reporting and monitoring.
- **3.3 IT Operations Management**: assets, interdependencies, SLAs, availability and capacity, data center, network architecture and monitoring, batch processing, incident and problem management, backup, virtualization.
- **3.4 System Change Management**: change governance, requirements, acquisition, development, testing, change security, release, configuration management, patch management, project management, quality assurance.

**Testing requirements**

- **Secure code review (3.4.4)**: for applications developed internally, and for externally developed ones when the source code is available. When it is not, a secure code review report or an equivalent such as an independent assurance statement is required.
- **Change testing (3.4.5)**: security testing is one of the minimum test types for every change, alongside unit, integration, stress and user acceptance testing. Testing runs on a separate test environment, and production data is not used, only sanitized data.
- **Vulnerability scanning (3.4.9)**: all systems are periodically scanned or inspected for outdated patches and vulnerabilities, and patches are tested in a separate environment before production.
- **Configuration management (3.4.8)**: a configuration management database (CMDB) with periodic verification of configuration items.

### Business Continuity Management Framework (BCMF)

Issued in February 2017, the BCM framework is based on ISO 22301, ISO 27001 and the BCI and DRII practice guidelines. It applies to member organizations, all banks in Saudi Arabia, banking subsidiaries of Saudi banks, and subsidiaries of foreign banks in the Kingdom, and covers their subsidiaries, staff, third parties and customers.

Its requirements cover governance, strategy, policy, business impact analysis and risk assessment, the business continuity plan, the IT disaster recovery plan, cyber resilience, crisis management, testing, awareness, communication, document review and assurance. The ones that matter most for security work are:

- **IT disaster recovery (2.6)**: an alternative data center, at a location approved by SAMA that does not share the main site's risks, with the same logical, physical and cyber security controls as the primary.
- **Cyber resilience (2.7)**: changes to infrastructure and software that support critical services go through in-depth risk assessment and strict development, testing and change procedures. For threat and vulnerability management it points back to the CSF.

**Testing requirements**

- **Business continuity plan testing (2.9.1)**: simulation exercises at least once a year, with scenarios that include cyber security, and an integrated test of all critical services once the individual tests are done.
- **Disaster recovery testing (2.9.2)**: a DR test combined with the BCP at least once a year, evaluating whether the DR infrastructure for critical systems can resume critical operations.
- **DR plan effectiveness (2.6)**: measured and evaluated at least yearly.

### Counter-Fraud Framework

Issued in October 2022, it applies to the member organizations SAMA notifies. It uses the same maturity model, with level 3 as the minimum, and has four domains:

- **Governance**: structure, strategy, policy, roles, a counter-fraud department, management information, supervisory notifications, technology and internal audit.
- **Prevent**: risk management, due diligence on employees, customers and third parties, training and awareness, authentication, alignment of fraud, financial crime and cyber, and prevention standards for internal and external fraud.
- **Detect**: detection standards and systems, monitoring and whistleblowing.
- **Respond**: response plan, alert and case management, investigation and remediation.

**Testing requirements**

None for vulnerability assessment or penetration testing. The framework's controls cover fraud prevention, detection and response.

### Cyber Resilience Fundamental Requirements (CRFR)

Issued in January 2022, the CRFR applies to entities entering SAMA's regulatory sandbox and entities applying for a licence. It is a prioritized subset of the CSF and BCM framework for young entities with limited resources. Once licensed, the entity has to meet the full CSF and BCM framework. SAMA can refuse sandbox graduation or a licence to an entity that cannot show compliance.

> **Note:** SAMA's regulatory sandbox, set up in November 2019, lets local and international firms test new digital solutions for the financial sector in a live environment before deploying them in the Kingdom. SAMA uses it to understand and assess the impact of new technologies on the Saudi financial market. Its own rules are in SAMA's Regulatory Sandbox Framework.

Its controls fall under Cyber Security Leadership and Governance, Cyber Security Operations and Technology, and Resilience. Several are more specific than the CSF:

- **Application shielding (3.2.8)**: on top of a secure SDLC, techniques such as code obfuscation, white-box cryptography and anti-tampering.
- **Passwords (3.1.5)**: access revoked after three successive incorrect passwords.
- **Sessions (3.2.15)**: inactive sessions time out after no more than 5 minutes.
- **Logs (3.2.11)**: security logs retained for at least one year.
- **Incidents (3.2.16)**: medium or higher cyber, fraud and disruptive incidents reported to SAMA immediately.

**Testing requirements**

- **Penetration testing (3.2.6)**: at least twice a year, and after any major or critical change. This is more frequent than the CSF's annual test.
- **Vulnerability assessment (3.2.5)**: periodic and comprehensive, covering both the application and infrastructure layers.
- **Patches (3.2.7)**: tested and applied in a timely manner.
- **Change management (3.2.2)**: changes are classified, tested and approved before deployment to production.

## NCA ECC vs SAMA CSF

| | NCA ECC | SAMA CSF |
|---|---|---|
| Regulator | NCA | SAMA |
| Scope | Government entities and CNI operators | SAMA-regulated financial entities |
| Current version | ECC-2:2024 (first issued 2018) | Version 1.0, 2017 |
| Structure | Domains, subdomains, numbered controls and subcontrols (e.g. 2-11-3-1) | Domains, subdomains, then principle, objective and control considerations |
| Assessment | Compliance per control | Maturity level 0 to 5, minimum level 3 |
| Style | Prescriptive | Principle-based |
| Related frameworks | CSCC, CCC, DCC, OTCC, TCC, OSMACC, NCS | IT Governance, BCM, CTI Principles, FEER, Counter-Fraud, CRFR |

## Testing requirements compared

The ECC requires vulnerability assessment and penetration testing **periodically** and never sets a number, so each entity defines its own frequency in an approved policy. Fixed frequencies appear only in the additional control sets (CSCC, CCC, OTCC, TCC) and in the SAMA frameworks.

<figure class="diagram not-prose">
<div class="dg-rows">
<div class="dg-row" title="ECC 2-11-3-2: penetration tests are conducted periodically"><span>ECC</span><span class="dg-track"><span class="dg-note">set by the entity's approved policy</span></span></div>
<div class="dg-row" title="CSCC 2-10-2: every 6 months"><span>CSCC</span><span class="dg-track"><span class="dg-bar" style="width:13.4%"></span><span>6 months</span></span></div>
<div class="dg-row" title="CCC 2-10-P-1-1: every 6 months for the cloud technology stack"><span>CCC (provider)</span><span class="dg-track"><span class="dg-bar" style="width:13.4%"></span><span>6 months</span></span></div>
<div class="dg-row" title="OTCC 2-10-1-3: Level 1 (high criticality) facilities every 3 months"><span>OTCC L1 facility</span><span class="dg-track"><span class="dg-bar" style="width:6.6%"></span><span>3 months</span></span></div>
<div class="dg-row" title="OTCC 2-10-1-3: Level 2 (moderate criticality) facilities every 6 months"><span>OTCC L2 facility</span><span class="dg-track"><span class="dg-bar" style="width:13.4%"></span><span>6 months</span></span></div>
<div class="dg-row" title="OTCC 2-10-1-3: Level 3 (low criticality) facilities every 12 months"><span>OTCC L3 facility</span><span class="dg-track"><span class="dg-bar" style="width:26.6%"></span><span>12 months</span></span></div>
<div class="dg-row" title="TCC 2-10-2: telework systems at least once every year"><span>TCC</span><span class="dg-track"><span class="dg-bar" style="width:26.6%"></span><span>12 months</span></span></div>
<div class="dg-row" title="SAMA CSF 3.2.4-2: annual review and penetration test of customer and internet facing services"><span>SAMA CSF</span><span class="dg-track"><span class="dg-bar" style="width:26.6%"></span><span>12 months</span></span></div>
<div class="dg-row" title="CRFR 3.2.6: twice a year as a minimum, and after major or critical changes"><span>SAMA CRFR</span><span class="dg-track"><span class="dg-bar" style="width:13.4%"></span><span>6 months</span></span></div>
<div class="dg-row dg-split" title="FEER 1.6: each member organization tested at least once every three years"><span>FEER red team</span><span class="dg-track"><span class="dg-bar dim" style="width:80%"></span><span>36 months</span></span></div>
</div>
<figcaption>Figure 5: Longest allowed interval between penetration tests. A shorter bar means more frequent testing. FEER sets the interval for red teaming exercises and is shown for comparison.</figcaption>
</figure>

### Summary

| Framework | Vulnerability assessment | Penetration testing | Code review | Configuration and hardening |
|---|---|---|---|---|
| **ECC-2:2024**, everyone in scope | Periodic (2-10-3-1), classified by severity and remediated by risk | Periodic (2-11-3-2), covering all internet-facing services (2-11-3-1) | Not named. Requires secure coding standards and compliance testing of software (1-6-3) | Review before go-live of projects, changes and software (1-6-2-2, 1-6-3-5) |
| **CSCC**, critical systems | Monthly (2-9-2). Remediate monthly for external systems, every 3 months for internal (2-9-1-2), critical vulnerabilities immediately (2-9-1-3) | Every 6 months (2-10-2), all technical components and internal and external services, by a qualified team (2-10-1) | Before every release of a critical system (1-3-2-1) | Every 6 months (2-3-1-6). Remove hard-coded, backdoor and default passwords (2-3-1-7) |
| **CCC-2:2024**, cloud | Provider: external monthly, internal every 3 months (2-9-P-1-1). Customer: at least every 3 months (2-9-T-1-1) | Provider: every 6 months, covering the cloud technology stack (2-10-P-1-1) | ECC applies | ECC applies |
| **OTCC-1:2022**, OT and ICS | By facility level: L1 every 3 months, L2 every 6, L3 every 12 (2-9-1-3), with limited or no impact on production | Same intervals (2-10-1-3), with limited or no impact on production or on an identical separate environment, and passive methods where production could be affected | Part of acceptance testing: FAT, SAT, commissioning, change and integration testing, and source code review (1-4-1-2) | Periodic configuration review and hardening (2-3-1-2) |
| **TCC-1:2021**, telework | Assess and classify at least every 3 months (2-9-1-1), remediate at least every 3 months (2-9-1-2) | At least once a year, covering all technical components of telework systems (2-10-1-1, 2-10-2) | ECC applies | ECC applies |
| **DCC-1:2022**, data | ECC applies. Patches monthly for Public and Confidential data, immediately for Secret and Top Secret (2-2-1-1) | ECC applies | ECC applies. No production data in test environments without masking or scrambling (2-4-1-3) | Annually for Public and Confidential, every 6 months for Secret and Top Secret (2-2-1-2) |
| **OSMACC-1:2021**, social media | Patches for social media applications and devices monthly (2-3-1-1, 2-4-1-2) | ECC applies | ECC applies | Account configuration review and hardening annually (2-3-1-2) |
| **SAMA CSF**, financial sector | Risk-based scan frequency over all information assets, with mitigation timelines per classification (3.3.17) | Annual for customer and internet facing services (3.2.4-2), periodic reviews of critical assets (3.2.4-1) | Part of security testing in change management (3.3.7). Secure SDLC and coding standards (3.3.6) | Infrastructure security standards including configuration parameters (3.3.8) |
| **SAMA ITGF**, financial sector | Periodic scanning for outdated patches and vulnerabilities (3.4.9) | None specific. Security testing is a minimum test type for every change (3.4.5) | Secure code review of internal applications, and of external ones when the source is available, otherwise a review report (3.4.4) | Configuration management with a CMDB (3.4.8) |
| **SAMA CRFR**, sandbox and licence applicants | Periodic, covering application and infrastructure layers (3.2.5) | At least twice a year and after major or critical changes (3.2.6) | Secure SDLC plus application shielding (3.2.8) | Secure network architecture and segmentation (3.2.3) |
| **FEER**, financial sector | n/a | Red teaming at least every 3 years (1.6) | n/a | n/a |

## Sources

- NCA, Essential Cybersecurity Controls (ECC-1:2018) and (ECC-2:2024), [nca.gov.sa](https://nca.gov.sa)
- NCA, Critical Systems Cybersecurity Controls (CSCC-1:2019)
- NCA, Cloud Cybersecurity Controls (CCC-1:2020) and (CCC-2:2024)
- NCA, Operational Technology Cybersecurity Controls (OTCC-1:2022)
- NCA, Telework Cybersecurity Controls (TCC-1:2021)
- NCA, Data Cybersecurity Controls (DCC-1:2022)
- NCA, Organizations' Social Media Accounts Cybersecurity Controls (OSMACC-1:2021)
- NCA, National Cryptographic Standards (NCS-1:2020)
- SAMA, Cyber Security Framework, version 1.0, May 2017, [sama.gov.sa](https://www.sama.gov.sa)
- SAMA, Financial Entities Ethical Red Teaming Framework, version 1.0, May 2019
- SAMA, Business Continuity Management Framework, version 1.0, February 2017
- SAMA, Information Technology Governance Framework, version 1.0, November 2021
- SAMA, Financial Sector Cyber Threat Intelligence Principles, version 1, February 2022
- SAMA, Counter-Fraud Framework, version 1.0, October 2022
- SAMA, Cyber Resilience Fundamental Requirements, version 1.0, January 2022

> **Note:** The Arabic version of each NCA document is the legally binding one.
