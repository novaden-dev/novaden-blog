---
author: Kayra
pubDatetime: 2026-08-21T00:00:00Z
title: "Secure Code Review by Stack"
slug: "secure-code-review-by-stack"
description: "Per-ecosystem reference for a secure code review: which build manifests reveal the toolchain, whether the analyser needs a compile, how to restore dependencies with no internet, and the sink patterns and framework traps for .NET, Java, PHP, Python, Node, Ruby, Go, and the major frontend frameworks."
tags: ["security", "devsecops", "cheatsheet"]
category: notes
draft: true
featured: false
---

## Introduction

This is the per-stack half of a secure code review. The process it plugs into (intake, recon, the manual techniques, reporting) is in [Secure Code Review: Process and Methodology](/posts/secure-code-review-methodology).

Each section answers the same four questions for one ecosystem:

1. **Manifests**: which files reveal the toolchain, so you can size the environment before the source arrives.
2. **Build and dependencies**: whether the analyser needs a compile, and how to restore packages with no internet access.
3. **Sinks**: what to grep for, by vulnerability class.
4. **Framework traps**: the configuration and idiom mistakes that recur in that ecosystem.

Two things to keep in mind while using the grep lists. A hit is a **lead, not a finding**: trace it backwards to a request-controlled source before it goes anywhere near a report. And the lists are deliberately not exhaustive, because an exhaustive list is a tool's job. These are the patterns worth a human's attention on a time-boxed review.

## .NET and C#

### Manifests

```bash
# Every target framework in the solution
grep -rhoE '<TargetFrameworks?>[^<]+' --include='*.csproj' . | sort -u

# Legacy .NET Framework projects: these change the whole plan
grep -rlE '<TargetFrameworkVersion>' --include='*.csproj' .

# Pinned SDK version
cat global.json 2>/dev/null

# Which feeds the build expects to reach
cat nuget.config 2>/dev/null
```

Read the results like this:

- **`<TargetFramework>net8.0`**: you need the .NET **SDK** 8, not just the runtime. Building needs the SDK.
- **Several target frameworks**: install every matching SDK. They coexist side by side and `dotnet --list-sdks` shows them all. A newer SDK can often build an older target, but only if the targeting pack for that version is present, and offline it usually is not.
- **`global.json` present**: it pins the SDK. If the pinned version is not installed, the build fails with a version error even when a newer SDK is sitting right there. Match it exactly, or agree that `rollForward` may be relaxed.
- **`<TargetFrameworkVersion>v4.x`**: this is .NET Framework, not modern .NET. It **cannot be built on Linux**. You need Windows, Visual Studio Build Tools, and the matching targeting pack. Finding this out mid-activity is the most expensive mistake in the phase, so grep for it during intake.

### Build and dependencies

**A build is required.** SonarQube's C# rules run as Roslyn analyzers inside the compiler: a `begin` step injects MSBuild targets, `dotnet build` executes the rules during compilation and emits results, and an `end` step collects them. No compile means no semantic model, so no type resolution and no analysis.

Offline restore, in order of preference:

```xml
<!-- nuget.config at the repo root. The <clear /> is what stops the stall on nuget.org -->
<?xml version="1.0" encoding="utf-8"?>
<configuration>
  <packageSources>
    <clear />
    <add key="internal" value="https://nexus.internal.corp/repository/nuget-group/index.json" />
  </packageSources>
</configuration>
```

```bash
# Or, on a connected machine that can already build it:
dotnet restore MySolution.sln --packages ./offline-nuget

# Then on the review machine:
dotnet restore MySolution.sln --source ./offline-nuget
export NUGET_PACKAGES=$PWD/offline-nuget
```

If the project has a `packages.lock.json`, add `--locked-mode` so an incomplete bundle fails immediately rather than halfway through the build.

Running the scan:

```bash
# The tool install hits a feed; use a local .nupkg copy or the standalone zip
dotnet tool install --global dotnet-sonarscanner --add-source ./offline-nuget

dotnet sonarscanner begin /k:"project-key" \
  /d:sonar.host.url="http://sonarqube.internal:9000" /d:sonar.token="$SONAR_TOKEN"
dotnet build MySolution.sln --no-incremental
dotnet sonarscanner end /d:sonar.token="$SONAR_TOKEN"
```

`--no-incremental` matters. An incremental build skips projects, skipped projects never invoke the analyzer, and you get a scan that silently covers a fraction of the solution.

