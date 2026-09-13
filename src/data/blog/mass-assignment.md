---
title: "Mass Assignment"
slug: mass-assignment
category: notes
handbook: oscp
tags: ["mass-assignment"]
draft: false
pubDatetime: 2026-08-07T21:57:33+03:00
modDatetime: 2026-08-07T21:57:33+03:00
description: "A mass assignment bug is a controller that binds a whole request hash onto a model in one call, so every column becomes settable from the request, including ones the form never showed."
---
A mass assignment bug is a controller that binds a whole request hash onto a model in one call, so every column becomes settable from the request, including ones the form never showed. Setting a security-relevant field (`admin`, `role`, `confirmed`, `is_active`, `verified`) turns an ordinary update into a privilege or state change.

The pattern is any framework that maps request keys straight onto object attributes without a whitelist. Ruby on Rails is the classic case, but Laravel (`$model->fill($request->all())`), Django (`**request.POST`), and Spring (`@ModelAttribute`) all have the same shape when strong parameters or an allow-list are missing.

## Rails shape

Rails nests model parameters under the model name, so the request key is `model[field]`:

```
user[email]=x@y.com
user[admin]=1
user[confirmed]=1
```

Sent in a normal update, whether the app takes it as a form POST, a JSON body, or a query string. Rails also tunnels PUT/PATCH through a POST with `_method=patch`, so the update action is often reached over POST:

```
POST /settings/email
_method=patch&authenticity_token=<token>&user[email]=x@y.com&commit=Change email&user[confirmed]=1
```

Boolean values take `1`/`true`, and appending the extra `user[...]` key to a request the app already accepts is enough. No error is expected on success, the record just comes back changed.

## Finding the field names

Guessing (`admin`, `role`, `confirmed`) works, but the app often hands over the exact columns. An update action that responds with the record as JSON prints every field:

```json
{"email":"x@y.com","id":1,"username":"admin1","confirmed":false,"created_at":"...","updated_at":"..."}
```

`confirmed` in that response is the field to set. Other sources of column names are error pages in development mode, leaked source or a git dump, and the framework's own conventions (`role_id`, `is_admin`). On Boolean the email-change response echoed the record, `user[confirmed]=1` on the same request flipped it to true, and that skipped the email-confirmation step and unlocked the rest of the app.

## Where it leads

- Confirm or verify an account that is gated behind email or admin approval.
- Set an admin or role flag on the account already logged in.
- Change another user's record when the action does not check ownership and the model exposes a foreign key.

It is application logic, not a versioned CVE, so try it by hand on any update, profile, or settings action before reaching for an exploit. See [Credential Hunting](/collections/oscp/credential-hunting) for what to do with the access it opens.
