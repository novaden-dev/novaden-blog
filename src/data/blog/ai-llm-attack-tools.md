---
title: "garak, PyRIT and ART"
slug: ai-llm-attack-tools
category: notes
handbook: ai-security
tags: ["ai"]
draft: false
pubDatetime: 2026-11-10T00:00:00+03:00
description: "Three open-source tools for testing AI systems: garak, a vulnerability scanner for LLMs; PyRIT, Microsoft's framework for automated and multi-turn red teaming; and the Adversarial Robustness Toolbox (ART), a library of attacks and defenses for classic machine learning models."
---

## Introduction

Manual prompting is enough to find a first weakness. Tools repeat hundreds of known attacks against a target, record which ones worked, and re-run the same test after the target changes. The three tools here cover different targets:

| Tool | Made by | Targets | What it does |
|---|---|---|---|
| garak | NVIDIA | LLMs and LLM applications | Runs a large library of known attack prompts and reports which ones succeeded |
| PyRIT | Microsoft | LLMs and LLM applications | Framework for building custom and multi-turn attack runs with automatic scoring |
| ART | Linux Foundation AI & Data (originally IBM) | Classic ML models: classifiers, image models, tabular models | Library of evasion, poisoning, extraction and inference attacks, plus defenses |

garak and PyRIT send text to a model and judge the text that comes back. ART works on the model object itself and needs the model, or at least its predictions, in Python.

Only run these against systems you are authorized to test. They send many requests, which costs money on paid APIs and can trip rate limits or alerts.

## garak

[garak](https://github.com/NVIDIA/garak) (Generative AI Red-teaming and Assessment Kit) is a command line scanner, similar in use to `nmap` or `nikto` for web servers. It has four kinds of component:

- **Generators**: the connection to the target, such as OpenAI, Hugging Face, a local model, or a REST endpoint.
- **Probes**: the attacks. Each probe sends a set of prompts that tries to produce one kind of failure, such as `dan` (DAN jailbreaks), `promptinject`, `encoding` (instructions hidden in Base64 and similar), `leakreplay` (training data leakage) or `malwaregen`.
- **Detectors**: check each reply to decide whether the attack worked, for example whether the model produced the forbidden string or complied with the jailbreak.
- **Buffs**: transform the prompts before they are sent, for example paraphrasing them or changing the encoding, to multiply the number of variants.

Install it and list what is available:

```bash
python -m pip install -U garak
python -m garak --list_probes
```

Run a probe family against a model:

```bash
export OPENAI_API_KEY="..."
python -m garak --target_type openai --target_name gpt-4o-mini --probes encoding
```

Use `--probes dan,promptinject,encoding` to run several families, and leave `--probes` out to run every probe, which takes a long time. Older versions use `--model_type` and `--model_name` for the two target options, so check `python -m garak --help` for the version you have. Models that run locally use `--target_type huggingface` with the Hugging Face model name. For a chatbot behind a web endpoint, the `rest` generator takes a JSON file that describes the request format and where the reply is in the response.

garak runs each prompt several times, since replies vary, and writes a report with a pass or fail rate per probe plus a log of every prompt and reply. Read the logged replies for the failures: detectors produce false positives and false negatives, and the counts alone do not show how serious a failure is.

## PyRIT

[PyRIT](https://github.com/microsoft/PyRIT) (Python Risk Identification Tool) is Microsoft's framework for automating AI red teaming. garak is a scanner with a fixed library. PyRIT is a set of parts you combine, which suits attacks that need several turns or a custom target. The documentation describes four core parts:

- **Targets**: what receives the prompts. Built-in targets cover OpenAI, Azure, Anthropic, Hugging Face and generic HTTP endpoints, and you can write your own.
- **Converters**: transform a prompt before it is sent, and they can be stacked. Examples are Base64 encoding, translation, rewording by another LLM, or turning the text into an image or document.
- **Scorers**: judge each reply, using a true or false check, a rating scale, a classifier, or another LLM that is asked whether the reply is harmful.
- **Attacks**: the algorithm that ties the others together. It sends prompts to the target, applies converters, and uses the scorer's result to choose the next prompt. Single-turn and multi-turn attacks are included, such as Crescendo (gradually escalating the conversation), TAP (a tree search over prompt variations) and Skeleton Key.

The multi-turn attacks use a second LLM as the attacker. It writes each new message based on the target's last reply, which automates the manual multi-turn jailbreaking described in [Jailbreaking](/collections/ai-security/ai-jailbreaking).

```bash
python -m pip install pyrit
```

PyRIT also stores every prompt and reply in a database, so a run can be reviewed and compared with later runs. Its Python interface and class names have changed between releases, so use the examples in the documentation for the version you install. Older tutorials often use class names that no longer exist. It can also run as a command line scanner (`pyrit_scan`) over bundled scenarios.

## Adversarial Robustness Toolbox (ART)

[ART](https://github.com/Trusted-AI/adversarial-robustness-toolbox) is a Python library for attacking and defending machine learning models, and it works with scikit-learn, PyTorch, TensorFlow, Keras and XGBoost among others. It covers four threat categories:

- **Evasion**: modify an input so the model gets it wrong (`art.attacks.evasion`).
- **Poisoning**: alter training data to change what the model learns (`art.attacks.poisoning`).
- **Extraction**: copy a model through its answers (`art.attacks.extraction`).
- **Inference**: recover private information, including whether a record was in the training data, and reconstruct training inputs (`art.attacks.inference`).

It also has defenses in `art.defences`, such as adversarial training and input preprocessing, so the same library measures how much a defense helps.

The first step is to wrap the trained model in an ART estimator. This gives every attack the same interface to the model, whichever library produced it. The example below attacks the kind of scikit-learn model built in [Logistic Regression](/collections/ai-security/ai-logistic-regression), using the Fast Gradient Method, which moves each input a small step in the direction that most increases the model's loss:

```python
from sklearn.datasets import load_digits
from sklearn.linear_model import LogisticRegression
from sklearn.model_selection import train_test_split
from art.estimators.classification import SklearnClassifier
from art.attacks.evasion import FastGradientMethod

X, y = load_digits(return_X_y=True)
X = X / 16.0  # scale pixel values to 0-1
X_train, X_test, y_train, y_test = train_test_split(X, y, random_state=0)

model = LogisticRegression(max_iter=1000).fit(X_train, y_train)
print("clean accuracy:", model.score(X_test, y_test))

classifier = SklearnClassifier(model=model, clip_values=(0.0, 1.0))
attack = FastGradientMethod(estimator=classifier, eps=0.2)
X_adv = attack.generate(x=X_test)

print("accuracy on adversarial inputs:", model.score(X_adv, y_test))
```

`eps` is the largest change allowed to each feature (here, to each pixel). Raising it lowers accuracy further and makes the changes more visible. The accuracy drop from the clean set to the adversarial set is the measurement to report.

ART does not attack chat models through text prompts. For a chat application, use garak or PyRIT. For the classifiers and image models in the rest of this handbook, use ART to produce adversarial examples.
