---
title: "Model Reverse Engineering"
slug: ai-model-reverse-engineering
category: notes
handbook: ai-security
tags: ["ai"]
draft: false
pubDatetime: 2026-11-18T00:00:00+03:00
description: "Building a copy of a classifier from its public API: sampling inputs, recording the model's answers, training a replica on them, and measuring how often the replica agrees with the original, with scikit-learn code and the controls that make it harder."
---

## Introduction

Model reverse engineering, also called model extraction or model stealing, builds a copy of a model using only its inputs and outputs. The attacker never sees the weights or the training data. They send inputs to the model, record what it returns, and train their own model on those input and output pairs. The copy is called a **replica** or **surrogate** model.

A replica is useful to an attacker in two ways:

- **Theft**: the replica does the same job as the original, without the cost of collecting data and training. A competitor can use it, or sell it.
- **Offline testing**: the attacker can try thousands of inputs against the replica without sending a single request to the target, and without being rate limited or logged. Inputs that fool the replica, such as a payment the replica scores as legitimate, often fool the original as well. Only those inputs are then sent to the real model.

The attack needs only the access a normal user has, so it belongs to black-box testing (see [AI Red Teaming](/collections/ai-security/ai-red-teaming)). In the OWASP Machine Learning Security Top 10 it is ML05 Model Theft, and in Google's SAIF it is Model Reverse Engineering.

## The Target

The target in this note is the fraud model from [Application and System Attacks](/collections/ai-security/ai-application-system). Partner shops send a payment's details to `/api/fraud-score` and receive the probability that the payment is fraudulent.

Each payment is described by four features:

| Feature | Meaning | Range |
|---|---|---|
| `amount` | Payment amount in dollars | 1 to 5,000 |
| `hour` | Hour of the day the payment was made | 0 to 23 |
| `account_age_days` | How long the customer account has existed | 0 to 3,650 |
| `items` | Number of items in the order | 1 to 20 |

A request and its response look like this:

```json
{"amount": 2400, "hour": 3, "account_age_days": 2, "items": 9}
```

```json
{"fraud_probability": 0.91, "label": "fraud"}
```

The attacker knows the feature names and ranges from the API documentation, or from watching the requests a partner shop's checkout sends. Without that knowledge the attack is much harder, because the replica has to take the same inputs as the original.

## Choosing Queries

The attacker first needs inputs to send. They have no copy of the training data, so they generate inputs. The simplest method is random sampling: pick each feature uniformly between its minimum and maximum.

```python
import numpy as np                      # numerical arrays and random numbers
import requests                         # sends HTTP requests to the API

rng = np.random.default_rng(seed=0)     # random number generator with a fixed seed, so runs can be repeated
n = 2000                                # number of queries to send

# One column per feature, each drawn uniformly from its documented range
X = np.column_stack([
    rng.uniform(1, 5000, n),            # amount
    rng.integers(0, 24, n),             # hour (the upper bound 24 is excluded)
    rng.integers(0, 3651, n),           # account_age_days
    rng.integers(1, 21, n),             # items
])

names = ["amount", "hour", "account_age_days", "items"]
y = []                                  # the target model's answers go here
for row in X:
    payload = dict(zip(names, row.tolist()))                     # turn one row into the JSON body the API expects
    r = requests.post("https://shop.example/api/fraud-score", json=payload)
    y.append(r.json()["label"])        # keep the label the target model returned
y = np.array(y)
```

`X` holds the inputs and `y` holds the target model's labels for them. These pairs are a labeled training set, and the target model did the labeling.

Random sampling wastes queries. Real fraud is rare, so most random payments come back as `legit`, and only a few land near the line where the target switches from `legit` to `fraud` (the decision boundary). The replica learns the boundary mostly from points near it. Two ways to spend the queries better:

- **Realistic inputs**: sample from data that looks like real traffic, such as public datasets of the same kind, so the queries cover the region the model was trained on.
- **Active sampling**: train a first replica on a small batch, then query the points where that replica is least sure (probability near 0.5), retrain, and repeat. Each round places more queries near the boundary.

## Training the Replica

The attacker trains a classifier on `X` and `y`. The replica does not need to be the same type of model as the original. Any classifier that can draw a similar boundary works, and a random forest is a common first choice because it needs no scaling of the features (see [Random Forests](/collections/ai-security/ai-random-forests)).

```python
from sklearn.ensemble import RandomForestClassifier
from sklearn.model_selection import train_test_split

# Hold back 20% of the queried points to measure the replica on points it did not train on
X_train, X_test, y_train, y_test = train_test_split(X, y, test_size=0.2, random_state=0)

replica = RandomForestClassifier(n_estimators=200, random_state=0)   # 200 trees
replica.fit(X_train, y_train)          # learn to predict the target's labels from the features
```

When the API returns probabilities, the attacker can train a regression model on `fraud_probability` instead of the label. A probability says how far a point is from the boundary, which a label does not, so the same number of queries produces a closer copy.

## Measuring Agreement

The attacker measures how often the replica gives the same answer as the target. This is called **fidelity** or **agreement**. It is different from accuracy: accuracy compares predictions with the true labels, and the attacker does not have true labels. They only have the target's answers, and their goal is to copy those answers, including the target's mistakes.

```python
from sklearn.metrics import accuracy_score, confusion_matrix

pred = replica.predict(X_test)         # replica's labels for the held-back points
print(accuracy_score(y_test, pred))    # share of held-back points where replica and target agree
print(confusion_matrix(y_test, pred))  # rows: target's label, columns: replica's label
```

`accuracy_score` is used here as an agreement score, because `y_test` holds the target's labels. The confusion matrix shows where the two models disagree. For fraud evasion, look at the cell where the target says `fraud` and the replica says `legit`: a payment that the replica would let through and the real model blocks. An attacker who relies on the replica to find passing payments wants that cell close to zero.

## Checking the Region the Attacker Will Use

Agreement on the held-back points is measured on random inputs. The attacker cares about agreement in the region they plan to use: large payments from new accounts. To compare the two models there, they build a smaller set of inputs in that region, query the target for it, and check the replica's agreement on that set alone. High agreement overall can hide low agreement in a small region, because the random sample put few points there.

The same comparison shows where to spend more queries. Points where the two models disagree usually lie near the target's boundary, and querying more points around them improves the replica faster than more random points.

## Remediation

Each control below raises the number of queries an attacker needs or makes them easier to spot. None prevents the attack, because the API has to return answers to be useful.

- Require authentication on the model API, so every query is tied to an account and can be limited and investigated.
- Limit queries per account and per IP address, sized to what a real partner sends in a day.
- Return the label only, or a rounded probability (`0.9` instead of `0.9137`), when the client does not need the exact value.
- Monitor query patterns. Real payments cluster in realistic ranges. Queries spread evenly across every feature's full range, or concentrated near the decision boundary, come from sampling.
- Add a watermark: train the model to give fixed, unusual answers on a small secret set of inputs. A replica trained on the model's answers often copies them, which shows that a suspected copy came from your model.
