---
title: "Linear Regression"
slug: ai-linear-regression
category: notes
handbook: ai-security
tags: ["ai"]
draft: false
pubDatetime: 2026-11-07T00:00:00+02:00
description: "Predicting a number with a straight line: one feature and several, how ordinary least squares finds the line, how to measure the fit, and the assumptions that tell you when a straight line is the wrong model."
---

## Introduction

Regression is supervised learning where the label is a number instead of a category. [Supervised Learning](/collections/ai-security/ai-supervised-learning) used classification, where the answer is phishing or legitimate. A regression model answers questions like "how many milliseconds will this request take?" or "how many GB of logs will the SIEM ingest tomorrow?". Linear regression is the simplest regression model: it predicts the number with a straight line, or with a flat surface when there are several features.

The running example is a web server's response time. Its operators want to know how slow it gets as load grows, before the next traffic spike.

## One Feature

Five load tests measured the average response time at different numbers of concurrent users:

| Concurrent users ($$x$$) | 10 | 20 | 30 | 40 | 50 |
|---|---|---|---|---|---|
| Response time in ms ($$y$$) | 120 | 150 | 210 | 230 | 290 |

Simple linear regression fits a straight line through these points:

$$
\hat{y} = w x + b
$$

$$\hat{y}$$ ("y-hat") is the predicted value, as opposed to $$y$$, the measured one. The model has two parameters:

- **Weight $$w$$ (the slope)**: how much the prediction changes when $$x$$ goes up by 1.
- **Bias $$b$$ (the intercept)**: the prediction when $$x$$ is 0.

For this data, the line that fits best is $$\hat{y} = 4.2x + 74$$. Each extra concurrent user adds 4.2 ms, and the server's baseline with no load is 74 ms. At 45 users the model predicts $$4.2 \times 45 + 74 = 263$$ ms.

![The five load test points with the fitted line y-hat = 4.2x + 74. Short vertical lines from each point to the line show the residuals: +4, -8, +10, -12, +6.](/images/ai-linear-regression/fit.svg)

The line misses every point by a little. The vertical gap between a measured value and the line is the residual, $$y - \hat{y}$$. At 30 users the line predicts 200 ms and the server measured 210 ms, so the residual is +10.

## Finding the Best Line

### Ordinary least squares

"Best" needs a definition. Ordinary least squares (OLS) defines it as the line with the smallest total of squared misses. The name describes the method read backwards:

- **Squares**: for each point, take the residual (measured value minus predicted value) and square it.
- **Least**: choose the line where those squares add up to the smallest total.
- **Ordinary**: the plain version, where every point counts equally and nothing else is added to the total. Variants such as weighted least squares or Ridge regression change one of those two things.

The total is called the sum of squared errors (SSE):

```text
SSE = (measured - predicted)² for every point, added up
```

For the fitted line, the residuals are +4, -8, +10, -12 and +6 ms:

| Residual | +4 | -8 | +10 | -12 | +6 | Total |
|---|---|---|---|---|---|---|
| Squared | 16 | 64 | 100 | 144 | 36 | **360** |

Any other slope or intercept gives a total above 360, so $$\hat{y} = 4.2x + 74$$ is the best line by this definition.

The residuals are squared for two reasons:

- **Signs cancel otherwise**: the raw residuals here add up to exactly 0, as would those of many bad lines. A miss of +4 and a miss of -4 would count as no miss at all. Squaring makes every miss positive.
- **Large misses cost more**: a miss of 12 ms costs 144, while two misses of 6 ms cost 72 together. The line is pulled hardest toward the points it misses most.

The squaring has a downside. One extreme measurement, such as a 2,000 ms response caused by a garbage-collection pause, pulls the whole line toward itself. Remove or investigate outliers before fitting.

### Computing the line

You do not compute the line by hand. scikit-learn's `LinearRegression().fit(X, y)` solves for the weights with the smallest SSE directly, in one calculation, with no trial and error.

On millions of rows, that direct calculation gets slow, so large models use the training loop from [Supervised Learning](/collections/ai-security/ai-supervised-learning) instead: start with random weights, check whether the SSE goes down when a weight moves up or down a little, move every weight that way, and repeat until the SSE stops going down. That method is called gradient descent, and it reaches the same line.

## Several Features

Response time depends on more than user count. Multiple linear regression gives each feature its own weight:

$$
\hat{y} = w_1 x_1 + w_2 x_2 + \cdots + w_n x_n + b
$$

Suppose a model fitted to a month of production logs comes out as:

$$
\hat{y} = 4 \cdot \text{users} + 0.5 \cdot \text{payload KB} - 1.5 \cdot \text{cache hit \%} + 150
$$

