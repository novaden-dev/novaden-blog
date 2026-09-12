---
author: Kayra
pubDatetime: 2026-08-24T00:00:00Z
title: "Application Architecture Layers"
slug: "application-architecture-layers"
description: "What a controller, service, repository, DTO, entity, middleware, filter, and dependency injection container actually are, how a request travels through them, what the same roles are called in other stacks, and which bug classes live in each layer."
tags: ["security", "web"]
category: notes
draft: true
featured: false
---

## Introduction

Open an unfamiliar codebase and most of the file names are not domain words. They are role words: `ReportController`, `EmployeeService`, `IEmployeeRepository`, `AuthenticationMiddleware`, `UserLoginResponse`. None of those names tell you what the application does. They tell you where the file sits in a pipeline.

That is the useful thing about layered architecture: the vocabulary is nearly the same across .NET, Java, Python, Node, and Ruby, so once you know the roles you can navigate almost any web application without knowing the framework. This note explains each role, what it is supposed to do, what it is not supposed to do, and which bug classes tend to live there.

## The Request Pipeline

Almost every server-side web application is the same shape. An HTTP request comes in, passes through a chain of general-purpose handlers, gets matched to one piece of code, and that code walks down through layers until something touches storage. The response comes back out the same way.

```text
HTTP request
   |
   v
[ Web server / host ]            Kestrel, Tomcat, Nginx, Node http
   |
   v
[ Middleware pipeline ]          HTTPS redirect, CORS, auth, logging, errors
   |
   v
[ Routing ]                      match URL + verb to one action
   |
   v
[ Filters / guards ]             per-endpoint checks, [Authorize], validation
   |
   v
[ Controller ]                   HTTP in, HTTP out
   |
   v
[ Service ]                      business rules, orchestration, transactions
   |
   v
[ Repository ]                   queries, persistence
   |
   v
[ Database / API / filesystem ]
```

The layers below the controller usually have no idea HTTP exists. That is deliberate. A service should be callable from a scheduled job or a console tool without a request object, and a repository should not care whether the caller is a web request or a nightly batch.

Two rules make the whole model easier to hold:

- **Each layer only talks downward**: controllers call services, services call repositories. When you find a layer reaching across or upward, treat it as a smell worth reading closely.
- **Each layer translates**: HTTP shapes at the top, domain objects in the middle, table rows at the bottom. Most of the mapping code in a large application exists to keep those three shapes separate.

## Middleware

Middleware is a function that wraps every request. It gets the request, can do something before passing it along, can do something on the way back out, and can decide to stop the request entirely and answer it itself.

The classic shape is the same in every stack: each component receives the request and a reference to "the next thing in the chain".

```javascript
// Express
app.use((req, res, next) => {
  console.log(req.method, req.url); // before
  next();                            // hand off to the rest of the pipeline
  // anything here runs on the way back out
});
```

```csharp
// ASP.NET Core
app.Use(async (context, next) =>
{
    // before
    await next();
    // after
});
```

Because each one wraps the next, the pipeline is not a list, it is a set of nested layers. The first component registered is the outermost, so it sees the request first and the response last.

### Order is the design

Middleware order is not a style preference, it is the behaviour. A few consequences that come up constantly:

- **Authentication must run before anything that reads the identity.** If an authorization check runs first, it evaluates an empty identity and either denies everything or, worse, sees no identity and treats the request as anonymous-but-allowed.
- **Exception handling belongs at the outside.** It can only catch what happens inside it, so a handler registered late catches nothing from the components before it.
- **Anything registered before authentication is public.** That is how documentation UIs, health endpoints, and static file handlers end up reachable without credentials while everyone assumes the global auth policy covers them.
- **Static files short-circuit.** A static file handler that matches a path answers immediately and the rest of the pipeline never runs.

> **Review tip:** the file that registers the middleware chain is the single highest-value file in a web codebase. It is usually short, it is called `Startup.cs`, `Program.cs`, `app.js`, `settings.py`, or `SecurityConfig.java`, and it tells you the real security posture faster than any amount of controller reading.

### What middleware usually handles

Middleware is where cross-cutting concerns live, meaning concerns that apply to every request rather than to one endpoint: HTTPS redirection, security headers, CORS, authentication, session handling, request logging, rate limiting, exception handling, static file serving, and response compression.

