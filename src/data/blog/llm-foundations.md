---
author: Kayra
pubDatetime: 2026-08-17T00:00:00Z
title: "LLM Foundations"
slug: "llm-foundations"
description: "The vocabulary you need to read AI security material: weights, fine-tuning, adapters, distillation, embeddings, RAG, context windows, tool calls, agents, and MCP, explained in plain language with why each one matters to an attacker."
tags: ["security", "ai", "llm"]
category: notes
draft: true
featured: false
---

## Introduction

Most AI security writing assumes you already know what a weight, an adapter, or an embedding is. If you came from application security rather than machine learning, that assumption is the thing standing between you and the actual content.

This post defines the terms, in the order they build on each other, with a note on why each one matters to someone attacking or defending the system. It is not a machine learning course. It is the vocabulary needed to read the [OWASP Top 10 for LLM Applications](/posts/owasp-llm-top-10) and its agentic counterpart without stopping every third sentence.

## The model itself

**Model.** The trained thing that takes text (or images, or audio) in and produces text out. In practice it is a large file of numbers plus the code to run it. When people say "the LLM", this is what they mean.

**Weights.** Those numbers. Training produces them, and they are what the model knows. Ship the weights and you have shipped the model. This is why model files are treated as artifacts to be signed and hash-pinned rather than as data.

**Open-weight.** A model whose weights you can download and run on your own hardware, as opposed to one you can only reach through somebody's API. The security consequence is direct: an attacker holding the weights can attack offline, at whatever rate they like, and none of your rate limits or monitoring apply.

**Token.** The unit a model reads and writes, roughly a word fragment. Everything is counted in tokens: billing, rate limits, context sizes, and the budget an attacker can force you to spend.

**Hallucination.** The model stating something false with exactly the same confidence it uses for something true. There is no signal in the output that separates the two, which is why "the model sounded sure" is not evidence of anything.

## Changing a model after training

**Fine-tuning.** Taking an already-trained model and training it further on a smaller dataset so it does your specific job better. It changes the weights. A fine-tuned model memorizes its training data more readily than the base model it came from, which makes it a better extraction target.

**Adapter (LoRA).** A cheap way to fine-tune. Instead of changing all the weights, you train a small separate file that gets applied on top of the original model when it loads. Cheap to train and easy to share, which is also what makes it a supply-chain problem: it arrives as its own file, from somewhere, and merges into a model you trusted.

**Quantization.** Shrinking a model by storing its weights at lower precision so it runs on smaller hardware. Worth knowing because weights can be crafted so the full-precision model behaves normally while the shrunk version, which is the one you actually deploy, does not.

**Distillation.** Training a smaller model to imitate a larger one by feeding it the larger one's answers. Legitimate as an engineering technique, and also exactly how someone clones your model through your own API.

> **Note:** the weights are not the whole model. Chat templates, tokenizer configs, adapters, and quantization artifacts ship alongside them and are loaded as configuration. Treat those files as code, because a backdoor can live in them while the weights stay untouched and benchmark normally.

## What the model can see

**Context window.** Everything the model can see at once for a single request. The system prompt, the user's message, retrieved documents, tool output, and conversation history all sit in here together, as one stream of tokens. Nothing in that stream is marked as more trustworthy than anything else, which is the root of most prompt-injection risk.

**System prompt.** The instructions the developer puts in front of every conversation to set the model's role and rules. Users do not normally see it. Treat it as discoverable anyway: it sits in the same context window as everything else.

## Retrieval

**Embedding.** Text or an image converted into a list of numbers that represents its meaning, arranged so that similar things end up with similar numbers. This is what makes search-by-meaning work rather than search-by-keyword.

**Vector store.** The database those embeddings live in, built to answer "what is closest to this". Worth knowing that embeddings can be turned back into readable source text, so a leaked vector store is a document leak, not a leak of harmless numbers.

**RAG (retrieval-augmented generation).** Before answering, the system searches a document store for relevant passages and pastes them into the prompt. It is how you get a model to answer questions about your own documents without retraining it. It is also how attacker-authored text reaches the context window without the attacker touching your application.

## Acting on the world

**Tool call.** A capability the developer hands the model so it can do something rather than only talk: read a file, send mail, query a database, run a command. The model does not execute anything itself. It emits a request, and your code decides whether to honor it, which is where authorization belongs.

**Agent.** A model wired to tools and run in a loop, where its output decides the next action. The loop is what distinguishes an agent from a chatbot: output becomes input, so an error or an injection at step one propagates through every step after it.

**Planner (orchestration).** The logic that decomposes a goal into steps and decides what to do next. It may be code, or it may be the model itself. When it is the model, the plan is as manipulable as any other output.

**Agent-to-agent communication.** One agent passing work or results to another. The receiving agent generally has no way to verify that a message reflects what actually happened upstream, so a wrong or manipulated result gets consumed as established fact.

**Human-in-the-loop.** A person approving an action before it executes. Effective in proportion to how much of the real action the person is actually shown, and how many approvals they are asked for per hour.

**MCP (Model Context Protocol).** A standard way to plug tools and data sources into an assistant. An MCP server is one such plug-in. It is the current default path by which third-party code and third-party data reach a model with your credentials attached.

## Why the vocabulary splits the way it does

The terms above fall into two groups, and OWASP splits its guidance along the same line.

While the model is a component that reads input and returns text, the risks are about what it reads and what it emits. That is the [OWASP Top 10 for LLM Applications](/posts/owasp-llm-top-10).

Once the model is an actor, holding tools, carrying memory between sessions, and setting off consequences downstream, the risks are about what it is permitted to do and how failures propagate. That is the OWASP Top 10 for Agentic Applications, a separate list.

Most real systems sit on the boundary, so both apply.
