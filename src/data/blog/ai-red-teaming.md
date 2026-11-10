---
title: "AI Red Teaming"
slug: ai-red-teaming
category: notes
handbook: ai-security
tags: ["ai"]
draft: false
pubDatetime: 2026-11-10T00:00:00+03:00
description: "What an AI red team tests in a system built around a machine learning model: training and inference, the model, data, application and system components, the OWASP Top 10 for Machine Learning, the OWASP Top 10 for LLM Applications, and Google's Secure AI Framework (SAIF)."
---

## Introduction

AI red teaming is security testing of a system that contains a machine learning model, done from an attacker's position. The scope covers the model, the data it was trained on, the application that sends input to the model and uses its output, and the infrastructure that hosts all of it.

Many findings in an AI red team assessment are ordinary application or infrastructure bugs, such as a storage bucket with training data that anyone can read. The rest are specific to machine learning: an input crafted to change a prediction, training records recovered from a model's answers, or instructions hidden in a document that an LLM summarizes.

Three references describe these findings in shared terms: the OWASP Top 10 for Machine Learning, the OWASP Top 10 for LLM Applications, and Google's Secure AI Framework (SAIF).

## Training and inference

A model goes through two phases. During **training**, an algorithm adjusts the model's weights until its predictions on labeled examples are accurate. During **inference**, the trained model receives new input and returns a prediction. Training runs once or on a schedule, separately from the live system. Inference runs every time someone uses the model: a spam filter scoring an incoming email, an image classifier labeling an upload, or an LLM generating a reply.

**Inference data** is the input sent to a deployed model at prediction time, together with the output it returns. For a spam filter, the inference data is each incoming email and its spam score. For an LLM chatbot, it is everything in the conversation: the system prompt, the user's messages, documents the application adds to the prompt, and the generated replies.

![Two lanes. Training: training data flows into training, which produces model weights. Poisoning and skewing target the training data; theft and tampering target the weights. A dashed deploy arrow carries the weights down to the inference lane, where input flows from the user to the application to the model and output flows back. Crafted input (evasion, prompt injection) comes from the user, unsafe output handling and excessive tool access sit in the application, and extraction, inversion and membership inference target the model.](/images/ai-red-teaming/training-inference.svg)

Attacks on training change what the model learns. **Poisoning** adds manipulated samples to the training set so the deployed model has a backdoor or a blind spot. It requires write access to the training data, or to a source the data is collected from, such as user feedback or scraped web pages.

Attacks at inference require only the ability to send queries:

- **Evasion**: an input modified so the model classifies it wrongly, such as spam with extra legitimate words added (the good word attack in [Naive Bayes](/collections/ai-security/ai-naive-bayes)).
- **Model extraction**: many queries, whose answers are used to train a copy of the model.
- **Model inversion**: reconstructing training inputs, such as faces from a face recognition model, using the model's outputs.
- **Membership inference**: using the model's confidence scores to tell whether a specific record was in the training set. Models are often more confident on records they were trained on.
- **Prompt injection**: instructions placed in an LLM's input that change what the application does.

Inference data is also sensitive by itself. Users paste confidential documents, credentials and personal data into chatbots, and applications often log every prompt and reply. Those logs, and any bug that shows one user's conversation to another user, leak data without any attack on the model.

## The four components of an ML system

An ML-based system splits into four components. A red team assessment covers all four.

| Component | What it includes | Example attacks |
|---|---|---|
| Model | The weights, the architecture, the inference endpoint | Evasion, extraction, inversion, membership inference |
| Data | Training sets, data collection pipelines, vector stores, prompt and reply logs | Poisoning, theft of training data, leaked conversation logs |
| Application | The code that builds the model's input and acts on its output: chat interface, API, plugins, tools | Prompt injection, model output rendered as HTML (XSS), tools with more permissions than the task needs |
| System | Hosting infrastructure, ML libraries, model files, the deployment pipeline | Model files that run code when loaded (Python pickle), exposed notebooks or model registries, expensive queries used for denial of service |

The attacks available depend on how much access the tester has. In a **black-box** assessment, the tester has only the public interface, the same as a normal user. In a **white-box** assessment, the tester also has the weights, training code and data. Hosted LLM applications are usually tested black-box through the chat interface, which makes information gathering the first step: [LLM Reconnaissance](/collections/ai-security/ai-llm-recon).

LLM assessments also test whether the model can be made to produce content its operator prohibits, such as malware or instructions for weapons. Those techniques are in [Jailbreaking](/collections/ai-security/ai-jailbreaking).

## OWASP Top 10 for Machine Learning

