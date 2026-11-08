---
title: "Math for Machine Learning"
slug: ai-math
category: notes
handbook: ai-security
tags: ["math", "ai"]
draft: false
pubDatetime: 2026-11-07T00:00:00+02:00
description: "The notation and math that machine learning papers and courses assume: sums, logs and exponentials, vectors and norms, matrices and eigenvectors, sets, and probability, each with a worked example and where ML uses it."
---

## Introduction

Machine learning formulas use a small set of operations written in compact notation: adding up lists, multiplying grids of numbers, measuring the distance between lists of numbers, and working with probabilities. Every one of them can also be written as a few lines of Python, and the code form is often easier to read than the symbols.

## Reading the Notation

### Subscripts and the ellipsis

A subscript picks one item out of a list. If $$x$$ is a list of failed login counts for each hour of the day, $$x_1$$ is the first hour, $$x_2$$ the second, and $$x_t$$ is hour $$t$$, whichever hour you are looking at. In code, $$x_t$$ is `x[t]`.

Subscripts with arithmetic point at neighbours: $$x_{t-1}$$ is the hour before $$t$$, and $$x_{t+1}$$ the hour after. Sequence models, such as the RNNs in [AI, Machine Learning, and Deep Learning](/collections/ai-security/ai-foundations), are written this way: the state at step $$t$$ is computed from the input at $$t$$ and the state at $$t-1$$.

The ellipsis ($$\ldots$$) means "continue the pattern". $$x_1 + x_2 + \cdots + x_n$$ is every item from the first to the $$n$$th added together, where $$n$$ is the length of the list.

### Summation (Σ)

$$\Sigma$$ (capital sigma) is a compact way to write that same sum:

$$
\sum_{i=1}^{n} x_i = x_1 + x_2 + \cdots + x_n
$$

Read it as a loop. The bottom says where the counter $$i$$ starts, the top says where it stops, and the expression on the right is what gets added each time:

```python
total = 0
for i in range(1, n + 1):
    total += x[i]
```

With $$x = (3, 5, 2, 6)$$, the sum is $$3 + 5 + 2 + 6 = 16$$.

The mean (average) is the sum divided by the count:

$$
\bar{x} = \frac{1}{n} \sum_{i=1}^{n} x_i = \frac{16}{4} = 4
$$

$$\frac{1}{n}$$ is the reciprocal of $$n$$, and multiplying by it is the same as dividing by $$n$$. Mean squared error, a standard way to score a model's predictions, is written this way: compute the error on each training example, square it, sum the squares with $$\Sigma$$, and divide by the number of examples.

### Functions

$$f(x)$$ is a rule that takes an input $$x$$ and returns an output. With $$f(x) = 2x + 1$$, $$f(3) = 7$$ and $$f(10) = 21$$. A function can take several inputs, written $$f(x, y)$$.

A trained model is a function. A spam filter is $$f(\text{email}) = $$ the probability the email is spam, and training is the process of adjusting $$f$$ until its outputs match the labels.

### max, min, and argmax

$$\max$$ returns the largest value and $$\min$$ the smallest: $$\max(0.2, 0.9, 0.5) = 0.9$$.

Machine learning also uses $$\arg\max$$, which returns which input produced the largest value instead of the value itself. A classifier that outputs these probabilities:

| Label | Probability |
|---|---|
| benign | 0.15 |
| phishing | 0.80 |
| malware | 0.05 |

has $$\max = 0.80$$ and $$\arg\max = \text{phishing}$$. The argmax is the prediction.

## Sets

A set is a collection of distinct items written in braces. Suppose these are the accounts that logged in on two days, and the company has five employees:

$$
\begin{aligned}
U &= \{\text{alice}, \text{bob}, \text{carol}, \text{dave}, \text{erin}\} && \text{every employee} \\
A &= \{\text{alice}, \text{bob}, \text{carol}\} && \text{logged in Monday} \\
B &= \{\text{bob}, \text{dave}\} && \text{logged in Tuesday}
\end{aligned}
$$

| Notation | Name | Result | Meaning | Python |
|---|---|---|---|---|
| $$\lvert A \rvert$$ | cardinality | 3 | how many items | `len(A)` |
| $$A \cup B$$ | union | {alice, bob, carol, dave} | in A or B or both | `A \| B` |
| $$A \cap B$$ | intersection | {bob} | in both | `A & B` |
| $$A^c$$ | complement | {dave, erin} | in U but not in A | `U - A` |

