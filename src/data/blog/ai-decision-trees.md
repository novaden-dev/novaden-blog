---
title: "Decision Trees"
slug: ai-decision-trees
category: notes
handbook: ai-security
tags: ["ai"]
draft: false
pubDatetime: 2026-11-07T00:00:00+02:00
description: "How a decision tree learns a set of yes/no questions from data: Gini impurity, entropy and information gain worked by hand on ten PowerShell executions, when to stop growing the tree, and what trees need from the data."
---

## Introduction

A decision tree classifies an example by asking a series of yes/no questions about its features. Each answer leads to the next question, and the last answer gives the prediction. Training a tree means choosing which question to ask at each step, using the labeled data.

Trees are easy to read. A trained tree can be printed and checked line by line, and each path from the top to a prediction is a rule such as "if PowerShell was launched by Office, it is malicious". That makes them common in security tooling, where an analyst needs to know why something was flagged.

## The Example Data

An EDR (endpoint detection and response) tool recorded 10 PowerShell executions, and an analyst labeled each one. Three yes/no features describe each run:

| # | Encoded command (`-enc`) | Downloads from the internet | Launched by an Office app | What it was | Label |
|---|---|---|---|---|---|
| 1 | yes | yes | yes | Word macro running an encoded download | malicious |
| 2 | yes | yes | no | Scheduled task running an encoded download | malicious |
| 3 | yes | no | yes | Excel macro running an encoded command | malicious |
| 4 | no | yes | no | Plain script fetching a second-stage payload | malicious |
| 5 | yes | no | no | Management tool running an encoded config script | benign |
| 6 | no | yes | no | Admin script updating a PowerShell module | benign |
| 7 | no | yes | no | Script downloading a vendor installer | benign |
| 8 | no | no | no | Local admin script | benign |
| 9 | no | no | no | Local admin script | benign |
| 10 | no | no | no | Local admin script | benign |

No single feature separates malicious from benign. Encoded commands are mostly malicious, but run 5 is a management tool. Downloads are mixed. The tree has to combine questions.

## Measuring a Mixed Group

At every step, the tree looks for the question that splits the current group into groups that are as close to all-malicious or all-benign as possible. That needs a number for how mixed a group is, called impurity. Two measures are used.

### Gini impurity

Gini impurity is the chance that two runs picked at random from the group (with replacement) have different labels. For a group where a share $$p_k$$ of the runs belongs to class $$k$$:

$$
\text{Gini} = 1 - \sum_k p_k^2
$$

The full dataset is 4 malicious out of 10, so $$p_{\text{mal}} = 0.4$$ and $$p_{\text{ben}} = 0.6$$:

$$
\text{Gini} = 1 - (0.4^2 + 0.6^2) = 1 - (0.16 + 0.36) = 0.48
$$

A pure group, all malicious or all benign, scores 0. With two classes, the worst case is a 50/50 mix at 0.5.

### Entropy

Entropy measures the same thing in bits, using the base-2 logarithm from [Math for Machine Learning](/posts/ai-math):

$$
H = -\sum_k p_k \log_2 p_k
$$

For the full dataset:

$$
H = -(0.4 \log_2 0.4 + 0.6 \log_2 0.6) = 0.529 + 0.442 = 0.971
$$

Entropy is the average number of yes/no questions needed to learn a run's label once you know which group it is in. A pure group needs none, so it scores 0. A 50/50 group needs a full question, so it scores 1.

![Gini impurity and entropy plotted against the share of a node that is malicious. Both are 0 at 0% and 100%, and peak at 50%: Gini at 0.5, entropy at 1.0. A dashed line at 40% marks the root node at Gini 0.48 and entropy 0.97.](/images/ai-decision-trees/impurity.svg)

The two curves have the same shape, and in practice they nearly always choose the same splits. Gini is the default in scikit-learn, the standard Python ML library, because it skips the logarithm and is faster to compute.

## Choosing a Split

### Information gain

Information gain is how much a split lowers entropy. It is the parent group's entropy minus the average entropy of the child groups, weighted by how many runs each child holds:

$$
\text{IG} = H(\text{parent}) - \sum_{\text{children}} \frac{n_{\text{child}}}{n_{\text{parent}}} H(\text{child})
$$

For the question "launched by Office?":

- **Yes**: runs 1 and 3, both malicious. Pure, so $$H = 0$$.
- **No**: the other 8 runs, 2 malicious and 6 benign. $$H = -(0.25 \log_2 0.25 + 0.75 \log_2 0.75) = 0.811$$.

$$
\text{IG} = 0.971 - \left(\frac{2}{10} \times 0 + \frac{8}{10} \times 0.811\right) = 0.971 - 0.649 = 0.322
$$

The same calculation with Gini uses the weighted Gini of the children, and the split with the lowest weighted Gini wins. Running both for every feature:

