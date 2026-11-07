---
title: "Supervised Learning"
slug: ai-supervised-learning
category: notes
handbook: ai-security
tags: ["ai"]
draft: false
pubDatetime: 2026-11-07T00:00:00+02:00
description: "How a supervised model is built and judged: features and labels, the training loop, prediction versus inference, accuracy, precision, recall and F1, overfitting and underfitting, cross-validation, and L1 and L2 regularization, worked through a phishing URL classifier."
---

## Introduction

Supervised learning trains a model on examples that already have the correct answer attached, so it can produce answers for new examples. [AI, Machine Learning, and Deep Learning](/posts/ai-foundations) places it next to unsupervised and reinforcement learning. The running example is a classifier that decides whether a URL is phishing.

## The Dataset

### Examples, features, and labels

A supervised dataset is a table. Each row is one example, each feature column is something measured about it, and the label column is the correct answer:

| URL | Length | Dots in host | Host is an IP | Domain age (days) | Has "login", "verify" or "update" | Label |
|---|---|---|---|---|---|---|
| `https://mybank.com/login` | 24 | 1 | no | 4,200 | yes | legitimate |
| `http://mybank.com.secure-verify.top/login` | 41 | 3 | no | 3 | yes | phishing |
| `http://185.220.101.4/mybank/update` | 34 | 3 | yes | none | yes | phishing |
| `https://docs.example.org/guide` | 30 | 2 | no | 7,300 | no | legitimate |
| `https://mybank-support.help/verify?id=88` | 40 | 1 | no | 12 | yes | phishing |

- **Features**: the inputs the model sees. A model can only work with numbers, so every feature is converted to one: "yes" becomes 1, "no" becomes 0. The URL itself is not a feature here. The model sees only the five measurements taken from it.
- **Label**: the output the model learns to produce, also called the target. Someone has to supply it for every training row, for example by checking each URL against a phishing blocklist or by having an analyst review it.

The choice of features limits what the model can learn. Keyword presence alone would label `https://mybank.com/login` as phishing. Domain age separates it from the lookalikes, because phishing domains are often registered only days before a campaign starts.

The quality of the labels limits the model too. If 5% of the phishing URLs in the training data are mislabeled as legitimate, the model learns that some phishing patterns are fine.

### Training set and test set

The labeled data is split before training. Usually 80% becomes the training set, which the model learns from, and 20% becomes the test set, which is kept aside and used only to measure the finished model. A model scored on data it trained on can look accurate just by having memorized it, so the test set stands in for the URLs it will see after deployment.

## Model and Training

A model is a function with adjustable numbers inside it, called parameters (or weights). For the URL classifier, a simple model gives each feature a weight, combines them with the dot product from [Math for Machine Learning](/posts/ai-math), and turns the result into a probability with the sigmoid:

$$
P(\text{phishing}) = \sigma(w_1 \cdot \text{length} + w_2 \cdot \text{dots} + w_3 \cdot \text{ip} + w_4 \cdot \text{age} + w_5 \cdot \text{keyword} + b)
$$

The bias $$b$$ is a constant added after the weighted sum. It sets the model's starting point: if every feature contributed nothing, the output would be $$\sigma(b)$$. Most URLs are legitimate, so training typically pushes $$b$$ negative, and with $$b = -2$$ the model starts at $$\sigma(-2) \approx 0.12$$ until the features push the probability up. It plays the same role as the $$+ 1$$ in $$f(x) = 2x + 1$$.

This model is called logistic regression. Before training, the weights are random and the outputs are meaningless. Training finds weights that make the outputs match the labels:

1. Run every training example through the model and collect its predictions.
2. Compare the predictions with the labels using a loss function, such as log loss, which gives one number for how wrong the model is overall.
3. Work out which direction each weight should move to lower the loss, and move every weight a small step that way.
4. Repeat until the loss stops dropping.

After training on enough URLs, the weight on domain age ends up negative (older domains push the probability of phishing down) and the weight on "host is an IP" ends up large and positive. Nobody set those values by hand.

### Parameters at scale

The parameter count quoted for AI models ("an 8B model") counts the same thing: the numbers that training adjusts. The URL classifier has 6 parameters, the five weights plus the bias $$b$$. Meta's Llama 3 8B has 8 billion, stored in the weight matrices of each of its layers, and OpenAI's GPT-3 has 175 billion.

At standard 16-bit precision each parameter takes 2 bytes, so Llama 3 8B needs about 16 GB of memory just to load, which fits on one consumer GPU, and GPT-3 needs about 350 GB, which takes several data-center GPUs. A quantized model stores each parameter in fewer bits: at 4 bits, the 8B model drops to about 4 GB, with a small loss in quality.

More parameters let a model represent more complex patterns, and also need more training data and compute. With too little data, the extra freedom turns into overfitting (see below).

Open-weight models, such as Llama, publish the parameter files, so anyone can download and run them. For an attacker, the parameter file is the model: stealing a closed model means stealing that file, or reconstructing parts of it by querying the model.

## Using a Trained Model

### Prediction

Prediction is running the trained model on a new input to get an output. A new URL arrives, its five features are measured, and the model returns $$P(\text{phishing}) = 0.93$$. The application compares that against a threshold, such as 0.5, and blocks the link.

### Inference

"Inference" has two meanings, depending on who is speaking:

