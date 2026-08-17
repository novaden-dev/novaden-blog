---
author: Kayra
pubDatetime: 2026-08-04T00:00:00Z
title: Race Conditions
slug: race-conditions
featured: false
draft: false
tags: ["security", "web"]
category: notes
description: An overview of race conditions, common attack patterns, testing techniques, and remediation strategies.
---

## Introduction

A race condition occurs when an application's behavior depends on the order or timing of operations that run concurrently. If two requests access the same shared state before either request finishes updating it, both may make decisions using stale data. An attacker can exploit this short window to bypass business rules that work correctly when requests arrive one at a time.

Race conditions are common in operations such as redeeming coupons, withdrawing funds, claiming rewards, changing account details, and creating resources with uniqueness requirements.

## The Check-Then-Act Problem

Many race conditions follow a **time-of-check to time-of-use** pattern, often shortened to TOCTOU:

1. The application checks whether an action is allowed.
2. The application performs the action.
3. The application updates the state to record that the action has occurred.

For example, a coupon endpoint might use this logic:

```text
1. Check whether the coupon has already been used.
2. Apply the discount.
3. Mark the coupon as used.
```

With sequential requests, the second request sees that the coupon is already used and fails. With concurrent requests, several workers may complete the first check before any worker reaches the final update. Each worker then applies the same discount.

The vulnerable period between the security check and the state update is called the **race window**.

## Common Race Condition Patterns

### Limit Overruns

Limit-overrun attacks repeat an action that should only succeed a fixed number of times. Common targets include:

- Applying a single-use discount multiple times
- Redeeming the same gift card more than once
- Withdrawing or transferring more money than an account contains
- Claiming the same reward multiple times
- Reusing a one-time token
- Sending more requests than a rate limit permits

The final database state may look valid even though the application performed the protected action multiple times. For example, a coupon may end as `used = true`, but its discount may have been applied to the order several times.

### Duplicate Resource Creation

An application may check whether a username, email address, invitation, or idempotency key already exists before creating a record. Concurrent requests can pass the check together and create duplicates if the database does not enforce uniqueness.

### Multi-Endpoint Races

The requests involved do not always target the same endpoint. One request may update a security-sensitive value while another request causes that value to be used.

Examples include:

- Changing an email address while requesting a password reset
- Changing an order while confirming payment
- Removing an item while completing checkout
- Revoking a permission while performing the protected action

These flaws are harder to find because the conflicting operations may be implemented by different services or code paths.

### Partial-State Races

Some workflows create objects in several steps. During processing, an object may temporarily exist without all of its expected properties or security controls. If another request can access it during this period, the attacker may interact with an invalid intermediate state.

Account registration is one example. An application might create the account first, attach a role next, and mark the email as unverified last. A carefully timed request could reach an endpoint while only part of that state exists.

## Detecting Race Conditions

Start by identifying endpoints that read and then modify shared state. Good candidates enforce a limit, validate a one-time condition, or move an object between states.

### Establish Normal Behavior

Send the request sequentially several times and record the expected behavior. Determine which request should succeed, which should fail, and what the final server-side state should be.

This baseline helps separate a real concurrency issue from an endpoint that simply allows repeated use.

### Send Requests Concurrently

Duplicate the request and send many copies as close together as possible. The goal is to place multiple requests inside the same race window. Tools that synchronize or group requests are more reliable than clicking a send button repeatedly.

Test with a small batch first, then increase the number of requests if the operation is safe to repeat. Network jitter can hide a vulnerability, so run the test several times and compare the resulting state, not only the HTTP responses.

> **Testing Tip:** HTTP/2 can send multiple requests over one connection, which reduces connection setup differences. Some testing tools also support last-byte synchronization, where most of each request is sent in advance and the final byte of every request is released together.

## Testing with Burp Suite

Burp Repeater is enough for an initial test. Turbo Intruder is useful when the test needs more requests, tighter control, or repeated attempts.

### Burp Repeater

1. Capture the target request in **Proxy** and send it to **Repeater**.
2. Send the request normally to confirm the expected response and record the initial server-side state.
3. Duplicate the Repeater tab several times.
4. Select the tabs and add them to a new tab group.
5. Use **Send group in parallel** from the send menu.
6. Compare the responses, then check the resulting balance, coupon state, order count, or other server-side value.
7. Reset the application to fresh state and repeat the test several times.

