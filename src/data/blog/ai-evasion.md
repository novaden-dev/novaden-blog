---
title: "Evasion Attacks"
slug: ai-evasion
category: notes
handbook: ai-security
tags: ["ai"]
draft: false
pubDatetime: 2026-11-20T00:00:00+03:00
description: "Evasion attacks that change an input at prediction time so a classifier gets it wrong, worked through the good words attack on a Naive Bayes spam filter: why added words outweigh spam words, ranking words with access to the model, finding them through an API with a query budget using epsilon-greedy and upper confidence bound search, and how to defend against it."
---

## Introduction

An evasion attack changes an input at prediction time so that the model gets it wrong. The model, its weights and its training data stay as they are. This separates evasion from the poisoning attacks in [Label Flipping](/collections/ai-security/ai-label-flipping) and [Clean Label Attacks](/collections/ai-security/ai-clean-label), which change the training data, and from the theft in [Model Reverse Engineering](/collections/ai-security/ai-model-reverse-engineering), which copies the model.

The attacker keeps whatever the input is meant to do: the spam still carries its link, the malware still runs, the fraudulent payment still moves money. Only the features the model sees change.

The example in this note is a spam filter built on Multinomial Naive Bayes, covered in [Naive Bayes](/collections/ai-security/ai-naive-bayes). The attack is to append ordinary words to a spam message until the filter calls it legitimate. It is called the **good words attack**, from "Good Word Attacks on Statistical Spam Filters" by Lowd and Meek (2005).

## Evasion Against a Classifier and Against an LLM

The same idea applies to a language model, with different inputs and outputs:

| | Classifier such as the spam filter | LLM |
|---|---|---|
| Input | Features, such as word counts | Free text, which the model also reads as instructions |
| Output | A class and usually a probability | Generated text, with no score the attacker can read |
| What the attacker changes | The words or values in the input | The wording of the prompt |
| How the search works | Rank features by their effect on the score | Try wordings by hand or with a tool, covered in [Jailbreaking](/collections/ai-security/ai-jailbreaking) and [garak, PyRIT and ART](/collections/ai-security/ai-llm-attack-tools) |

A classifier shows a number after every query, so the attacker can measure how much each change helps. An LLM shows only text, so the attacker has to judge each reply. Search methods that decide which changes to try next, such as the ones below, work on both.

## Why Added Words Outweigh Spam Words

Naive Bayes compares the two classes as odds of spam to ham. The odds start at the share of each class in the training data. Each word in the message then multiplies the odds by a number:

```text
multiplier for a word = how likely spam is to use the word ÷ how likely ham is to use it
```

A word that spam uses far more often than ham has a multiplier above 1 and pushes the odds toward spam. A word that ham uses more often has a multiplier below 1 and pushes them toward ham. The message is classified as spam while the odds are above 1, which is the point where the probability of spam is 50%.

