---
title: "Storage and Deployment Attacks"
slug: ai-storage-and-deployment
category: notes
handbook: ai-security
tags: ["ai"]
draft: false
pubDatetime: 2026-11-18T00:00:00+03:00
description: "How an ML system's stored data, model files, deployment path, servers and framework code get attacked: excess data kept, open storage, a swapped model file, a compromised GPU server, and a model file that runs code when it is loaded, with checks that stop each."
---

## Introduction

A model is a file, and the data it learned from and the data it handles are files and database rows. They sit in storage, travel through a deployment pipeline to a server, and are loaded by framework code. Each step has an attack. The shop from [Application and System Attacks](/collections/ai-security/ai-application-system) has this layout:

- A conversation database holding every chat with the support assistant.
- A training set of past payments for the fraud model.
- A storage bucket, `shop-ml-models`, holding the model files.
- A pipeline that trains, tests and uploads a new fraud model each week, and a serving program on a GPU server that loads the newest file at startup.

## Keeping More Data Than the System Needs

Excessive data handling is collecting, keeping or reusing user data beyond what the feature needs. It increases the damage from every other storage flaw, because a breach exposes more data.

The shop shows three forms of it:

- **Collecting too much**: the fraud model's training set contains full card numbers, though the model uses only the amount, hour, account age and item count.
- **Keeping too long**: the assistant's conversations are stored forever, with the addresses and card numbers customers pasted into them.
- **Reusing for another purpose**: the stored conversations are used to fine-tune the next version of the assistant. A model can repeat text from its training data, so a customer's address from one conversation can appear in a reply to another customer. [LLM Reconnaissance](/collections/ai-security/ai-llm-recon) and [Prompt Injection](/collections/ai-security/ai-prompt-injection) cover ways to get a model to repeat what it was given.

As a tester, ask what is stored, for how long, who can read it, and whether it is used to train a model.

## Storage That Anyone Can Read or Write

Insecure storage is data or model files reachable by someone who should not reach them. Common forms in an ML system:

- **A public bucket**: the model bucket allows listing or reading without credentials. Anyone can download the fraud model file, which is a faster way to copy a model than [Model Reverse Engineering](/collections/ai-security/ai-model-reverse-engineering), and can also download the training data.
- **A writable bucket**: a bucket that allows writes lets an attacker replace files (see the next section).
- **Credentials in the wrong place**: access keys in a notebook, a Git repository, or an environment variable that a debug page prints.
- **No encryption**: data at rest in the bucket and the database is not encrypted, and traffic to the bucket is not required to use TLS.
- **Unprotected supporting services**: a vector database that stores the assistant's document embeddings with no password, or backups and prompt logs kept in a bucket with weaker access rules than the main database.

## Replacing the Deployed Model

Model deployment tampering changes the model that runs in production without changing the application. The model's path from training to serving has several places where a file can be replaced:

| Stage | What an attacker with access can do | Control |
|---|---|---|
| Training | Poison the data, or change the training code (see [AI Data Pipelines](/collections/ai-security/ai-data-pipeline)) | Review of data sources and code changes |
| Pipeline | Steal the pipeline's credentials and upload their own file | Short-lived credentials, upload only from the pipeline |
| Bucket or registry | Overwrite `latest.pkl` | Write access for the pipeline only, versioning, object lock |
| Serving server | Replace the file on disk, or the file path the server loads | Read-only file system, hash check on load |

The replaced model can behave normally on almost every input and differently on inputs the attacker chose. A fraud model with a backdoor scores any payment of exactly 13.37 dollars as legitimate, so the attacker's fraud passes and the shop's tests, which never use that amount, still pass. A swapped file can also contain code that runs when it is loaded (see below).

The check is to record the SHA-256 hash of each model file when it passes evaluation, store the hash where the bucket's writers cannot change it, and verify it before loading:

