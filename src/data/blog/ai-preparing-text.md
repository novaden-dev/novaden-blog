---
title: "Preparing Text"
slug: ai-preparing-text
category: notes
handbook: ai-security
tags: ["ai"]
draft: false
pubDatetime: 2026-11-09T00:00:00+03:00
description: "Turning raw text into numeric features: finding what to clean, regex cleanup, HTML tags and accents, tokenization, stop words and negations, stemming and lemmatization, bag of words with n-grams, min_df and max_df, TF-IDF, and keeping preparation identical at prediction time. Worked on the SMS Spam Collection and IMDB movie reviews."
---

## Introduction

A model takes numbers as input, and a message is a string. Preparing text means cleaning the string, splitting it into words, reducing the number of distinct words, and counting them, so that each message becomes a row of numbers. Each step removes information, so each one is a choice about which information the model does not need.

The examples use the [SMS Spam Collection](https://archive.ics.uci.edu/dataset/228/sms+spam+collection), a public dataset of 5,572 text messages labeled `ham` (legitimate) or `spam`. 403 rows are exact [duplicates](/collections/ai-security/ai-datasets#duplicates). Without them, 5,169 messages remain: 4,516 ham and 653 spam.

## Cleaning the Text

### Lowercasing

`str.lower()` turns `Free`, `FREE` and `free` into the same word, so the model sees one feature instead of three. The downside is that the capitals are gone. In this dataset, 70% of spam messages contain a word of three or more capital letters, such as `FREE` or `URGENT`, against 6% of ham messages.

```python
df["message"] = df["message"].str.lower()
```

### Removing characters

A regular expression removes every character outside a chosen set:

```python
import re

df["message"] = df["message"].apply(lambda x: re.sub(r"[^a-z\s$!]", "", x))
```

`[^...]` matches any character that is not in the brackets, and `re.sub` replaces each match with an empty string. This pattern keeps the letters `a` to `z`, whitespace (`\s`), `$` and `!`, and deletes everything else:

```text
call 09061701461 to claim £900 prize! don't
call  to claim  prize! dont
```

Removing the apostrophe joins `don't` into `dont`. New messages go through the same step, so their `don't` also becomes `dont` and matches the same column. In this dataset, 128 messages already write `dont` and 116 write `don't`, and the step merges both spellings into one feature.

Removing digits deletes phone numbers, short codes and prices. In this dataset, 94% of spam messages contain a digit, against 16% of ham messages, so digits separate the two classes well. Replacing each run of digits with a placeholder word keeps that signal while still merging all the different numbers into one feature:

```python
x = re.sub(r"\d+", " num ", x)   # before removing other characters
```

### Finding what to clean

Which characters need handling depends on the dataset. Reading a few rows shows some of them. Counting every character that is not a letter, digit or space over the whole column shows all of them, with how often each one occurs:

```python
import re
from collections import Counter

tags = Counter()
chars = Counter()
for text in df["text"]:
    tags.update(re.findall(r"<[^>]{0,20}>", text))      # anything shaped like an HTML tag
    chars.update(re.findall(r"[^a-zA-Z0-9\s]", text))   # every character that is not a letter, digit or space

print(tags.most_common(10))
print(chars.most_common(40))
```

`re.findall` returns every match in one text, `Counter.update` adds them to the running totals, and `most_common(n)` lists the n most frequent with their counts.

On the [IMDB movie reviews](https://ai.stanford.edu/~amaas/data/sentiment/) dataset, 50,000 reviews collected from web pages and labeled positive or negative, the counts show four things the SMS messages do not have:

| Found | Example | Handling |
|---|---|---|
| HTML tags | `<br />` about 100,000 times in 25,000 reviews, and a few `<i>` and `<em>` | Remove every tag with one pattern |
| Other apostrophe characters | `` ` ``, `´` and `’` | Convert them to `'` before tokenizing, so `didn’t` is split the same way as `didn't` |
| Accented letters | `é` in `café` and `Pokémon` | Convert them to the plain letter, so `[^a-z]` does not split the word in two |
| Characters from an old Windows encoding | `\x96` and `\x97`, which are dashes | Remove them together with the accents |

### HTML tags, apostrophes and accents

```python
import unicodedata

def clean(text):
    text = text.lower()
    text = re.sub(r"<[^>]+>", " ", text)                    # every HTML tag
    text = re.sub(r"[`´’‘]", "'", text)                     # other apostrophe characters become '
    text = unicodedata.normalize("NFKD", text)              # é becomes e followed by a separate accent mark
    text = text.encode("ascii", "ignore").decode("ascii")   # drops the accent marks and every other non-ASCII character
    text = re.sub(r"[^a-z\s']", " ", text)                  # remaining digits and punctuation become spaces
    return text
```

Tags and punctuation are replaced with a space instead of an empty string, so `movie.<br />the` becomes `movie the`, and the two words stay separate. The extra spaces do no harm, because the tokenizer ignores whitespace.

`unicodedata.normalize("NFKD", ...)` splits each accented letter into the plain letter and a separate accent character. Encoding to ASCII with `"ignore"` drops every character outside ASCII, which removes the accent characters and the `\x96` and `\x97` dashes. `CountVectorizer` and `TfidfVectorizer` can remove accents themselves with `strip_accents="unicode"`.

## Tokenization

A token is one unit of text, usually a word or a punctuation mark. Tokenization splits a string into a list of tokens. NLTK (the Natural Language Toolkit) is a Python library for working with human-language text: it provides tokenizers, stop word lists, stemmers and lemmatizers. Their data files are downloaded separately with `nltk.download`. NLTK's `word_tokenize` does more than splitting on spaces. It separates punctuation from words and splits contractions:

```python
from nltk.tokenize import word_tokenize

word_tokenize("go until jurong point, crazy.. don't")
# ['go', 'until', 'jurong', 'point', ',', 'crazy', '..', 'do', "n't"]
```

`word_tokenize` uses a pretrained sentence splitter called Punkt. Its data files are downloaded once with `nltk.download("punkt")` and `nltk.download("punkt_tab")`.

## Stop Words

Stop words are very common words such as `the`, `is` and `in`. They appear in almost every message, so whether they appear tells you little about whether a message is spam. NLTK's English list has 198 of them, downloaded with `nltk.download("stopwords")`:

```python
from nltk.corpus import stopwords

stop_words = set(stopwords.words("english"))
df["message"] = df["message"].apply(lambda x: [w for w in x if w not in stop_words])
```

On this dataset, removing them cuts the total number of tokens from 77,697 to 46,920.

The list also contains `not` and `no`. After removal, `not free` and `free` look the same. For tasks where negation changes the meaning, such as sentiment analysis, these words have to stay. Removing them from the set before filtering keeps them in the text:

```python
negations = {"not", "no", "nor", "never", "n't"}
stop_words = set(stopwords.words("english")) - negations
```

`word_tokenize` splits a contraction into two tokens: `didn't` becomes `did` and `n't`, and `isn't` becomes `is` and `n't`. `did` and `is` are stop words, so `n't` is the token that keeps the negation. Replacing it with `not` after tokenizing makes `isn't good` and `not good` the same feature:

```python
tokens = ["not" if t == "n't" else t for t in tokens]
```

The list contains `don't` and `don`, but the regex step runs first and has already turned `don't` into `dont`, which is not on the list, so `dont` stays in every message. A stop word list only works on text in the form the list expects.

## Stemming and Lemmatization

Both reduce the different forms of a word to one form, so `claim`, `claimed` and `claiming` count as the same feature. They differ in how they find that form:

- **A stemmer** cuts the end off each word with fixed rules, such as removing `-ing` or turning a final `-y` into `-i`. It has no list of real words. NLTK's `PorterStemmer` implements the Porter algorithm, a set of suffix rules for English published in 1980.
- **A lemmatizer** looks each word up in a dictionary and returns its base form (the lemma), which is always a real word. NLTK's `WordNetLemmatizer` uses the WordNet dictionary, downloaded with `nltk.download("wordnet")`.

Their output on the same words:

| Word | Stem (`PorterStemmer`) | Lemma (`WordNetLemmatizer`) |
|---|---|---|
| claimed, claiming | claim | claim |
| studies, studying | studi | study |
| crazy | crazi | crazy |
| university, universe | univers | university, universe |
| went | went | go |
| won | won | win |
| better | better | good |
| mice | mice | mouse |

The stem does not have to be a real word. `crazi` is fine for a model, which only needs every form of `crazy` to map to the same feature. The rules make mistakes in both directions, though. `university` and `universe` merge although they are unrelated, because they start the same way. Irregular forms such as `went`, `won` and `mice` stay separate from `go`, `win` and `mouse`, because they have no suffix to cut off. The lemmatizer gets all of these right, because the dictionary lists irregular forms.

The lemmatizer needs to know the part of speech (noun, verb, adjective) of each word. Without it, `WordNetLemmatizer` treats every word as a noun, and `claiming` and `went` come back unchanged. The rows above were lemmatized with the right part of speech, such as `lemmatize("went", pos="v")`. Getting it for every word in a text means running a part-of-speech tagger first, which makes lemmatization slower. The part of speech also separates meanings: `meeting` as a noun (`the meeting`) stays `meeting`, and as a verb (`meeting you`) becomes `meet`. The stemmer turns both into `meet`.

```python
from nltk.stem import PorterStemmer

stemmer = PorterStemmer()
df["message"] = df["message"].apply(lambda x: [stemmer.stem(w) for w in x])
```

Stemming is faster and needs no tagger, and its non-words do not matter when the output only feeds a model and nobody reads it. On this dataset, stemming reduces the number of distinct words from 8,459 to 7,121.

## From Tokens to Counts

After the steps above, each message is a list of tokens, such as `['free', 'entri', 'win']`. The next step turns the messages into counts with scikit-learn's `CountVectorizer`, described in [Bag of Words](#bag-of-words). Like every [scikit-learn](/collections/ai-security/ai-tools#scikit-learn) tool, it works in two steps: `fit` learns from the training messages, which for `CountVectorizer` means building the list of words, and `transform` turns any messages into counts using that list. `fit_transform` does both on the same data. By default, `CountVectorizer` expects each message as one string, because it runs its own steps on the text first: it lowercases it, splits it into tokens and builds n-grams. Given a list, it fails at the first of those steps:

```text
AttributeError: 'list' object has no attribute 'lower'
```

There are two ways to give it the tokens.

| | Join the tokens into a string | Pass the token lists directly |
|---|---|---|
| How | `" ".join(tokens)`, then the default `CountVectorizer()` | `CountVectorizer` set up to skip its own lowercasing and splitting |
| Tokenized | Twice: by NLTK, then again by `CountVectorizer` | Once, by NLTK |
| `$`, `!` and single letters | Dropped by the second tokenizer | Kept |
| Prepared data | Strings, easy to print, read and save to a CSV | Lists |
| New messages | Passed as strings | Passed as token lists |

Pass the lists directly when the regex step kept symbols on purpose, since joining throws them away again. Joining is shorter and works with the default settings.

### Passing the token lists directly

`CountVectorizer`'s `preprocessor` and `tokenizer` parameters accept functions that replace its own lowercasing and splitting. A function that returns its input unchanged makes both steps do nothing, so the lists from NLTK are used as they are:

```python
from sklearn.feature_extraction.text import CountVectorizer

def identity(x):
    return x

vectorizer = CountVectorizer(
    preprocessor=identity,   # no preprocessing of its own
    tokenizer=identity,      # the input is already a list of tokens
    lowercase=False,         # already lowercased
    token_pattern=None,      # not used when tokenizer is set
    ngram_range=(1, 2),
)
X = vectorizer.fit_transform(df["message"])   # a column of token lists
```

N-grams still work: the vocabulary includes bigrams such as `win $`.

`identity` is a named function and not a `lambda`, because a model saved with [joblib](/collections/ai-security/ai-tools#saving-a-model) can store a named function but cannot store a `lambda`.

### Joining the tokens into a string

Joining each list with spaces turns it back into a string that the default `CountVectorizer` accepts:

```python
df["message"] = df["message"].apply(lambda x: " ".join(x))
```

```text
Go until jurong point, crazy.. Available only in bugis n great world la e buffet... Cine there got amore wat...
go jurong point crazi avail bugi n great world la e buffet cine got amor wat
```

`CountVectorizer` then splits the string into tokens a second time, with its own rules. Its default `token_pattern` is `(?u)\b\w\w+\b`: a token is two or more letters, digits or underscores. It drops `$`, `!` and single letters such as `u`, `n` and `c`, so keeping `$` and `!` in the regex step has no effect. `!` appears in 47% of spam messages and 12% of ham messages, so dropping it removes a feature that separates the two classes. Changing the pattern so that any run of non-space characters is a token keeps them:

```python
CountVectorizer(token_pattern=r"\S+")
```

The rest of this note uses joined strings, because they are easier to show.

## Bag of Words

A bag of words represents each message by how often each word appears in it. Word order is lost, which is where the name comes from. `CountVectorizer` builds a vocabulary of every word in the training messages, gives each word a column, and turns each message into a row of counts. Here it is with two messages and `ngram_range=(1, 2)`, which is explained below:

| | call | call free | cash | entri | entri win | free | free entri | free now | now | win | win cash |
|---|---|---|---|---|---|---|---|---|---|---|---|
| `free entri win cash` | 0 | 0 | 1 | 1 | 1 | 1 | 1 | 0 | 0 | 1 | 1 |
| `call free now` | 1 | 1 | 0 | 0 | 0 | 1 | 0 | 1 | 1 | 0 | 0 |

```python
from sklearn.feature_extraction.text import CountVectorizer

vectorizer = CountVectorizer(min_df=1, max_df=0.9, ngram_range=(1, 2))
X = vectorizer.fit_transform(df["message"])
vectorizer.get_feature_names_out()   # the vocabulary, one name per column
```

### N-grams

An n-gram is a sequence of n adjacent tokens. Unigrams are single words and bigrams are pairs. `ngram_range=(1, 2)` creates a column for every unigram and every bigram. Bigrams keep some of the word order: `free entri` is a column of its own, separate from `free` and `entri`.

The cost is the number of columns. On this dataset, unigrams alone give 7,101 columns, and unigrams plus bigrams give 37,069.

### Sparse matrices

Each message uses only a few of the 37,069 columns, so almost every value in the matrix is 0. Of its 5,169 × 37,069 cells, 80,181 are non-zero, which is 0.04%. `fit_transform` returns a scipy sparse matrix, which stores only the non-zero values and their positions. A dense array of the same shape would need about 1.5 GB as 64-bit integers.

### min_df and max_df

Both remove columns based on document frequency: the number of messages a term appears in.

| Parameter | Removes terms that appear in | Typical use |
|---|---|---|
| `min_df=5` | fewer than 5 messages | Drops typos, names and one-off words |
| `min_df=0.01` | less than 1% of messages | The same, as a fraction |
| `max_df=0.9` | more than 90% of messages | Drops words common in this dataset, like a stop word list built from the data |

An integer is a number of messages and a float is a fraction. `min_df=1` keeps every term. On this dataset, `max_df=0.9` removes nothing either: the most common term, `call`, appears in 9.7% of messages. Raising `min_df` to 5 reduces the columns from 37,069 to 1,881.

### Fitting on training data only

`fit` reads the training messages and creates one column for each word it finds. After that, the list of columns does not change. A word that was not in the training messages has no column, and `transform` ignores it, so a word that spammers start using after training has no effect on the prediction. The vectorizer belongs to the model and has to be fitted on the training set only, as described in [Splitting Without Leakage](/collections/ai-security/ai-datasets#splitting-without-leakage).

## TF-IDF

Bag-of-words counts have two problems on longer texts, such as reviews:

- **Length**: a review of 2,000 words has larger counts than a review of 50 words that says the same thing.
- **Common words**: words that appear in most documents, such as `movi` and `film` in movie reviews, get large counts and carry little information about the label.

TF-IDF (term frequency, inverse document frequency) corrects both. Each value is the term's count in the document (TF) multiplied by a weight for the term (IDF), which is low for terms that appear in many documents and high for terms that appear in few. scikit-learn computes the IDF as

$$
\text{idf}(t) = \ln\frac{1 + n}{1 + \text{df}(t)} + 1
$$

where $$n$$ is the number of documents and $$\text{df}(t)$$ is the number of documents that contain the term $$t$$. The added 1s keep the IDF above 0, so a term that appears in every document still has a small weight. With 4 documents:

| Term appears in | IDF |
|---|---|
| 4 of 4 documents | $$\ln(5/5) + 1 = 1.00$$ |
| 2 of 4 documents | $$\ln(5/3) + 1 = 1.51$$ |
| 1 of 4 documents | $$\ln(5/2) + 1 = 1.92$$ |

After the multiplication, each row is divided by its [L2 norm](/collections/ai-security/ai-math#norms-the-size-of-a-vector), so every document's row has length 1, however many words the document has. That corrects the length problem.

```python
from sklearn.feature_extraction.text import TfidfVectorizer

vectorizer = TfidfVectorizer(ngram_range=(1, 2), min_df=2, max_df=0.9, sublinear_tf=True)
X_train = vectorizer.fit_transform(train_texts)
X_test = vectorizer.transform(test_texts)
```

`TfidfVectorizer` takes the same `ngram_range`, `min_df` and `max_df` parameters as `CountVectorizer`. `fit` learns the vocabulary and the IDF of every term from the training documents, and `transform` uses both unchanged on new documents.

`sublinear_tf=True` replaces each count with $$1 + \ln(\text{count})$$. A word used 10 times in one review then counts 3.3 times as much as a word used once, instead of 10 times, so one long review that repeats a word does not dominate that word's column.

| | Counts (`CountVectorizer`) | TF-IDF (`TfidfVectorizer`) |
|---|---|---|
| Values | Whole numbers | Decimals, each row of length 1 |
| Documents of very different lengths | Longer documents get larger values | Every document on the same scale |
| Terms common to most documents | The same weight as other terms | A lower weight |
| Designed for | [Multinomial Naive Bayes](/collections/ai-security/ai-naive-bayes#multinomial-naive-bayes), which models word counts | Linear models such as [logistic regression](/collections/ai-security/ai-logistic-regression) |

## Preparing New Messages

A trained model only works on text prepared exactly like its training data. If training stemmed `claiming` to `claim` and prediction does not, the new message's `claiming` matches no column. Every step, in the same order, has to run again before each prediction:

```python
def preprocess_message(message):
    message = message.lower()
    message = re.sub(r"[^a-z\s$!]", "", message)
    tokens = word_tokenize(message)
    tokens = [w for w in tokens if w not in stop_words]
    tokens = [stemmer.stem(w) for w in tokens]
    return " ".join(tokens)
```

Keeping a separate copy of the steps for prediction means two copies that have to stay identical. Putting the preparation inside a scikit-learn [pipeline](/collections/ai-security/ai-tools#pipelines) keeps one copy, which runs at both training and prediction.

A pipeline that includes a custom function, such as `preprocess_message` inside a `FunctionTransformer`, saves only the function's name, as described in [Saving a model](/collections/ai-security/ai-tools#saving-a-model). Loading it on another machine fails unless the same function is defined there. When the model will be loaded somewhere else, such as a service that scores submitted models, the vectorizer's built-in options can do much of the preparation instead: `lowercase=True` (the default), `strip_accents="unicode"`, `stop_words`, `token_pattern` and `ngram_range`. A pipeline made only of a vectorizer and a model needs nothing but scikit-learn to load.