### Sinks

```bash
# Query construction
grep -rn "FromSqlRaw\|ExecuteSqlRaw\|ExecuteSqlCommand\|new SqlCommand\|CommandText" --include='*.cs' .
# Command execution
grep -rn "Process\.Start\|ProcessStartInfo\|UseShellExecute" --include='*.cs' .
# Deserialization
grep -rn "BinaryFormatter\|LosFormatter\|SoapFormatter\|NetDataContractSerializer\|ObjectStateFormatter" --include='*.cs' .
grep -rn "TypeNameHandling\|SimpleTypeResolver\|Activator\.CreateInstance" --include='*.cs' .
# XXE
grep -rn "XmlDocument\|XmlTextReader\|DtdProcessing\|XmlResolver" --include='*.cs' .
# Path handling
grep -rn "Path\.Combine\|File\.ReadAllText\|File\.OpenRead\|Server\.MapPath" --include='*.cs' .
# Outbound and TLS
grep -rn "ServerCertificateValidationCallback\|DangerousAcceptAnyServerCertificateValidator" --include='*.cs' .
# Output encoding
grep -rn "Html\.Raw\|new HtmlString\|MvcHtmlString\|ValidateInput(false)\|AllowHtml" --include='*.cs' --include='*.cshtml' .
# Crypto and randomness
grep -rn "MD5\|SHA1\.\|DESCryptoServiceProvider\|TripleDES\|RC2\|CipherMode\.ECB\|new Random()" --include='*.cs' .
```

`FromSqlInterpolated` and `ExecuteSqlInterpolated` are the parameterised versions and are usually fine. `FromSqlRaw` with an interpolated `$"..."` string is the classic .NET SQL injection, because the developer read the `Interpolated` naming as meaning it was handled. `TypeNameHandling` set to anything but `None` in a Json.NET setting is remote code execution when the input is attacker-controlled.

### Framework traps

- **`Program.cs` or `Startup.cs`**: middleware order. `UseAuthorization` before `UseAuthentication` authorises an unpopulated identity. `UseDeveloperExceptionPage` outside an environment check leaks stack traces. Check for a fallback authorization policy: without one, every unattributed endpoint is anonymous.
- **JWT**: read every flag on `TokenValidationParameters`. Any of `ValidateIssuer`, `ValidateAudience`, `ValidateLifetime`, or `ValidateIssuerSigningKey` set to `false` is a finding on its own, as is `RequireHttpsMetadata = false`.
- **CORS**: `AllowAnyOrigin` with `AllowCredentials` is rejected at runtime, so the pattern you will actually find is `SetIsOriginAllowed(_ => true)` with `AllowCredentials`.
- **Mass assignment**: an action binding directly to an EF entity rather than a DTO makes every property settable, including `IsAdmin`, `Role`, and `Price`.
- **IDOR**: `_db.Orders.Find(id)` with no owner predicate.
- **Config**: `appsettings*.json` connection strings, signing keys as plain strings, `<compilation debug="true">` in `web.config`.

## Java and Spring

### Manifests

```bash
grep -E '<java.version>|<maven.compiler.(source|target|release)>' pom.xml
grep -E 'sourceCompatibility|targetCompatibility|JavaVersion' build.gradle
grep distributionUrl gradle/wrapper/gradle-wrapper.properties   # Gradle version
grep -E '<mirror>|<repository>' ~/.m2/settings.xml pom.xml 2>/dev/null
```

The JDK version, the build tool, and the build tool's own version are three separate requests. A Gradle wrapper will try to download its own distribution on first run, which fails with no internet, so request the Gradle distribution zip too or pre-seed `GRADLE_USER_HOME`.

### Build and dependencies

**A build is required.** The Sonar Java analyser works from compiled classes and needs `sonar.java.binaries` pointing at them.

```bash
# On a connected machine
mvn dependency:go-offline -Dmaven.repo.local=./m2repo
# or simply tar the populated local repository
tar czf m2repo.tgz -C ~ .m2/repository

# On the review machine
mvn -o -Dmaven.repo.local=./m2repo clean install
gradle --offline build      # Gradle equivalent
```

For an internal mirror, a `<mirror>` block in `settings.xml` with `<mirrorOf>*</mirrorOf>` redirects everything to Nexus in one place.

### Sinks