The complement always depends on $$U$$, the full set being considered. Probability uses the same idea: the probability that an event does not happen is $$1 - P(A)$$, the probability of its complement.

## Exponents and Logarithms

An exponent says how many times to multiply a number by itself: $$2^3 = 2 \times 2 \times 2 = 8$$. A logarithm runs the other way. It answers "what power do I raise the base to, to get this number?"

| Exponent | Logarithm | Base |
|---|---|---|
| $$2^{10} = 1024$$ | $$\log_2 1024 = 10$$ | 2 |
| $$e^3 \approx 20.09$$ | $$\ln 20.09 \approx 3$$ | $$e$$ |

### Base 2: bits

$$2^x$$ counts the combinations of $$x$$ bits. A byte has 8 bits, so it holds $$2^8 = 256$$ values. A 128-bit key has $$2^{128}$$ possible values.

$$\log_2 x$$ counts the bits needed to represent $$x$$ options, which is also how entropy is measured. A password of 4 random lowercase letters has $$26^4 = 456{,}976$$ possibilities, and $$\log_2 456{,}976 \approx 18.8$$, so it carries about 18.8 bits of entropy. A fair coin flip carries exactly 1 bit.

### Base e: growth and probabilities

$$e$$ is a constant, about 2.718, in the same way that $$\pi$$ is about 3.14. $$e^x$$ is always positive: it grows quickly as $$x$$ grows and gets close to zero as $$x$$ becomes negative ($$e^3 \approx 20.09$$, $$e^0 = 1$$, $$e^{-3} \approx 0.05$$).

Neural networks use $$e^x$$ to turn raw outputs into probabilities. A network's raw output can be any number, such as -3 or 250, but a probability has to be between 0 and 1. The sigmoid function does that conversion:

$$
\sigma(x) = \frac{1}{1 + e^{-x}}
$$

Large positive inputs come out close to 1, large negative inputs come out close to 0, and an input of 0 comes out as exactly 0.5:

![The sigmoid curve: flat near 0 for inputs below -4, rising steeply through 0.5 at input 0, and flat near 1 for inputs above 4](/images/ai-math/sigmoid.svg)

Softmax does the same job for several outputs at once and makes them add up to 1. That is how a classifier produces probabilities like the three in the argmax table above.

$$\ln x$$ is the logarithm with base $$e$$, called the natural logarithm: $$\ln 20.09 \approx 3$$ because $$e^3 \approx 20.09$$. Machine learning uses it to score how wrong a classifier is, which is called log loss. If the model gave the correct label probability $$p$$, the loss is:

$$
\text{loss} = -\ln p
$$

![The log loss curve: loss is near 0 when p is close to 1, and climbs steeply as p approaches 0. p = 0.9 gives 0.11, p = 0.1 gives 2.30](/images/ai-math/log-loss.svg)

A confident correct answer ($$p = 0.9$$) costs 0.11. A confident wrong answer, where the correct label only got $$p = 0.1$$, costs 2.30, about 20 times more. Training lowers the average loss, so the steep left side of the curve pushes the model hardest to fix its confident mistakes.

Logs also turn multiplication into addition: $$\ln(a \times b) = \ln a + \ln b$$. A language model scores a sentence by multiplying the probability of each word, and multiplying hundreds of numbers below 1 gives a result too small for a computer to store. Adding their logs carries the same information in a number of normal size.

## Vectors and Norms

A vector is an ordered list of numbers, and in machine learning it describes one thing. A login event could be the vector (hour, failed attempts, MB downloaded) $$= (3, 7, 450)$$. Every input a model sees is turned into a vector first.

### Dot product

The dot product of two vectors multiplies them item by item and adds the results:

$$
\begin{aligned}
\mathbf{x} &= (3, 1, 2) \qquad \mathbf{w} = (0.5, -1, 2) \\
\mathbf{x} \cdot \mathbf{w} &= 3 \times 0.5 + 1 \times (-1) + 2 \times 2 = 1.5 - 1 + 4 = 4.5
\end{aligned}
$$

