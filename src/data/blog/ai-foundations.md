---
title: "AI, Machine Learning, and Deep Learning"
slug: ai-foundations
category: notes
handbook: ai-security
tags: ["ai"]
draft: false
pubDatetime: 2026-11-07T00:00:00+02:00
description: "How AI, machine learning, and deep learning fit inside each other, the three ways a model learns from data, what CNNs, RNNs, and transformers are each built for, and the benchmark results that made deep learning the default."
---

## Introduction

Artificial intelligence (AI) is any software that handles work such as reading text, recognizing faces, or choosing a move in a game, whether it does that with hand-written rules or by learning. Machine learning (ML) is the part of AI where the system learns from data instead of following rules a programmer wrote. Deep learning (DL) is the part of machine learning that uses neural networks with many layers. Every deep learning system is also a machine learning system, and every machine learning system is an AI system.

![Three nested ellipses: Artificial Intelligence on the outside, Machine Learning inside it, and Deep Learning inside Machine Learning](/images/ai-foundations/ai-ml-dl.svg)

## Artificial Intelligence

AI work is usually grouped by the kind of input or task:

- **Expert systems**: programs that store a human expert's knowledge as if/then rules. MYCIN, built at Stanford in the 1970s, recommended antibiotics for blood infections using rules written with doctors.
- **Natural language processing (NLP)**: working with human language. Translating text, answering questions in a chatbot, summarizing a document, sorting support emails into complaints and questions.
- **Computer vision**: working with images and video. Face unlock on a phone, reading license plates, spotting tumors in X-rays.
- **Recommendation systems**: choosing what to show each user, such as the next video on YouTube or the products on an Amazon page, based on what similar users watched or bought.
- **Robotics**: machines that act in the physical world, such as warehouse robots that move shelves or a robot vacuum that maps a room.

Expert systems do not learn. Every rule is written by hand, and the system can only handle cases its rules cover. Machine learning replaces the hand-written rules with patterns found in data.

## Machine Learning

In a traditional program, a programmer writes the rule: if the subject line contains "free money", mark the email as spam. In machine learning, you give the algorithm thousands of example emails and it works out the rules itself, including ones nobody would have thought to write.

There are three ways a model learns, and they differ in what the training data contains.

### Supervised learning

Each training example comes with the correct answer, called the label. The model learns to map inputs to labels, then predicts the label for inputs it has never seen.

- **Spam detection**: train on 100,000 emails, each labeled spam or not spam. The model picks up which words, sender domains, and link counts go with spam, then labels new emails as they arrive.
- **Medical imaging**: train on chest X-rays that radiologists have labeled "pneumonia" or "clear". The model learns which patterns in the image go with each label and flags new scans for a doctor to review.
- **Fraud detection**: train on past card transactions marked fraud or legitimate, described by amount, country, time of day, and merchant. A $2,000 purchase at 3 a.m. from a country the cardholder has never used gets a high fraud score.

Predicting a category (spam or not spam) is called classification. Predicting a number, such as a house price from its size, location, and number of rooms, is called regression.

The downside is the labels. Someone has to produce the correct answer for every training example, often by hand, and that is slow and expensive at the scale models need.

### Unsupervised learning

The training data has no labels. The model finds structure in the data on its own.

- **Clustering malware samples**: give the model 50,000 unknown malware samples, each described by features such as the Windows API functions it imports, the strings inside it, and the domains it contacts. The model groups samples that look alike. An analyst then reverses one sample per group instead of all 50,000, and names each group as a malware family. Nobody defined the families in advance.
- **Anomaly detection**: the model learns what normal activity looks like for each user (login times, locations, how much data they download) and flags anything far outside it. A user who logs in from Cairo at 9:00 and from São Paulo at 9:05 gets flagged, even though nobody wrote an "impossible travel" rule.
- **Dimensionality reduction**: a dataset might describe each customer with 500 columns, many of which overlap. Total spend, for example, is close to average order value times number of orders. Dimensionality reduction compresses the 500 columns into a few, such as 10, that keep most of the information. Later models train faster on the smaller version, and two or three columns can be plotted on a chart.

### Reinforcement learning

There is no dataset. An agent takes actions in an environment and receives a reward or a penalty for the result. Over many attempts it learns which actions lead to the highest total reward.

- **Game playing**: AlphaZero (DeepMind, 2017) learned chess, shogi, and Go only by playing against itself, starting from random moves, with +1 for a win and -1 for a loss. Nobody gave it human games or strategy.
- **Robotics**: a robot arm gets a reward for lifting a cup and a penalty for dropping it or knocking it over, and learns a working grip from the failures. Training usually happens in simulation first so the real hardware does not get damaged.
- **Chatbot training**: after a language model is trained on text, people rate its answers, and those ratings become the reward. The model is then tuned to produce answers that score higher. This is called reinforcement learning from human feedback (RLHF), and OpenAI used it to turn GPT-3 into the more helpful InstructGPT in 2022.