### The same idea under other names

| Stack | Name |
|---|---|
| ASP.NET Core | Middleware |
| Express, Koa, NestJS | Middleware |
| Django | Middleware |
| Java Servlet | Filter |
| Spring | Filter, and `HandlerInterceptor` for the routed variant |
| Ruby on Rails | Rack middleware |
| PHP (Laravel) | Middleware |

## Filters, Interceptors, and Guards

Middleware runs before routing, so it knows the URL but not which method will handle it. Filters run after routing, so they know exactly which action they are wrapping and can read that action's attributes and metadata.

That distinction is why per-endpoint authorization lives in filters rather than middleware. `[Authorize(Roles = "Admin")]` on a controller action is only meaningful to something that knows which action was selected.

Filters typically cover authorization, model validation, action-level logging, caching, and exception translation for one controller or action.

```csharp
[Authorize(Roles = "Admin")]          // read by the authorization filter
[HttpPost("employees")]
public IActionResult Create(EmployeeDto dto) { ... }
```

### Client-side guards are not access control

Single-page applications have their own thing called a guard: Angular's `CanActivate`, React route wrappers, Vue navigation guards. These decide whether the browser will render a route.

They are user experience, not security. The code behind that route was already downloaded to the browser, and nothing stops anyone calling the API directly with a token and a terminal. A client-side guard is a signal about what the developers intended, which makes it useful for building a picture of the role model, but the enforcement has to exist on the server or it does not exist.

## Controllers

A controller translates HTTP into a method call and a result back into HTTP. Reading route parameters, query strings, headers, and request bodies; calling into the layer below; returning a status code with a body.

What belongs in a controller: model binding, input validation, calling one service, mapping the result to a response shape, choosing the status code.

What does not: business rules, SQL, transaction management, sending email.

The single most useful question to ask of a controller action during review is **where does the identity come from**. Compare these:

```csharp
// Derived from the validated token. The caller cannot choose.
var userId = _claimsProvider.GetUserClaims(User).UserId;
var report = _reportService.GetReport(reportId, userId);

// Supplied by the caller. Whatever the client sends is what gets used.
public IActionResult GetReport(int reportId, int employeeId) { ... }
```

The second is how insecure direct object references and horizontal privilege escalation happen. The parameter looks innocuous, and the query built from it is perfectly parameterised, and it still lets one user read another user's data.

## Services

The service layer holds business logic. It is where the rules of the domain live: what makes a report valid, who is allowed to close one, what happens when it is closed, which notifications go out.

It exists so that those rules do not depend on HTTP and do not depend on the database vendor. A service usually orchestrates several things: two or three repositories, a notification component, a transaction boundary, some domain validation.

```csharp
public class ReportService
{
    public void CloseReport(int reportId, int actingUserId)
    {
        var report = _reportRepository.GetById(reportId);
        if (report.AssignedTo != actingUserId) throw new ForbiddenException();

        report.Status = ReportStatus.Closed;
        _reportRepository.Update(report);
        _notifier.NotifyClosed(report);
    }
}
```

Two things make the service layer matter during review. First, business-rule authorization lives here, the kind that cannot be expressed as an attribute: "only the assigned handler may close this report" is a service-layer decision, not something `[Authorize]` can express. Second, it is where an operation that should be atomic either gets a transaction or does not.

## Repositories

A repository encapsulates data access. Everything above it asks for objects and gets objects, without knowing whether they came from SQL Server, an HTTP API, or a file on disk.

```csharp
public interface IEmployeeRepository
{
    Employee GetById(int employeeId);
    IEnumerable<Employee> GetByDepartment(int departmentId);
    void Update(Employee employee);
}
```

The interface goes in a project that everything can reference. The implementation goes in a project that knows about the database. That is why codebases so often have a pair like `App.Data` and `App.Data.SQL`: the first holds the contracts, the second holds the SQL. Swapping the implementation is the stated reason for the split, but the more common real benefit is that the layers above become testable without a database.

### What lives here

The repository layer is where two important properties are either present or absent across the whole application:

