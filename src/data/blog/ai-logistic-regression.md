---
title: "Logistic Regression"
slug: ai-logistic-regression
category: notes
handbook: ai-security
tags: ["ai"]
draft: false
pubDatetime: 2026-11-07T00:00:00+02:00
description: "How logistic regression turns a weighted sum into a class probability: the sigmoid, reading weights as odds, the decision boundary as a hyperplane, choosing a threshold, training with log loss, and the assumptions it needs, worked through a password-attack detector."
---

## Introduction

Logistic regression is a classification model. It predicts the probability that an example belongs to a class, such as "this login source is attacking", and a threshold turns that probability into a yes or no. Despite the name, it is not used to predict numbers: the "regression" comes from the weighted sum inside it, which it shares with [Linear Regression](/collections/ai-security/ai-linear-regression).

The running example is a detector for password attacks. For each source IP, it looks at two features over the last 10 minutes:

- $$x_1$$: failed logins from that source
- $$x_2$$: distinct usernames that source tried

A user who mistypes their password fails once or twice with one username. Brute force fails many times. Password spraying tries a few common passwords against many usernames.

## From a Weighted Sum to a Probability

### Why a straight line does not work

Labeling attacks as 1 and benign sources as 0, then fitting linear regression, gives a line that predicts numbers like -0.3 or 1.4 for sources far from the training data. Neither is a probability. A single source with 500 failed logins would also tilt the whole line toward itself, shifting predictions for every ordinary source.

### The sigmoid

Logistic regression keeps the weighted sum and passes it through the sigmoid from [Math for Machine Learning](/collections/ai-security/ai-math), which squeezes any number into the range 0 to 1:

$$
z = w_1 x_1 + w_2 x_2 + b
\qquad
P(\text{attack}) = \sigma(z) = \frac{1}{1 + e^{-z}}
$$

Suppose training produced $$w_1 = 0.3$$, $$w_2 = 0.8$$ and $$b = -6$$:

| Source | Failed logins | Usernames | $$z$$ | $$P(\text{attack})$$ |
|---|---|---|---|---|
| User who forgot a password | 5 | 1 | $$1.5 + 0.8 - 6 = -3.7$$ | 0.02 |
| Brute force against one account | 20 | 1 | $$6 + 0.8 - 6 = 0.8$$ | 0.69 |
| Password spraying | 2 | 7 | $$0.6 + 5.6 - 6 = 0.2$$ | 0.55 |
| Brute force plus spraying | 12 | 6 | $$3.6 + 4.8 - 6 = 2.4$$ | 0.92 |

The bias of -6 means a source with no failed logins starts at $$\sigma(-6) \approx 0.002$$. The features have to push it a long way before it looks like an attack.

### Reading the weights as odds

Odds compare the chance something happens with the chance it does not: $$\text{odds} = \frac{p}{1 - p}$$. A probability of 0.92 is odds of about 11 to 1.

The weighted sum $$z$$ is the logarithm of the odds, called the log-odds:

$$
z = \ln \frac{p}{1 - p}
$$

That gives every weight a direct meaning. Adding 1 to a feature adds its weight to the log-odds, which multiplies the odds by $$e^{w}$$:

- **One more failed login**: odds multiply by $$e^{0.3} \approx 1.35$$, so they go up 35%.
- **One more distinct username**: odds multiply by $$e^{0.8} \approx 2.23$$, so they more than double.

So in this model, trying a new username is stronger evidence of an attack than one more failed attempt. This is the statistics sense of inference from [Supervised Learning](/collections/ai-security/ai-supervised-learning): reading what the trained model has learned about the data, in addition to using its predictions.

### Training

Least squares is not used here. Logistic regression is trained with log loss, also from the math note: for each example, the loss is $$-\ln p$$, where $$p$$ is the probability the model gave the correct class. There is no direct formula for the best weights, so they are found with gradient descent, the same training loop described in Supervised Learning.

## The Decision Boundary

### A line in two dimensions

With a threshold of 0.5, the model flags a source when $$\sigma(z) \geq 0.5$$, which happens exactly when $$z \geq 0$$. The sources where $$z = 0$$ form the decision boundary:

$$
0.3 x_1 + 0.8 x_2 - 6 = 0
$$

With two features that is a straight line. It crosses the failed-logins axis at 20 (with one username tried, 20 failures are needed) and the usernames axis at 7.5:

