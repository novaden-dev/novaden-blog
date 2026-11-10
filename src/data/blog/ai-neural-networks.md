---
title: "Neural Networks"
slug: ai-neural-networks
category: notes
handbook: ai-security
tags: ["ai"]
draft: false
pubDatetime: 2026-11-10T00:00:00+03:00
description: "How a neural network is built and trained in PyTorch: layers of weighted sums, ReLU between them, logits and softmax at the output, cross-entropy loss, backpropagation, optimizers and the learning rate, batches and epochs, the training loop, train and eval modes, and saving the weights safely."
---

## Introduction

A neural network is a model built from layers. Each layer computes many weighted sums of its inputs, passes them through a simple function, and gives the results to the next layer as its inputs. [Deep Learning](/collections/ai-security/ai-foundations#deep-learning) in the foundations note describes the idea. This note covers how a network is defined in PyTorch and how it is trained.

The example network sorts malware samples into 25 families, such as `Allaple.A` and `Yuner.A`. Each sample is described by 2,048 numbers, and the network outputs the family the sample belongs to. Here the 2,048 numbers come from a pretrained image network that reads each malware file as a picture, as described in [CNNs and Transfer Learning](/collections/ai-security/ai-cnns).

Training follows the same four steps as [logistic regression](/collections/ai-security/ai-supervised-learning#model-and-training): predict, measure the loss, move every weight a small step in the direction that lowers the loss, and repeat. A network has many more weights, and PyTorch computes the direction for each of them.

## Layers

### A layer is many weighted sums

A unit (also called a neuron) multiplies each of its inputs by its own weight, adds the results, and adds a bias. This is the calculation logistic regression does before the sigmoid. A layer is many units side by side, each with its own weights, all reading the same inputs.

A layer with 2,048 inputs and 1,000 units computes 1,000 weighted sums. It has 2,048 × 1,000 weights plus one bias per unit, 2,049,000 parameters in total. In PyTorch this layer is `nn.Linear(2048, 1000)`. It computes all 1,000 sums at once as a [matrix times a vector](/collections/ai-security/ai-math#matrix-times-vector). GPUs are built for matrix arithmetic, so training a network on a GPU is much faster than on a CPU.

This kind of layer is called fully connected (or dense, or linear), because every unit reads every input. The layers between the input and the output are called hidden layers.

### Activation functions

Two linear layers in a row can only compute what one linear layer can. The second layer computes weighted sums of weighted sums, and those simplify to a single weighted sum of the original inputs:

$$
W_2(W_1 \mathbf{x} + \mathbf{b}_1) + \mathbf{b}_2 = (W_2 W_1)\mathbf{x} + (W_2 \mathbf{b}_1 + \mathbf{b}_2)
$$

Ten stacked linear layers still separate classes with a flat boundary, the same [hyperplane](/collections/ai-security/ai-logistic-regression#hyperplanes) as logistic regression. An activation function between the layers prevents this. It is applied to each unit's output separately, and since its graph is not a straight line, the layers no longer simplify into one, and the network can separate classes with curved boundaries.

Hidden layers usually use ReLU (rectified linear unit), which replaces negative values with 0 and leaves positive values unchanged:

$$
\text{ReLU}(x) = \max(0, x)
$$

| Activation | Formula | Output range | Used in |
|---|---|---|---|
| ReLU | $$\max(0, x)$$ | 0 and above | Hidden layers, by default |
| Sigmoid | $$\frac{1}{1 + e^{-x}}$$ | 0 to 1 | The output of a two-class network |
| Tanh | $$\frac{e^x - e^{-x}}{e^x + e^{-x}}$$ | -1 to 1 | Hidden layers of older and recurrent networks |

ReLU is fast to compute, and its gradient is 1 for every positive input. The sigmoid is almost flat at both ends, so its gradient is close to 0 for large positive or negative inputs. In a deep network, these small gradients are multiplied together layer by layer during [backpropagation](#backpropagation), and the weights of the first layers receive gradients so small that they hardly change. This is called the vanishing gradient problem. ReLU's gradient stays 1 for positive inputs, so its gradients do not shrink this way.

### The output layer

The last layer has one unit per class, so the malware network ends with 25 outputs. These outputs are raw scores called logits, and they can be any number, such as -3.1 or 7.4. [Softmax](/collections/ai-security/ai-math#base-e-growth-and-probabilities) turns them into probabilities that add up to 1, and the prediction is the [argmax](/collections/ai-security/ai-math#max-min-and-argmax): the class with the highest value.

Softmax keeps the order of the outputs, so the largest logit is also the largest probability, and the prediction can be read from the logits directly. Softmax is needed when the probabilities themselves are used, for example to send a sample to an analyst when its highest probability is below 0.9.

## Defining a Network in PyTorch

A network is a Python class that inherits from `nn.Module`. `__init__` creates the layers, and `forward` defines how an input passes through them:

```python
import torch.nn as nn

class MalwareClassifier(nn.Module):
    def __init__(self, n_features, n_classes):
        super().__init__()
        self.layers = nn.Sequential(
            nn.Linear(n_features, 1000),  # hidden layer with 1,000 units
            nn.ReLU(),
            nn.Linear(1000, n_classes),   # output layer: one logit per class
        )

    def forward(self, x):
        return self.layers(x)

model = MalwareClassifier(n_features=2048, n_classes=25)
```

`nn.Sequential` runs its layers in order, each on the output of the previous one. Calling `model(x)` runs `forward`. `x` holds a batch of samples, one per row, so for 64 samples of 2,048 features `model(x)` returns a 64 × 25 tensor of logits.

The network ends without a softmax, because the loss function in the next section applies softmax itself.

PyTorch fills the weights with small random numbers when it creates the layers, so the predictions are random until the network is trained.

## Training

### Cross-entropy loss

`nn.CrossEntropyLoss` measures how wrong the logits are. For each sample, it applies softmax and takes the [log loss](/collections/ai-security/ai-math#base-e-growth-and-probabilities) of the probability given to the correct class, $$-\ln p$$, then averages over the batch. It is the loss of logistic regression extended to any number of classes.

It takes the logits and the correct class numbers (0 to 24 for 25 classes). If the model also ended with a softmax, softmax would run twice, and the loss would be computed on the wrong numbers.

Before training, the random weights give each class roughly the same probability, 1/25, so the first loss is close to $$-\ln(1/25) \approx 3.2$$. A first loss far from that value points to a bug in the data or the model.

### Backpropagation

Each weight needs its gradient: how much the loss changes when that weight changes slightly. PyTorch computes these with its [automatic gradients](/collections/ai-security/ai-tools#pytorch). During the forward pass, PyTorch records every operation. `loss.backward()` goes back through that record from the loss to the first layer, and uses the chain rule from calculus to compute each layer's gradients from the gradients of the layer after it. This is called backpropagation. Each weight's gradient is stored in its `.grad` attribute.

### Optimizers and the learning rate

An optimizer uses the gradients to update the weights. Gradient descent, the simplest optimizer, moves each weight a step in the direction opposite to its gradient:

$$
w \leftarrow w - \eta \cdot \frac{\partial \text{loss}}{\partial w}
$$

$$\eta$$ (eta) is the learning rate, the size of the step:

| Learning rate | Effect on training |
|---|---|
| Too high | Each step jumps past the lowest point. The loss goes up and down or keeps growing until it becomes `nan` (not a number) |
| Too low | The weights change very little per step, and the loss falls so slowly that training needs many more epochs |
| Suitable | The loss falls quickly at first, then levels off |

Networks are usually trained with Adam, an optimizer that adjusts the step size for each weight. Adam keeps a running average of each weight's recent gradients and a running average of their squares, and divides the first by the square root of the second. A weight whose gradients keep pointing the same way takes steps close to the learning rate, and a weight whose gradients keep changing sign takes smaller steps. Adam's default learning rate, 0.001, works for many networks without tuning.

```python
optimizer = torch.optim.Adam(model.parameters(), lr=0.001)
```

`model.parameters()` gives the optimizer every weight it is allowed to update.

### Batches and epochs

Computing the loss over the whole training set before each update is slow on a large dataset, and the whole set may not fit in memory. Training uses mini-batches instead: small groups of samples, such as 64. Each batch gives one loss, one backward pass and one update. The gradient of one batch is an estimate of the gradient over all the data. It is less accurate, and far cheaper to compute.

An epoch is one pass through every training sample. With 6,500 training samples and a batch size of 64, one epoch is 102 updates. Training usually runs for several epochs.

PyTorch's `DataLoader` splits a dataset into batches:

```python
from torch.utils.data import DataLoader

train_loader = DataLoader(train_dataset, batch_size=64, shuffle=True)
val_loader = DataLoader(val_dataset, batch_size=256, shuffle=False)
```

`shuffle=True` puts the training samples in a new random order every epoch. Without it, a dataset stored family by family produces batches that each hold a single family, and each update moves the weights towards that family only. The validation and test sets do not need shuffling, because every sample is measured once in any order.

| Batch size | Effect |
|---|---|
| Small (16 to 64) | More updates per epoch, less accurate gradients, less memory |
| Large (512 and more) | Fewer updates per epoch, more accurate gradients, more memory, and usually a higher learning rate to compensate for the fewer updates |

### The training loop

PyTorch has no `fit` method like scikit-learn's. The training loop is written in Python:

```python
import torch

if torch.cuda.is_available():
    device = "cuda"
elif torch.xpu.is_available():
    device = "xpu"
else:
    device = "cpu"

model = model.to(device)
criterion = nn.CrossEntropyLoss()
optimizer = torch.optim.Adam(model.parameters(), lr=0.001)

for epoch in range(10):
    model.train()
    for inputs, labels in train_loader:
        inputs, labels = inputs.to(device), labels.to(device)

        optimizer.zero_grad()              # clear the gradients of the previous batch
        outputs = model(inputs)            # forward pass: logits for the batch
        loss = criterion(outputs, labels)  # one number for the batch
        loss.backward()                    # backpropagation: fills each weight's .grad
        optimizer.step()                   # update the weights
```

`loss.backward()` adds the new gradients to `.grad` instead of replacing them. Without `optimizer.zero_grad()`, each update would use the sum of every gradient since training started.

The model and each batch have to be on the same [device](/collections/ai-security/ai-tools#pytorch). A model that is never moved with `.to(device)` trains on the CPU even when a GPU is available, and a batch on a different device from the model raises an error.

## Watching Training

At the end of each epoch, the network is measured on the [validation set](/collections/ai-security/ai-supervised-learning#validation-set):

```python
def evaluate(model, loader):
    model.eval()
    total_loss, correct, n = 0.0, 0, 0
    with torch.no_grad():
        for inputs, labels in loader:
            inputs, labels = inputs.to(device), labels.to(device)
            outputs = model(inputs)
            total_loss += criterion(outputs, labels).item() * len(labels)
            correct += (outputs.argmax(dim=1) == labels).sum().item()
            n += len(labels)
    return total_loss / n, correct / n
```

Recording the training loss and the validation loss of every epoch, and plotting them, shows how training is going:

| Training loss | Validation loss | Meaning |
|---|---|---|
| Falling | Falling | The network is still improving, so more epochs help |
| Low and flat | Low and flat | Training is finished |
| Falling | Rising | [Overfitting](/collections/ai-security/ai-supervised-learning#generalization-overfitting-and-underfitting): the network fits the training samples better and new samples worse |
| High and flat | High and flat | Underfitting, or a learning rate that is too low |

Early stopping uses the validation loss to choose the number of epochs. Save the weights each time the validation loss reaches a new low, stop when it has not improved for a few epochs, and keep the saved weights.

Accuracy counted on the training batches during an epoch does not measure the network at the end of that epoch. Each batch is scored with the weights at that moment, so the early batches are scored by a less trained network. Those samples are also the ones the network trains on, so the count says nothing about new samples. The validation set, measured after the epoch, has neither problem.

## Train and Eval Modes

`model.train()` and `model.eval()` switch the layers that work differently during training:

- **Dropout**: in train mode, sets a random share of a layer's outputs to 0 on each batch, so the predictions cannot depend on any single unit. This reduces overfitting. In eval mode, dropout does nothing.
- **Batch normalization**: in train mode, rescales a layer's outputs with the mean and variance of the current batch, and updates a running average of both. In eval mode, it uses the running averages, so a sample's prediction does not depend on the other samples in its batch.

A network measured in train mode gives different predictions from run to run, and its batch normalization layers update their averages from the test data. Call `model.eval()` before measuring or predicting, and `model.train()` before training again.

`torch.no_grad()` does something else: it stops PyTorch from recording operations for backpropagation, which saves memory and time when no gradients are needed. Prediction uses both:

```python
model.eval()
with torch.no_grad():
    logits = model(samples.to(device))
    probabilities = torch.softmax(logits, dim=1)
    predicted = logits.argmax(dim=1)
```

## Saving a Network

A network's weights are in its `state_dict`, a dictionary that maps each layer's name to its weight tensors. Saving the `state_dict` saves the trained network:

```python
torch.save(model.state_dict(), "malware_classifier.pt")
```

The file holds only the weights, so loading it needs the class definition:

```python
model = MalwareClassifier(n_features=2048, n_classes=25)
model.load_state_dict(torch.load("malware_classifier.pt", weights_only=True))
model.eval()
```

`.pt` and `.pth` are both common extensions, and PyTorch treats them the same way.

`torch.save` writes a [pickle](/collections/ai-security/ai-tools#saving-a-model) file, so loading a file from someone else can run code. With `weights_only=True`, `torch.load` accepts only tensors and basic Python types and raises an error for anything else. It is the default since PyTorch 2.6. Older versions load anything unless it is passed, and passing `weights_only=False` turns the check off.

`torch.save(model)` without `.state_dict()` pickles the whole model, including a reference to its class. Loading it fails unless the class can be imported under the same name, and it needs `weights_only=False`.

TorchScript, `torch.jit.script(model).save(path)`, saves the network's code together with its weights, so it can be loaded without the class definition. Current PyTorch versions mark TorchScript as deprecated and recommend `torch.export`, which also saves a network as code and weights so it can run outside the Python code that defined it.