The numbers below come from the SMS Spam Collection counts in [Naive Bayes](/collections/ai-security/ai-naive-bayes#multinomial-naive-bayes), with additive smoothing at $$\alpha = 1$$ (one extra count added to every word, so no word has probability zero) and a vocabulary of 7,101 words. Of 5,169 messages, 653 are spam, so the starting odds are 653 spam to 4,516 ham, which is 0.145 to 1.

| Word | Count in spam | Count in ham | Multiplier |
|---|---|---|---|
| free | 190 | 55 | 8.9 |
| claim | 98 | 0 | 258.9 |
| ok | 5 | 247 | 0.0633 |
| lunch | 0 | 38 | 0.0671 |
| love | 10 | 218 | 0.131 |

Start with the message `free claim` and append the ham words one at a time:

| Message | Spam odds | Probability of spam |
|---|---|---|
| `free claim` | 0.145 × 8.9 × 258.9 ≈ 334 | 99.7% |
| `free claim ok` | 334 × 0.0633 ≈ 21.1 | 95.5% |
| `free claim ok lunch` | 21.1 × 0.0671 ≈ 1.42 | 58.6% |
| `free claim ok lunch love` | 1.42 × 0.131 ≈ 0.19 | 15.7% |

Three ordinary words move the message from 99.7% spam to 15.7%. The spam words are still in the message, and nothing the attacker added removed their effect. Each word only multiplies the odds by its own number, and the model has no way to see that the added words are unrelated to the rest of the message. The independence assumption in [The Naive Assumption](/collections/ai-security/ai-naive-bayes#the-naive-assumption) is the reason.

The filter only checks which side of 1 the odds fall on. A message that ends at 0.9 odds (about 47% spam) passes the same as one at 0.01.

Multinomial Naive Bayes scores word counts, so a word that appears three times multiplies the odds three times. `free claim ok ok ok` ends at odds of 0.085, about 8% spam, with one added word repeated. Bernoulli Naive Bayes only records whether a word is present, so it counts a repeated word once and repeating stops helping.

## Ranking Words with Access to the Model

With access to the model, the attacker can read each word's multiplier directly. scikit-learn's `MultinomialNB` stores the logarithm of each word's probability for each class in `feature_log_prob_`. The ranking takes them back out of the log and divides:

```python
import numpy as np

# One column per word in the vectorizer's vocabulary
words = vectorizer.get_feature_names_out()

# model.classes_ is ['ham', 'spam'], so row 0 is ham and row 1 is spam
# np.exp undoes the logarithm, which gives the probability of each word in a class
ham_prob = np.exp(model.feature_log_prob_[0])
spam_prob = np.exp(model.feature_log_prob_[1])

# How many times likelier each word is in ham than in spam.
# MultinomialNB adds alpha (1 by default) to every word count before computing
# these probabilities (additive smoothing), so even a word never seen in spam
# has a spam probability above zero and the division is safe
ratio = ham_prob / spam_prob

# argsort lists word positions from smallest ratio to largest, [::-1] reverses that
order = np.argsort(ratio)[::-1]
good_words = [words[i] for i in order[:20]]
```

The multipliers multiply, so among different words, the fewest that push the odds under 1 are the ones with the largest ratios, taken from the top of the list until the odds fall below 1. No search is needed. If repeats are allowed, repeating the top word needs even fewer added words, because no other word lowers the odds as much per copy.

Testing a message means appending the first `k` words and checking which class wins:

```python
def evades(message, extra_words):
    # Append the chosen words to the end of the message
    augmented = message + " " + " ".join(extra_words)
    # predict_proba returns [ham probability, spam probability]
    probs = model.predict_proba(vectorizer.transform([augmented]))[0]
    # The message evades when ham is more likely than spam
    return probs[0] > probs[1]

# Smallest number of words that makes this message evade
for k in range(len(good_words) + 1):
    if evades(spam_message, good_words[:k]):
        print(k)
        break
```

## Ranking Words Through an API

An attacker usually has only the public interface: they send a message and read the answer. The word probabilities are not visible, so the ranking above is not available. Every query also has a cost. Services limit requests per account, log them, and bill for them, and a long run of near-identical messages stands out in those logs (see [Model Reverse Engineering](/collections/ai-security/ai-model-reverse-engineering#remediation)).

There are two ways to get a ranking:

- **Build a replica**: train a copy of the model on its answers, as in [Model Reverse Engineering](/collections/ai-security/ai-model-reverse-engineering), rank the words on the copy with the code above, and send only the best candidates to the real model.
- **Measure each word on the target**: append a candidate word to a spam message and record how far the spam probability drops. A larger drop means a better word.

The second way needs a list of candidates. Any collection of ordinary text works, since the attacker is looking for words that normal conversation uses and spam does not, such as `later`, `home` or `thanks`. The training data is not needed.

One measurement is two queries, the probability before and the probability after. The probability before only needs to be asked once per message and can be saved, which brings the cost down to about one query per measurement.

```python
def query_spam_prob(message):
    # Stands in for one request to the target's API.
    # Column 1 of predict_proba is the probability of spam
    return model.predict_proba(vectorizer.transform([message]))[0][1]

# Each message's own spam probability, saved after the first request
saved = {}

def impact(word, message):
    # Ask for the message's own probability only the first time it is used
    if message not in saved:
        saved[message] = query_spam_prob(message)
    # One request: how much appending the word lowers the spam probability
    return saved[message] - query_spam_prob(message + " " + word)
```

Measuring the drop in probability breaks when the filter is sure. A message the filter scores at 0.99999 spam leaves so little room below 1 that one word's effect on the probability is smaller than the precision the number is stored in, so every word measures as a drop of zero even though each one is helping. The fix is to measure on the odds instead. The log-odds, $$\log \frac{p}{1 - p}$$, move by a roughly constant amount per word however sure the filter is, for the same reason each word multiplies the odds by a fixed number in [Why Added Words Outweigh Spam Words](#why-added-words-outweigh-spam-words). A filter that returns a probability for each class makes this exact, since the log-odds are the difference of the two logs:

```python
import math

def query_probs(message):
    # One request to the target, returning a probability for each class,
    # e.g. {"spam": 0.98, "ham": 0.02}
    p = model.predict_proba(vectorizer.transform([message]))[0]
    return {"ham": p[0], "spam": p[1]}

def impact_logodds(word, message):
    before = query_probs(message)
    after = query_probs(message + " " + word)
    # log-odds of spam, before and after; the rise is the word's effect
    lo_before = math.log(before["spam"]) - math.log(before["ham"])
    lo_after = math.log(after["spam"]) - math.log(after["ham"])
    return lo_before - lo_after             # bigger drop in log-odds = better word
```

If the service returns only a label and no probability, there is no score to measure at all. The attacker counts instead how many of a set of spam messages each word turns into ham, which is a coarser signal and needs more queries per word.

## Searching with a Query Budget

With a vocabulary of a few hundred candidate words and a limit of a few hundred queries, the attacker cannot test every word on every message. The problem has a standard form called the **multi-armed bandit**: a row of slot machines (arms), each with an unknown average payout, and a fixed number of pulls. Each candidate word is an arm. Testing it on a spam message is a pull, and the payout is the drop in spam probability. The payout varies from message to message, so a single test is a noisy estimate.

Before each pull, the search chooses between two things:

- **Exploring**: test a word that has been tried few times or never, in case it is better than the current best.
- **Exploiting**: test the word that has looked best so far, to confirm it and collect its result.

A search that only explores spends most of its queries on bad words. A search that only exploits can keep testing a word that looked good by luck on one message and never try the better ones. The strategies below mix the two.

### Epsilon-greedy

Epsilon-greedy decides before each test whether to explore or exploit, at random. A setting called epsilon ($$\varepsilon$$) is the share of tests that explore. With $$\varepsilon = 0.1$$, about 1 test in 10 goes to a random word from the candidate list, and the other 9 go to the word with the best score so far. Over 100 tests, that is about 10 random words and 90 tests of the current best.

In the code, `random.random()` returns a random number between 0 and 1. It is below 0.1 about 10% of the time, which is when the search explores.

```python
import random

def pick_word(scores, candidates, epsilon=0.1):
    # scores: word -> score so far, for every word tested at least once
    # Explore on a share of pulls, and on the first pull, when no word has a score yet
    if not scores or random.random() < epsilon:
        return random.choice(candidates)
    # Exploit: the word with the highest score so far
    return max(scores, key=scores.get)
```

Early on, the best word is whichever word happened to be tested first, and exploiting keeps testing it until exploring finds a better one. A random pick can also land on a word that was already tested many times, while some candidates are never tested at all. And a fixed 10% of pulls still goes to exploring late in the search, when the best words are already clear. UCB, below, avoids all three.

### Upper confidence bound

Upper confidence bound (UCB) replaces the random exploring with a bonus. Each word gets a score made of its plain average impact plus a bonus that is large for words tested only a few times and shrinks as a word is tested more:

```text
UCB score = average impact + c × sqrt(ln(total tests) ÷ tests of this word)
```

`c` sets how much the bonus counts, `sqrt` is the square root, and `ln` is the natural logarithm, which grows slowly. The next pull goes to the word with the highest UCB score. A word with a high average wins, and so does a word with a mediocre average that has barely been tested. As the number of tests on a word grows, its bonus falls and the word is ranked mostly by its average.

With $$c = 0.1$$ and 60 tests in total, two words compare like this. The counts and averages are made up to show the effect:

| Word | Average impact | Tests | Bonus | UCB score |
|---|---|---|---|---|
| A | 0.10 | 40 | 0.1 × sqrt(4.09 ÷ 40) = 0.032 | 0.132 |
| B | 0.08 | 5 | 0.1 × sqrt(4.09 ÷ 5) = 0.090 | 0.170 |

Word A has the better average, but B is chosen next because only 5 tests back its average. If B's next results are poor, its average falls, its bonus shrinks and A takes the lead again.

```python
import math

def ucb_pick(averages, tests, candidates, c=0.1):
    # averages: word -> plain average impact, tests: word -> how many times it was tested
    # Test every word once first, so each has an average to compare
    untested = [w for w in candidates if w not in tests]
    if untested:
        return random.choice(untested)
    total = sum(tests.values())
    # Highest average plus bonus wins
    return max(candidates,
               key=lambda w: averages[w] + c * math.sqrt(math.log(total) / tests[w]))
```

UCB is defined on the plain average, where every test counts the same. The running score in the next section weights recent tests more, and suits epsilon-greedy.

### Keeping a running score

A word's payout depends on the message it is tested on, so each word needs a score that settles as results come in. A running score that gives recent results more weight is called an **exponential moving average**:

```text
new score = 0.6 × old score + 0.4 × latest impact
```

The first result is used as it is, since there is no old score to blend it with. Take a word that has almost no effect for four tests, after which the filter is retrained and its impact jumps to 0.20. The impacts are made up to show the effect:

| Test | Impact | Score after the test |
|---|---|---|
| 1 to 4 | 0.02 each | 0.02 |
| 5 | 0.20 | 0.6 × 0.02 + 0.4 × 0.20 = 0.092 |
| 6 | 0.20 | 0.6 × 0.092 + 0.4 × 0.20 = 0.135 |

A plain average of the same six results is 0.08, and it keeps counting the four old tests as much as the two new ones. The moving average gives each older test less weight, so it moves toward 0.20 faster. The 0.4 is a setting: a larger value follows new results faster and is noisier.

```python
def update_score(scores, word, drop, alpha=0.4):
    if word not in scores:
        # First result for this word: there is no old score to blend it with
        scores[word] = drop
    else:
        # Blend the new result into the running score
        scores[word] = (1 - alpha) * scores[word] + alpha * drop

# One test: measure the word on a message, then update its score
update_score(scores, word, impact(word, message))
```

### Splitting the budget

The budget can also be split into phases, each with its own share of the queries. One possible split:

| Phase | What it does | Share in this example |
|---|---|---|
| Exploration | Tests many words on many messages to find which ones have an effect | 40% |
| Exploitation | Tests only the words that scored best, to confirm their scores | 40% |
| Combination | Tests small sets of top words together | 20% |

For a budget of 500 queries that is 200, 200 and 100. The shares are a choice: a search that finds strong words early can move queries from exploration to exploitation.

Combinations are tested because words do not always add up. In Naive Bayes they add up on the odds: a pair multiplies the odds by both words' numbers. Measured as a drop in probability, the same word looks weaker on a message that is already low, because the probability cannot fall below 0. A word that takes one message from 99% spam to 60% takes a message at 10% down to 0.2%: a drop of 39 points on the first and under 10 on the second, from the same multiplier. In a neural network or an ensemble, words can also interact, so a pair can help more or less than its two words suggest. The **synergy** of a pair compares its measured effect with the effect expected from the two words separately. Comparing them on the odds removes the 0 to 100% limit, and a positive synergy means the pair works better together.

The final list is the words ranked by score, with the best combinations added where synergy was positive. The attacker appends the first few to the spam message and sends it.

## Remediation

The attack works because the model scores each word on its own and adds the results, and because it gives the attacker a probability to measure. The defenses either change how the message is scored or limit what the attacker learns from each query.

- Add features that appended words cannot change, such as sender reputation, SPF and DKIM results, the reputation of linked domains and the sending history of the account.
- Train on evasion attempts. Append good words to known spam, keep the label as spam, and add those messages to the training set so the model learns that a block of unrelated words does not make a message legitimate.
- Combine the model with one that does not add up independent word scores, such as a tree-based model, and flag messages where the two disagree.
- Flag a block of unrelated common words at the end of a message. The words are statistically unlike the text before them, which a language model or a simple check on how common the words are will pick up.
- Return only the label, without the probability, and round or add noise to any score that has to be returned. This gives the attacker a coarser signal and costs them more queries per word.
- Limit queries per account and watch for the search pattern: many messages that share the same start and differ by a few appended words.
