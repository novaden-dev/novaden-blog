---
title: "Datasets and Preprocessing"
slug: ai-datasets
category: notes
handbook: ai-security
tags: ["ai"]
draft: false
pubDatetime: 2026-11-08T00:00:00+02:00
description: "What makes a dataset usable for machine learning, and the preprocessing steps that turn raw data into model input: cleaning, fixing types and formats, combining and aggregating sources, checking label mappings, encoding categories, scaling, reducing skew, splitting without leakage, and splitting for unseen attacks."
---

## Introduction

A model learns only what its training data contains. Raw data, such as a server log or a database export, is rarely ready for that. Values are missing or recorded in different formats, the information is spread across sources, and categories are stored as text. Preprocessing turns raw data into a table with one row per example, one numeric column per feature, and a label.

This note covers the concepts. [Labeling SSH Attackers](/collections/ai-security/ai-ssh-attackers) applies the ones a real SSH server log needed, step by step.

## What Makes a Dataset Good

The usual properties of a good dataset answer four questions.

**Does it fit the problem?**

| Property | Meaning |
|---|---|
| Relevance | The data carries the signal the model needs. Login attempts are relevant for detecting password attacks. Firewall logs that only show "port 22 allowed" are not |
| Representativeness | The data looks like what the model will see in production. A log from one server does not show the attacks aimed at a different kind of server |

**Is it correct?**

| Property | Meaning |
|---|---|
| Completeness | Few missing values or gaps in time |
| Consistency | The same thing is always recorded the same way, in the same format and time zone |
| Quality | The values are accurate |
| Label quality | The labels are accurate. A row can be recorded perfectly and still carry the wrong label |
| No leakage | No column gives the label away for a reason that will not hold in production |

**Is there enough of it?**

| Property | Meaning |
|---|---|
| Size | Enough examples to learn the pattern without memorizing them |
| Balance | Each class has enough examples. With 1 attacker per 1,000 sources, accuracy is useless as a metric (see [Supervised Learning](/collections/ai-security/ai-supervised-learning)) |

**Can it be trusted?**

| Property | Meaning |
|---|---|
| Timeliness | The data is recent. Attack tools change, and a detector trained on old attacks misses new ones. This is called drift |
| Provenance | It is known where the data came from and who could have changed it, and the license allows the use |

Preprocessing can fix consistency, some quality problems and some leakage. Relevance, representativeness, size and balance depend on how the data was collected, and cleaning cannot fix them afterwards.

## Cleaning

### Missing values

A missing value can be handled in four ways:

| Option | When it fits |
|---|---|
| Drop the row | Few rows are affected, and the gaps are random |
| Fill with a fixed value | The gap means something, such as "not recorded" |
| Fill with a statistic (mean, median, most common value) | A numeric gap where a typical value is a fair guess |
| Add a "was missing" column, then fill | The gap itself may be a signal |

Filling can hide a signal. If the missing values cluster on attack traffic, filling them with the median makes the attacks look average.

An empty cell is not always a missing value. In some formats, an empty field means "no" or "not applicable", and filling it would change its meaning.

### Duplicates

Duplicates appear when the same event is recorded twice, for example when two log collectors both forward it. If they stay in, that event counts twice. Drop exact copies of the same event, and deduplicate on a unique event ID where one exists, since two real events can look identical.

### Records that stand for several events

