---
title: "AI Data Pipelines"
slug: ai-data-pipeline
category: notes
handbook: ai-security
tags: ["ai"]
draft: false
pubDatetime: 2026-11-15T00:00:00+03:00
description: "The six stages that turn raw data into a deployed model and keep it updated (collection, storage, processing, modeling, deployment, monitoring), worked through a spam filter trained on user reports, with the attack on each stage and where each one sits in the OWASP Top 10 lists and Google's SAIF."
---

## Introduction

A deployed model is the output of a pipeline. Data is collected, stored, cleaned and turned into features, a model is trained on it, and the trained model is deployed and monitored. When a model has to keep up with new data, the pipeline then runs again, and the model is retrained on a schedule.

Each stage reads what the previous stage wrote. Unless a stage checks that input, a change made at any stage carries through to the deployed model. An attacker therefore needs write access to only one stage: whichever one they can reach. The data attacks in this handbook are grouped by the stage they target.

## A Spam Filter Trained on User Reports

The example used throughout the data attack notes is an email provider's spam filter. It is a classifier that gives each incoming message a probability of being spam. The provider retrains it every week, partly on labels that come from users clicking "Report spam" or "Not spam" in their mail client.

![Six stages in a loop. Top row, left to right: 1. Collection (mail and user reports), 2. Storage (object storage bucket), 3. Processing (labels and features). An arrow leads down to the bottom row, right to left: 4. Modeling (training, model file), 5. Deployment (scoring service), 6. Monitoring (metrics, retraining). A dashed arrow from Monitoring back up to Collection is labeled "new reports feed the next training run". Each stage has an attack in red: data poisoning, storage tampering, processing manipulation, model poisoning, deployment injection and retraining exploitation.](/images/ai-data-pipeline/pipeline.svg)

## The Stages and Their Attacks

### 1. Collection: data poisoning

**What happens:** the pipeline gathers raw data. For the spam filter that means the incoming messages, the reports users send from the mail client, and any third-party feeds, such as lists of domains known to send spam. The data is usually streamed into a message queue, such as Apache Kafka, which buffers it until it is written to storage.

**The attack:** data poisoning is sending data into the pipeline that is crafted to change what the model learns. The attacker registers accounts, sends spam to them, and reports it as "Not spam". They can also send many legitimate-looking messages that contain the words their spam campaign uses, so those words end up associated with legitimate mail. Neither needs access to the provider's systems, only to the same sources everyone else uses. A third-party feed the attacker controls or has compromised works the same way.

[Label Flipping](/collections/ai-security/ai-label-flipping) and [Clean Label Attacks](/collections/ai-security/ai-clean-label) cover two forms of this attack in detail.

### 2. Storage: storage tampering

**What happens:** the collected data is written to an object storage bucket, such as Amazon S3. A store that keeps large amounts of raw data in its original form, to be processed later, is called a data lake. The prepared training sets are usually stored in the same place.

**The attack:** storage tampering is changing the data at rest. An attacker with write access to the bucket can flip labels in bulk, delete every example of one spam campaign so the next model never learns it, or replace a whole training set. Write access usually comes from leaked cloud credentials, a bucket policy that grants more than intended, or an insider. Data written straight to storage bypasses every check at collection, such as limits on how many reports one account can send.

### 3. Processing: processing manipulation

**What happens:** a batch job, often written for Apache Spark when the data is large, turns raw data into training data. For the spam filter it joins each report to the message it refers to, decides each message's label (for example, spam when most reports say spam), cleans the text, and extracts features such as word counts, the number of links and the sender's reputation. It writes the result as training files.

**The attack:** processing manipulation is changing the code, configuration or libraries the job runs, so it writes wrong training data from correct raw data. A one-line change to the label rule, such as "one 'Not spam' report overrides any number of spam reports", or a tokenizer that drops one domain name from every message, produces training files that look normal. The access needed is the ability to change the job: a commit to its repository, control of the build system, or a compromised library the job imports.

### 4. Modeling: model poisoning

**What happens:** a training job reads the training files, trains the model, evaluates it on a held-out test set, and saves it as a model file. With scikit-learn the file is usually written with `joblib`, which uses Python's pickle format (see [Saving a model](/collections/ai-security/ai-tools#saving-a-model)). The file goes to a model registry, a store that keeps each trained model version with its metadata, or to a bucket.