This is what a single neuron computes. $$\mathbf{x}$$ is the input, $$\mathbf{w}$$ holds the neuron's weights, and the output is $$\mathbf{x} \cdot \mathbf{w}$$ plus a constant called the bias. Training adjusts the weights.

### Norms: the size of a vector

A norm measures how big a vector is, written $$\lVert \mathbf{v} \rVert$$. There are three common ones. For $$\mathbf{v} = (3, 4)$$:

| Norm | Formula | For (3, 4) |
|---|---|---|
| L2 (Euclidean) | $$\lVert \mathbf{v} \rVert_2 = \sqrt{v_1^2 + v_2^2 + \cdots + v_n^2}$$ | $$\sqrt{9 + 16} = 5$$ |
| L1 (Manhattan) | $$\lVert \mathbf{v} \rVert_1 = \lvert v_1 \rvert + \lvert v_2 \rvert + \cdots + \lvert v_n \rvert$$ | $$3 + 4 = 7$$ |
| L∞ (max) | $$\lVert \mathbf{v} \rVert_\infty = \max(\lvert v_1 \rvert, \ldots, \lvert v_n \rvert)$$ | $$4$$ |

When $$\lVert \mathbf{v} \rVert$$ is written with no subscript, it means L2.

The distance between two vectors is the norm of their difference. For $$\mathbf{a} = (2, 1)$$ and $$\mathbf{b} = (8, 9)$$, the difference is $$(6, 8)$$:

![A grid with points a at (2, 1) and b at (8, 9). A straight line between them has L2 length 10. A path 6 across then 8 up has L1 length 14. The longest side, 8, is the L-infinity distance.](/images/ai-math/norms.svg)

L2 is the straight-line distance. L1 is the distance along the grid lines, like walking city blocks. L∞ is the largest single difference.

Machine learning uses norms in three places:

- **Similarity**: models that find similar items, such as nearest-neighbour classifiers or search over embeddings (vectors a model produces to represent a piece of text or an image), rank items by the distance between vectors.
- **Regularization**: during training, the norm of the weight vector is added to the error, so large weights cost more. This discourages a model from fitting the training data too closely (overfitting). An L1 penalty pushes many weights to exactly zero, and an L2 penalty keeps all of them small.
- **Normalizing**: dividing a vector by its norm gives a vector of length 1 pointing the same way: $$(3, 4) / 5 = (0.6, 0.8)$$.

Norms also appear in attacks on models. An adversarial example changes an input slightly so that a model gets it wrong, and "slightly" is defined as a norm limit on the change, for example no pixel changed by more than 8 out of 255 (an L∞ limit).

## Matrices

A matrix is a grid of numbers. Its shape is written rows × columns, so a matrix with 2 rows and 3 columns is 2×3.

### Matrix times vector

Multiplying a matrix by a vector takes the dot product of each row with the vector. Each row produces one number in the output:

$$
W = \begin{bmatrix} 2 & 0 & 1 \\ 1 & 3 & -1 \end{bmatrix}
\qquad
\mathbf{x} = \begin{bmatrix} 1 \\ 2 \\ 3 \end{bmatrix}
\qquad
W\mathbf{x} = \begin{bmatrix} 2 \times 1 + 0 \times 2 + 1 \times 3 \\ 1 \times 1 + 3 \times 2 + (-1) \times 3 \end{bmatrix} = \begin{bmatrix} 5 \\ 4 \end{bmatrix}
$$

The vector's length must equal the matrix's number of columns. A 2×3 matrix takes a vector of length 3 and returns a vector of length 2.

This is one layer of a neural network. Each row of $$W$$ holds the weights of one neuron, so this layer has 2 neurons, each reading 3 inputs. A deep network is a chain of these multiplications.

### Matrix times matrix

Multiplying two matrices takes the dot product of each row of the first with each column of the second:

$$
A = \begin{bmatrix} 2 & 1 \\ 0 & 3 \end{bmatrix}
\qquad
B = \begin{bmatrix} 1 & 4 \\ 2 & 5 \end{bmatrix}
\qquad
AB = \begin{bmatrix} 2 \times 1 + 1 \times 2 & 2 \times 4 + 1 \times 5 \\ 0 \times 1 + 3 \times 2 & 0 \times 4 + 3 \times 5 \end{bmatrix} = \begin{bmatrix} 4 & 13 \\ 6 & 15 \end{bmatrix}
$$