![Login sources plotted by failed logins and distinct usernames. A solid diagonal line marks p = 0.5. Dashed lines below and above it mark p = 0.2 and p = 0.9. Most benign sources sit in the lower left, most attacks in the upper right, and a few points sit on the wrong side of the line.](/images/ai-logistic-regression/boundary.svg)

The probability changes smoothly across the plot. Moving away from the line in either direction makes the model more confident, and the dashed lines show where it reaches 0.2 and 0.9. A few points sit on the wrong side of the line: the model is a straight cut, and real data does not split perfectly.

### Hyperplanes

With more features the boundary keeps the same shape in more dimensions:

| Features | Boundary |
|---|---|
| 2 | a line |
| 3 | a flat plane |
| $$n$$ | a hyperplane, the $$n$$-dimensional version of a flat plane |

In vector form, with the dot product from the math note, the boundary is:

$$
\mathbf{w} \cdot \mathbf{x} + b = 0
$$

The weight vector $$\mathbf{w}$$ points straight out of the hyperplane, in the direction where the probability of an attack rises fastest. Logistic regression can only draw this one flat cut. If attacks and benign traffic cannot be separated by a flat surface, for example if attacks sit in a ring around benign traffic, the model cannot fit them without new features.

### Evading the boundary

The boundary is also what an attacker works against. A detector with a fixed boundary tells an attacker exactly how to stay under it. Running the same brute force at 8 failed logins per 10 minutes instead of 20 gives:

$$
z = 0.3 \times 8 + 0.8 \times 1 - 6 = -2.8
\qquad
\sigma(-2.8) \approx 0.06
$$

The attack is the same, only slower, and the probability drops from 0.69 to 0.06. This is the "low and slow" pattern, and it is an evasion attack: moving an input across the decision boundary with the smallest change that works. Attacks on larger models follow the same idea with more features.

## Choosing the Threshold

0.5 is only the default threshold. Changing it moves the boundary parallel to itself, to one of the dashed lines in the figure. [Supervised Learning](/collections/ai-security/ai-supervised-learning) covers the trade-off: a lower threshold catches more attacks (higher recall) and raises more false alarms (lower precision).

One model can serve several thresholds at once, each tied to an action:

| Threshold | Action | Reasoning |
|---|---|---|
| 0.2 | Raise an alert for an analyst | A false alarm costs a few minutes of review |
| 0.5 | Require CAPTCHA or MFA for that source | A false alarm adds friction for a real user |
| 0.9 | Block the source IP | A false alarm locks out real users, so only act when the model is confident |

The threshold is a business decision about the cost of each mistake. The model only supplies the probability.

## More Than Two Classes

Logistic regression separates two classes. For more, such as benign, brute force and spraying, there are two common extensions:

- **One-vs-rest**: train one logistic regression per class ("brute force or not", "spraying or not") and pick the class whose model gives the highest probability.
- **Softmax regression** (multinomial logistic regression): one model with a weight vector per class, and softmax instead of sigmoid, so the class probabilities add up to 1.

## Assumptions

Logistic regression needs fewer assumptions than linear regression.

| Assumption | What it means | What goes wrong |
|---|---|---|
| Two classes | The label is binary | Use one-vs-rest or softmax for more |
| Independent examples | Each row is a separate observation | 100 rows from the same attacker look like 100 separate attackers and overweight that pattern |
| Linear in the log-odds | Each feature moves the log-odds by a fixed amount per unit | If going from 50 to 51 failures means much less than going from 1 to 2, transform the feature, for example with $$\log(x_1 + 1)$$ |
| No strong multicollinearity | Features are not near-copies of each other | Failed logins counted per 10 minutes and per 15 minutes carry the same information, and their weights become unstable |
| Enough examples of each class | The rarer class has many examples per feature | With 30 attacks and 20 features, the weights fit noise. A common rule of thumb is at least 10 examples of the rarer class per feature |

Compared with linear regression, three assumptions drop out. The residuals do not need to be normal or have constant variance, because the model outputs probabilities instead of values scattered around a line. The relationship between the features and the probability is not linear either; only the relationship with the log-odds is.

One failure is specific to logistic regression. If a feature separates the classes perfectly in the training data, for example every attack in the sample used 5 or more usernames and no benign source did, training keeps increasing that weight forever, because a steeper sigmoid always lowers the loss a little more. The result is a model that is 100% confident on a pattern seen in a small sample. Regularization, from Supervised Learning, stops this by penalizing the growing weight.
