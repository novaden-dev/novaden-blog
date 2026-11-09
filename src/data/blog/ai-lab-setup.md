---
title: "AI Lab Setup"
slug: ai-lab-setup
category: notes
format: guide
handbook: ai-security
tags: ["ai"]
draft: false
pubDatetime: 2026-11-09T00:00:00+03:00
description: "Building the Python environment the AI handbook runs on: Miniconda with conda-forge only, an isolated environment, the numerical and Hugging Face libraries, the PyTorch build for your GPU, the Intel GPU driver on Ubuntu, and starting JupyterLab."
---

The code in this handbook runs in one conda environment named `ai`. This guide builds it on Linux. The commands were run on Ubuntu 24.04 with an Intel Arc GPU, and the GPU-specific steps say what changes for NVIDIA or a CPU-only machine.

## What the Environment Needs

| Part | Why |
|---|---|
| An isolated Python 3.11 environment | The libraries and their versions stay separate from the system Python and from other projects. |
| numpy, scipy, pandas, scikit-learn, matplotlib, seaborn | Arrays, tables, plots and the classic models. |
| nltk (Natural Language Toolkit), category_encoders | Tokenizing, stop words and stemming for text, and encoders for categorical features. |
| Hugging Face libraries | Pretrained models and datasets. |
| PyTorch, built for your GPU | Neural networks. The scikit-learn work runs on the CPU and does not need it. |
| JupyterLab | The notebook interface the labs run in. |

The finished environment takes about 9 GB of disk, mostly PyTorch and its GPU runtime libraries.

## Installing and Configuring Miniconda

Miniconda is the minimal installer for conda: conda itself and Python, with no preinstalled packages. Download and run the installer:

```bash
curl -LO https://repo.anaconda.com/miniconda/Miniconda3-latest-Linux-x86_64.sh
bash Miniconda3-latest-Linux-x86_64.sh
```

Accept the offer to initialize conda in your shell, then open a new terminal.

Before installing anything, change three settings:

```bash
conda config --set auto_activate false
conda config --add channels conda-forge
conda config --remove channels defaults
conda config --set channel_priority strict
conda config --show channels      # should list only conda-forge
conda config --show solver        # should say libmamba
```

- **`auto_activate false`**: by default conda activates its `base` environment in every new shell, which puts conda's Python ahead of the system one in every terminal. With this off, a shell uses the system Python until you activate an environment. On older conda versions, the setting is named `auto_activate_base`.
- **conda-forge only**: a channel is a package source. `defaults` is Anaconda's channel and comes with Anaconda's licensing terms. With both channels configured, the solver has two separate builds of most packages to choose between, and installs get slower.
- **`channel_priority strict`**: conda takes each package from the highest-priority channel that has it, instead of mixing builds from several channels.

If `--remove channels defaults` prints an error, `defaults` was not in the list and nothing needs removing. If the solver is `classic`, switch it with `conda config --set solver libmamba`.

## Creating the Environment

```bash
conda create -n ai python=3.11
conda activate ai
```

`-n ai` names the environment. The shell prompt shows `(ai)` while it is active, and `conda deactivate` leaves it. Check for `(ai)` before every install command below, so nothing goes into `base`.

## Installing the Libraries

Install in this order. conda does not track packages that pip installed, so a later `conda install` can replace them with its own versions. Run conda first and pip after.

1. The numerical stack, from conda-forge:

   ```bash
   conda install -y numpy scipy pandas scikit-learn matplotlib seaborn nltk category_encoders
   ```

2. PyTorch, from PyTorch's own package index for your hardware:

   ```bash
   pip install torch torchvision torchaudio --index-url https://download.pytorch.org/whl/xpu
   ```

   | Hardware | Index URL |
   |---|---|
   | Intel GPU (Arc, Core Ultra) | `https://download.pytorch.org/whl/xpu` |
   | No usable GPU | `https://download.pytorch.org/whl/cpu` |
   | NVIDIA GPU | The `cu` index that the selector on [pytorch.org](https://pytorch.org/get-started/locally/) gives for your CUDA version |

3. The Hugging Face libraries and JupyterLab:

   ```bash
   pip install transformers datasets tokenizers accelerate evaluate optimum huggingface_hub requests
   pip install jupyterlab ipykernel
   ```

PyTorch goes in before the Hugging Face libraries because `accelerate` depends on PyTorch. If PyTorch is not installed yet, pip installs the default build from PyPI, which is the NVIDIA build plus about 2 GB of CUDA libraries. On a machine without an NVIDIA GPU, those libraries are never used, and you have to uninstall that build and install the right one.

The Hugging Face libraries come from pip. With them in the same `conda install` as the numerical stack, the solver ran for minutes without finishing, while pip installed them in seconds.

Run `pip check` at the end. It lists any package whose requirements are not met, and prints `No broken requirements found.` when everything fits.

## The Intel GPU Driver on Ubuntu

The XPU build of PyTorch needs Intel's compute runtime, which Ubuntu does not install by default. Ubuntu 24.04's own copy dates from 2023, and Intel's install guide for Ubuntu uses its graphics PPA instead:

```bash
sudo add-apt-repository -y ppa:kobuk-team/intel-graphics
sudo apt install -y libze-intel-gpu1 libze1
```

Without the driver, PyTorch still runs on the CPU. The [scikit-learn](/collections/ai-security/ai-tools#scikit-learn) work in this handbook does not need the GPU, so this step can wait until the first neural network.

With an NVIDIA GPU, the NVIDIA driver is needed instead. PyTorch's CUDA build includes the CUDA libraries it uses.

## Starting JupyterLab

Each session starts with activating the environment:

```bash
conda activate ai
cd ai-security-notebooks
jupyter lab
```

JupyterLab opens in the browser, and new notebooks run in the `ai` environment. If the shell prints `Command 'jupyter' not found`, the environment is not active: `jupyter` is installed inside `ai` and is on the PATH only after `conda activate ai`.

## Verifying the Setup

With the environment active, run:

```bash
python -c "
import numpy, pandas, sklearn, torch, transformers
print('pandas', pandas.__version__, '| scikit-learn', sklearn.__version__, '| torch', torch.__version__)
print('GPU:', torch.xpu.is_available())
"
```

```text
pandas 3.1.1 | scikit-learn 1.9.1 | torch 2.15.0+xpu
GPU: True
```

Every import has to succeed. On NVIDIA, replace `torch.xpu` with `torch.cuda`. `GPU: False` means PyTorch cannot reach the GPU, either because the driver is missing or because the CPU build was installed. The `+xpu` or `+cpu` suffix on the torch version shows which build is installed.

With that working, the environment is ready for [Jupyter, scikit-learn and PyTorch](/collections/ai-security/ai-tools) and the labs.