The shapes must line up: an $$m \times n$$ matrix times an $$n \times p$$ matrix gives an $$m \times p$$ matrix. Order changes the result. With the same matrices:

$$
BA = \begin{bmatrix} 2 & 13 \\ 4 & 17 \end{bmatrix} \neq AB
$$

Neural networks use this to process many inputs at once. Stack 1,000 input vectors as the rows of one matrix, and a single multiplication runs all of them through a layer. GPUs are designed to run this kind of operation in parallel.

### Transpose

The transpose $$A^T$$ turns rows into columns:

$$
C = \begin{bmatrix} 1 & 2 & 3 \\ 4 & 5 & 6 \end{bmatrix}
\qquad
C^T = \begin{bmatrix} 1 & 4 \\ 2 & 5 \\ 3 & 6 \end{bmatrix}
$$

A 2×3 matrix becomes 3×2. It is mostly used to make shapes line up for a multiplication. The dot product of two column vectors is often written $$\mathbf{a}^T \mathbf{b}$$.

### Determinant, inverse, and trace

These apply to square matrices (same number of rows and columns). For a 2×2 matrix with entries $$a, b, c, d$$, using the same $$A$$ as above:

| Name | Notation | 2×2 formula | For $$A = \begin{bmatrix} 2 & 1 \\ 0 & 3 \end{bmatrix}$$ |
|---|---|---|---|
| Determinant | $$\det(A)$$ | $$ad - bc$$ | $$2 \times 3 - 1 \times 0 = 6$$ |
| Inverse | $$A^{-1}$$ | $$\frac{1}{ad - bc} \begin{bmatrix} d & -b \\ -c & a \end{bmatrix}$$ | $$\begin{bmatrix} 0.5 & -0.167 \\ 0 & 0.333 \end{bmatrix}$$ |
| Trace | $$\operatorname{tr}(A)$$ | $$a + d$$ | $$2 + 3 = 5$$ |

- **Determinant**: how much the matrix stretches area. A determinant of 6 means a shape's area grows six times. A determinant of 0 means the matrix squashes everything onto a line, and the information cannot be recovered. $$\begin{bmatrix} 2 & 4 \\ 1 & 2 \end{bmatrix}$$ has determinant $$2 \times 2 - 4 \times 1 = 0$$, because its second column is double the first.
- **Inverse**: the matrix that undoes $$A$$. Multiplying $$A$$ by $$A^{-1}$$ gives the identity matrix $$I = \begin{bmatrix} 1 & 0 \\ 0 & 1 \end{bmatrix}$$, the matrix equivalent of 1. A matrix with determinant 0 has no inverse, since the formula divides by the determinant. Linear regression has a direct solution that uses an inverse: $$\mathbf{w} = (X^T X)^{-1} X^T \mathbf{y}$$.
- **Trace**: the sum of the diagonal from top left to bottom right. It equals the sum of the matrix's eigenvalues.

### Eigenvectors and eigenvalues

Multiplying a vector by a matrix usually changes its direction. An eigenvector is a vector whose direction does not change: the matrix only stretches it. The stretch factor is the eigenvalue, written $$\lambda$$ (lambda):

$$
A\mathbf{v} = \lambda \mathbf{v}
$$

With the same $$A$$:

$$
\begin{aligned}
A \begin{bmatrix} 1 \\ 1 \end{bmatrix} &= \begin{bmatrix} 3 \\ 3 \end{bmatrix} = 3 \begin{bmatrix} 1 \\ 1 \end{bmatrix} && \text{eigenvector } (1, 1)\text{, eigenvalue } 3 \\[4pt]
A \begin{bmatrix} 1 \\ 0 \end{bmatrix} &= \begin{bmatrix} 2 \\ 0 \end{bmatrix} = 2 \begin{bmatrix} 1 \\ 0 \end{bmatrix} && \text{eigenvector } (1, 0)\text{, eigenvalue } 2 \\[4pt]
A \begin{bmatrix} 0 \\ 1 \end{bmatrix} &= \begin{bmatrix} 1 \\ 3 \end{bmatrix} && \text{not a multiple of } (0, 1)\text{, so not an eigenvector}
\end{aligned}
$$

The eigenvalues are 3 and 2. Their sum, 5, is the trace, and their product, 6, is the determinant.

