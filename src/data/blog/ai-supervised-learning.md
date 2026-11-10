---
title: "Supervised Learning"
slug: ai-supervised-learning
category: notes
handbook: ai-security
tags: ["ai"]
draft: false
pubDatetime: 2026-11-07T00:00:00+02:00
description: "How a supervised model is built and judged: features and labels, the training loop, prediction versus inference, accuracy, precision, recall and F1, validation sets, metrics for more than two classes, overfitting and underfitting, cross-validation, L1 and L2 regularization, and class imbalance, worked through a phishing URL classifier and NSL-KDD network connections."
---

## Introduction

Supervised learning trains a model on examples that already have the correct answer attached, so it can produce answers for new examples. [AI, Machine Learning, and Deep Learning](/collections/ai-security/ai-foundations) places it next to unsupervised and reinforcement learning. The running example is a classifier that decides whether a URL is phishing.

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

### Validation set

Building a model involves choices: which model, which features, which hyperparameter values. Each choice is made by comparing scores. If those scores come from the test set, the test set has helped pick the model, and its score is no longer a measurement on unseen data. After enough comparisons, the winner is partly the model that happened to do well on those particular test rows.

A third set keeps the test set clean. The data is split into three parts, for example 60% training, 20% validation and 20% test:

| Set | Used for |
|---|---|
| Training | Fitting the model |
| Validation | Comparing models and settings, as often as needed |
| Test | Measuring the final model, once, after every choice is made |

In scikit-learn this takes two calls to `train_test_split`: one to set the test set aside, and one to split the rest into training and validation. [Cross-validation](#cross-validation) replaces the fixed validation set by rotating it through the training data, which is how a [grid search](/collections/ai-security/ai-tools#grid-search) compares settings.

## Model and Training

A model is a function with adjustable numbers inside it, called parameters (or weights). For the URL classifier, a simple model gives each feature a weight, combines them with the dot product from [Math for Machine Learning](/collections/ai-security/ai-math), and turns the result into a probability with the sigmoid:

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

### More than two classes

With more than two classes, every class gets its own precision, recall and F1, computed as if that class were "positive" and all the others "negative". The confusion matrix grows to one row and one column per class: each row is the real class, each column the predicted class, and the diagonal holds the correct predictions.

A random forest that sorts [NSL-KDD](/collections/ai-security/ai-random-forests#introduction) network connections into normal traffic and four attack classes (DoS, Probe, U2R for privilege escalation, and R2L for remote access) gives this confusion matrix on 25,195 test connections:

| Actual \ Predicted | Normal | DoS | Probe | U2R | R2L |
|---|---|---|---|---|---|
| **Normal** | 13,464 | 3 | 1 | 0 | 1 |
| **DoS** | 2 | 9,184 | 0 | 0 | 0 |
| **Probe** | 8 | 0 | 2,323 | 0 | 0 |
| **U2R** | 5 | 0 | 0 | 5 | 0 |
| **R2L** | 8 | 0 | 0 | 1 | 190 |

scikit-learn's `classification_report` prints the per-class metrics, plus `support`, the number of real examples of each class in the test set:

```text
              precision    recall  f1-score   support

      Normal      0.998     1.000     0.999     13469
         DoS      1.000     1.000     1.000      9186
       Probe      1.000     0.997     0.998      2331
         U2R      0.833     0.500     0.625        10
         R2L      0.995     0.955     0.974       199

    accuracy                          0.999     25195
   macro avg      0.965     0.890     0.919     25195
weighted avg      0.999     0.999     0.999     25195
```

The last two rows combine the classes into one number, in two different ways:

- **Macro average**: the plain mean of the five classes. Every class counts the same, whatever its size.
- **Weighted average**: the mean weighted by support. Normal, with 13,469 rows, counts 1,347 times as much as U2R, with 10.

The model finds only 5 of the 10 U2R connections (recall 0.500). The weighted F1 of 0.999 hides that completely, because U2R is 0.04% of the weight. The macro F1 of 0.919 shows that at least one class is detected poorly. `precision_score`, `recall_score` and `f1_score` take the same choice through their `average` parameter (`"macro"`, `"weighted"`, or `None` for one value per class). When the rare classes are attacks, report the macro average and the per-class values.

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

## Class Imbalance

A dataset is imbalanced when one class is much rarer than the others. Security data usually is: attacks are rare compared to normal activity. In NSL-KDD's training set, U2R (privilege escalation) attacks are 52 of 125,973 connections, 0.04%.

Training minimizes errors over all rows, so the rare class barely affects it. Getting all 52 U2R rows wrong adds as many errors as getting 0.08% of the normal rows wrong. The model learns the common classes well and the rare one poorly, as the 0.500 U2R recall above shows. There are four ways to counter it.

### Metrics that show the rare class

Accuracy and weighted averages are dominated by the common classes. Per-class recall and the macro average show the rare class, as described in [More than two classes](#more-than-two-classes). This does not fix the model, but without it the problem goes unnoticed.

### Stratified splits

A random split can leave a rare class with very few rows in the test set, or none. `train_test_split(..., stratify=y)` keeps each class's share the same in every set, as described in [Splitting Without Leakage](/collections/ai-security/ai-datasets#training-and-test-sets).

It splits each class separately. NSL-KDD's training set has 52 U2R connections, so an 80/20 split should put about 10 of them in the test set. Over 20 random splits with different `random_state` values, the test set got between 8 and 18. Over 20 stratified splits, it got exactly 10 every time.

Even with stratification, 10 test rows make a noisy measurement. One more or one fewer correct U2R prediction moves its recall by 0.10. Five stratified splits of the same data, each with a different `random_state`, gave the same forest settings U2R recalls of 0.5, 0.5, 0.7, 0.8 and 0.3. Per-class scores on a handful of rows say little on their own.

### Class weights

Class weights make errors on the rare class cost more during training. Many scikit-learn classifiers, including trees, forests and logistic regression, take `class_weight="balanced"`, which gives each class the weight

$$
w_c = \frac{\text{number of rows}}{\text{number of classes} \times \text{rows in class } c}
$$

so every class contributes the same total weight. On the NSL-KDD training rows, that gives Normal 0.37 and U2R 479.9: one U2R row counts as much as about 1,280 normal rows.

The same forest with `class_weight="balanced"`:

| | Without weights | Balanced |
|---|---|---|
| U2R recall | 0.500 (5 of 10) | 0.700 (7 of 10) |
| R2L recall | 0.955 | 0.965 |
| Normal connections flagged as an attack | 5 | 12 |
| Macro F1 | 0.919 | 0.949 |
| Accuracy | 99.88% | 99.87% |

The rare classes are caught more often, and the cost is more false alarms on normal traffic. Accuracy barely moves in either direction, which is another reason not to judge an imbalanced model by it.

### Resampling

Resampling changes the training set itself instead of the weights:

- **Oversampling**: repeat rows of the rare class until it is larger.
- **Undersampling**: drop rows of the common classes until they are smaller. It discards real data, so it suits datasets with plenty of rows.
- **SMOTE** (Synthetic Minority Oversampling Technique): create new rare-class rows between existing ones, by picking a rare row and one of its nearest rare neighbours and placing a new row at a random point between them. It is in the `imbalanced-learn` library.

Resampling is applied to the training set only. The validation and test sets keep the real class shares, because they have to measure the model on data as it really is.

