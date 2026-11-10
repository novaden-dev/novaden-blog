---
title: "CNNs and Transfer Learning"
slug: ai-cnns
category: notes
handbook: ai-security
tags: ["ai"]
draft: false
pubDatetime: 2026-11-10T00:00:00+03:00
description: "How convolutional networks process images, and how to reuse one trained on photos for a new task: malware files as grayscale images, convolution and pooling, ResNet50 and residual connections, freezing layers and replacing the last one, preparing images for a pretrained network, and loading image folders in PyTorch."
---

## Introduction

A convolutional neural network (CNN) is a [neural network](/collections/ai-security/ai-neural-networks) built for grid-shaped data such as images. [The foundations note](/collections/ai-security/ai-foundations#convolutional-neural-networks-cnns) describes the idea: small filters slide across the image, and later layers combine what earlier layers found into larger shapes. This note covers how that works in numbers, and how a CNN trained on millions of photos can be reused to classify something else, such as malware.

Training a large CNN from scratch takes millions of labeled images. Transfer learning starts instead from a network someone else trained on a large dataset, keeps most of its layers, and trains only a new last layer on the new task. A few thousand labeled samples are then enough.

The examples classify malware samples into families using [Malimg](https://vision.ece.ucsb.edu/node/563), a public dataset of 9,339 Windows malware samples from 25 families, published as images.

## Malware as Images

A file is a sequence of bytes, and each byte is a number from 0 to 255, which is also the range of a grayscale pixel. Writing the bytes into rows of a fixed width turns any file into a grayscale image: byte 0 is the top left pixel, and the image gets taller as the file gets longer.

```python
import numpy as np
from PIL import Image

def file_to_image(path, width=256):
    data = np.fromfile(path, dtype=np.uint8)  # the file's bytes as numbers 0 to 255
    height = len(data) // width
    pixels = data[: height * width].reshape(height, width)  # the last partial row is dropped
    return Image.fromarray(pixels)                          # an 8-bit grayscale image
```

Malimg picks the width from the file size, from 32 pixels for files under 10 KB up to 1,024 pixels for files over 1 MB, so large files do not become extremely tall images.

The image shows the layout of the file. The sections of a Windows executable, such as the code, the data and the zero padding between them, appear as bands with different textures: padding is a black area, and compressed or encrypted data looks like noise. Samples of one family are usually built from the same code with small changes, so their images look alike, and a CNN can learn those textures without anyone writing rules about the file format.

The image does not show what the program does when it runs:

- **Packing**: a packer compresses or encrypts a program and adds a small stub that unpacks it at run time. Two unrelated programs packed with the same packer can produce similar images, and one family repacked with a different packer can look completely different.
- **Changed layout**: bytes appended to the end of a file, or a section added, change the image without changing what the program does. An attacker who knows the classifier works on images can add bytes until the predicted family changes.

## Convolution

### Filters

A filter is a small grid of weights, such as 3 × 3. It is placed over the top left corner of the image, each pixel is multiplied by the weight above it, and the nine products are added. The sum is one output value. The filter then moves one pixel to the right and repeats, row by row, across the whole image. The grid of outputs is called a feature map.

A filter that detects vertical edges, where dark pixels on the left meet bright pixels on the right:

$$
\text{filter} = \begin{bmatrix} -1 & 0 & 1 \\ -1 & 0 & 1 \\ -1 & 0 & 1 \end{bmatrix}
\qquad
\text{image} = \begin{bmatrix} 0 & 0 & 9 & 9 & 9 \\ 0 & 0 & 9 & 9 & 9 \\ 0 & 0 & 9 & 9 & 9 \end{bmatrix}
$$

The filter fits in three positions across this image:

| Columns covered | Pixels in each row | Sum per row | Output |
|---|---|---|---|
| 1 to 3 | 0, 0, 9 | -0 + 0 + 9 = 9 | 27 |
| 2 to 4 | 0, 9, 9 | -0 + 0 + 9 = 9 | 27 |
| 3 to 5 | 9, 9, 9 | -9 + 0 + 9 = 0 | 0 |

The output is high where the filter covers the edge and 0 where the area is flat. The weights of the filters are not written by hand: they are parameters, and training sets them like any other weight.

A convolutional layer has many filters, such as 64, and each produces its own feature map. A color image has 3 channels (red, green and blue), so each filter in the first layer is 3 × 3 × 3 and reads all three channels at once. The next layer then has 64 channels as input, one per feature map.

### Why convolution fits images

The same filter is applied at every position, so a layer of 64 filters of 3 × 3 × 3 has $$64 \times 27 + 64 = 1{,}792$$ parameters, whatever the size of the image. A [fully connected layer](/collections/ai-security/ai-neural-networks#a-layer-is-many-weighted-sums) with 1,000 units reading a 224 × 224 color image has $$224 \times 224 \times 3 \times 1{,}000 \approx 150$$ million weights. Applying the same filter everywhere also means a pattern is detected wherever it appears in the image.

### Pooling

A pooling layer shrinks each feature map. Max pooling with a 2 × 2 window keeps the largest of every four values, which halves the width and the height. After several rounds of convolution and pooling, each value in a feature map covers a large area of the original image, so the later filters combine edges into textures and textures into larger structures.

A typical CNN repeats convolution, [ReLU](/collections/ai-security/ai-neural-networks#activation-functions) and pooling several times, then averages each final feature map to one number, and passes those numbers to fully connected layers that output one logit per class.

## ResNet50

ResNet50 is a CNN with 50 layers, published by Microsoft researchers in 2015. torchvision includes it with weights trained on ImageNet, a dataset of about 1.28 million photos in 1,000 classes such as dogs, cars and mushrooms.

Its layers are grouped into blocks, and each block adds its input to its output:

$$
\text{output} = \text{block}(\mathbf{x}) + \mathbf{x}
$$

This addition is called a residual connection (or skip connection). During backpropagation, the gradient passes through the addition unchanged, so it reaches the first layers without shrinking through every block in between. Without residual connections, adding layers made networks harder to train: in the ResNet paper, a 56-layer network without them had a higher error on its own training data than a 20-layer one. The [vanishing gradient problem](/collections/ai-security/ai-neural-networks#activation-functions) is part of the reason.

The last convolutional block outputs 2,048 feature maps, and averaging each one gives 2,048 numbers per image. The last layer, `fc`, is a fully connected layer from those 2,048 numbers to the 1,000 ImageNet classes. In total, ResNet50 has 25,557,032 parameters.

## Transfer Learning

### What transfers

The early layers of a network trained on ImageNet detect edges, gradients and textures. These patterns appear in almost any image, including images of malware, although ImageNet contains no malware. The last layers are specific to the 1,000 ImageNet classes, and the final layer outputs exactly those classes, so it has to be replaced.

There are two ways to reuse the network:

| Approach | What is trained | When to use it |
|---|---|---|
| Feature extraction | Only the new last layers. Every pretrained layer is frozen | Little labeled data, or little computing power |
| Fine-tuning | The new last layers and some or all pretrained layers, with a small learning rate | More labeled data, or images very different from photos |

With feature extraction, the pretrained part of the network turns each image into 2,048 numbers, and the new layers are a small classifier trained on those numbers, as in the [Neural Networks](/collections/ai-security/ai-neural-networks) note.

### Freezing the layers and replacing the last one

```python
import torch.nn as nn
from torchvision import models

class MalwareClassifier(nn.Module):
    def __init__(self, n_classes):
        super().__init__()
        self.resnet = models.resnet50(weights=models.ResNet50_Weights.DEFAULT)

        for param in self.resnet.parameters():
            param.requires_grad = False  # frozen: training leaves these weights unchanged

        n_features = self.resnet.fc.in_features  # 2048
        self.resnet.fc = nn.Sequential(          # new layers, trainable by default
            nn.Linear(n_features, 1000),
            nn.ReLU(),
            nn.Linear(1000, n_classes),
        )

    def forward(self, x):
        return self.resnet(x)

model = MalwareClassifier(n_classes=25)
```

`weights=models.ResNet50_Weights.DEFAULT` downloads the ImageNet weights the first time and stores them in `~/.cache/torch/hub/checkpoints/`. `requires_grad = False` tells PyTorch not to compute gradients for those weights, so backpropagation stops at the new layers and training is faster. Layers created after the freezing loop, such as the new `fc`, have `requires_grad = True` by default.

The optimizer only needs the trainable weights:

```python
trainable = [p for p in model.parameters() if p.requires_grad]
optimizer = torch.optim.Adam(trainable, lr=0.001)
```

For fine-tuning, set `requires_grad = True` again on the last block, `model.resnet.layer4`, and use a smaller learning rate, such as 0.0001, so the pretrained weights change slowly.

### Frozen batch normalization layers

ResNet50 contains batch normalization layers, which keep running averages of the mean and variance of their inputs. `requires_grad = False` does not freeze those averages: they are not weights, and `model.train()` makes the layers update them from every training batch. In train mode, the averages of the frozen layers change to match the malware images, and those layers then normalize their inputs differently from the way they did during training on ImageNet.

To keep the pretrained part fixed, put it back in eval mode after `model.train()` at the start of each epoch:

```python
model.train()            # every layer in train mode
model.resnet.eval()      # the whole ResNet, including batch normalization, in eval mode
model.resnet.fc.train()  # the new fc layers back in train mode
```

`model.eval()` before measuring then puts every layer in eval mode, as described in [Train and Eval Modes](/collections/ai-security/ai-neural-networks#train-and-eval-modes).

## Preparing Images for a Pretrained Network

A pretrained network expects its input in the same form as its training images. torchvision's `transforms` convert each image:

```python
from torchvision import transforms

transform = transforms.Compose([
    transforms.Resize((224, 224)),
    transforms.ToTensor(),
    transforms.Normalize(mean=[0.485, 0.456, 0.406], std=[0.229, 0.224, 0.225]),
])
```

| Step | What it does | Why |
|---|---|---|
| `Resize((224, 224))` | Scales every image to 224 × 224 pixels | ResNet50 was trained on 224 × 224 images, and a batch needs all images the same size |
| `ToTensor()` | Converts pixel values from 0 to 255 into 0 to 1, in the order channel, height, width | PyTorch layers expect float tensors in this order |
| `Normalize(mean, std)` | Subtracts the mean and divides by the standard deviation, per channel | These are the means and standard deviations of the red, green and blue channels over ImageNet. The pretrained weights were trained on inputs [standardized](/collections/ai-security/ai-datasets#standardization) with these values |

Malimg images are grayscale, with one channel. `ImageFolder`, in the next section, opens every image as RGB, which copies the gray value into all three channels, so the input still has the 3 channels the first layer of ResNet50 expects.

`ResNet50_Weights.DEFAULT.transforms()` returns the exact preprocessing used for ImageNet: resize the shorter side to 232 pixels, then cut a 224 × 224 square out of the center. For photos, the center crop keeps the subject. For malware images, it cuts off the start and end of the file, so `Resize((224, 224))` on the whole image suits them better. A smaller size, such as 75 × 75, makes training faster, and each pixel of the resized image then averages many more bytes of the file, so fine textures are lost.

Photos are often augmented during training: randomly flipped, rotated or cropped, so the network sees more variations of each image. A flipped photo of a dog is still a dog, but a flipped malware image puts the bytes of the file in a different order, so these augmentations do not suit malware images.

## Loading Image Folders

Image datasets are often stored as one folder per class:

```
malimg/
├── Adialer.C/
│   ├── 000bde2e9a94ba41c0c111ffd80647c2.png
│   └── ...
├── Agent.FYI/
└── ...
```

torchvision's `ImageFolder` reads this layout. Each subfolder becomes a class, numbered in alphabetical order, and each image is loaded from disk and passed through the transform only when the `DataLoader` builds a batch that contains it:

```python
from torchvision.datasets import ImageFolder

dataset = ImageFolder("malimg/", transform=transform)
dataset.classes        # ['Adialer.C', 'Agent.FYI', ...]
dataset.class_to_idx   # {'Adialer.C': 0, 'Agent.FYI': 1, ...}
```

`dataset.classes` maps the network's output numbers back to family names, so it has to be saved with the model.

### Splitting into training, validation and test sets

The `split-folders` package copies the images into separate `train/`, `val/` and `test/` folders, splitting each class folder by the same ratio, so each family keeps its share in every set, as with a [stratified split](/collections/ai-security/ai-supervised-learning#stratified-splits):

```python
import splitfolders

splitfolders.ratio("malimg/", output="malimg_split/", seed=0, ratio=(0.7, 0.15, 0.15))
```

The three folders are then loaded with three `ImageFolder` calls. Without a validation share, there is no data left to compare settings or choose the number of epochs without using the test set.

The same split without copying files uses `train_test_split` on the sample indices and `Subset`:

```python
from sklearn.model_selection import train_test_split
from torch.utils.data import Subset

indices = list(range(len(dataset)))
train_idx, rest = train_test_split(indices, test_size=0.3, stratify=dataset.targets, random_state=0)
rest_labels = [dataset.targets[i] for i in rest]
val_idx, test_idx = train_test_split(rest, test_size=0.5, stratify=rest_labels, random_state=0)

train_set, val_set, test_set = Subset(dataset, train_idx), Subset(dataset, val_idx), Subset(dataset, test_idx)
```

Both are random splits, so variants of every family appear on both sides. The test score then measures how well the network recognizes new variants of families it has seen. A family that appears only after training is a different question, as described in [Splitting for Unseen Attacks](/collections/ai-security/ai-datasets#splitting-for-unseen-attacks).

### Imbalanced families

Malware datasets are usually imbalanced. In Malimg, `Allaple.A` has 2,949 of the 9,339 samples and `Skintrim.N` has 80, so a network that always predicts `Allaple.A` is right 32% of the time. Measure per-family recall and the macro average, as described in [Class Imbalance](/collections/ai-security/ai-supervised-learning#class-imbalance).

PyTorch's cross-entropy loss takes [class weights](/collections/ai-security/ai-supervised-learning#class-weights) through its `weight` argument, one weight per class in the order of `dataset.classes`:

```python
from collections import Counter
import torch

counts = Counter(dataset.targets[i] for i in train_idx)
n, k = len(train_idx), len(dataset.classes)
weights = torch.tensor([n / (k * counts[c]) for c in range(k)], dtype=torch.float)
criterion = nn.CrossEntropyLoss(weight=weights.to(device))
```
