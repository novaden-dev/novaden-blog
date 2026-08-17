---
author: Kayra
pubDatetime: 2026-05-02T00:00:00Z
title: NoSQL Injection
slug: nosql-injection
featured: false
draft: false
tags: ["security", "web"]
category: notes
description: An overview of NoSQL Injection types, identification techniques, and remediation strategies.
---

## Introduction

NoSQL Injection is the equivalent of SQL Injection but for NoSQL databases. Unlike relational databases that store data in structured tables with strict schemas, NoSQL databases store data in unstructured or semi-structured formats.

There are different types of NoSQL databases (document, key-value, wide-column, graph) and each has its own query language and syntax.

## Types of NoSQL Injection

NoSQL injection generally falls into two categories:

### Syntax Injection

This happens when user input is concatenated directly into a query string. An attacker can break out of the intended syntax and inject additional query logic. This is most common when the application builds queries by directly interpolating strings.

### Operator Injection

This happens when the application properly structures the query but fails to sanitize the *values* within that structure. The attacker submits valid data objects that contain NoSQL operators (e.g., `$ne`, `$gt`, `$regex`). Because these operators are parsed by the database, they change the logic of the query without breaking its syntax.

In short: **Syntax injection affects the query structure, while operator injection changes the values inside the existing structure.**

## Detecting NoSQL Injection

To identify NoSQL injection, fuzz endpoints with special characters that might trigger database errors or change application behavior. This reveals how the input is being processed and validated by the server.

### Fuzzing Characters

When testing for NoSQL injection, try sending the following characters individually and observe the response:

- `' " \ ; { } ( ) [ ]` - Quote and bracket characters
- `$` - Used to prefix NoSQL operators (e.g., `$ne`, `$gt`, `$where`)
- `,` - Used to separate object properties
- `:` - Used as key-value separators in JSON/BSON objects
- `\x00` - Null byte (can cause parsing issues)
- `//` or `/*` - Comment syntax in some contexts

Look for changes in response codes, error messages, response times, or response lengths.

### Confirming Vulnerability

Once the attacker identifies that input reaches the query:

1. **Test conditional behavior**: Send payloads that evaluate to true and false. Observe if the application behavior changes accordingly.
2. **Monitor response uniformity**: If the application returns a generic error page or consistent response regardless of input, switch to **time-based detection**.
3. **Check for JavaScript execution**: Some operators (like `$where` in MongoDB) allow execution of JavaScript functions. If enabled, this opens the door wide for multiple attacks.

## Exploitation Examples

### Authentication Bypass

**Example: Using the `$regex` operator**

```json
{"username":"admin","password":{"$regex":"^.*"}}
```

This payload matches any password for the `admin` user by using a regular expression that matches everything.

**Example: Using the `$ne` operator**

```json
{"username":{"$ne":null},"password":{"$ne":null}}
```

This causes the database to return the first user where both username and password are not null, bypassing the authentication check.

### Information Disclosure via `$where`

The `$where` operator executes a JavaScript expression or function on each document. This can be abused to extract schema information or enumerate field names.

**Enumerate if a field exists (matching by name prefix):**

```json
"$where": "function() { if(Object.keys(this)[4].match(/^ema/) ) return 1; else 0; }"
```

This checks whether the 5th field (0-indexed) of the document starts with `ema`, which could help identify an `email` field.

**Determine field name length:**

```json
"$where": "function(){ if(Object.keys(this)[3].length == 1) return 1; else 0; }"
```

By iterating through indices and lengths, an attacker can reconstruct the schema of the collection character by character.

### Denial of Service (CPU Spike)

Even when data extraction is not the goal, `$where` can be used to cause a denial of service. Because JavaScript runs server-side on the database, a crafted loop will pin the CPU at 100% for the duration specified.

**Payload:**

```javascript
0;var date=new Date(); do{curDate = new Date();}while(curDate-date<10000)
```

This forces the database to spin in a busy-wait loop for 10 seconds per document it evaluates. If run against a large collection, it can degrade or crash the database entirely.

### Time-Based Blind Detection

When the application response is uniform and does not reveal whether a query succeeded or failed, time-based injection can be used. The response time itself becomes the hint.

**Example using `$where` with `sleep`:**

```json
{"$where": "sleep(5000)"}
```

If the response consistently delays by approximately 5 seconds, the attacker has confirmed that JavaScript execution is possible and that the input reaches the query.

## The PHP Variable Injection Edge Case

Even if application developers properly sanitize user input or use parameterized queries, there is an alternate path to trigger NoSQL injection that is specific to the application programming language.

Many NoSQL databases use operators that begin with `$`. In PHP, any string beginning with `$` inside **double quotes** is interpreted as a variable. If a developer constructs a query using double-quoted strings, PHP will substitute the variable before the query ever reaches the database.

The PHP MongoDB documentation explicitly warns developers:

> *Please make sure that for all special query operators (starting with `$`) you use single quotes so that PHP doesn't try to replace `$exists` with the value of the variable `$exists`.*

### Exploitation Scenario

Consider a query that contains no user input at all:

```javascript
db.myCollection.find( { $where: function() { return obj.credits - obj.debits < 0; } } );
```

If this query is defined in a PHP string using double quotes, an attacker who can influence the value of a PHP variable named `$where` can inject malicious code. Because `$where` is a valid PHP variable name, PHP will replace it with the attacker's payload before the query is sent to MongoDB.

This means **the vulnerability exists not in the database layer, but in how the application language handles string interpolation.**

## Remediation

The correct way to prevent NoSQL injection attacks depends on the specific NoSQL technology being used. Always use the official security documentation for your database.

### General Guidelines

- **Use parameterized queries / prepared statements**. Never concatenate user input directly into query strings.
- **Sanitize and validate user input**. Use an allowlist of accepted characters and reject everything else.
- **Prevent operator injection**. Apply an allowlist of accepted keys. Reject any key that starts with `$` unless it is explicitly expected.
- **Disable dangerous features**. If your database supports JavaScript execution in queries (e.g., MongoDB's `$where`, `$eval`), disable or restrict them if they are not required.
- **Use least-privilege database accounts**. Ensure the application database user only has the permissions it strictly needs.
- **Mind language-specific quirks**. In PHP, always use single quotes when writing query operators that start with `$` to prevent variable interpolation.