```bash
# Query construction
grep -rn "createQuery(\|createNativeQuery(\|executeQuery(\|nativeQuery *= *true" --include='*.java' .
grep -rn "jdbcTemplate\.\(query\|update\)(\"" --include='*.java' .
# Command execution
grep -rn "Runtime\.getRuntime()\.exec\|new ProcessBuilder" --include='*.java' .
# Deserialization
grep -rn "ObjectInputStream\|readObject(\|XMLDecoder\|XStream\|enableDefaultTyping\|@JsonTypeInfo" --include='*.java' .
grep -rn "new Yaml()" --include='*.java' .
# XXE
grep -rn "DocumentBuilderFactory\|SAXParserFactory\|XMLInputFactory\|TransformerFactory" --include='*.java' .
# Expression and template injection
grep -rn "SpelExpressionParser\|ScriptEngineManager\|Ognl\|MVEL" --include='*.java' .
# Outbound
grep -rn "RestTemplate\|WebClient\|new URL(\|HttpURLConnection" --include='*.java' .
# Crypto and randomness
grep -rn "Cipher\.getInstance(\|MessageDigest\.getInstance(\|new SecretKeySpec\|new Random()\|Math\.random()" --include='*.java' .
# JWT
grep -rn "parseClaimsJwt\|setSigningKey\|parse(" --include='*.java' .
```

Two Java-specific traps worth knowing. `Cipher.getInstance("AES")` with no mode specified **defaults to ECB**, so the string to look for is the short one, not a literal `ECB`. And in the JJWT library `parseClaimsJwt` parses an *unsigned* token while `parseClaimsJws` verifies the signature, a one-character difference that disables authentication.

### Framework traps

- **Security config**: in `SecurityFilterChain` or the older `WebSecurityConfigurerAdapter`, matcher rules are evaluated in order and **first match wins**, so a broad `permitAll()` above a specific rule opens everything below it. Look for `.csrf().disable()` and whether the API is genuinely token-authenticated.
- **Method security**: `@PreAuthorize` and `@Secured` do nothing unless method security is enabled. Check for `@EnableMethodSecurity` or the older `@EnableGlobalMethodSecurity`, then check which handlers carry annotations and which do not.
- **Actuator**: `management.endpoints.web.exposure.include=*` exposes `/env`, `/heapdump`, and `/mappings`. A heap dump is credentials.
- **`application.properties` or `.yml`**: datasource credentials, `server.error.include-stacktrace=always`, `spring.h2.console.enabled=true`.
- **CORS**: `@CrossOrigin` with no arguments defaults to permissive.
- **Mass assignment**: binding a request body straight to a JPA entity.

## PHP

### Manifests

```bash
grep -E '"php"|"require"' composer.json
cat .php-version 2>/dev/null
grep -rn "framework\|laravel\|symfony" composer.json
```

### Build and dependencies

**No build is required.** The analyser reads source directly, so a failed `composer install` does not block the scan. It only costs you framework-aware resolution, which matters less in PHP than type resolution does in a compiled language.

```bash
# Connected machine
composer install --no-scripts --no-dev && tar czf vendor.tgz vendor/
# Or point at an internal Satis or Nexus mirror in composer.json's "repositories"
```

### Sinks

```bash
# Query construction
grep -rn "mysqli_query\|->query(\|->exec(\|pg_query" --include='*.php' .
# Command execution
grep -rn "system(\|exec(\|shell_exec(\|passthru(\|popen(\|proc_open(" --include='*.php' .
# Code execution
grep -rn "eval(\|assert(\|create_function(\|preg_replace(.*/e" --include='*.php' .
# File inclusion, the PHP-specific one
grep -rnE "(include|require)(_once)? *\(? *\\\$" --include='*.php' .
# Deserialization
grep -rn "unserialize(" --include='*.php' .
# XXE
grep -rn "simplexml_load\|DOMDocument\|libxml_disable_entity_loader" --include='*.php' .
# Crypto and randomness
grep -rn "md5(\|sha1(\|mcrypt_\|rand(\|mt_rand(\|uniqid(" --include='*.php' .
# Superglobals used directly
grep -rn '\$_REQUEST\|\$_GET\|\$_POST\|\$_COOKIE' --include='*.php' .
# Variable variables and extraction
grep -rn "extract(\|\\\$\\\$" --include='*.php' .
```

