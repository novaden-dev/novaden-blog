---
title: "Naive Bayes"
slug: ai-naive-bayes
category: notes
handbook: ai-security
tags: ["ai"]
draft: false
pubDatetime: 2026-11-09T00:00:00+03:00
description: "How Naive Bayes classifies text from word counts: Bayes' rule, the independence assumption, Multinomial Naive Bayes, the zero-count problem and the alpha smoothing parameter, worked on SMS spam, plus the good word attack that flips its predictions."
---

## Introduction

Naive Bayes classifies a message by asking, for each class, how likely that class is to produce the message's words. The word probabilities come from counting words in the labeled training messages. Training is one pass of counting, so it is fast even with tens of thousands of word columns. Paul Graham's [A Plan for Spam](https://paulgraham.com/spam.html) (2002) made it a standard method for spam filtering.

The numbers below come from the [SMS Spam Collection](https://archive.ics.uci.edu/dataset/228/sms+spam+collection) after the preparation steps in [Preparing Text](/collections/ai-security/ai-preparing-text): 5,169 messages, of which 653 are spam.

## Bayes' Rule

Bayes' rule turns one [conditional probability](/collections/ai-security/ai-math#probability-and-conditional-probability) around:

$$
P(A \mid B) = \frac{P(B \mid A) \cdot P(A)}{P(B)}
$$

For spam, $$A$$ is "the message is spam" and $$B$$ is the message:

$$
P(\text{spam} \mid \text{message}) = \frac{P(\text{message} \mid \text{spam}) \cdot P(\text{spam})}{P(\text{message})}
$$

| Term | Name | Meaning |
|---|---|---|
| $$P(\text{spam})$$ | Prior | The share of spam before reading the message: $$653 / 5169 = 12.6\%$$ |
| $$P(\text{message} \mid \text{spam})$$ | Likelihood | How likely spam is to contain this message's words |
| $$P(\text{message})$$ | Evidence | How likely the message is overall |
| $$P(\text{spam} \mid \text{message})$$ | Posterior | The probability of spam after reading the message |

The evidence is the same for both classes, so the classifier only compares the two numerators, $$P(\text{message} \mid \text{spam}) \cdot P(\text{spam})$$ and $$P(\text{message} \mid \text{ham}) \cdot P(\text{ham})$$, and picks the larger.

## The Naive Assumption

$$P(\text{message} \mid \text{spam})$$ cannot be counted directly, because almost every new message is unique: no training message has exactly the same words. Naive Bayes assumes that, within a class, each word appears independently of the others. The probability of the whole message is then the product of the probabilities of its words:

$$
P(\text{message} \mid \text{spam}) = P(w_1 \mid \text{spam}) \cdot P(w_2 \mid \text{spam}) \cdots P(w_n \mid \text{spam})
$$

Each $$P(w \mid \text{spam})$$ can be counted. The assumption is false for real text. `free` appears in 22% of spam messages and `entri` in 2.8%, so if they were independent, both would appear together in 0.6% of spam messages. They appear together in 2.3%, almost four times as often. The predicted class is still often right, but the probabilities are overconfident. Words that often appear together are counted as separate evidence, so the output is pushed close to 0 or 1. On 1,034 held-out test messages, 88% get a spam probability above 0.99 or below 0.01.

## Multinomial Naive Bayes

The multinomial variant works with word counts. The probability of a word given a class is the number of times the word appears in that class's messages, divided by the total number of words in that class:

$$
P(w \mid \text{spam}) = \frac{\text{count of } w \text{ in spam}}{\text{total words in spam}}
$$

The spam messages contain 8,936 words in total, and the ham messages 34,834:

| Word | In spam | In ham |
|---|---|---|
| free | 190 | 55 |
| claim | 98 | 0 |
| prize | 82 | 0 |
| txt | 140 | 13 |
| lunch | 0 | 38 |
| love | 10 | 218 |
| ok | 5 | 247 |

scikit-learn has several variants, each for a different kind of feature:

| Class | Features |
|---|---|
| `MultinomialNB` | Counts, such as word counts from `CountVectorizer` |
| `BernoulliNB` | Yes/no features, such as whether a word appears at all |
| `GaussianNB` | Continuous numbers, modeled as a normal distribution per class |
| `ComplementNB` | Counts, like `MultinomialNB`, with a correction for imbalanced classes |

## The Zero-Count Problem

`claim` appears 98 times in spam and never in ham, so $$P(\text{claim} \mid \text{ham}) = 0 / 34834 = 0$$. One zero in the product makes the whole product zero. Any message containing `claim` then gets $$P(\text{ham}) = 0$$, whatever its other words are. With the counts as they are, `ok i will claim it at home` is classified as spam with probability 100%, although `ok` appears 247 times in ham and 5 times in spam.

### Additive smoothing

Smoothing adds a small number $$\alpha$$ (alpha) to every count, so no word has probability zero:

$$
P(w \mid c) = \frac{\text{count of } w \text{ in } c + \alpha}{\text{total words in } c + \alpha \cdot V}
$$

$$V$$ is the vocabulary size, 7,101 words here. Adding $$\alpha \cdot V$$ to the denominator keeps the probabilities of all words in a class summing to 1. $$\alpha = 1$$ is called Laplace smoothing, and values below 1 are called Lidstone smoothing. With $$\alpha = 1$$:

| Word | $$P(w \mid \text{spam})$$ | $$P(w \mid \text{ham})$$ |
|---|---|---|
| free | $$\frac{190 + 1}{8936 + 7101} = 0.01191$$ | $$\frac{55 + 1}{34834 + 7101} = 0.001335$$ |
| claim | $$\frac{98 + 1}{8936 + 7101} = 0.006173$$ | $$\frac{0 + 1}{34834 + 7101} = 0.0000238$$ |

`ok i will claim it at home` now comes out 89% ham. `claim` still counts strongly toward spam, but `ok` and `home` now outweigh it.

## A Worked Example

The message `free claim`, with $$\alpha = 1$$. Multiply the prior by each word's probability:

$$
\text{spam: } 0.1263 \times 0.01191 \times 0.006173 = 9.29 \times 10^{-6}
$$

$$
\text{ham: } 0.8737 \times 0.001335 \times 0.0000238 = 2.78 \times 10^{-8}
$$

The two numbers are not probabilities yet, because the evidence was left out. Dividing each by their sum turns them into probabilities that add up to 1:

$$
P(\text{spam} \mid \text{free claim}) = \frac{9.29 \times 10^{-6}}{9.29 \times 10^{-6} + 2.78 \times 10^{-8}} = 0.997
$$

`MultinomialNB(alpha=1).predict_proba` returns the same 0.997.

Each word multiplies the score by a small number, mostly below 0.01. After a few hundred words, the product is smaller than the smallest number a 64-bit float can store, about $$10^{-308}$$, and becomes 0. Implementations add [logarithms](/collections/ai-security/ai-math#exponents-and-logarithms) instead of multiplying probabilities, since $$\log(a \cdot b) = \log a + \log b$$. scikit-learn stores them in `feature_log_prob_` and `class_log_prior_`.

## Choosing Alpha

$$\alpha$$ is a hyperparameter: a setting chosen before training, as opposed to the word probabilities, which training computes. A larger $$\alpha$$ moves every word's probability closer to the same value, so rare words count for less. A smaller $$\alpha$$ trusts the counts more.

A [grid search](/collections/ai-security/ai-tools#grid-search) over eight values, scoring each with the mean F1 over 5-fold [cross-validation](/collections/ai-security/ai-supervised-learning#cross-validation), gives:

| $$\alpha$$ | 0.01 | 0.1 | 0.15 | 0.2 | 0.25 | 0.5 | 0.75 | 1.0 |
|---|---|---|---|---|---|---|---|---|
| Mean F1 | 0.917 | 0.925 | 0.927 | 0.926 | 0.928 | 0.925 | 0.925 | 0.925 |

0.25 scores highest, but every value from 0.1 to 1.0 is within 0.004 of it, while the F1 of a single value varies by about 0.01 from one fold to the next. The ranking between those values comes from which messages landed in which fold: on a different split of the same data, the grid search picked 0.5. Only 0.01, close to no smoothing, is clearly worse.

## What Naive Bayes Needs from the Data

- **Non-negative counts**: `MultinomialNB` raises an error on negative values, so features scaled with standardization cannot be used with it. Word counts need no scaling.
- **Sparse input**: it works directly on the sparse matrix from `CountVectorizer`, with tens of thousands of columns.
- **A representative prior**: the prior comes from the class shares in the training data. If spam is 12.6% of training messages but 50% of real traffic, the prior pulls predictions toward ham.

## Naive Bayes and Attackers

Each word multiplies the score independently, so an attacker can add words that are common in legitimate messages until their factors outweigh the spam words. This is called a good word attack, studied by Lowd and Meek in "Good Word Attacks on Statistical Spam Filters" (2005). The attacker's spam text stays the same, and the added words only change the score.

Against a model trained on this dataset with unigrams and bigrams and $$\alpha = 0.25$$:

| Message | P(spam) |
|---|---|
| `Urgent! Your account has been compromised. Verify your details here: www.fakebank.com/verify` | 0.96 |
| the same, plus ` ok` | 0.60 |
| the same, plus ` ok see you at home` | 0.02 |

Three ordinary words move the phishing message from 96% spam to 2% spam. The attacker does not need the model: a list of words that are common in normal messages is enough. The same idea applies to the decision boundary of any linear model, as described in [Logistic Regression](/collections/ai-security/ai-logistic-regression#evading-the-boundary).