Unlike in supervised learning, the agent is never told the correct action. It only learns whether the outcome was good, and the reward often arrives many steps after the action that earned it.

| Type | Learns from | Example |
|---|---|---|
| Supervised | Inputs paired with correct answers | Spam filter trained on labeled emails |
| Unsupervised | Inputs with no answers | Grouping malware samples into families |
| Reinforcement | Rewards and penalties from its own actions | Game agent trained by self-play |

## Deep Learning

A neural network is made of layers of simple units. Each unit takes numbers in, multiplies each one by a weight, adds the results, and passes the total to the next layer. Training adjusts the weights, a little at a time, until the network's outputs match the training data. A deep network has many layers, and each layer works on the output of the one before it.

In older machine learning, a person chooses the features the model looks at. For a spam filter that means deciding to count links, check the sender domain, and look for certain words. A deep network receives the raw data (pixels, characters, audio samples) and its layers learn the features themselves. That is what it means for deep learning to "extract features".

Different network designs suit different shapes of data.

### Convolutional neural networks (CNNs)

CNNs are built for grid-shaped data, mainly images. A CNN slides small filters, such as 3x3 pixel windows, across the image and records where each filter matches. The layers build on each other:

1. Early layers detect edges and changes in color.
2. Middle layers combine edges into shapes and textures: curves, corners, fur.
3. Later layers combine shapes into objects: two eyes, a nose, and whiskers make a cat face.

The same filter is applied across the whole image, so a cat is recognized whether it is in the top left corner or the bottom right. Face unlock, X-ray analysis, and license plate readers all use CNNs.

### Recurrent neural networks (RNNs)

RNNs are built for sequences such as text and speech, where order changes the meaning ("dog bites man" and "man bites dog"). An RNN reads one item at a time and carries a hidden state, a running summary of what it has read so far, into the next step. At word 5 it still holds information about words 1 to 4.

Predicting the next word is a typical use. After "The clouds are dark, it is going to", the hidden state still holds "clouds" and "dark", and the network predicts "rain". Phone keyboard suggestions and Google Translate before 2017 used RNNs.

RNNs have two problems. Information from early in a long sequence fades as the hidden state is overwritten, so by word 200 the network has little left of word 1. And because each step depends on the one before, the sequence cannot be processed in parallel, which makes training slow.

### Transformers

Transformers, introduced in 2017, process the whole sequence at once instead of one word at a time. Their core mechanism is self-attention: for each word, the model computes a score against every other word in the input, and builds that word's representation mostly from the high-scoring ones.

In "The animal didn't cross the street because it was too tired", a trained model scores "it" highly against "animal". Change "tired" to "wide" and the high score moves to "street". The distance between the words makes no difference, which is what "long-range dependencies" means: links between words that sit far apart.

Processing every word at once also means the work runs in parallel on GPUs, so transformers can be trained on far more data than RNNs in the same time. Large language models such as GPT, Claude, and Gemini are transformers (the T in GPT stands for transformer), and the design is now used for images and audio too.

| Network | Data shape | How it works | Example |
|---|---|---|---|
| CNN | Grids (images) | Small local patterns combine into larger ones | Face unlock |
| RNN | Sequences | Carries a running summary from step to step | Keyboard next-word suggestions |
| Transformer | Sequences, now also images | Every part scores its relevance to every other part | Chatbots such as ChatGPT and Claude |

### Benchmarks and state of the art

State-of-the-art (SOTA) means the best result anyone has reported so far on a standard benchmark. Researchers test their methods on shared datasets so the scores can be compared, and a method holds SOTA until another one scores higher. When people say deep learning reached state-of-the-art performance in an area, they mean deep learning methods beat every earlier approach on that area's benchmarks.

- **Image classification**: ImageNet is a benchmark of about 1.2 million images in 1,000 categories. In 2012 the best non-deep-learning entry had a top-5 error of 26%, meaning the correct label was missing from its five best guesses 26% of the time. AlexNet, a CNN, scored 15.3% that year. In 2015 ResNet reached 3.6%, below the roughly 5% error measured for a trained human on the same test.
- **Machine translation**: in 2016 Google replaced its phrase-based translation system with a neural one, and reported that it cut translation errors by about 60% on several language pairs in human evaluations.
- **Protein structure**: predicting a protein's 3D shape from its amino acid sequence had been an open problem in biology for 50 years. At the CASP14 competition in 2020, DeepMind's AlphaFold 2 predicted structures with a median accuracy score of 92.4 out of 100, close to what lab experiments that take months or years produce.
- **Game playing**: in 2016 DeepMind's AlphaGo beat Lee Sedol, one of the top Go players in the world, 4 games to 1. Go has too many possible positions for brute-force search, and most researchers had expected this to take another decade.

A SOTA claim is only true as of the date it was made. The ImageNet record has been beaten many times since ResNet, and new language models overtake each other on benchmarks every few months.