`include` or `require` with a variable is local and sometimes remote file inclusion, and it is the highest-value grep in the PHP list. Also check comparisons on secrets: `==` performs type juggling, so a hash comparison should use `hash_equals` and a password check should use `password_verify`.

### Framework traps

**Laravel**

- `DB::raw`, `whereRaw`, `selectRaw`, `orderByRaw` with interpolated input.
- Mass assignment: `$guarded = []` on a model, or `Model::create($request->all())`.
- Blade: `{!! $x !!}` is unescaped output; `{{ $x }}` is not.
- `.env` committed to the repository, `APP_DEBUG=true` in production, a leaked `APP_KEY` (which signs sessions and encrypts cookies).
- Routes without `auth` middleware, and authorization gates or policies that exist but are never called.

**Symfony**

- `security.yaml` access control rules are ordered and first match wins.
- `@IsGranted` or `denyAccessUnlessGranted` present on some controllers and missing on others.
- Twig `|raw` filter.

## Python

### Manifests

```bash
cat .python-version runtime.txt 2>/dev/null
grep -E 'python_requires|requires-python' setup.py pyproject.toml 2>/dev/null
grep -iE '^(django|flask|fastapi)' requirements.txt 2>/dev/null
```

### Build and dependencies

**No build is required** for the analysis itself.

```bash
# Connected machine
pip download -d ./wheels -r requirements.txt
# Review machine
pip install --no-index --find-links ./wheels -r requirements.txt
```

### Sinks

```bash
# Query construction
grep -rn "cursor\.execute(\|\.raw(\|\.extra(\|RawSQL" --include='*.py' .
# Command execution
grep -rn "os\.system\|os\.popen\|subprocess\..*shell *= *True" --include='*.py' .
# Code execution
grep -rn "\beval(\|\bexec(\|compile(" --include='*.py' .
# Deserialization
grep -rn "pickle\.load\|marshal\.load\|jsonpickle\|yaml\.load(" --include='*.py' .
# Template injection
grep -rn "render_template_string\|Template(\|mark_safe\|autoescape" --include='*.py' --include='*.html' .
# Path handling
grep -rn "send_file\|send_from_directory\|open(\|os\.path\.join" --include='*.py' .
# Outbound
grep -rn "requests\.\|urlopen(" --include='*.py' .
# Crypto and randomness
grep -rn "hashlib\.md5\|hashlib\.sha1\|random\." --include='*.py' .
# Authorization via assert, which -O strips out
grep -rn "^\s*assert " --include='*.py' .
```

`yaml.load` without an explicit `SafeLoader` instantiates arbitrary Python objects. `random` is a Mersenne Twister and is not a CSPRNG: security values need `secrets`.

### Framework traps

**Django**

- `settings.py`: `DEBUG = True`, a hardcoded `SECRET_KEY`, `ALLOWED_HOSTS = ['*']`, and missing `SESSION_COOKIE_SECURE`, `CSRF_COOKIE_SECURE`, `SECURE_SSL_REDIRECT`, `SECURE_HSTS_SECONDS`, `X_FRAME_OPTIONS`.
- `@csrf_exempt` on any state-changing view.
- Views without `@login_required`, `LoginRequiredMixin`, or `PermissionRequiredMixin`.
- `Model.objects.get(pk=request.GET['id'])` with no ownership filter.
- `ModelForm` with `fields = '__all__'`, which is mass assignment.
- Django REST Framework: `DEFAULT_PERMISSION_CLASSES` left at `AllowAny`, per-view `permission_classes` missing, serializers with `fields = '__all__'`.

**Flask**

- `app.run(debug=True)`: the Werkzeug debugger is remote code execution if reachable.
- A hardcoded or absent `SECRET_KEY`. Flask sessions are signed client-side cookies, so the key is the session integrity.

## Node.js

### Manifests

```bash
grep -A5 '"engines"' package.json
grep -E '"(express|@nestjs/core|fastify|next)"' package.json
cat .npmrc 2>/dev/null
```

### Build and dependencies

**No build is required for JavaScript.** TypeScript needs resolved dependencies for type-aware rules, because types come from declaration files that have to resolve. Without `node_modules` a TypeScript scan comes back suspiciously clean.

```bash
# Connected machine
npm ci && tar czf npm-cache.tgz -C ~ .npm/_cacache
# or just move node_modules across, which is fine for review purposes
tar czf node_modules.tgz node_modules

# Review machine
tar xzf npm-cache.tgz -C ~ && npm ci --offline
```