- **In machine learning engineering**: running a trained model, the same thing as prediction. "Inference cost" is the cost of serving a model's answers, and an "inference API" is an endpoint that returns model outputs. This handbook uses this meaning.
- **In statistics**: drawing conclusions about the data from the trained model. Looking at the URL classifier's weights shows which features drive its decisions, for example that domain age moves the output more than URL length does. A decision tree can report which feature each split uses, and a linear model's weights show how much each feature moves the output.

## Measuring a Model

### The confusion matrix

Suppose the test set holds 1,000 URLs, 100 of them phishing. Every prediction falls in one of four cells:

| | Model says phishing | Model says legitimate |
|---|---|---|
| **Actually phishing (100)** | 80 true positives (TP) | 20 false negatives (FN) |
| **Actually legitimate (900)** | 10 false positives (FP) | 890 true negatives (TN) |

"Positive" means the model flagged the URL, and "true" or "false" says whether the flag was right. Every evaluation metric is a ratio of these four numbers.

### Accuracy, precision, recall, F1

| Metric | Question it answers | Formula | Value |
|---|---|---|---|
| Accuracy | What share of all predictions were right? | $$\frac{TP + TN}{\text{all}}$$ | $$\frac{80 + 890}{1000} = 97\%$$ |
| Precision | When it flags a URL, how often is it really phishing? | $$\frac{TP}{TP + FP}$$ | $$\frac{80}{90} = 88.9\%$$ |
| Recall | Of the real phishing URLs, how many did it catch? | $$\frac{TP}{TP + FN}$$ | $$\frac{80}{100} = 80\%$$ |
| F1 | One number combining precision and recall | $$2 \cdot \frac{P \cdot R}{P + R}$$ | $$84.2\%$$ |

Accuracy misleads when one class is rare, which is the normal case in security data. A model that labels every URL legitimate scores 90% accuracy on this test set, and catches zero phishing URLs: its recall is 0.

Precision and recall trade against each other through the threshold. Lowering the threshold from 0.5 to 0.2 flags more URLs, which catches more phishing (higher recall) and blocks more legitimate links by mistake (lower precision). Which one to favour depends on the cost of each mistake. A missed phishing link can lead to a compromised account. A blocked legitimate link costs a user a support ticket.

F1 is the harmonic mean of precision and recall, which stays low unless both are high. A model with 100% precision and 2% recall has an F1 of about 4%, while a plain average would report 51%.

## Generalization, Overfitting, and Underfitting

Generalization is how well a model performs on data it was not trained on. The test set measures it. A model's training error and its error on new data together show which of three states it is in:

![Three panels fitting the same training points. Underfit: a straight line misses the curved pattern, training error 0.28 and error on new data 0.26. Good fit: a smooth curve follows the pattern, training error 0.03 and error on new data 0.06. Overfit: a wild curve passes through every training point, training error 0.00 and error on new data 3.15.](/images/ai-supervised-learning/fitting.svg)

| State | Training error | Error on new data | Cause |
|---|---|---|---|
| Underfit | high | high | Model too simple for the pattern, or features that do not carry it |
| Good fit | low | low, close to training | Model matches the real pattern |
| Overfit | very low | high | Model learned the noise and quirks of the training rows |

An overfit URL classifier could learn that every phishing URL in its training data came from three specific domains, and score perfectly on them. A new campaign on a new domain gets through. A model with many parameters and little training data overfits easily, because it has enough freedom to fit every row exactly.

An underfit classifier that only sees URL length cannot separate phishing from legitimate URLs no matter how long it trains, because length alone does not carry the pattern. The fix is a more flexible model or better features.

## Regularization

Regularization reduces overfitting by adding a penalty on large weights to the loss. Training then has to balance fitting the data against keeping the weights small:

$$
\text{total loss} = \text{prediction loss} + \lambda \cdot \text{penalty}(\mathbf{w})
$$

$$\lambda$$ (lambda) sets the strength. At $$\lambda = 0$$ there is no regularization. If $$\lambda$$ is too large, the weights are forced so close to zero that the model underfits.

The penalty is a norm of the weight vector. For weights $$\mathbf{w} = (3, -0.5, 0.01)$$:

| Type | Penalty | For (3, -0.5, 0.01) | Effect |
|---|---|---|---|
| L1 (lasso) | $$\sum \lvert w_i \rvert$$ | $$3 + 0.5 + 0.01 = 3.51$$ | Pushes small weights to exactly zero, which removes those features from the model |
| L2 (ridge) | $$\sum w_i^2$$ | $$9 + 0.25 + 0.0001 = 9.25$$ | Shrinks all weights, and punishes the large ones hardest because of the square |

In the URL classifier, L1 regularization would likely set the weight on URL length to zero if length adds little once domain age and the IP feature are known. That doubles as feature selection: the features with non-zero weights are the ones the model needs.

## Cross-Validation

A single 80/20 split gives one test score, and that score depends on which URLs happened to land in the test set. Cross-validation repeats the measurement on different splits. In 5-fold cross-validation, the data is cut into five equal parts (folds). The model is trained five times, each time holding out a different fold for testing and training on the other four:

![Five rounds of five folds. In each round a different fold is the test fold and the other four are training folds. The round scores are 0.91, 0.88, 0.93, 0.90 and 0.89, averaging 0.90.](/images/ai-supervised-learning/cross-validation.svg)

Every example is used for testing exactly once. The average of the five scores is a steadier estimate than any single split, and a large spread between rounds is a warning that the model's performance depends heavily on which data it sees.

Cross-validation is also how the regularization strength $$\lambda$$ gets chosen: try several values, cross-validate each, and keep the value with the best average score.