- **Parameterisation**: whether values reach the database as parameters or as concatenated string fragments. This is the SQL injection question, and the repository layer is where you can answer it once for many endpoints.
- **Ownership filtering**: whether the `WHERE` clause includes the caller's identity. `SELECT * FROM Reports WHERE ReportId = @id` returns any report to anyone who asks. `WHERE ReportId = @id AND AssignedTo = @userId` does not. When the filtering is not here, it must be in the service, and if it is in neither you have an access control finding.

> **Note:** an ORM is a repository substitute, not a different category. Entity Framework's `DbContext`, Hibernate's `Session`, and Django's model manager all occupy the same slot. Code that injects a `DbContext` directly into a controller has skipped the layer, not avoided the concept.

## Entities, Models, and DTOs

Three names for object shapes that beginners reasonably confuse, because in small applications they are the same class.

- **Entity (or domain model)**: the shape of your data as stored. Usually one class per table, with the relationships between them. `Employee`, `Report`, `Attachment`.
- **DTO (data transfer object)**: the shape of data crossing a boundary, most often the wire format of a request or a response. `CreateReportRequest`, `UserLoginResponse`.
- **ViewModel**: a DTO shaped for one specific screen. Same idea, presentation flavour.

Keeping them separate feels like duplicated code until you see the two bug classes that the split prevents.

### Mass assignment

If a request body is bound directly onto an entity, every property of that entity becomes settable by whoever sends the request.

```csharp
// The client sends {"name":"Bob","isAdmin":true} and the framework
// helpfully binds isAdmin, because it is a property on the entity.
[HttpPost]
public IActionResult Create(Employee employee) { _repo.Insert(employee); }
```

A DTO that only carries the fields a caller is allowed to set makes the attack impossible instead of merely unlikely. This bug is called mass assignment, over-posting, or autobinding depending on the ecosystem, and it appears in the OWASP API Top 10 as broken object property level authorization.

### Over-disclosure

The same problem in the other direction. Returning an entity serialises everything on it, including the columns nobody thought about: password hashes, internal flags, soft-delete markers, the secret answer, the full claims collection copied off a token. A response DTO is an allowlist of what leaves the building.

## Dependency Injection and the Composition Root

Dependency injection means a class does not build its own collaborators. It declares what it needs, usually as interfaces in its constructor, and something else supplies them.

```csharp
public class ReportController : ControllerBase
{
    private readonly IReportService _reportService;

    // The controller never says "new ReportService(...)".
    public ReportController(IReportService reportService)
    {
        _reportService = reportService;
    }
}
```

The "something else" is the container, and the place where you tell the container which concrete class satisfies which interface is the composition root: `ConfigureServices` in ASP.NET Core, a `@Configuration` class in Spring, a module provider list in NestJS or Angular.

```csharp
services.AddScoped<IReportService, ReportService>();
services.AddScoped<IUserClaimsProvider, AdfsUserClaimProvider>();
```

That second line is the reason the composition root matters when reading code. An interface can have several implementations sitting in the source tree, including test doubles and abandoned ones, and the registration is the only thing that tells you which one actually runs.

### Lifetimes

Registration also fixes how long an instance lives, and the names are near-identical across frameworks:

| Lifetime | Meaning | Typical mistake |
|---|---|---|
| Transient | New instance every time it is requested | Rarely harmful, sometimes wasteful |
| Scoped (per-request) | One instance for the duration of one request | Injecting a scoped service into a singleton, which quietly promotes it |
| Singleton | One instance for the whole process | Holding per-user state on it, so one user's data leaks into another user's request |

A singleton that caches "the current user" is a real bug and a subtle one, because it only misbehaves under concurrency.

## The Vaguer Suffixes

Not every role word carries a precise meaning. These are worth knowing as conventions rather than definitions:

- **Provider**: supplies something on demand, often with a swappable backend. `IUserClaimsProvider`, `IStorageProvider`. Effectively a repository for things that are not rows.
- **Factory**: builds objects whose construction needs a decision. `IHttpClientFactory`.
- **Handler**: the thing that handles one message, command, or event, common in CQRS and message-bus code.
- **Manager**: usually means the author had no better word. Read it, do not trust the name.
- **Helper** or **Utils**: static functions with no home. Worth reading in a security review, because sanitisation and crypto routines get parked here.
- **Facade**: one entry point in front of several subsystems.
- **Adapter** or **Client**: wraps an external system, usually a third-party API.

