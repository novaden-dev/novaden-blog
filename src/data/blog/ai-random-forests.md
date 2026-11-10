---
title: "Random Forests"
slug: ai-random-forests
category: notes
handbook: ai-security
tags: ["ai"]
draft: false
pubDatetime: 2026-11-09T00:00:00+03:00
description: "How a random forest combines hundreds of decision trees: bootstrap samples, random feature subsets at each split, averaging the trees' probabilities, the main hyperparameters, feature importance and its limits, and what a forest costs. Worked on NSL-KDD network connections."
---

## Introduction

A random forest is a classifier made of many [decision trees](/collections/ai-security/ai-decision-trees), usually a hundred or more. Each tree is trained on a slightly different version of the data, and the forest's prediction combines all of their predictions. A model built from several models like this is called an ensemble.

A single tree is unstable: changing a few training rows can change its first split and, with it, the whole tree. Trees trained on different versions of the data make different mistakes, and averaging many of them cancels much of that out.

The examples use [NSL-KDD](https://www.unb.ca/cic/datasets/nsl.html), a public intrusion detection dataset from the Canadian Institute for Cybersecurity. Each row is one network connection, described by 41 features such as the protocol, the service, the bytes sent in each direction, and how many connections went to the same destination host in the previous two seconds. Each row is labeled `normal` or with one of 39 attack names, grouped into four classes. The dataset comes as an official training set of 125,973 connections and a test set of 22,544. The training set contains:

| Class | Attacks | Rows |
|---|---|---|
| Normal | Ordinary traffic | 67,343 |
| DoS (denial of service) | Floods such as `neptune` (SYN flood) and `smurf` | 45,927 |
| Probe | Scans such as `nmap`, `satan` and `portsweep` | 11,656 |
| R2L (remote to local) | Gaining access from outside, such as `guess_passwd` and `warezmaster` | 995 |
| U2R (user to root) | Privilege escalation, such as `buffer_overflow` and `rootkit` | 52 |

An accuracy figure depends on which connections the model was trained on and which it was measured on. The forests in this note are trained on 80% of the official training set and measured on the other 20% (25,195 connections). The official test set contains attack types that never appear in the training set, so a score on it mostly measures how the forest handles new attacks. That score would hide the effects of bootstrap samples, voting and hyperparameters. The note uses the official test set only in the last paragraph of [What Forests Need from the Data](#what-forests-need-from-the-data). The 80/20 split is [stratified](/collections/ai-security/ai-supervised-learning#stratified-splits): each class keeps the same share in both parts, so the 52 U2R connections split into 42 for training and 10 for testing. The forests use the preparation described in [What Forests Need from the Data](#what-forests-need-from-the-data).

## Bootstrap Samples

Each tree trains on a bootstrap sample: as many rows as the training set has, drawn at random with replacement. With replacement means that each drawn row goes back before the next draw, so it can be drawn again. Some rows are drawn two or more times and others not at all.

With a training set of 10 rows, numbered 1 to 10, three trees could get these samples:

| Tree | Bootstrap sample (10 draws) | Drawn more than once | Never drawn |
|---|---|---|---|
| 1 | 9, 7, 6, 3, 4, 1, 1, 1, 2, 9 | 1 (three times), 9 | 5, 8, 10 |
| 2 | 5, 6, 8, 10, 1, 2, 9, 10, 3, 4 | 10 | 7 |
| 3 | 9, 3, 2, 3, 5, 9, 5, 1, 4, 7 | 3, 5, 9 | 6, 8, 10 |

Each sample has the same size as the training set, but a different mix of rows. A row drawn three times counts three times in that tree's training. The trees learn from different data and come out different, which is what makes averaging them useful: trees trained on identical rows would all be the same.

On average a bootstrap sample contains 63% of the distinct training rows, and the rest of its draws are repeats, so every tree sees a different 63%.

Training models on bootstrap samples and combining them is called bagging (bootstrap aggregating).

The rows a tree never drew are its out-of-bag rows, such as rows 5, 8 and 10 for tree 1 above. They work as a test set that needs no extra data: each row is predicted only by the trees that never trained on it, and the prediction is compared with the row's label. In the table, row 7 is predicted by tree 2 alone, row 8 by trees 1 and 3 together, and rows 1, 2, 3, 4 and 9, which every tree drew, are skipped. With 100 trees, each row is out-of-bag for about 37 of them, so every row gets a prediction from the trees that never saw it.

The share of correct out-of-bag predictions is the out-of-bag score. scikit-learn computes it with `oob_score=True` and stores it in `oob_score_`:

```python
forest = RandomForestClassifier(oob_score=True, n_jobs=-1).fit(X_train, y_train)
forest.oob_score_
```

The same NSL-KDD forest, measured in two ways:

| Method | Data used for the measurement | Accuracy |
|---|---|---|
| Held-out test set | 25,195 connections set aside before training, never used to train | 99.88% |
| Out-of-bag score | The 100,778 training connections, each one predicted only by the trees that never drew it | 99.87% |

The held-out test set is the standard measurement, and the out-of-bag score gives the same result without it. The out-of-bag score therefore lets the forest train on every labeled row and still get a fair measurement. With 125,973 connections, setting 20% aside costs little. With a few hundred labeled samples, such as a small malware collection, every row set aside for testing is a row the model cannot learn from.

## Random Features at Each Split

Bootstrap samples alone still produce similar trees. If one feature is much stronger than the rest, almost every tree splits on it first. A random forest also limits the choice at each split: the tree may only pick from a random subset of the features, drawn fresh for every split.

scikit-learn's default for classification is the square root of the number of features. NSL-KDD has 121 features after encoding, so each split chooses among 11 random ones. As a result, the 100 trees of the forest start with different questions: the most common first split, on `same_srv_rate`, is the first question in only 11 of the 100 trees. `same_srv_rate` is the share of the connections to the same host in the previous two seconds that went to the same service as the current connection. Ordinary traffic keeps using one service, so its value is close to 1. A scan that probes many ports on one host has a low value.

## Combining the Trees

For a new connection, every tree predicts class probabilities, and the forest averages them. The class with the highest average wins. Most of the time the trees agree: all 100 trees give the same class for 93.8% of the held-out connections. For one DoS connection, 96 trees said DoS and 4 said Normal, so the forest gave it 0.96 DoS and 0.04 Normal.

The individual trees of the forest score between 99.47% and 99.69% accuracy on the held-out connections. The forest scores 99.88%. Each tree misclassifies some connections, but rarely the same ones as most other trees, so the average is right more often than any single tree.

## Hyperparameters

| Parameter | Default | Effect |
|---|---|---|
| `n_estimators` | 100 | Number of trees. Adding trees does not make the forest overfit, but the gain stops after some point and each tree adds training time and memory |
| `max_features` | `"sqrt"` | Features considered at each split. Fewer makes the trees more different from each other |
| `max_depth`, `min_samples_leaf` | No limit, 1 | The [stopping rules](/collections/ai-security/ai-decision-trees#stopping-before-it-overfits) of each tree. By default every tree grows until its leaves are pure |
| `class_weight` | None | Weights rare classes higher, as described in [Class Imbalance](/collections/ai-security/ai-supervised-learning#class-imbalance) |
| `random_state` | None | Fixes the random draws, so the same data gives the same forest every time |
| `n_jobs` | None | Number of CPU cores used to build trees in parallel. `-1` uses all of them |

On NSL-KDD, accuracy rises with the number of trees and then levels off:

| Trees | 1 | 10 | 50 | 100 | 300 |
|---|---|---|---|---|---|
| Accuracy | 99.63% | 99.86% | 99.87% | 99.88% | 99.89% |

The trees in a forest are usually grown without depth limits. A single fully grown tree overfits, but the averaging cancels much of that, so a forest needs less tuning than a single tree.

## Feature Importance

After training, `feature_importances_` gives one number per feature: how much the splits on that feature reduced [Gini impurity](/collections/ai-security/ai-decision-trees#gini-impurity), averaged over all trees and scaled so that all features add up to 1. On NSL-KDD, the top three are `src_bytes` (0.11), `same_srv_rate` (0.08) and `diff_srv_rate` (0.08). `src_bytes` is the number of bytes the client sent to the server, and `diff_srv_rate` is the opposite of `same_srv_rate`: the share of the recent connections to the same host that went to a different service.

```python
import pandas as pd

importances = pd.Series(
    model.named_steps["forest"].feature_importances_,
    index=model.named_steps["encode"].get_feature_names_out(),
)
importances.sort_values(ascending=False).head(10)
```

It shows which features the forest used. A high importance does not mean that the feature causes an attack. The measure also has two known biases. Features with many distinct values, such as byte counts, get more chances to produce a good split and score higher. When two features carry the same information, the forest splits on one or the other, and the importance is divided between them, so each one looks less important than it is. `permutation_importance` in `sklearn.inspection` measures it differently: it shuffles one feature in the test set and records how much the score drops.

## The Cost of a Forest

A forest is less readable than a single tree. One tree can be printed and followed as a set of rules. The trees of the NSL-KDD forest, grown to full depth, have an average depth of 30 and about 585 leaves each, far too many to read as rules.

A forest is also larger and slower than a single tree. The NSL-KDD forest has 116,824 nodes in total, and saved with [joblib](/collections/ai-security/ai-tools#saving-a-model) it takes 12 MB. Each prediction runs through all 100 trees. Training is fast because trees are independent and can be built in parallel with `n_jobs=-1`: on NSL-KDD it takes about 4 seconds.

## What Forests Need from the Data

Forests share what [trees need](/collections/ai-security/ai-decision-trees#what-trees-need-from-the-data): no [scaling](/collections/ai-security/ai-datasets#scaling), and no problem with skewed features, since each split only compares a feature to a threshold.

scikit-learn's forests only accept numbers, so text categories have to be [encoded](/collections/ai-security/ai-datasets#encoding-categorical-features) first. NSL-KDD has three: `protocol_type` (3 values), `service` (70 values) and `flag` (11 values, the state the connection ended in). One-hot encoding turns them into 84 columns, and the other 37 features stay as they are. A fourth column, `num_outbound_cmds` (the number of outbound commands in an FTP session), is 0 in every row and is [dropped](/collections/ai-security/ai-datasets#columns-with-one-value), which gives 121 features in total.

`ColumnTransformer` applies the encoder to the text columns only and passes the rest through. Putting it in a [pipeline](/collections/ai-security/ai-tools#pipelines) with the forest fits the encoder on the training data only:

```python
from sklearn.compose import ColumnTransformer
from sklearn.preprocessing import OneHotEncoder
from sklearn.pipeline import Pipeline
from sklearn.ensemble import RandomForestClassifier

categorical = ["protocol_type", "service", "flag"]

model = Pipeline([
    ("encode", ColumnTransformer(
        [("onehot", OneHotEncoder(handle_unknown="ignore"), categorical)],
        remainder="passthrough",          # keep the numeric columns unchanged
        verbose_feature_names_out=False,  # plain column names, such as flag_SF
    )),
    ("forest", RandomForestClassifier(n_jobs=-1, random_state=0)),
])
model.fit(X_train, y_train)
```

A forest also only recognizes what its training data contains. Trained on the whole official training set and measured on the official test set, which contains attack types that never appear in training, the forest's accuracy drops from 99.88% to 74.8%, and a single tree does no worse at 76.5%. Averaging trees reduces their random mistakes, but every tree learned from the same attacks, so none of them learned the new ones. [Splitting for Unseen Attacks](/collections/ai-security/ai-datasets#splitting-for-unseen-attacks) covers this in detail.