**The attack:** model poisoning is changing the trained model directly, without touching the training data. In a logistic regression filter, setting the weight of the feature "message contains `deals.example.net`" to a large negative value makes every message from that domain score as legitimate, and the rest of the model behaves as before. A pickle model file can also run code when it is loaded, so replacing it gives code execution on every machine that loads it. A pre-trained model downloaded from a public hub can carry planted behavior from before the provider ever touched it.

### 5. Deployment: deployment injection

**What happens:** an inference service, a small API that loads the model file and returns a prediction for each request, scores every incoming message. It usually runs in a container, for example on Kubernetes. The mail system acts on the score: it moves the message to the spam folder, adds a warning, or delivers it.

**The attack:** deployment injection is changing what runs in production after the model has passed evaluation. The attacker can swap the model file the service loads, modify the container image, change the threshold in the service's configuration, or alter scores on their way from the service to the mail system. In each case the model that was tested is not the model that runs.

### 6. Monitoring and maintenance: retraining exploitation

**What happens:** the provider tracks how the filter performs: the share of mail it marks as spam, how many "Not spam" reports it gets per day, and whether incoming mail starts to look different from the training data (drift, see [Datasets](/collections/ai-security/ai-datasets)). Retraining runs every week on the reports collected since the last run, and the loop starts again at collection.

**The attack:** retraining exploitation uses the loop itself. Each retraining run moves the model only a little, so poisoned data spread across many runs shifts it gradually, and no single new model looks different enough from the previous one to raise an alert. An attacker can also manipulate the metrics that trigger retraining, for example by flooding the filter with reports to force a retraining run at a time that suits them.

## Mapping to OWASP and SAIF

[AI Red Teaming](/collections/ai-security/ai-red-teaming) describes the OWASP Machine Learning Security Top 10, the OWASP Top 10 for LLM Applications and Google's SAIF risk map. The lists group attacks differently from the pipeline stages, so some attacks map to more than one entry. The table lists the closest entries. The LLM entries apply when the model being trained or fine-tuned is an LLM; their 2025 number comes first, with the 2026 number in brackets.

| Attack | OWASP ML Top 10 | OWASP LLM Top 10 | SAIF risk |
|---|---|---|---|
| Data poisoning | ML02 Data Poisoning | LLM04 (LLM05) Data and Model Poisoning | Data Poisoning |
| Storage tampering | ML02 Data Poisoning | LLM04 (LLM05) Data and Model Poisoning | Data Poisoning |
| Processing manipulation | ML02 Data Poisoning, or ML06 AI Supply Chain Attacks through a library | LLM03 (LLM04) Supply Chain, through a library | Data Poisoning, or Model Source Tampering when the code changes |
| Model poisoning | ML10 Model Poisoning, or ML06 and ML07 for a downloaded pre-trained model | LLM04 (LLM05) Data and Model Poisoning, LLM03 (LLM04) Supply Chain | Model Source Tampering |
| Deployment injection | ML10 Model Poisoning when the file is swapped, ML09 Output Integrity Attack when scores are changed | No direct entry | Model Deployment Tampering |
| Retraining exploitation | ML08 Model Skewing | LLM04 (LLM05) Data and Model Poisoning | Data Poisoning |

## Remediation

Each stage should check what it receives, and each stage should be writable only by the component that owns it.

- Give each stage its own credentials with write access to its own output only, and log every write to data stores and the model registry.
- Record where every record and label came from, so data from a malicious source can be found, removed, and the model retrained without it.
- Limit how much any one account or source can contribute to a training set, and how much new data one retraining run can add.
- Hash each dataset and model file when a stage writes it, and check the hash before the next stage reads it. Deploy only the model file whose hash matches the one that passed evaluation.
- Review changes to processing and training code like any other production code, and pin the versions of the libraries it imports.
- Never load pickle model files from an untrusted source. safetensors stores neural network weights as plain numbers and cannot run code when loaded. skops, for scikit-learn models, refuses to load any type that is not on a list of trusted types.
- Keep a trusted evaluation set, labeled by your own team and stored where the pipeline cannot write. Compare every retrained model with the previous one on that set before deploying it.