### Sinks

```bash
# Command execution
grep -rn "child_process\|\.exec(\|execSync\|spawnSync" --include='*.js' --include='*.ts' src/
# Code execution
grep -rn "\beval(\|new Function(\|vm\.runIn" --include='*.js' --include='*.ts' src/
# Query construction
grep -rn "\.query(\`\|knex\.raw\|sequelize\.query\|\$where" --include='*.js' --include='*.ts' src/
# Path handling
grep -rn "sendFile\|path\.join\|fs\.readFile\|express\.static" --include='*.js' --include='*.ts' src/
# Prototype pollution
grep -rn "Object\.assign\|_\.merge\|_\.defaultsDeep\|__proto__" --include='*.js' --include='*.ts' src/
# Outbound
grep -rn "axios\.\|fetch(\|http\.request" --include='*.js' --include='*.ts' src/
# Crypto and randomness
grep -rn "createHash('md5')\|createHash('sha1')\|Math\.random()" --include='*.js' --include='*.ts' src/
# JWT
grep -rn "jwt\.decode\|jwt\.verify\|algorithms:" --include='*.js' --include='*.ts' src/
```

`jwt.decode` does not verify the signature. Any authorization decision made on its output is an authentication bypass. And `jwt.verify` without an explicit `algorithms` allowlist is open to algorithm confusion.

A NoSQL note: passing `req.body` straight into a MongoDB filter lets the caller inject operators, so a password field arriving as `{"$ne": null}` matches any user.

### Framework traps

**Express**

- `cors()` with no options allows any origin.
- Session config: `cookie.secure`, `httpOnly`, `sameSite`, and a hardcoded session secret.
- An error handler that returns `err.stack` to the client.
- No `helmet` or equivalent, so no security headers. See [HTTP Security Headers](/posts/http-security-headers).
- Route ordering: a permissive middleware mounted above a protected route applies to it.

**NestJS**

- `@UseGuards` present on some controllers and missing on others, and any `@Public()` escape-hatch decorator: enumerate every use of it.
- A global guard registered in the module vs per-controller guards, and which one actually wins.

## Frontend Frameworks

### What is the same everywhere

All three major frameworks escape by default, so frontend XSS almost always comes from an explicit escape hatch rather than from ordinary rendering. That makes the review tractable: find the escape hatches, then check what feeds them.

```bash
# Raw DOM sinks, framework-independent
grep -rn "innerHTML\|outerHTML\|insertAdjacentHTML\|document\.write" src/
grep -rn "\beval(\|new Function(" src/
# Cross-window messaging without an origin check
grep -rn "addEventListener('message'\|postMessage" src/
# Reverse tabnabbing
grep -rn 'target="_blank"' src/
# Token storage
grep -rn "localStorage\|sessionStorage" src/
```

A `message` listener with no `event.origin` check accepts messages from any frame. A JWT in `localStorage` is readable by any script on the origin, which turns any XSS into full session theft.

### React

```bash
grep -rn "dangerouslySetInnerHTML" src/
grep -rn "href={\|src={" src/                  # javascript: URLs from user data
grep -rn "useRef\|createRef\|findDOMNode" src/  # direct DOM access
grep -rn "REACT_APP_\|NEXT_PUBLIC_" src/ .env*  # anything here ships to the browser
```

`dangerouslySetInnerHTML` is the main one. The subtler React finding is a `href` or `src` bound to user-controlled data, because `javascript:` URLs still execute and React does not block them in every version.

### Angular

```bash
grep -rn "bypassSecurityTrust" --include='*.ts' src/
grep -rn "\[innerHTML\]" --include='*.html' src/
grep -rn "nativeElement\|ElementRef\|Renderer2" --include='*.ts' src/
grep -rn "canActivate\|canLoad" --include='*.ts' src/
grep -rn "sourceMap" angular.json
cat src/environments/environment.prod.ts
```

`bypassSecurityTrustHtml` on a value that came from an API response is a finding. `bypassSecurityTrustResourceUrl` on user-controlled data is usually a worse one.

### Vue

```bash
grep -rn "v-html" src/
grep -rn ":href=\|:src=" src/
grep -rn "Vue\.compile\|template:" src/
grep -rn "VUE_APP_" src/ .env*
```