The opposite problem also happens. Logging systems often write a repeated message once, followed by a summary such as `message repeated 5 times`. Counting lines then undercounts events, and the data shows no gap or error. Before counting anything in a log, check whether some lines stand for more than one event. In the [SSH log](/collections/ai-security/ai-ssh-attackers#step-2-find-the-repeated-messages), summary lines hid 43% of all login attempts.

### Labels that match nothing

Labels often have to be mapped from detailed values to broader classes. [NSL-KDD](/collections/ai-security/ai-random-forests#introduction), a network intrusion dataset, labels each connection with one of 39 attack names, such as `neptune` or `httptunnel`, which are grouped into four attack classes. The mapping is written by hand, so it can miss names or misspell them.

A mapping that ends with a default, such as "anything not listed is normal", hides those mistakes: rows with a misspelled or forgotten attack name are labeled normal traffic, the model learns from wrong labels, and nothing reports an error. A dictionary with `.map` leaves unmatched values empty instead, so a check can catch them:

```python
attack_class = {
    "normal": 0,
    "neptune": 1, "smurf": 1,            # DoS
    "nmap": 2, "portsweep": 2,           # Probe
    "buffer_overflow": 3, "rootkit": 3,  # U2R
    "guess_passwd": 4, "httptunnel": 4,  # R2L
    # one entry for every attack name in the data
}
df["label"] = df["attack"].map(attack_class)

unmapped = df.loc[df["label"].isna(), "attack"].unique()
assert len(unmapped) == 0, f"no class for: {unmapped}"
```

Map only the values you expect, and make every other value an error, so new or misspelled values are found when the code runs. Copy the names from the data, for example from `df["attack"].unique()`, instead of typing them.

### Columns with one value

A column with the same value in every row carries no information. In NSL-KDD, `num_outbound_cmds` is 0 in all 148,517 rows of the training and test sets. `df.nunique()` counts the distinct values in each column, and columns where it is 1 can be dropped.

## Fixing Types and Formats

Data read from text files arrives as text, and each column has to be converted to the type it represents:

| Column holds | Convert to | So that |
|---|---|---|
| Counts or measurements | Numbers | They can be added, averaged and compared |
| Yes/no information | True/False | They can be counted and filtered |
| Timestamps | Date-times | They can be sorted, subtracted and grouped by hour or day |

Timestamps have two common problems. Some formats leave out the year or the time zone. A date parser that is not given a year fills in a default, often 1900, without a warning, and a log that crosses New Year then sorts January before December. Logs from different sources also have to be converted to one time zone, usually UTC, before they can be compared.

Values that mean the same thing have to be written the same way: `a` and `A` for the same DNS record type, or `US` and `United States` for the same country. Normalize them before counting or encoding.

## Combining and Aggregating

### Combining sources

One source rarely holds everything a model needs. A login detector might join its authentication log with a firewall log, a threat intelligence feed of known-bad IPs, or the list of employee accounts. pandas `merge` joins two tables on a shared column, such as the IP. The sources need the same time zone and the same format for that column before they can be joined.

### Aggregating to the right unit

Each row of the final dataset has to be one example of what the label describes. If the label says "this IP is attacking", the rows have to be IPs, while the raw data has one row per event. Aggregation groups the events by IP and summarizes each group into features, such as the number of attempts, the number of distinct usernames, and the time between the first and last attempt. In pandas, that is `groupby` followed by `agg`. The [SSH lab](/collections/ai-security/ai-ssh-attackers#step-5-one-row-per-ip) reduces 197,769 login events to 1,042 IP rows this way.

## Encoding Categorical Features

A model only does arithmetic, so a column of words has to become numbers first. Say each login attempt records the authentication method:

| attempt | method |
|---|---|
| 1 | password |
| 2 | publickey |
| 3 | password |
| 4 | keyboard-interactive |

There are four common ways to encode a column like this, and the right one depends on the column.

### One-hot

One-hot encoding (`OneHotEncoder` in scikit-learn) creates one yes/no column per value:

| attempt | method_password | method_publickey | method_keyboard |
|---|---|---|---|
| 1 | 1 | 0 | 0 |
| 2 | 0 | 1 | 0 |
| 3 | 1 | 0 | 0 |
| 4 | 0 | 0 | 1 |

Each row has a 1 in the column for its value. This works for any column with a few distinct values.

pandas has its own one-hot function, `pd.get_dummies`. It creates columns from the values present in the data it is given, so data with different values gets different columns: training data with `tcp` and `udp` gives `protocol_tcp` and `protocol_udp`, while a new batch containing only `icmp` gives a single `protocol_icmp` column, which the model has never seen. `OneHotEncoder` learns the columns during `fit` and produces the same columns for every later batch. With `handle_unknown="ignore"`, a value it never saw becomes all zeros. Use `get_dummies` to explore data, and `OneHotEncoder` for anything a model will be trained and used on.

### Ordinal

Ordinal encoding (`OrdinalEncoder`) replaces each value with a number: `password` = 0, `publickey` = 1, `keyboard-interactive` = 2. That takes one column instead of three, but it also tells a model that `publickey` sits between the other two methods and that `keyboard-interactive` is "more" than `password`. Models built on weighted sums treat that order as real. Use ordinal encoding only when the values have a real order, such as a severity of `low` = 0, `medium` = 1, `high` = 2.

`LabelEncoder` does the same for the label column: `benign` = 0, `attack` = 1.

### Hashing

The [SSH log](/collections/ai-security/ai-ssh-attackers) has 1,752 different usernames. One-hot encoding would create 1,752 columns, and a username that first appears tomorrow would have no column. Hashing (`HashingEncoder` from category_encoders) fixes the number of columns in advance, say 8. A hash function turns any text into a number, and that number picks one of the 8 columns. The column numbers below are an illustration:

| username | column |
|---|---|
| root | 3 |
| admin | 6 |
| curi | 3 |
| a username never seen before | one of the 8 |

`root` and `curi` landed in the same column here, so a model cannot tell them apart. That is a collision. More columns mean fewer collisions, at the cost of a wider table.

### Frequency

Frequency encoding replaces each value with how common it is. For usernames, that can be the number of different IPs that tried the name:

| username | IPs that tried it |
|---|---|
| root | 588 |
| admin | 440 |
| curi | 10 |

`root` and `admin` are guesses that hundreds of attackers make. `curi` is a real user, logging in from 10 addresses. One number carries the signal the model needs: a common guess, or a name only one person uses.

### Choosing an encoder

| The column has | Use |
|---|---|
| A few values, no order | One-hot |
| A few values, with a real order | Ordinal |
| Thousands of values | Hashing or frequency |
| The labels | Label encoding |

After encoding, check two things: ordinal numbers were only given to values with a real order, and the number of new columns is what you expected. One-hot encoding on a column with thousands of values silently creates thousands of columns.

## Scaling

Features can have very different ranges. In the [SSH data](/collections/ai-security/ai-ssh-attackers), `invalid_share` runs from 0 to 1 and `hours_active` from 0 to 678. Take three IPs:

| IP | invalid_share | hours_active |
|---|---|---|
| A | 0.0 | 10 |
| B | 1.0 | 12 |
| C | 0.0 | 200 |

A and B behave in opposite ways: A tries only usernames that exist, B only made-up ones. A and C behave the same way, over different lengths of time. A model that compares rows by the size of their differences sees the opposite. A and B differ by 1.0 on one feature and 2 on the other, while A and C differ by 190. The hours column outweighs the share column only because its numbers are larger. Scaling puts every feature on a comparable range first.

### Min-max normalization

Min-max normalization maps each feature to the range 0 to 1:

$$
x' = \frac{x - \min}{\max - \min}
$$

With a maximum of 678 hours, 10 becomes 0.015, 12 becomes 0.018 and 200 becomes 0.29. One extreme value sets the whole range: half the IPs were active for 0 hours, and an IP active for 1 hour becomes 0.001, so almost every value ends up crowded near 0.

### Standardization

Standardization measures each value as its distance from the mean, in standard deviations:

$$
x' = \frac{x - \text{mean}}{\text{std}}
$$

`hours_active` has a mean of 52.5 and a standard deviation of 141, so 10 becomes -0.30 and 200 becomes 1.04. `invalid_share` has a mean of 0.52 and a standard deviation of 0.45, so 0.0 becomes -1.17 and 1.0 becomes 1.08. A and B now differ by 2.25 on the share and almost nothing on hours, while A and C differ by 1.35 on hours. A ends up closer to C, which matches their behaviour. Standardization is the usual default. On a heavily skewed feature, apply a log transform first (see below), since extreme values still stretch the result.

### Which models need it

Models that compare rows by distance, such as k-nearest neighbours, and models trained step by step on weighted sums, such as logistic regression and neural networks, need scaled features. Decision trees do not. They ask one question about one feature at a time, such as "is `hours_active` above 50?", so the ranges of different features never compete.

## Skewed Data

A feature is skewed when most values are small and a few are very large. Counts in security data usually look like this: most sources make a few connections, and a handful make tens of thousands. In models built on weighted sums or distances, the largest values then set the scale, and the differences between small values, which often separate the classes, become too small to matter.

A log transform, $$\log(1 + x)$$, compresses large values much more than small ones:

| x | log(1 + x) |
|---|---|
| 1 | 0.69 |
| 6 | 1.95 |
| 20 | 3.04 |
| 1,000 | 6.91 |
| 86,294 | 11.37 |

The `1 +` keeps 0 defined, since $$\log 0$$ is not. In numpy this is `np.log1p`. pandas measures skew with `.skew()`: 0 is symmetric, and above 1 is strongly skewed. In the [SSH data](/collections/ai-security/ai-ssh-attackers#step-7-reduce-the-skew), the log transform brought the skew of login attempts per IP down from 19.1 to 2.1.

A skewed label is a different problem, called class imbalance. It is handled with the choice of metric, class weights or resampling, which belong to model training.

## Splitting Without Leakage

### Training and test sets

The model trains on one part of the data and is measured on the other, which it never sees during training. scikit-learn's `train_test_split` does this:

| Argument | Effect |
|---|---|
| `test_size=0.25` | A quarter of the rows go to the test set |
| `stratify=y` | Each class keeps the same share in both sets. With a rare class, a plain random split can leave the test set with almost none of it |
| `random_state=0` | Fixes the shuffle, so every run produces the same split |

`train_test_split` shuffles the rows before splitting (`shuffle=True` is the default). Datasets are often stored sorted, for example all positive reviews followed by all negative ones. Taking the last 20% of a sorted file as the test set, without shuffling, gives a test set of one class only. `df["label"].value_counts()` shows the real class counts, whatever the order of the rows.

Rows that belong together should stay on the same side. If one attacker's events end up in both sets, the model can learn to recognize that attacker instead of the attack pattern. Aggregating to one row per source before splitting avoids this. For data collected over time, training on the earlier part and testing on the later part is closer to how the model will be used.

### Leakage

Leakage is information in the training data that gives away the answer and will not be there in production. A model with leakage scores well in testing and fails in production. There are four common sources.

**A feature the label was made from.** If the labels say "benign" for every source with a successful login, and the success count is also a feature, the model reads the answer from that column. The [SSH lab](/collections/ai-security/ai-ssh-attackers#step-8-split-into-training-and-test-sets) leaves the success count out for this reason.

**A feature recorded after the event.** The ticket number of an incident only exists because an alert already fired. At prediction time it is not there yet.

**Preprocessing fitted on all the data.** The test set plays the role of a sealed exam: it measures the model on data it has never seen. A scaler is the tool that applies the [scaling](#scaling) above, such as scikit-learn's `StandardScaler` for standardization. Before it can scale anything, it calculates each feature's mean and standard deviation from the data it is given. That step is called fitting:

```python
scaler = StandardScaler().fit(X_train)    # mean and std from the training rows only
X_train_scaled = scaler.transform(X_train)
X_test_scaled = scaler.transform(X_test)  # the same mean and std, from training
```

Fitted on all the data before the split, the scaler calculates them partly from the test rows, and the training data is then transformed with information taken from the exam. The model never sees a test row directly, but its training data was shaped by them. For a plain scaler the effect on the score is usually small. It grows with steps that learn more from the data, such as choosing features based on all rows, filling missing values with averages over all rows, or creating synthetic copies of rare examples before splitting. The fix is the same for all of them: split first, fit every preprocessing step on the training set only, then apply it to the test set.

**Collection artifacts.** These are differences between the classes that come from how the data was recorded, unrelated to the behaviour the model should detect. A public [DNS exfiltration dataset](https://data.mendeley.com/datasets/v2cy9y58t7/2) shows two:

| Column | Benign rows | Exfiltration rows |
|---|---|---|
| Date recorded | 13 to 14 June | 20 August to 6 October |
| Source IP | 831 of the 832 source IPs appear in only one class | One IP sent 7,000 queries, all labeled malicious |

A model trained on it can score close to 100% by learning that August dates or certain IPs mean exfiltration, without learning anything about DNS tunneling. In production every day is a new date and attackers use new IPs. The dataset has no missing values and no duplicates, so the usual quality checks pass. The problem shows up only when the classes are compared column by column, for example with `pd.crosstab(df["src_ip"], df["label"])`.

### Splitting for unseen attacks

A random split usually puts rows of each attack type in both the training and the test set, so the test set contains almost only attack types the model has already seen. Real attackers also use techniques that were not in the training data.

NSL-KDD comes with an official training set and an official test set, and the test set contains 17 attack types that never appear in training. They make up 3,750 of its 22,544 rows. The same [random forest](/collections/ai-security/ai-random-forests) setup scores very differently depending on the split:

| Split | Accuracy | Macro F1 |
|---|---|---|
| Stratified 80/20 split of the official training set | 99.9% | 0.92 |
| Official training set, measured on the official test set | 74.8% | 0.51 |

On the official test set, the forest labels 82% of the connections from the unseen attack types as normal traffic. For attack types it did see in training, that share is 23%.

The test set has to contain the situation the model will face. To measure how a model handles new attack types, keep whole attack types out of training: scikit-learn's `GroupShuffleSplit` and `GroupKFold` split by a group column, such as the attack name, so all rows of a group go to the same side.

A classifier trained on labeled attacks recognizes those attacks and variations of them. Anomaly detection is the approach aimed at new ones: it learns only what normal traffic looks like, and flags anything that differs from it, whether or not that kind of attack was ever seen.

