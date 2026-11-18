---
title: "Denial of ML Service"
slug: ai-denial-of-ml-service
category: notes
handbook: ai-security
tags: ["ai"]
draft: false
pubDatetime: 2026-11-18T00:00:00+03:00
description: "Why a model query costs far more than a web request, how long inputs, long outputs and sponge examples raise that cost, the conditions under which flooding a model works, and the limits that stop it."
---

## Introduction

Denial of ML service makes a model slow, unavailable or expensive to run by sending requests that use up its compute. It is the model version of a denial of service attack, and it works at a lower request volume because each request costs more. It appears in the OWASP LLM Top 10 as Unbounded Consumption and in Google's SAIF as Denial of ML Service (see the table in [Application and System Attacks](/collections/ai-security/ai-application-system)).

The shop from that note has two targets. The support assistant is an LLM chatbot, and the fraud model scores each payment through `/api/fraud-score`. Both run on the same GPU server, so load on one slows the other.

## Why a Model Query Is Expensive

A request to an ordinary web page reads a few rows from a database and fills in a template. It finishes in milliseconds on a CPU, and one server handles thousands per second.

A model query runs the input through the model's weights, which means millions or billions of multiplications on a GPU. Three things set the cost of an LLM request:

- **Input length**: the model reads every input token (a token is a word or a piece of a word). The attention step compares each token with every other token, so for long inputs the work grows faster than the input length does.
- **Output length**: the model produces one token at a time, and each new token needs another pass through the whole model. A reply of 2,000 tokens takes about 2,000 passes.
- **Memory**: for every request in progress, the GPU keeps the intermediate results for all tokens so far (the key-value cache). A long conversation holds that memory for the whole time the reply is generated. When the memory is full, the server cannot accept more requests, even if the GPU is not busy computing.

Applications also multiply the cost. One user message can trigger a retrieval search, several model calls (an agent that plans, calls tools and reads the results), and a moderation check on the input and the output. The attacker pays for one request and the shop pays for all of them.

A GPU server also costs much more per hour than a web server, and many LLM applications pay a provider per token instead. In that case a flood of requests becomes a large bill without the service ever going down. This is sometimes called denial of wallet.

## Sponge Examples

A sponge example is an input crafted to make a model use as much compute, memory or energy as possible. The term comes from the paper "Sponge Examples: Energy-Latency Attacks on Neural Networks" (Shumailov et al., 2021). The attacker does not need the model's weights. They send candidate inputs, measure how long each takes, keep the slowest, change them slightly, and repeat.

For a language model, an input is slow when it becomes many tokens or when it makes the model write a long reply:

- **Many tokens from few characters**: the tokenizer splits common words into one token each, but rare characters and unusual strings into several tokens each. A 1,000 character input made of rare characters can become more tokens than 1,000 characters of English.
- **Inputs that fill the context window**: sending the longest input the application accepts, in every request, keeps each request at its maximum cost.
- **Prompts that ask for long output**: "Write a 5,000 word essay on every product in the catalog" produces a reply up to the output limit. Asking the model to repeat a word forever has the same effect.
- **Prompts that cause repeated tool calls**: "Check the status of every order from 1 to 10000 one at a time" makes an agent loop through tool calls, and each loop sends the growing conversation through the model again.

The token counts below come from `cl100k_base`, the tokenizer used by GPT-4. Other tokenizers split text differently, but common words take fewer tokens than rare ones in all of them:

| Input | Characters | Tokens | How it is split |
|---|---|---|---|
| `refund` | 6 | 1 | `refund` |
| `antidisestablishmentarianism` | 28 | 6 | `ant` `idis` `establish` `ment` `arian` `ism` |
| `Xq7#zv!Pk9&` | 11 | 10 | one token per character, except `Pk` |

A common word is one token. A rare word is split into pieces, and a random string is split into almost single characters, so the same number of characters costs the model several times more work.

The fraud model gives a sponge example almost nothing to work with. It takes four numbers (`amount`, `hour`, `account_age_days`, `items`), so every input has the same size, and a request costs about the same whatever the values are. Against the fraud model, the attacker can only send a large number of requests. Against the assistant, the attacker can choose inputs that cost far more than average.

## When the Attack Works

The attack works when these conditions hold:

- **No authentication or free accounts**: an attacker can send requests without an identity, or can create accounts without limits, so a per-account limit does not stop them.
- **No limit on request volume**: nothing slows an account that sends hundreds of requests a minute.
- **No limit on input or output length**: one request can use as many tokens as the attacker wants.
- **Shared hardware**: the assistant and the fraud model use the same GPU. A flood of long chat requests makes fraud scores time out, so payments fail or are approved without a score. The attack also hurts the fraud model, although the attacker never sent it a request.
- **Automatic scaling without a spending cap**: the service starts more GPU servers when load rises. It stays up, and the cost rises with the attack.

It does not work, or works poorly, when each user has a token budget, requests have a maximum length and a timeout, and the model that serves customers runs on separate hardware from the models the business depends on.

## Testing for It

A test checks whether the application enforces limits at all. It does not need a flood. A few requests show whether input and output length are capped and whether time per request grows with input size.

```python
import time                                   # measures how long each request takes
import requests                               # sends HTTP requests

URL = "https://shop.example/api/chat"         # the assistant's chat endpoint

for size in [100, 1000, 10000, 100000]:       # input sizes in characters
    message = "order " * (size // 6)          # a message of roughly `size` characters
    start = time.time()                       # note the time before the request
    r = requests.post(URL, json={"message": message}, timeout=120)
    elapsed = time.time() - start             # seconds the whole request took
    print(size, r.status_code, round(elapsed, 2))   # status code shows whether a limit rejected it
```

A `400` or `413` status at some size shows an input limit. If the status stays `200` and the time keeps growing, there is no limit. Repeat the test with a prompt that asks for a very long reply and check how long the reply gets before it is cut off.

## Remediation

The controls limit what one user can consume and keep the models the business depends on away from the models users can reach freely.

- Require authentication on every model API, and limit requests and tokens per account, per IP address and per time window.
- Set a maximum input length and a maximum output length (the `max_tokens` setting on most LLM APIs), and a timeout on every request.
- Set a maximum number of tool calls and model calls per user message, so an agent loop ends.
- Reject inputs that tokenize to far more tokens than their character count suggests.
- Run models on separate hardware, or give each its own share of one GPU, so a flood against the assistant cannot starve the fraud model.
- Put a queue in front of the model and reject requests when the queue is full, instead of letting every request wait.
- Set a spending cap and an alert on the model provider account and on the autoscaling group.
- Monitor tokens per request, latency and cost per user, and alert on accounts far above the average.
