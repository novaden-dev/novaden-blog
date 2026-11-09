---
title: "Jupyter, scikit-learn and PyTorch"
slug: ai-tools
category: notes
handbook: ai-security
tags: ["ai"]
draft: false
pubDatetime: 2026-11-08T00:00:00+02:00
description: "The three tools the rest of this handbook's code runs on: Jupyter notebooks and their hidden state, scikit-learn's fit and predict interface, pipelines, grid search and saving models, and PyTorch's tensors, gradients and devices for neural networks."
---

## Introduction

The code in these notes runs in Python, inside the conda environment built in [AI Lab Setup](/collections/ai-security/ai-lab-setup), with the usual ML libraries: numpy for arrays, pandas for tables, matplotlib for plots, scikit-learn for classic models, PyTorch for neural networks, and Hugging Face `transformers` for pretrained models. Most of it is written and run in Jupyter.

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

### Pipelines

A `Pipeline` chains preparation steps and a model into one object. `fit` fits each step in order on the training data, and `predict` runs new data through the same fitted steps. Each step has a name:

```python
from sklearn.pipeline import Pipeline
from sklearn.preprocessing import FunctionTransformer
from sklearn.feature_extraction.text import CountVectorizer
from sklearn.naive_bayes import MultinomialNB

def preprocess_all(messages):
    return [preprocess_message(m) for m in messages]

pipeline = Pipeline([
    ("prepare", FunctionTransformer(preprocess_all)),
    ("vectorizer", CountVectorizer(ngram_range=(1, 2), max_df=0.9)),
    ("classifier", MultinomialNB()),
])
pipeline.fit(X_train, y_train)
pipeline.predict(["Hey, are we still meeting up for lunch today?"])
```

`FunctionTransformer` turns a plain function into a pipeline step. Here it runs the text cleanup from [Preparing Text](/collections/ai-security/ai-preparing-text#preparing-new-messages), so raw messages go in at both training and prediction, and the cleanup cannot differ between the two.

A pipeline also prevents [leakage](/collections/ai-security/ai-datasets#leakage) during cross-validation. When a pipeline is cross-validated, the vectorizer is refitted on the training folds of each round, so its vocabulary never includes words from the fold it is tested on.

Two parts of the syntax come from the step names:

- **`named_steps`**: gives access to one fitted step. `pipeline.named_steps["vectorizer"].get_feature_names_out()` lists the vocabulary, and `pipeline.named_steps["classifier"]` is the fitted model with its learned values. Prediction still goes through the whole pipeline: calling the steps one by one gives the same result but means repeating each step yourself.
- **`step__parameter`**: a double underscore joins a step name and one of its parameters. `classifier__alpha` is the `alpha` parameter of the step named `classifier`. `pipeline.set_params(classifier__alpha=0.5)` and grid search both use this form.

### Grid search

A hyperparameter is a setting chosen before training, such as $$\alpha$$ in [Naive Bayes](/collections/ai-security/ai-naive-bayes#choosing-alpha) or the depth of a [decision tree](/collections/ai-security/ai-decision-trees). Training does not learn it. `GridSearchCV` tries every combination of the values it is given, [cross-validates](/collections/ai-security/ai-supervised-learning#cross-validation) each one, and keeps the best:

```python
from sklearn.model_selection import GridSearchCV

param_grid = {"classifier__alpha": [0.01, 0.1, 0.25, 0.5, 1.0]}
grid_search = GridSearchCV(pipeline, param_grid, cv=5, scoring="f1")
grid_search.fit(X_train, y_train)
```

Five values with 5 folds means 25 trainings. With two parameters of five values each, it is 25 combinations and 125 trainings, so the grid grows quickly. `scoring="f1"` picks the [metric](/collections/ai-security/ai-supervised-learning#accuracy-precision-recall-f1) to compare. F1 suits spam, because only 12.6% of the messages are spam: a model that labels everything ham still scores 87% accuracy and 0 F1.

| Attribute | Contains |
|---|---|
| `best_params_` | The winning values, such as `{'classifier__alpha': 0.5}` |
| `best_score_` | Their mean cross-validation score |
| `best_estimator_` | The pipeline with those values, refitted on all the data passed to `fit` |
| `cv_results_` | The score of every combination in every fold |

`best_score_` is not a fair estimate of how the model will do on new data. It is the highest of several cross-validation scores, and the highest of several noisy scores tends to be higher than the true value. A test set that the grid search never saw gives the fair estimate, so split first, search on the training part, and measure once on the test part:

```python
from sklearn.model_selection import train_test_split
from sklearn.metrics import classification_report

X_train, X_test, y_train, y_test = train_test_split(
    df["message"], y, test_size=0.2, stratify=y, random_state=0
)
grid_search.fit(X_train, y_train)
print(classification_report(y_test, grid_search.predict(X_test)))
```

On the [SMS Spam Collection](/collections/ai-security/ai-preparing-text#introduction) (5,169 messages after removing duplicates), the search on the training part picks $$\alpha = 0.5$$ with a cross-validation F1 of 0.926. On the 1,034 test messages, spam gets precision 0.944, recall 0.901 and F1 0.922: 13 of the 131 spam messages pass as ham, and 7 of the 903 ham messages are flagged as spam.

### Saving a model

`joblib` writes a fitted model or pipeline to a file and reads it back, so it does not have to be trained again:

```python
import joblib

joblib.dump(grid_search.best_estimator_, "spam_detection_model.joblib")
model = joblib.load("spam_detection_model.joblib")
model.predict(["WIN a free prize now"])
```

The file is built on Python's `pickle` format, which has three consequences:

- **Loading a file runs code from it.** A pickle file can tell Python to call any function while it loads. A file built from this class runs `id` on the machine that loads it:

  ```python
  import os, joblib

  class Payload:
      def __reduce__(self):
          return (os.system, ("id",))

  joblib.dump(Payload(), "model.joblib")
  ```

  `joblib.load("model.joblib")` prints the uid of whoever loads it. Load only files you created or trust. Model files with payloads like this have been found on public model hubs such as Hugging Face. [skops](https://skops.readthedocs.io/) offers a format for scikit-learn models that loads only types on an allow list and raises an error for any other type.
- **Functions are saved as a name only.** A pipeline with `FunctionTransformer(preprocess_all)` stores only the name `preprocess_all`. Loading it in a new Python session fails with `Can't get attribute 'preprocess_all'` until that function is defined or imported again.
- **Versions have to match.** A model saved with one scikit-learn version may load with a warning, or not work, under another. Record the versions the model was trained with.

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