## Same Roles, Different Words

| Role | ASP.NET Core | Spring | Django / DRF | Node (Express / NestJS) | Rails |
|---|---|---|---|---|---|
| Endpoint code | Controller | `@RestController` | View, ViewSet | Route handler, Controller | Controller |
| Business logic | Service | `@Service` | `services.py` by convention | Provider, Service | Service object |
| Data access | Repository, `DbContext` | `@Repository`, `JpaRepository` | Model manager, QuerySet | Repository, Prisma client | ActiveRecord model |
| Cross-cutting | Middleware | Filter, Interceptor | Middleware | Middleware, Interceptor | Rack middleware |
| Per-endpoint hook | Filter, Attribute | Interceptor, Annotation | Decorator, Permission class | Guard, Pipe | `before_action` |
| Wire shape | DTO, ViewModel | DTO, Record | Serializer | DTO | Serializer |
| Stored shape | Entity, POCO | `@Entity` | Model | Entity | ActiveRecord model |
| Wiring | `ConfigureServices` | `@Configuration` | `settings.py` | Module providers | Initializers |

Rails and Django deliberately merge the entity and the data access layer into one class, which is the ActiveRecord pattern. It is not a missing layer, it is a different trade: less indirection, tighter coupling to the database.

## When the Layering Is Fake

Textbook layering and shipped layering differ, and the gaps are informative.

- **Anemic services**: the service exists but every method forwards straight to the repository with no logic in between. That is not automatically bad, but it does mean the business rules are somewhere else, usually the controller. Go find them.
- **Layer skipping**: a controller injecting a `DbContext`, or a service opening its own connection. The consequence for review is specific. If you read the repository layer, confirmed every query is parameterised, and concluded the application is safe from SQL injection, a single controller that queries directly invalidates the conclusion. Verify the layer is the only path before you generalise from it.
- **God services**: one class of two thousand lines that everything calls. Usually the highest-risk file in the codebase, since it accumulates the special cases.
- **Logic in the wrong place**: authorization inside a repository, or SQL inside a controller. Both work. Both mean the property you want to verify is scattered rather than centralised, which costs you time and coverage.

## Where the Bugs Live, by Layer

| Layer | Bug classes that concentrate here |
|---|---|
| Middleware and pipeline | Ordering mistakes, missing authentication, permissive CORS, debug error pages in production, unguarded documentation UIs, missing security headers |
| Filters and attributes | Missing or bare `[Authorize]`, endpoints opted out with `[AllowAnonymous]`, validation that is declared but never enforced |
| Controller | Identity taken from a parameter instead of the token, mass assignment, unbounded uploads, verbose error responses |
| Service | Missing business-rule authorization, race conditions, non-atomic multi-step operations, workflow states that can be skipped |
| Repository and ORM | SQL injection through concatenation, missing ownership filter in the `WHERE` clause, raw query escape hatches next to otherwise safe code |
| DTO and serialization | Over-disclosure of internal fields, deserialization of untrusted types, secrets in log-friendly `ToString` output |
| Composition root | Wrong implementation registered, incorrect lifetimes, secrets read from a file with no environment layering |

## Reading an Unfamiliar Codebase in Layer Order

The layering gives you a reading order that works even when you know nothing about the domain.

1. **The composition root.** Which middleware, in which order, and which implementations are registered. Short file, highest yield per line.
2. **The controllers.** One pass for the attack surface: every route, every verb, and every endpoint marked anonymous.
3. **One vertical slice, end to end.** Pick a single interesting endpoint and follow it down through service and repository to the query and back out through the response shape. This is where you learn the codebase's idioms and calibrate what "normal" looks like.
4. **The data access layer as a whole.** Now that you know the idiom, check whether it holds everywhere: parameterisation, ownership filtering, raw query escape hatches.
5. **The cross-cutting pieces.** Error handling, logging, DTO mapping, configuration and secrets.

By step three you can usually predict what the rest of the codebase looks like, and the value of the remaining steps is confirming the prediction and cataloguing the exceptions.

> **Related:** for the process this reading order plugs into, see [Secure Code Review: Process and Methodology](/posts/secure-code-review-methodology). For per-ecosystem manifests, sinks, and framework traps, see [Secure Code Review by Stack](/posts/secure-code-review-by-stack).
