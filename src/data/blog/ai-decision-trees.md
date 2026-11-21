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

An EDR (endpoint detection and response) tool recorded 10 PowerShell runs, where a run is one time PowerShell was started on a machine, and an analyst labeled each run as malicious or benign. Three yes/no features describe each run:

![Ten cards, one per PowerShell run, each listing encoded command, downloads from the internet and launched by an Office app, what the run was, and its label. Run 1: yes, yes, yes, Word macro running an encoded download, malicious. Run 2: yes, yes, no, scheduled task running an encoded download, malicious. Run 3: yes, no, yes, Excel macro running an encoded command, malicious. Run 4: no, yes, no, plain script fetching a second-stage payload, malicious. Run 5: yes, no, no, management tool running an encoded config script, benign. Run 6: no, yes, no, admin script updating a PowerShell module, benign. Run 7: no, yes, no, script downloading a vendor installer, benign. Runs 8, 9 and 10: no, no, no, local admin script, benign.](/images/ai-decision-trees/runs.svg)

No single feature separates malicious from benign. Encoded commands are mostly malicious, but run 5 is a management tool. Downloads are mixed. The tree has to combine questions.

![The 10 runs split by each feature on its own, as numbered dots colored malicious or benign. Encoded command: yes holds runs 1, 2 and 3 (malicious) and 5 (benign); no holds 4 (malicious) and 6 to 10 (benign). Both sides are mixed. Downloads from the internet: yes holds 1, 2 and 4 (malicious) and 6 and 7 (benign); no holds 3 (malicious) and 5, 8, 9 and 10 (benign). Both sides are mixed. Launched by an Office app: yes holds 1 and 3, both malicious, so that side is pure; no holds 2 and 4 (malicious) and 5 to 10 (benign).](/images/ai-decision-trees/feature-splits.svg)

## Measuring a Mixed Group

At every step, the tree looks for the question that splits the current group into groups that are as close to all-malicious or all-benign as possible. To compare questions, it needs a score for how mixed a group is, called impurity. A group where every run has the same label scores 0, and the score rises as the labels get more mixed. scikit-learn, the standard Python ML library, offers two impurity scores: Gini impurity and entropy.

### Gini impurity

Gini impurity is the chance that two runs picked at random from the group have different labels.

- A group of only malicious runs scores 0: any two runs you pick match.
- A group that is half malicious and half benign scores 0.5, the highest possible with two labels: two picks disagree half the time.
- The full dataset, 4 malicious and 6 benign, scores 0.48. That is close to the highest score, because the labels are well mixed.

Lower is better. The tree looks for the question whose groups have the lowest Gini.

### Entropy

Entropy measures the same mixing as how unpredictable a run's label is. Pick a run from the group at random and guess its label before looking. In a group of only malicious runs, the guess is always right, so the entropy is 0. In a half-and-half group, the guess is a coin flip, the most unpredictable case, and the entropy is 1, the highest score with two labels.

The full dataset, 4 malicious and 6 benign, has an entropy of 0.97: almost as unpredictable as a coin flip. The formula uses logarithms, and scikit-learn computes it for you.

![Gini impurity and entropy plotted against the share of a node that is malicious. Both are 0 at 0% and 100%, and peak at 50%: Gini at 0.5, entropy at 1.0. A dashed line at 40% marks the root node at Gini 0.48 and entropy 0.97.](/images/ai-decision-trees/impurity.svg)

The two curves have the same shape, and in practice they nearly always choose the same splits. Gini is the default in scikit-learn because it has no logarithm and is faster to compute.

## Choosing a Split

Training a tree means choosing which question to ask at each step. The tree starts with all 10 runs and one decision: which of the three questions to ask first. Every later question is asked inside one of the groups that this first question creates. This section shows how the tree makes that choice with the impurity scores from [Measuring a Mixed Group](#measuring-a-mixed-group), and how it does the same for numeric features such as command length.

### Scoring a question

The tree tries each of the three questions, splits the 10 runs by it, and gives the question a score: how mixed the two groups are after the split. The question whose groups are least mixed is the one the tree asks. These are the three splits drawn in [The Example Data](#the-example-data).

Each group has its own Gini score, and the question's score is their average weighted by size: each group's Gini is multiplied by its share of the runs, and the results are added. A group holding 8 of the 10 runs then counts for 80% of the score. Without the weights, a question that splits off a single run into a pure group would score well even though the other 9 runs stay as mixed as before.

For "launched by Office?":

- **Before**: all 10 runs, Gini 0.48.
- **Yes**: runs 1 and 3, both malicious. Gini 0. This group holds 2 of the 10 runs.
- **No**: the other 8 runs, 2 malicious and 6 benign. Gini 0.375, still mixed. This group holds 8 of the 10 runs.
- **After**: most of the runs (8 of 10) are in the group scoring 0.375, and the rest are in the group scoring 0. Weighted by size, that averages to 0.30.

The score drops from 0.48 to 0.30. The question with the lowest score after the split wins.

The example above uses Gini. Information gain is the same comparison done with entropy, written as a drop: entropy before the split minus entropy after it. For the Office question it is 0.97 - 0.65 = 0.32. A bigger drop is better, so the question with the highest information gain wins. Every question starts from the same entropy before the split, so the question with the biggest drop is also the one with the least mixed groups after it.

| Question | Yes group | No group | Gini after the split | Information gain |
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

![The finished tree, with the runs that reach each node as numbered dots colored malicious or benign. Launched by Office? holds all 10 runs. Yes leads to a malicious leaf with runs 1 and 3, 2 of 2. No leads to Downloads from the internet? with runs 2, 4 and 5 to 10. Its no branch is a benign leaf with runs 5, 8, 9 and 10, 4 of 4. Its yes branch is Encoded command? with runs 2, 4, 6 and 7. Yes leads to a malicious leaf with run 2, 1 of 1. No leads to a benign leaf with runs 4, 6 and 7, 2 of 3, marked impure because run 4 is malicious.](/images/ai-decision-trees/decision-tree.svg)

A new execution is classified by walking from the top. PowerShell launched by `explorer.exe` that downloads a file with an encoded command goes no, yes, yes, and ends at malicious.

### A leaf that cannot be pure

The bottom-right leaf holds runs 4, 6 and 7. All three have the same features (not encoded, downloads, not launched by Office), but run 4 is malicious and runs 6 and 7 are benign. No question about these three features can separate them, so the leaf predicts the majority label, benign, and run 4 is misclassified.

This is a data problem. Separating a script that fetches a payload from one that fetches a vendor installer needs another feature, such as the reputation of the download domain.

### Stopping before it overfits

A tree grown until every leaf is pure ends up memorizing its training data, which is the overfitting described in [Supervised Learning](/collections/ai-security/ai-supervised-learning). On a real dataset with hundreds of features, it creates leaves for single runs, based on a quirk such as a specific file name. Trees are limited in two ways:

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
| Splits are straight cuts on one feature at a time | A diagonal boundary, like the one in [Logistic Regression](/collections/ai-security/ai-logistic-regression), becomes a staircase of many small splits | More data, or a feature that combines the two |
| Favours features with many values | A unique ID column splits every run into its own pure leaf and scores the highest information gain while meaning nothing | Remove ID-like columns, or use gain ratio, which penalizes splits into many small groups |
| Class imbalance | With 1 malicious run per 1,000, a tree that always says benign has low impurity | Weight the rare class higher during training |

[Random forests](/collections/ai-security/ai-random-forests) and gradient-boosted trees (XGBoost, LightGBM) fix the stability problem by combining hundreds of trees. Each of their trees is built with the same splitting process.