For 40 users, 200 KB responses and an 80% cache hit rate, it predicts $$160 + 100 - 120 + 150 = 290$$ ms.

Each weight is read with the other features held fixed. $$w_3 = -1.5$$ means one extra percentage point of cache hits saves 1.5 ms, at the same user count and payload size. With two features the model is a flat plane through 3D space, and with more it is the same idea in more dimensions, which cannot be drawn but is computed the same way.

The raw size of a weight depends on the feature's units. Payload measured in bytes instead of KB would get a weight 1,000 times smaller with no change in its effect. To compare which features have the most effect, scale all features to the same range before fitting.

The URL classifier in the supervised learning note is logistic regression: the same weighted sum, passed through a sigmoid to produce a probability. Despite the name, logistic regression is a classification model.

## Measuring the Fit

Two numbers summarize how well the line fits.

**RMSE** (root mean squared error) is the typical size of a miss, in the same unit as the label. It comes from the SSE in three steps:

1. Take the SSE: 360.
2. Divide by the number of points to get the average squared miss: 360 ÷ 5 = 72.
3. Take the square root, which undoes the squaring and brings the number back to milliseconds: √72 ≈ 8.5 ms.

The line's predictions are typically about 8.5 ms off.

RMSE gives the size of a typical miss, but not whether that size is good. A miss of 8.5 ms is small when response times range from 120 to 290 ms, and large when they range from 200 to 210 ms. **R²** (R-squared) answers that with a score from 0 to 1, by comparing the line with a guess that knows nothing: it ignores the user count and always predicts the average of the five measurements, (120 + 150 + 210 + 230 + 290) ÷ 5 = 200 ms. That guess misses by much more:

| Measured | 120 | 150 | 210 | 230 | 290 | Total |
|---|---|---|---|---|---|---|
| Miss against 200 | -80 | -50 | +10 | +30 | +90 | |
| Squared | 6400 | 2500 | 100 | 900 | 8100 | **18000** |

Using the user count brings the total from 18,000 down to the line's SSE of 360. That removes 98% of the error, so R² is 0.98. R² is the share of the know-nothing guess's error that the model removes. An R² of 1 means no error is left, 0 means the line does no better than the average, and a value below 0, which can happen on a test set, means it does worse.

User count explains 98% of the variation in response time across these load tests.

Both numbers should be measured on a test set the model did not train on, for the same overfitting reasons as in classification.

## When a Straight Line Is the Wrong Model

Linear regression produces a line for any data, including data where a line makes no sense. Its results can be trusted when the following assumptions hold. Most of them can be checked by plotting the residuals against the predicted values:

![Three residual plots. Fine: residuals form a random horizontal band around zero. Curve: residuals form a U shape, positive at both ends and negative in the middle. Fan: residuals spread wider as the predicted value grows.](/images/ai-linear-regression/residual-patterns.svg)

| Assumption | What it means | Sign it is broken | What to do |
|---|---|---|---|
| Linearity | The real relationship is a straight line | Residuals curve (middle panel) | Add a transformed feature such as $$x^2$$ or $$\log x$$, or use a non-linear model |
| Independence | One example's error says nothing about the next | Residuals in time order run in streaks | Add time-based features, or use a time-series model |
| Constant variance | Misses are about the same size across the range | Residuals fan out (right panel) | Predict $$\log y$$ instead of $$y$$ |
| Normal residuals | Residuals follow a bell curve | A histogram of residuals is skewed or has long tails | Needed for confidence intervals and significance tests; predictions still work without it |
| No multicollinearity | No feature is close to a copy of another | Weights flip sign or swing wildly between fits | Drop one of the correlated features |

Applied to the server:

- **Linearity**: response time is linear only up to a point. Once the CPU saturates, requests queue and response time climbs much faster than 4.2 ms per user, so the residuals curve upward at high load.
- **Independence**: response times logged every minute are not independent. A slow minute is usually followed by another slow minute, because whatever caused it (a backup job, a traffic burst) is still running.
- **Constant variance**: at low load every request is fast. At high load some hit the cache and some wait in a queue, so the spread of response times grows with load and the residuals fan out.
- **Multicollinearity**: a model given both payload in KB and payload in network packets has two features carrying the same information. OLS cannot tell which one deserves the weight, and small changes in the data swing the weight between them.

A related limit is extrapolation. The load tests covered 10 to 50 users. Asking the model about 500 users gives $$4.2 \times 500 + 74 = 2174$$ ms, but nothing in the data says the server stays linear that far, and in practice it would likely start failing requests well before that. A linear model is only reliable inside the range of data it was fitted on.