When the target supports HTTP/2, Burp can synchronize the requests using a single-packet attack. For HTTP/1.1, Burp uses last-byte synchronization. Both techniques reduce the timing differences that occur when independent requests are sent normally.

> **Testing Tip:** Start with two requests. Increase the group size only when the operation is safe and the test account contains enough disposable data. A large group can create real transactions, emails, orders, or other side effects.

### Turbo Intruder

Install **Turbo Intruder** from Burp's BApp Store, right-click the request, and select **Extensions > Turbo Intruder > Send to Turbo Intruder**. A gate can queue several requests and release them together:

```python
def queueRequests(target, wordlists):
    engine = RequestEngine(
        endpoint=target.endpoint,
        concurrentConnections=1,
        engine=Engine.BURP2
    )

    for i in range(20):
        engine.queue(target.req, gate="race1")

    engine.openGate("race1")


def handleResponse(req, interesting):
    table.add(req)
```

The gate holds the queued requests until `openGate()` releases them. `Engine.BURP2` uses HTTP/2, so the target must support it. The request count and engine should be adjusted to match the target and the authorized test scope.

### Interpreting the Result

Multiple `200 OK` responses do not prove that a race condition exists. The important result is whether the protected action occurred more times than allowed.

- Use a fresh coupon, account, token, invitation, or other test object for each attempt.
- Compare the state before and after the request group.
- Record which responses succeeded and how many state changes occurred.
- Repeat the test to distinguish a reliable race from unrelated application behavior.
- Stop if the test causes unexpected side effects or affects data outside the authorized test account.

### Confirm the Impact

A useful test proves that a protected action occurred more often than intended. Evidence may include:

- Multiple successful transactions from one allowed action
- A negative balance or exceeded quota
- Duplicate records with a supposedly unique value
- Several valid sessions or tokens created from one-time input
- A workflow reaching an impossible state

Do not rely only on identical `200 OK` responses. Some systems return success before asynchronous work fails, while others return errors even though the underlying action completed.

## Example Attack

Consider a transfer endpoint that uses this simplified logic:

```javascript
const account = await getAccount(userId);

if (account.balance >= amount) {
  await sendMoney(destination, amount);
  await updateBalance(userId, account.balance - amount);
}
```

If the balance is 100 and two requests attempt to transfer 80 concurrently, both may read a balance of 100 and pass the check. Both transfers can complete, even though the account only has enough funds for one.

The bug is not fixed by moving lines around in application code. The check and update must be enforced as one indivisible operation at the authoritative data store.

## Factors That Affect Exploitation

The size and reliability of a race window depend on several parts of the system:

- **Application work:** slow validation, external API calls, or expensive calculations can widen the window.
- **Database behavior:** isolation levels, row locks, constraints, and query structure determine which concurrent operations are possible.
- **Architecture:** queues, replicas, caches, and multiple application instances can introduce stale state or delay updates.
- **Protocol behavior:** separate connections may have different setup times, while multiplexed requests can arrive closer together.
- **Background jobs:** an endpoint may return before a queued state change is committed.

A test that fails to trigger a race does not prove that the endpoint is safe. It may only mean that the requests did not overlap at the vulnerable operation.

## Remediation

Prevent race conditions by enforcing each security-sensitive state transition atomically at the layer that owns the state. Application-level checks alone are not enough when multiple workers can execute them concurrently.

- Use database transactions with the isolation level and locking behavior required by the operation.
- Replace separate read and write operations with a single conditional update, such as decrementing a balance only when the remaining balance cannot become negative.
- Add database constraints for invariants such as unique usernames, one redemption per user, and non-negative balances.
- Lock the smallest practical record or resource while a protected operation is in progress.
- Use idempotency keys for operations that clients may retry, and enforce each key with a unique database constraint.
- Model complex workflows as explicit state machines and reject invalid state transitions.
- Keep transactions short. Avoid slow network calls while holding locks when the operation can be safely reorganized.
- Do not rely on in-process mutexes in a system with multiple application instances unless a correctly implemented distributed lock protects the shared resource.
- Test security-sensitive workflows with concurrent requests and verify the resulting server-side state.