```python
import hashlib                                # computes file hashes
import json                                   # reads the manifest

def sha256_of(path):
    h = hashlib.sha256()                      # start a hash
    with open(path, "rb") as f:               # read the file in binary mode
        for chunk in iter(lambda: f.read(1 << 20), b""):   # 1 MiB at a time, so large models do not fill memory
            h.update(chunk)
    return h.hexdigest()                      # the hash as a hexadecimal string

manifest = json.load(open("manifest.json"))   # written by the pipeline when the model passed tests, stored separately from the bucket
path = "fraud/latest.pkl"
if sha256_of(path) != manifest[path]:         # the file differs from the one that was tested
    raise SystemExit("model file does not match the approved hash, refusing to load")
```

A manifest stored in the same bucket as the model can be replaced along with it, so it needs its own storage or a digital signature.

## Compromising the Server

The GPU server holds the model files, read access to the training data, and credentials to the cloud account. An attacker who can run code on it has access to all three, and to the GPUs.

The overview note lists ways to get access: Jupyter and Ray dashboards with no authentication, a model server management API on every network interface, and unpatched serving software. With access, an attacker can:

- Read the cloud credentials from the instance metadata address (`169.254.169.254`) or from environment variables, and use them against the bucket, the database and other services.
- Read the model files and the training data directly from disk, or the model's weights from memory.
- Replace the model file, then restart the serving program.
- Use the GPUs for other work. Exposed Ray clusters were used for cryptocurrency mining in the ShadowRay campaign.

Containers that run as root, with the host's file system or network mounted, give an attacker on the server more than the model's own process needs. A cloud role with permission to read every bucket gives them every bucket.

## Model Files That Run Code

Many frameworks save models with Python's `pickle` format, directly or inside another file type. A pickle file can tell Python to call any function, and Python calls it while loading the file. PyTorch's `torch.load` uses pickle, and so do many `.pkl` and `.pt` model files.

The following creates a file that prints a message when loaded. The message stands in for any command:

```python
import pickle                                 # Python's object serialization format
import os                                     # used by the payload

class Payload:
    def __reduce__(self):                     # pickle calls this to learn how to rebuild the object
        return (os.system, ("echo model file ran this command",))   # "rebuild" by calling os.system with this string

with open("fraud.pkl", "wb") as f:            # write the file the way a model would be saved
    pickle.dump(Payload(), f)

with open("fraud.pkl", "rb") as f:            # the serving program loads the file
    pickle.load(f)                            # prints the message here, before any model exists
```

An attacker who can put a file like this in the model bucket, or publish it on a model sharing site, runs code on every server that loads it, with the server's permissions. After that, everything in the previous section applies.

Other framework features run code from the model's source as well. Keras models can contain `Lambda` layers that hold Python code, and Hugging Face's `trust_remote_code=True` option runs the Python files that come with a model repository. Vulnerabilities in the frameworks themselves, such as the `weights_only` bypass in old PyTorch versions listed in the overview note, also turn a model file into code execution.

## Remediation

Keep only the data the system needs, restrict who can read and write each store, and verify every file before the serving program loads it.

- Remove fields the model does not use, such as card numbers, from training sets, and delete conversations and logs after a fixed period.
- Do not train on conversations without a stated purpose and a way to remove a user's data.
- Block public access on buckets and databases, encrypt data at rest, and require TLS. Grant the pipeline write access to the model bucket and give everything else read-only access.
- Keep credentials out of notebooks, repositories and logs. Use short-lived credentials from the platform instead of long-lived access keys.
- Turn on versioning for the model bucket so an overwritten file can be recovered, and object lock (a setting that blocks deletes and overwrites for a set period) for approved model files.
- Hash or sign each model file when it passes evaluation, and verify it before loading. Store the hash or signature separately from the bucket.
- Save models in a format that cannot run code, such as `safetensors` (a format that stores only the numbers of the weights), and load pickle files only from sources that the shop controls. Use `weights_only=True` in `torch.load` on a patched PyTorch version, and leave `trust_remote_code` off unless the code has been reviewed.
- Run the serving program as a non-root user in a container with a read-only file system, and give its cloud role access to the model bucket only.
- Block access to the instance metadata address from the serving program, or require the token-based version of the metadata service.
- Keep Jupyter, Ray, MLflow and serving management APIs off the internet and behind authentication, and patch ML frameworks and serving software on the same schedule as the rest of the servers.