| Question | Yes group | No group | Weighted Gini | Information gain |
|---|---|---|---|---|
| Encoded command? | 4 runs, 3 malicious | 6 runs, 1 malicious | 0.317 | 0.256 |
| Downloads from the internet? | 5 runs, 3 malicious | 5 runs, 1 malicious | 0.400 | 0.125 |
| Launched by Office? | 2 runs, 2 malicious | 8 runs, 2 malicious | **0.300** | **0.322** |

Both measures pick "launched by Office?" for the first question. "Encoded command?" is a close second: it catches more malicious runs, but leaves both of its groups mixed, while the Office split produces one pure group.

### Numeric features

The features here are yes/no. For a numeric feature, such as command length in characters, the tree turns it into yes/no questions by testing thresholds. It sorts the values, tries a cut between each pair of neighbouring values ("length > 412?", "length > 650?", ...), and scores each cut the same way. The best threshold competes with the other features' best questions.

## Growing the Tree

### Repeating the split

After the first split, the tree treats each child group as a new dataset and repeats the process:

1. If the group is pure, stop and make it a leaf with that label.
2. Otherwise, score every remaining question on this group and split on the best one.
3. Repeat for each new child group.

The "launched by Office" group is already pure. The other 8 runs split on "downloads from the internet?" (information gain 0.311), which separates out 4 benign runs that download nothing. The remaining 4 runs split on "encoded command?":

![The finished tree. Launched by Office? Yes leads to Malicious, 2 of 2. No leads to Downloads from internet? No leads to Benign, 4 of 4. Yes leads to Encoded command? Yes leads to Malicious, 1 of 1. No leads to Benign, 2 of 3, marked impure.](/images/ai-decision-trees/tree.svg)

A new execution is classified by walking from the top. PowerShell launched by `explorer.exe` that downloads a file with an encoded command goes no, yes, yes, and ends at malicious.

### A leaf that cannot be pure

The bottom-right leaf holds runs 4, 6 and 7. All three have the same features (not encoded, downloads, not launched by Office), but run 4 is malicious and runs 6 and 7 are benign. No question about these three features can separate them, so the leaf predicts the majority label, benign, and run 4 is misclassified.

This is a data problem. Separating a script that fetches a payload from one that fetches a vendor installer needs another feature, such as the reputation of the download domain.

### Stopping before it overfits

A tree grown until every leaf is pure ends up memorizing its training data, which is the overfitting described in [Supervised Learning](/posts/ai-supervised-learning). On a real dataset with hundreds of features, it creates leaves for single runs, based on a quirk such as a specific file name. Trees are limited in two ways:

- **Stopping rules**: a maximum depth (no more than, say, 5 questions on any path), a minimum number of runs a group needs before it can be split, or a minimum information gain a split has to reach.
- **Pruning**: grow the full tree, then remove branches that do not improve accuracy on held-out data.

The right settings are found with cross-validation.

## Trees and Attackers

Because the rules are readable, they are also easy to work around once known. An attacker who learns that the first question is "launched by Office?" can launch PowerShell through WMI instead. The new process's parent is then `WmiPrvSE.exe` instead of Word, and the answer to the first question becomes no. One changed feature moves the execution down a different branch.

A tree also only knows about the features it was given. Run 4 shows the result: a malicious script with ordinary-looking features lands in a benign leaf.

## What Trees Need from the Data

Trees make fewer assumptions than linear or logistic regression:

| Property | What it means for the data |
|---|---|
| No linearity needed | A tree models any shape of relationship, one split at a time |
| No scaling needed | Splits compare values against thresholds, so features in bytes and in percent can sit side by side |
| Mixed feature types | Yes/no, categories and numbers work in the same tree |
| Missing values | Many implementations route missing values down a branch or use a substitute feature |

They also have weaknesses that the data has to make up for:

| Weakness | What goes wrong | What helps |
|---|---|---|
| Greedy choices | Each split is the best one at that moment, and the tree never revisits it, so a better overall tree can be missed | Ensembles of many trees |
| Unstable | Changing a few training rows can change the first split and with it the whole tree | Random forests, which average many trees |
| Splits are straight cuts on one feature at a time | A diagonal boundary, like the one in [Logistic Regression](/posts/ai-logistic-regression), becomes a staircase of many small splits | More data, or a feature that combines the two |
| Favours features with many values | A unique ID column splits every run into its own pure leaf and scores the highest information gain while meaning nothing | Remove ID-like columns, or use gain ratio, which penalizes splits into many small groups |
| Class imbalance | With 1 malicious run per 1,000, a tree that always says benign has low impurity | Weight the rare class higher during training |

Random forests and gradient-boosted trees (XGBoost, LightGBM) fix the stability problem by combining hundreds of trees. Each of their trees is built with the same splitting process.