The [OWASP Machine Learning Security Top 10](https://owasp.org/www-project-machine-learning-security-top-10/) (2023 draft) covers attacks on trained models of any type: classifiers, regression models, and neural networks.

| ID | Name | What the attacker does |
|---|---|---|
| ML01 | Input Manipulation Attack | Changes an input slightly so the model returns a wrong prediction (evasion, adversarial examples) |
| ML02 | Data Poisoning Attack | Adds or alters training samples so the model learns wrong behavior |
| ML03 | Model Inversion Attack | Reconstructs training inputs from the model's outputs |
| ML04 | Membership Inference Attack | Determines whether a specific record was in the training data |
| ML05 | Model Theft | Copies the model, by stealing the weights or by training a replica on its answers |
| ML06 | AI Supply Chain Attacks | Compromises a library, dataset or pre-trained model the system depends on |
| ML07 | Transfer Learning Attack | Plants behavior in a pre-trained model that stays in models fine-tuned from it |
| ML08 | Model Skewing | Shifts the training data distribution over time, for example by sending false feedback to a model that retrains on user feedback |
| ML09 | Output Integrity Attack | Modifies the model's output after it is produced and before the consuming system receives it |
| ML10 | Model Poisoning | Edits the model's weights directly, without touching the training data |

ML02 and ML10 both produce a model with planted behavior. They differ in what the attacker modifies: ML02 changes the training data, ML10 changes the trained weights.

## OWASP Top 10 for LLM Applications

The [OWASP Top 10 for LLM Applications](https://genai.owasp.org/llm-top-10/) covers applications built on large language models. The 2026 edition renumbered several entries and renamed System Prompt Leakage to Hidden Context Exposure. Many articles and courses still use the 2025 numbers, so the table lists both.

| 2026 | 2025 | Name | Short description |
|---|---|---|---|
| LLM01 | LLM01 | Prompt Injection | Input that changes the model's behavior against the developer's intent, typed by the user (direct) or placed in content the model processes (indirect) |
| LLM02 | LLM02 | Sensitive Information Disclosure | The model reveals personal data, credentials, or confidential business data from its training data or context |
| LLM03 | LLM06 | Excessive Agency | The model can call tools or take actions beyond what its task needs, so a manipulated model can delete records, send messages or spend money |
| LLM04 | LLM03 | Supply Chain | Compromised models, adapters, datasets or libraries |
| LLM05 | LLM04 | Data and Model Poisoning | Manipulated pre-training, fine-tuning or embedding data that plants backdoors or bias |
| LLM06 | LLM10 | Unbounded Consumption | No limits on requests or tokens, which allows denial of service, runaway costs, or model extraction through mass queries |
| LLM07 | LLM09 | Misinformation | The application presents false model output as fact, and users or other systems act on it |
| LLM08 | LLM07 (System Prompt Leakage) | Hidden Context Exposure | The system prompt or other hidden context (tool lists, retrieved documents, secrets placed in the prompt) can be extracted |
| LLM09 | LLM08 | Vector and Embedding Weaknesses | Flaws in retrieval-augmented generation (RAG): poisoned documents, embeddings leaking source text, missing access control between tenants |
| LLM10 | LLM05 | Improper Output Handling | Model output passed to a browser, shell, database or other system without validation, causing XSS, command injection or SQL injection |

Several other entries are reached through prompt injection: an injected instruction is how an attacker extracts hidden context (LLM08), triggers a tool call (LLM03), or gets a payload into output that the application handles unsafely (LLM10). [Prompt Injection](/collections/ai-security/ai-prompt-injection) covers the techniques.

## Google's Secure AI Framework (SAIF)

[SAIF](https://saif.google/) is a framework for organizations building or using AI, published by Google in 2023. The OWASP lists name vulnerability classes for testers. SAIF names the controls an organization needs and which team owns each one.

It has six core elements:

1. **Expand strong security foundations to the AI ecosystem**: apply existing controls, such as access control, input validation and supply chain checks, to models, data and AI infrastructure.
2. **Extend detection and response to bring AI into the threat universe**: monitor model inputs and outputs for attacks, and include AI systems in threat intelligence and incident response.
3. **Automate defenses**: use automation, including AI, to respond to attacks at the speed and volume they arrive.
4. **Harmonize platform-level controls**: use the same AI security controls and tooling across the organization instead of a separate set per team.
5. **Adapt controls and create faster feedback loops**: test AI systems continuously (red teaming included) and feed the results back into training data, fine-tuning and safeguards.
6. **Contextualize AI system risks in surrounding business processes**: assess each AI system's risk based on what it is used for, what data it handles, and what it can do.

SAIF also publishes a risk map that groups an AI system into four areas, Data, Infrastructure, Model and Application, and lists the risks for each:

| Risk | Short description |
|---|---|
| Data Poisoning | Training or tuning data altered to change model behavior |
| Unauthorized Training Data | The model is trained on data it is not permitted to use, such as user data without consent |
| Model Source Tampering | Model code, weights or dependencies modified before deployment |
| Excessive Data Handling | User data collected, kept or processed beyond what is allowed |
| Model Exfiltration | The model's files are stolen |
| Model Deployment Tampering | The serving infrastructure is modified to change the model that runs |
| Denial of ML Service | Requests that exhaust the model's resources so it becomes unavailable |
| Model Reverse Engineering | A copy of the model built from its inputs and outputs |
| Insecure Integrated Component | A vulnerable plugin, library or tool connected to the model |
| Prompt Injection | Instructions in the input that override the intended behavior |
| Model Evasion | Inputs crafted so the model classifies them wrongly |
| Sensitive Data Disclosure | The model reveals data from its training set or context |
| Inferred Sensitive Data | The model deduces sensitive facts about people that were never given to it |
| Insecure Model Output | Output passed to other systems without validation |
| Rogue Actions | The model takes unintended actions through the tools it has access to |

For each risk, the map shows whether the model creator (the team that trains the model) or the model consumer (the team that builds an application on it) is responsible for the control. A company calling a hosted LLM through an API can do little about Data Poisoning, which belongs to the model creator, and is fully responsible for Insecure Model Output and Rogue Actions.