`v-html` is Vue's escape hatch and behaves like `innerHTML`.

### Shared frontend config traps

- **Secrets in the bundle.** Any environment variable exposed to the build (`REACT_APP_*`, `NEXT_PUBLIC_*`, `VUE_APP_*`, Angular's `environment.ts`) is shipped to every visitor. An API key there is public, whatever the variable is named.
- **Source maps in production.** Enabled in the production build configuration, they ship readable source to everyone.
- **Client-side route guards treated as authorization.** Covered as its own technique in the methodology note, and it is the highest-yield frontend finding.
- **Verbose HTTP interceptors** attaching auth tokens to outbound requests without checking the destination host, which leaks the token to any third-party API the app calls.

## Ruby on Rails

### Manifests and dependencies

```bash
cat .ruby-version
grep -E "^ruby |rails" Gemfile
```

No build required for analysis.

```bash
# Connected machine
bundle package --all          # vendors gems into vendor/cache
# Review machine
bundle install --local
```

### Sinks and traps

```bash
grep -rn 'where("\|find_by_sql\|\.order("' app/
grep -rn "\bsend(\|constantize\|\beval(\|system(" app/
grep -rn "Marshal\.load\|YAML\.load" app/
grep -rn "render inline:\|\braw(\|html_safe" app/
grep -rn "permit!\|skip_before_action :verify_authenticity_token" app/
```

- `permit!` disables strong parameters entirely, which is mass assignment.
- `skip_before_action :verify_authenticity_token` disables CSRF protection for that controller.
- `send` with a user-controlled method name calls arbitrary methods on the object.
- Check `config.force_ssl` and whether credentials live in `config/credentials.yml.enc` or in plain `secrets.yml`.

## Go

### Manifests and dependencies

```bash
grep "^go " go.mod        # language version
```

**A build is required** for most analysers.

```bash
# Connected machine
go mod vendor
# Review machine
GOFLAGS=-mod=vendor GOPROXY=off go build ./...
```

### Sinks and traps

```bash
grep -rn "fmt\.Sprintf" --include='*.go' . | grep -i "select\|insert\|update\|delete"
grep -rn "exec\.Command" --include='*.go' .
grep -rn "text/template" --include='*.go' .        # does not escape; html/template does
grep -rn "template\.HTML\|template\.JS\|template\.URL" --include='*.go' .
grep -rn "math/rand" --include='*.go' .            # not a CSPRNG; use crypto/rand
grep -rn "crypto/md5\|crypto/sha1" --include='*.go' .
grep -rn "InsecureSkipVerify" --include='*.go' .
```

The two Go-specific ones: importing `text/template` instead of `html/template` for HTML output removes contextual escaping entirely, and the `template.HTML` type conversion marks a string as trusted, which is the Go equivalent of `dangerouslySetInnerHTML`.

## Cross-Stack Notes

### Reading a stack you do not know

You will be handed an unfamiliar framework sooner or later. The four questions at the top of this note are the same in every ecosystem, and they are answerable in about an hour:

1. **How does a request reach code?** Find the routing mechanism. That gives you the entry point inventory.
2. **How does the framework say "this requires authentication"?** Find one protected handler and one unprotected one, and diff them. Then check whether the default is deny or allow, because that decides whether a forgotten annotation is safe or public.
3. **How does it build queries, and what is the parameterised form?** Find one correct call, then grep for everything that is not it.
4. **What is the escape hatch for raw output?** Every templating engine has one. Find its name and grep for it.

### Dependency inventory without a network

The manifest gives you the direct dependencies and the lockfile gives you the transitive tree. Produce the list on the review machine, then check versions on a connected machine if the engagement permits taking it out.

```bash
# .NET
grep -rhoE '<PackageReference Include="[^"]+" Version="[^"]+"' --include='*.csproj' . | sort -u
# Node
jq -r '.packages | to_entries[] | "\(.key) \(.value.version)"' package-lock.json | sort -u
# Python
pip freeze
# PHP
jq -r '.packages[] | "\(.name) \(.version)"' composer.lock
# Java
mvn -o dependency:list -DoutputFile=deps.txt
# Ruby
grep -A1000 "^GEM" Gemfile.lock
# Go
cat go.sum | awk '{print $1, $2}' | sort -u
```

> The process this plugs into is in [Secure Code Review: Process and Methodology](/posts/secure-code-review-methodology).
