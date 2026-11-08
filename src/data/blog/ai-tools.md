---
title: "Jupyter, scikit-learn and PyTorch"
slug: ai-tools
category: notes
handbook: ai-security
tags: ["ai"]
draft: false
pubDatetime: 2026-11-08T00:00:00+02:00
description: "The three tools the rest of this handbook's code runs on: Jupyter notebooks and their hidden state, scikit-learn's fit and predict interface for classic models, and PyTorch's tensors, gradients and devices for neural networks."
---

## Introduction

The code in these notes runs in Python, inside a conda environment with the usual ML libraries: numpy for arrays, pandas for tables, matplotlib for plots, scikit-learn for classic models, PyTorch for neural networks, and Hugging Face `transformers` for pretrained models. Most of it is written and run in Jupyter.

## Jupyter

A Jupyter notebook is a document made of cells. A code cell runs Python and shows its output, such as a table or a plot, directly below it. A text cell holds notes in Markdown. JupyterLab is the browser interface for working with notebooks, started with `jupyter lab` from the active environment.

Behind each notebook is a kernel: one Python process that runs every cell and keeps every variable in memory between runs. That is what makes notebooks fast for exploring data. A large dataset is loaded once, and later cells try different plots or models on it without loading it again.

The same kernel is also a common source of notebook bugs. Cells can run in any order, and the kernel remembers everything that ran, including cells that were edited or deleted since. A notebook can work for its author and fail for anyone who runs it top to bottom. **Restart Kernel and Run All Cells** shows whether it works from a clean start.

## scikit-learn

scikit-learn holds the classic models: [linear regression](/collections/ai-security/ai-linear-regression), [logistic regression](/collections/ai-security/ai-logistic-regression), [decision trees](/collections/ai-security/ai-decision-trees) and many more, plus the tools around them for splitting data, scaling features and computing metrics.

Every model has the same interface. `fit` trains it on data, `predict` returns predictions for new rows, and `score` returns a default metric, such as accuracy for a classifier. Preprocessing tools follow the same pattern, with `transform` in place of `predict`:

```python
from sklearn.datasets import load_breast_cancer
from sklearn.model_selection import train_test_split
from sklearn.preprocessing import StandardScaler
from sklearn.linear_model import LogisticRegression

X, y = load_breast_cancer(return_X_y=True)
X_train, X_test, y_train, y_test = train_test_split(X, y, test_size=0.2, random_state=0)

scaler = StandardScaler().fit(X_train)
model = LogisticRegression().fit(scaler.transform(X_train), y_train)
print(model.score(scaler.transform(X_test), y_test))  # 0.965
```

Swapping `LogisticRegression` for `DecisionTreeClassifier` changes one import and one line. The rest stays the same, which makes it quick to compare several models on one dataset.

## PyTorch

PyTorch is a library for building and training neural networks. It is built on three ideas:

- **Tensors**: multi-dimensional arrays, like numpy arrays, that can be stored in GPU memory.
- **Automatic gradients**: PyTorch records every operation on a tensor and can work out how the result changes when each input changes. Training uses that gradient to decide which direction to move each weight, as described in [Supervised Learning](/collections/ai-security/ai-supervised-learning).
- **Devices**: the same code runs on the CPU or a GPU, selected with `.to("cuda")` for NVIDIA, `"xpu"` for Intel or `"mps"` for Apple Silicon.

A gradient computed by PyTorch for $$y = x^2 + 3x$$ at $$x = 2$$:

```python
import torch

x = torch.tensor(2.0, requires_grad=True)
y = x**2 + 3 * x
y.backward()
print(y.item(), x.grad.item())  # 10.0 7.0
```

The derivative is $$2x + 3$$, which is 7 at $$x = 2$$. A neural network does the same thing with millions of weights instead of one $$x$$, and a loss in place of $$y$$.

## Which One to Use

| | scikit-learn | PyTorch |
|---|---|---|
| Models | Classic ML: regression, trees, clustering, ensembles | Neural networks of any shape |
| Data size | Fits in memory, up to millions of rows | Any size, streamed in batches |
| Training | One `fit` call | A training loop you write, or a library such as Hugging Face's that writes it for you |
| GPU | Not used | CPU or GPU |
| Typical input | Tables of numeric features | Images, text, audio, and tables |

For a table of features, such as the log data in these notes, start with scikit-learn. Use PyTorch when the model has to be a neural network, for example to process raw text or images.