Principal component analysis (PCA), a dimensionality reduction method, is built on this. It computes the eigenvectors of the data's covariance matrix (covered below). Each eigenvector is a direction in the data, and its eigenvalue says how much the data spreads out along it. Keeping the few directions with the largest eigenvalues keeps most of the information in far fewer columns.

## Probability and Statistics

### Probability and conditional probability

$$P(A)$$ is the probability that $$A$$ happens, from 0 (never) to 1 (always). $$P(A \mid B)$$ is the probability of $$A$$ given that $$B$$ is known to be true. The vertical bar reads "given".

If 2% of a company's incoming email is phishing, $$P(\text{phishing}) = 0.02$$. If 60% of emails containing the phrase "urgent wire transfer" are phishing, $$P(\text{phishing} \mid \text{"urgent wire transfer"}) = 0.6$$. Knowing $$B$$ changes the probability.

Model outputs are conditional probabilities. A classifier outputs $$P(\text{label} \mid \text{input})$$, and a language model outputs $$P(\text{next word} \mid \text{all previous words})$$, then picks or samples a word from that distribution.

### Expected value

$$E[X]$$ is the average value of $$X$$, weighting each possible value by its probability:

$$
E[X] = \sum_i x_i \, P(x_i)
$$

If a server raises 0 alerts in 50% of hours, 1 alert in 30%, and 4 alerts in 20%:

$$
E[X] = 0 \times 0.5 + 1 \times 0.3 + 4 \times 0.2 = 1.1 \text{ alerts per hour}
$$

No single hour has 1.1 alerts. The expected value is the long-run average.

### Variance and standard deviation

Two servers both average 100 ms per response:

```text
Server 1:  100, 100, 100, 100
Server 2:   50, 150,  50, 150
```

Variance measures how far values spread from the mean:

$$
\operatorname{Var}(X) = E\big[(X - E[X])^2\big]
$$

Take each value's distance from the mean, square it, and average the squares. Server 1 has variance 0. Server 2's values are each 50 away from the mean, so its variance is $$50^2 = 2500$$.

Squaring makes the units ms², which is hard to read. The standard deviation returns to the original unit:

$$
\sigma(X) = \sqrt{\operatorname{Var}(X)}
$$

Server 2 has $$\sigma = 50$$ ms. A simple anomaly detector flags any value more than 3 standard deviations from the mean.

### Covariance and correlation

Covariance measures whether two variables rise and fall together:

$$
\operatorname{Cov}(X, Y) = E\big[(X - E[X])(Y - E[Y])\big]
$$

Take the data below, with failed logins on four accounts and the alerts each account raised:

| | Account 1 | Account 2 | Account 3 | Account 4 | Mean |
|---|---|---|---|---|---|
| X (failed logins) | 1 | 2 | 3 | 4 | 2.5 |
| Y (alerts) | 2 | 4 | 5 | 9 | 5 |

$$
\operatorname{Cov}(X, Y) = \frac{(-1.5)(-3) + (-0.5)(-1) + (0.5)(0) + (1.5)(4)}{4} = \frac{4.5 + 0.5 + 0 + 6}{4} = 2.75
$$

A positive covariance means they rise together, and a negative one means one falls as the other rises. The size of the number depends on the units, so 2.75 alone does not say how strong the link is.

Correlation fixes that by dividing by both standard deviations:

$$
\rho(X, Y) = \frac{\operatorname{Cov}(X, Y)}{\sigma(X)\,\sigma(Y)} = \frac{2.75}{1.12 \times 2.55} \approx 0.96
$$

Correlation is always between -1 and 1:

| $$\rho$$ | Meaning |
|---|---|
| 1 | both rise together, exactly on a straight line |
| 0 | no straight-line relationship |
| -1 | one falls as the other rises, exactly on a straight line |

![Three scatter plots of 40 points each. Left: points rise together, correlation 0.95. Middle: no pattern, correlation 0.01. Right: one falls as the other rises, correlation -0.96](/images/ai-math/correlation.svg)

A correlation of 0.96 says the two rise together. It does not say failed logins cause alerts; something else could drive both.

Before training, correlation is used to find features that duplicate each other. Two features with a correlation near 1 carry almost the same information, and one of them can usually be dropped.
