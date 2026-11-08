---
title: "Labeling SSH Attackers"
slug: ai-ssh-attackers
category: notes
handbook: ai-security
tags: ["ai"]
draft: false
pubDatetime: 2026-11-08T00:00:00+02:00
description: "A hands-on pass with pandas that turns a real SSH server log into a labeled dataset of brute force, password spraying and probing: reading the raw log, parsing it, fixing types, aggregating per IP, labeling with rules, reducing skew and splitting."
---

## Introduction

This note applies the concepts from [Datasets and Preprocessing](/collections/ai-security/ai-datasets) to real data: an SSH server log, turned into a labeled dataset of login attackers. It includes only the steps this data needed.

## The Dataset

The data is the OpenSSH log from [Loghub 2.0](https://zenodo.org/records/8275861), a public collection of system logs released under CC BY 4.0. It comes from a lab server that was reachable from the internet for about four weeks, from 10 December to 7 January. Its SSH port received constant password attacks, and a handful of real users also logged in to it. The log has no labels: nothing marks which sources are attackers, so labeling is part of the work. The per-IP features and labels below were made for this note.

The goal is a table with one row per source IP, a few numeric features describing its behaviour, and a label: benign (a real user), brute force, password spraying, or probe.

The steps run in a Jupyter notebook, in the environment described in [Jupyter, scikit-learn and PyTorch](/collections/ai-security/ai-tools). To get the data:

```bash
mkdir -p ai-security-notebooks/data && cd ai-security-notebooks
curl -L -o data/OpenSSH.zip "https://zenodo.org/api/records/8275861/files/OpenSSH.zip/content"
unzip data/OpenSSH.zip -d data/
```

The archive contains the raw log, `OpenSSH_full.log` (70 MB), plus two CSV files with Loghub's own parsing of it. The steps below parse the raw log directly.

## Step 1: Read the Raw Log

Look at the raw data before loading it into anything:

```python
from pathlib import Path

lines = Path("data/OpenSSH/OpenSSH_full.log").read_text(errors="replace").splitlines()
print(len(lines))
for line in lines[:15]:
    print(line)
```

Python decodes the file as UTF-8 and stops with an error at the first invalid byte. Logs that record attacker input can contain such bytes. With `errors="replace"`, Python puts a `�` in place of the invalid byte and continues reading.

The file has 638,947 lines. Each one has the same layout:

```
Dec 10 06:55:46   LabSZ   sshd[24200]:   Invalid user webmaster from 173.234.31.186
└─ timestamp ─┘   host    process ID     message
```

sshd starts one process per connection, so lines with the same process ID belong to the same connection. The first six lines are one connection, trying the username `webmaster`:

```
sshd[24200]: reverse mapping checking getaddrinfo for ns.marryaldkfaczcz.com [173.234.31.186] failed - POSSIBLE BREAK-IN ATTEMPT!
sshd[24200]: Invalid user webmaster from 173.234.31.186
sshd[24200]: input_userauth_request: invalid user webmaster [preauth]
sshd[24200]: pam_unix(sshd:auth): check pass; user unknown
sshd[24200]: Failed password for invalid user webmaster from 173.234.31.186 port 38926 ssh2
sshd[24200]: Connection closed by 173.234.31.186 [preauth]
```

To see which kinds of messages the file holds, count them by their first three words:

```python
from collections import Counter

messages = [line.split(": ", 1)[1] for line in lines if ": " in line]
kinds = Counter(" ".join(m.split()[:3]) for m in messages)
for kind, count in kinds.most_common(15):
    print(count, kind)
```

```
160620 Failed password for
140701 pam_unix(sshd:auth): authentication failure;
 68958 Connection closed by
 47563 Received disconnect from
 37963 PAM service(sshd) ignoring
 37298 Disconnecting: Too many
 36443 message repeated 5
 ...
```

This works on most syslog-style files without knowing their content in advance. `Failed password for` is the line to count attempts with. Two other lines come back later: `message repeated` and `Disconnecting: Too many`.

## Step 2: Find the Repeated Messages

```python
for i, line in enumerate(lines):
    if "message repeated" in line:
        print("\n".join(lines[i-2:i+1]))
        break
```

The loop finds the first `message repeated` line and prints it with the two lines before it:

```
sshd[24227]: pam_unix(sshd:auth): authentication failure; ... user=root
sshd[24227]: Failed password for root from 5.36.59.76 port 42393 ssh2
sshd[24227]: message repeated 5 times: [ Failed password for root from 5.36.59.76 port 42393 ssh2]
```

The logging system writes an identical message once, then a summary line instead of the copies. This connection tried 6 passwords for `root`: the logged attempt plus 5 more. Counting only `Failed password` lines would miss every attempt hidden in the summaries, and nothing in the data would point to the error. Summary lines hide 147,044 attempts here, 43% of the total (see [records that stand for several events](/collections/ai-security/ai-datasets#records-that-stand-for-several-events)).

## Step 3: Parse the Lines into a Table

pandas holds data as a DataFrame, a table with named columns and one type per column. Most pandas code names that variable `df`. A regular expression pulls the fields out of each login line:

```python
import re
import pandas as pd

pattern = re.compile(
    r"^(?P<ts>\w{3}\s+\d+ [\d:]{8}) \S+ sshd\[(?P<pid>\d+)\]: "
    r"(?:message repeated (?P<repeat>\d+) times: \[ )?"
    r"(?P<result>Failed|Accepted) password for (?P<invalid>invalid user )?(?P<user>.*?) "
    r"from (?P<ip>[\d.]+) port"
)

rows = [m.groupdict() for line in lines if (m := pattern.match(line))]
df = pd.DataFrame(rows)
```

Each `(?P<name>...)` group becomes a column:

| Part | Matches | Example |
|---|---|---|
| `(?P<ts>\w{3}\s+\d+ [\d:]{8})` | Month, day and time | `Dec 10 07:13:43` |
| `sshd\[(?P<pid>\d+)\]` | Process ID | `24227` |
| `(?:message repeated (?P<repeat>\d+) times: \[ )?` | The optional summary wrapper | `5` |
| `(?P<result>Failed\|Accepted)` | Outcome | `Failed` |
| `(?P<invalid>invalid user )?` | Present only when the account does not exist | `invalid user ` |
| `(?P<user>.*?)` | Username | `root` |
| `(?P<ip>[\d.]+)` | Source IP | `5.36.59.76` |

The username uses `.*?` (any characters, as few as possible) instead of `\S+` (no spaces), because attackers put unusual values there. One tried `" 0101"`, with a leading space.

`m.groupdict()` turns each match into a dictionary such as `{"ts": "Dec 10 07:13:43", "pid": "24227", "user": "root", ...}`, and `pd.DataFrame(rows)` lines the dictionaries up into a table. Lines that do not match, such as `Connection closed`, are skipped. The result has 197,769 rows:

| ts | pid | repeat | result | invalid | user | ip |
|---|---|---|---|---|---|---|
| Dec 10 06:55:48 | 24200 | NaN | Failed | invalid user | webmaster | 173.234.31.186 |
| Dec 10 07:07:45 | 24206 | NaN | Failed | invalid user | test9 | 52.80.34.196 |
| Dec 10 07:13:43 | 24227 | NaN | Failed | NaN | root | 5.36.59.76 |

`NaN` ("not a number") is how pandas marks an empty value. The first two rows try usernames that do not exist. The third tries `root`, which does exist.

## Step 4: Fix the Types

Every value a regex extracts is text. Two columns need to become something a program can count:

```python
df["attempts"] = pd.to_numeric(df["repeat"]).fillna(1).astype(int)
df["invalid"] = df["invalid"].notna()
```

- **`attempts`**: `pd.to_numeric` turns `"5"` into 5, `fillna(1)` fills the empty values of normal lines with 1, and `astype(int)` makes them whole numbers. A normal line is 1 attempt, and a summary line is the number it states.
- **`invalid`**: `notna()` gives `True` where the text `invalid user ` was and `False` where the cell was empty.

The conversion has to come before the fill. Filling the text column with the number 1 first mixes text and numbers in one column, which pandas currently allows with a warning and a future version will refuse.

The totals show what the summary lines were hiding: 197,769 rows but **344,813 attempts**, 75% more. 182 of them succeeded.

The timestamps are text too. Syslog timestamps have no year, and pandas needs one to build a date. Given none, it uses 1900 without saying so. Adding a year explicitly at least makes the choice visible:

```python
df["pid"] = df["pid"].astype(int)
df["ts"] = pd.to_datetime("2015 " + df["ts"], format="%Y %b %d %H:%M:%S")
df = df.drop(columns="repeat")
```

The real year is unknown, and 2015 is a placeholder. Only the order of events and the time between them matter here, and those come out the same with any year. The `format` string spells out how to read the text: `%Y` year, `%b` short month name, `%d` day, `%H:%M:%S` time.

Giving every row the same year breaks the data at New Year. Sorted by time, the log ends on 31 December, and the January rows sit at the start:

```python
df[df["ts"].dt.month == 1]["ts"].agg(["min", "max"])
# min   2015-01-01 00:12:30
# max   2015-01-07 17:22:01
```

They were given 2015 too, which puts them eleven months before December instead of a week after it. Sorting, time gaps and any split by date would all be wrong, with no error. The fix moves them to the next year:

```python
df.loc[df["ts"].dt.month == 1, "ts"] += pd.DateOffset(years=1)
df = df.sort_values("ts").reset_index(drop=True)
# min   2015-12-10 06:55:48
# max   2016-01-07 17:22:01
```

Checking for month 1 works because this log covers only December and January. For a longer log, the general rule is to add a year wherever the month drops from one line to the next, since the file is in time order.

## Re-running Cells

Both cells above change `df` in a way that breaks if they run twice. Run the `invalid` line a second time and every value turns `True`, because `True` and `False` are both "not empty". Run the year fix twice and January moves to 2017. A notebook remembers the result of every cell that has run, so running a cell again after editing it can silently corrupt the data.

While preparing this note, the `invalid` cell ran twice by accident, and every IP later showed 100% invalid usernames. **Kernel → Restart Kernel and Run All Cells** reran everything once from the top and fixed it. The run counter next to each cell, such as `[7]`, shows the order cells ran in. A gap means something ran in between.

## Step 5: One Row per IP

Each label describes a source IP. "This IP is brute-forcing" is something a detector can act on, while one failed password on its own says nothing. `groupby` collects all rows from the same IP, and `agg` reduces each group to one row:

```python
df["invalid_attempts"] = df["attempts"] * df["invalid"]
df["success"] = df["result"] == "Accepted"

per_ip = df.groupby("ip").agg(
    attempts=("attempts", "sum"),
    users=("user", "nunique"),
    invalid_attempts=("invalid_attempts", "sum"),
    successes=("success", "sum"),
    first_seen=("ts", "min"),
    last_seen=("ts", "max"),
)
per_ip["invalid_share"] = (per_ip["invalid_attempts"] / per_ip["attempts"]).round(2)
per_ip["hours_active"] = ((per_ip["last_seen"] - per_ip["first_seen"]).dt.total_seconds() / 3600).round(1)
per_ip = per_ip.drop(columns=["invalid_attempts", "first_seen", "last_seen"])
```

In arithmetic, `True` counts as 1 and `False` as 0, so `invalid_attempts` counts only the attempts on invalid usernames, and summing `success` counts the logins. Each `new_column=(old_column, function)` line in `agg` defines one feature:

| Feature | Computed as | What it shows |
|---|---|---|
| `attempts` | Total attempts | Volume. Brute force is high |
| `users` | Number of distinct usernames | Spraying is high, brute force is low |
| `successes` | Successful logins | Real users log in |
| `invalid_share` | Share of attempts on usernames that do not exist | Guessing usernames, as in enumeration |
| `hours_active` | Time between first and last attempt | A one-off scan, or a campaign over days |

The result is 1,042 rows, one per IP, and 5 feature columns. pandas uses the IP as the row label, called the index. Two extremes:

| ip | attempts | users | successes | invalid_share | hours_active |
|---|---|---|---|---|---|
| 59.63.188.30 | 86,294 | 1 | 0 | 0.0 | 50.3 |
| 119.137.63.195 | 14 | 1 | 14 | 0.0 | 112.2 |

The first tried one existing account 86,294 times over two days. Before the summary lines were counted, it showed 14,384. The second logged in 14 times out of 14 over five days, the pattern of a person using their own account. All 42 IPs with successful logins look like the second: few attempts, one real username, most attempts succeeding, activity spread over days. They use 9 accounts between them, and no attacker ever tried one of those 9 usernames. The attackers guessed generic names such as `root`, `admin` and `pi`.

## Step 6: Label with Rules

With no labels in the data, the labels come from rules written after looking at it. `np.select` from numpy takes a list of conditions and a list of labels, and gives each row the label of the first condition it matches. The first version:

```python
import numpy as np

rules = [
    per_ip["successes"] > 0,                                # logged in: a real user
    per_ip["users"] >= 5,                                   # many usernames: spraying
    (per_ip["users"] <= 2) & (per_ip["attempts"] >= 20),    # one or two accounts, many tries: brute force
    per_ip["attempts"] <= 5,                                # a handful of tries: a probe
]
labels = ["benign", "spray", "brute_force", "probe"]
per_ip["label"] = np.select(rules, labels, default="unclear")
```

487 of the 1,042 IPs matched no rule. Their summary showed the reason:

| | attempts |
|---|---|
| 25% | 6 |
| 50% | 6 |
| 75% | 6 |

Most of them made exactly 6 attempts. OpenSSH allows 6 password tries per connection by default (the `MaxAuthTries` setting), then logs `Disconnecting: Too many authentication failures` and closes the connection. The 37,298 lines of that message in Step 1 are connections that hit the limit. These IPs connected once, used all 6 tries, and never returned. That is what a single pass by an automated scanner looks like. The probe threshold of 5 was a guess, and the server's own limit gives the right value.

With the probe rule at 6, 119 IPs were still unlabeled. None of them looked like real users: no successful logins, and mostly made-up usernames. They fell into gaps between the rules:

| Gap | Example | Why no rule matched |
|---|---|---|
| 3 or 4 usernames | 60 attempts on 3 usernames over 8 days | Too few usernames for spraying, too many for brute force |
| 7 to 19 attempts | 12 attempts on 1 username | More than one connection, below the brute force threshold |

Separating attackers from real users was easy, and rule 1 alone did it. Telling the attack types apart was harder, because the boundary between brute force on a few accounts and spraying a few usernames is a choice with no natural line in the data. The final rules make that choice explicit:

```python
rules = [
    per_ip["successes"] > 0,     # logged in: a real user
    per_ip["users"] >= 5,        # 5+ usernames: spraying or enumeration
    per_ip["attempts"] <= 6,     # one connection's worth: a probe
    per_ip["attempts"] > 6,      # more than one connection, 1 to 4 usernames: brute force
]
labels = ["benign", "spray", "probe", "brute_force"]

per_ip["label"] = np.select(rules, labels, default="unclear")
per_ip["is_attack"] = (per_ip["label"] != "benign").astype(int)
```

| label | IPs |
|---|---|
| probe | 658 |
| brute_force | 188 |
| spray | 154 |
| benign | 42 |

`is_attack` is a second label with two classes: 1 for every attack type and 0 for benign, the format models expect. It is the label to train on first, since blocking an IP does not depend on the type of attack. The split is 1,000 attackers to 42 real users. A model that answered "attack" every time would be 96% accurate and would block every real user.

`default="unclear"` stays as a check. Every IP now matches a rule, so an `unclear` appearing later means the data has changed in a way the rules do not cover.

Save the result, so the next session can start from the table instead of the raw log:

```python
per_ip.to_csv("data/ssh_per_ip.csv")
```

## Step 7: Reduce the Skew

`attempts` is heavily [skewed](/collections/ai-security/ai-datasets#skewed-data): its median is 6 and its mean is 331, and the top 10 IPs, 1% of the total, made 75% of all attempts. Next to 86,294, the difference between 6 attempts and 20 disappears for a model built on weighted sums, even though it separates a probe from a brute force. After a log transform, 6 becomes 1.95, 20 becomes 3.04 and 86,294 becomes 11.37. Applied to the three count-like features:

```python
skewed = ["attempts", "users", "hours_active"]
print(per_ip[skewed].skew().round(1))

per_ip[[f"log_{c}" for c in skewed]] = np.log1p(per_ip[skewed])
print(per_ip[[f"log_{c}" for c in skewed]].skew().round(1))
```

| Feature | Skew before | Skew after |
|---|---|---|
| attempts | 19.1 | 2.1 |
| users | 7.4 | 2.4 |
| hours_active | 3.0 | 1.6 |

The transformed columns are still skewed, but the largest values no longer set the scale. `invalid_share` is left as it is, because it already runs from 0 to 1. The original columns stay in the table for reading.

## Step 8: Split into Training and Test Sets

Before [splitting](/collections/ai-security/ai-datasets#splitting-without-leakage), choose the columns the model gets:

```python
from sklearn.model_selection import train_test_split

features = ["log_attempts", "log_users", "log_hours_active", "invalid_share"]
X = per_ip[features]
y = per_ip["is_attack"]

X_train, X_test, y_train, y_test = train_test_split(
    X, y, test_size=0.25, stratify=y, random_state=0
)
```

`X` holds the features and `y` the label. Two columns are left out on purpose:

- **`successes`**: the label was made from it. Rule 1 says that any IP with a successful login is benign, so a model given this column scores 100% by copying the answer from it. That is [leakage](/collections/ai-security/ai-datasets#leakage).
- **`label`**: it is the answer, in text form.

A quarter of the IPs go to the test set. With only 42 benign IPs, `stratify=y` is needed: without it, the test set got 7 benign IPs with one random seed and 13 with another. With it:

| Set | IPs | Attackers | Benign |
|---|---|---|---|
| Training | 781 | 750 | 31 |
| Test | 261 | 250 | 11 |

Both sets keep the dataset's 4% of real users.

## What These Labels Can and Cannot Show

The labels come from rules on the same features the model trains on. A model trained on them mostly learns the rules back, so a high test score only shows that it copied them. These rule-made labels work as practice data for preprocessing and training. Measuring a real detector needs labels from an independent source, such as attacks run against the server on purpose, or IPs confirmed by incident response.

Anyone who knows the rules can also avoid them. An attacker spreading a brute force across thousands of IPs, each making at most 6 attempts, ends up with every IP labeled a probe, and the pattern only shows across IPs.
