---
author: Kayra
pubDatetime: 2026-05-28T00:00:00Z
title: "DevSecOps — Exam Cheatsheet"
description: "Personal quick-reference for the DevSecOps exam: SCA, SAST, DAST, IaC, CaC, and Vulnerability Management commands and pipeline jobs."
tags: ["devsecops", "cheatsheet"]
category: notes
draft: false
featured: false
---

# DevSecOps — Exam Cheatsheet

> Covers: **SCA · SAST · DAST · IaC · CaC · Vulnerability Management**.
> Always save tool output in machine-readable format (`--json`).

---

## 1. FULL PIPELINE (`.gitlab-ci.yml`)

```yaml
services:
  - docker:dind       # docker daemon inside the runner (docker-in-docker)

stages:
  - build
  - test
  - release
  - preprod
  - integration
  - prod

build:
  stage: build
  image: python:3.6
  before_script:
   - pip3 install --upgrade virtualenv
  script:
   - virtualenv env                       # create venv
   - source env/bin/activate              # activate venv
   - pip install -r requirements.txt      # install deps
   - python manage.py check               # sanity check

test:
  stage: test
  image: python:3.6
  before_script:
   - pip3 install --upgrade virtualenv
  script:
   - virtualenv env
   - source env/bin/activate
   - pip install -r requirements.txt
   - python manage.py test taskManager

# Software Component Analysis
sca-frontend:
  stage: build
  image: node:alpine3.10
  script:
    - npm install
    - npm install -g retire@5.0.0
    - retire --outputformat json --outputpath retirejs-report.json --severity high
  artifacts:
    paths: [retirejs-report.json]
    when: always
    expire_in: one week

sca-backend:
  stage: build
  script:
    - docker pull hysnsec/safety
    - |
      cat > .safety-policy.yml <<EOF
      security:
        ignore-vulnerabilities: {}
      EOF
    - docker run --rm -v $(pwd):/src hysnsec/safety check -r requirements.txt --json > oast-results.json
  artifacts:
    paths: [oast-results.json]
    when: always
  allow_failure: true

# Git Secrets Scanning
secrets-scanning:
  stage: build
  script:
    - docker run -v $(pwd):/src --rm hysnsec/trufflehog filesystem /src --json | tee trufflehog-output.json
  artifacts:
    paths: [trufflehog-output.json]
    when: always
    expire_in: one week
  allow_failure: true

detect-secrets:
  stage: build
  image: python:3.6
  script:
    - pip install detect-secrets==1.4.0
    - detect-secrets scan --all-files > detect-secrets-output.json
    # no entropy scanning:
    # - detect-secrets scan --all-files --disable-plugin Base64HighEntropyString --disable-plugin HexHighEntropyString > detect-secrets-output.json
  artifacts:
    paths: [detect-secrets-output.json]
    when: always
    expire_in: one week
  allow_failure: true

# Static Application Security Testing
sast:
  stage: build
  script:
    - docker pull hysnsec/bandit
    - docker run --user $(id -u):$(id -g) -v $(pwd):/src --rm hysnsec/bandit -r /src -f json -o /src/bandit-output.json
  artifacts:
    paths: [bandit-output.json]
    when: always
  allow_failure: true

# Dynamic Application Security Testing
nikto:
  stage: integration
  script:
    - docker pull hysnsec/nikto
    - docker run --rm -v $(pwd):/tmp hysnsec/nikto -h prod-1bhwjtpi -o /tmp/nikto-output.xml
  artifacts:
    paths: [nikto-output.xml]
    when: always

sslscan:
  stage: integration
  script:
    - docker pull hysnsec/sslyze
    - docker run --rm -v $(pwd):/tmp hysnsec/sslyze prod-1bhwjtpi.lab.practical-devsecops.training:443 --json_out /tmp/sslyze-output.json
  artifacts:
    paths: [sslyze-output.json]
    when: always

nmap:
  stage: integration
  script:
    - docker pull hysnsec/nmap
    - docker run --rm -v $(pwd):/tmp hysnsec/nmap prod-1bhwjtpi -oX /tmp/nmap-output.xml
  artifacts:
    paths: [nmap-output.xml]
    when: always

zap-baseline:
  stage: integration
  script:
    - docker pull hysnsec/zap:2.16.1
    - docker run --user $(id -u):$(id -g) --rm -v $(pwd):/zap/wrk:rw hysnsec/zap:2.16.1 zap-baseline.py -t https://prod-1bhwjtpi.lab.practical-devsecops.training -J zap-output.json
  after_script:
    - docker rmi hysnsec/zap:2.16.1   # free disk space
  artifacts:
    paths: [zap-output.json]
    when: always
  allow_failure: true

# Infrastructure as Code  (set env vars + files first!)
ansible-hardening:
  stage: prod
  image: willhallonline/ansible:2.16-ubuntu-22.04
  before_script:
    - mkdir -p ~/.ssh
    - echo "$DEPLOYMENT_SERVER_SSH_PRIVKEY" | tr -d '\r' > ~/.ssh/id_rsa
    - chmod 600 ~/.ssh/id_rsa
    - eval "$(ssh-agent -s)"
    - ssh-add ~/.ssh/id_rsa
    - ssh-keyscan -H $DEPLOYMENT_SERVER >> ~/.ssh/known_hosts
  script:
    - echo -e "[prod]\n$DEPLOYMENT_SERVER" >> inventory.ini
    - ansible-galaxy install dev-sec.os-hardening
    - ansible-playbook -i inventory.ini ansible-hardening.yml

# Compliance as Code  (set env vars + files first!)
inspec:
  stage: prod
  only:
    - "main"
  environment: production
  before_script:
    - mkdir -p ~/.ssh
    - echo "$DEPLOYMENT_SERVER_SSH_PRIVKEY" | tr -d '\r' > ~/.ssh/id_rsa
    - chmod 600 ~/.ssh/id_rsa
    - eval "$(ssh-agent -s)"
    - ssh-add ~/.ssh/id_rsa
    - ssh-keyscan -H $DEPLOYMENT_SERVER >> ~/.ssh/known_hosts
  script:
    - docker run --rm -v ~/.ssh:/root/.ssh -v $(pwd):/share hysnsec/inspec exec https://github.com/dev-sec/linux-baseline.git -t ssh://root@$DEPLOYMENT_SERVER -i ~/.ssh/id_rsa --chef-license accept --reporter json:inspec-output.json
  artifacts:
    paths: [inspec-output.json]
    when: always

# Vulnerability Management (DefectDojo upload)
sast-with-vm:
  stage: build
  before_script:
    - apk add py-pip py-requests curl
    - curl https://gitlab.practical-devsecops.training/-/snippets/28/raw -o upload-results.py
  script:
    - docker pull hysnsec/bandit
    - docker run --user $(id -u):$(id -g) -v $(pwd):/src --rm hysnsec/bandit -r /src -f json -o /src/bandit-output.json
  after_script:
    - python3 upload-results.py --host $DOJO_HOST --api_key $DOJO_API_TOKEN --engagement_id 1 --product_id 1 --lead_id 1 --environment "Production" --result_file bandit-output.json --scanner "Bandit Scan"
  artifacts:
    paths: [bandit-output.json]
    when: always
```

**Key YAML knobs:** `artifacts.when: always` → keep report even if job fails · `expire_in` → artifact TTL · `allow_failure: true` → job can fail without breaking the pipeline.

---

## 2. SCA — SOFTWARE COMPONENT ANALYSIS

> Target: < 15 min.

Common clone (Python target):
```bash
git clone https://gitlab.practical-devsecops.training/pdso/django.nv webapp && cd webapp
```
Common Node 20 install (needed by retire / auditjs / snyk-from-source):
```bash
mkdir -p /etc/apt/keyrings
curl -fsSL https://deb.nodesource.com/gpgkey/nodesource-repo.gpg.key | gpg --dearmor -o /etc/apt/keyrings/nodesource.gpg
NODE_MAJOR=20
echo "deb [signed-by=/etc/apt/keyrings/nodesource.gpg] https://deb.nodesource.com/node_$NODE_MAJOR.x nodistro main" | tee /etc/apt/sources.list.d/nodesource.list
apt update && apt install nodejs -y
```

---

### Safety (Python deps)
```bash
pip3 install safety==2.3.5
# if build error: apt-get update && apt-get install -y build-essential python3-dev
safety check --help
# if policy error:
cat > .safety-policy.yml <<EOF
security:
  ignore-vulnerabilities: {}
EOF
safety check -r requirements.txt --json | tee safety-output.json
```
```yaml
sca-backend:
  stage: build
  script:
    - docker pull hysnsec/safety
    - |
      cat > .safety-policy.yml <<EOF
      security:
        ignore-vulnerabilities: {}
      EOF
    - docker run --rm -v $(pwd):/src hysnsec/safety check -r requirements.txt --json > oast-results.json
  artifacts:
    paths: [oast-results.json]
    when: always
  allow_failure: true
```

### RetireJS (JS/Node deps)
```bash
npm install -g retire@5.0.0
retire --outputformat json --outputpath no-npm-install-retire-output.json   # before npm install
npm install
retire --outputformat json --outputpath retire_output.json
retire --severity critical --outputformat json --outputpath retire_output.json
cat retire_output.json | jq .
```
```yaml
sca-frontend:
  stage: build
  image: node:alpine3.10
  script:
    - npm install
    - npm install -g retire@5.0.0
    - retire --outputformat json --outputpath retirejs-report.json --severity high
  artifacts:
    paths: [retirejs-report.json]
    when: always
    expire_in: one week
```

### OWASP Dependency-Check (Java target: WebGoat)
```bash
git clone https://github.com/WebGoat/WebGoat.git webapp
apt update && apt install openjdk-17-jre -y
wget -O /opt/v12.1.6.zip https://github.com/dependency-check/DependencyCheck/releases/download/v12.1.6/dependency-check-12.1.6-release.zip
unzip /opt/v12.1.6.zip -d /opt/
export PATH=/opt/dependency-check/bin:$PATH
dependency-check.sh --scan webapp --format "JSON" --project "Webgoat" --out /opt
# faster + fail gates:
dependency-check.sh --scan webapp --format "JSON" --project "Webgoat" --nvdApiKey [KEY] --out /opt
dependency-check.sh --scan webapp --format "JSON" --project "Webgoat" --failOnCVSS 4 --out /opt
```
> **Slow!** First run 20–30 min building NVD DB. Use an NVD API key (`--nvdApiKey`) → https://nvd.nist.gov/developers/request-an-api-key

Suppression file (mark FP):
```xml
<?xml version="1.0" encoding="UTF-8"?>
<suppressions xmlns="https://jeremylong.github.io/DependencyCheck/dependency-suppression.1.3.xsd">
    <suppress>
        <notes><![CDATA[ Ignore underscore-min.js issue as FP ]]></notes>
        <vulnerabilityName>CVE-2021-23358</vulnerabilityName>
    </suppress>
</suppressions>
```
`run-depcheck.sh` (persistent data/reports + docker):
```sh
#!/bin/sh
DATA_DIRECTORY="$PWD/data"
REPORT_DIRECTORY="$PWD/reports"
if [ ! -d "$DATA_DIRECTORY" ]; then
  echo "Initially creating persistent directories"
  mkdir -p "$DATA_DIRECTORY"; chmod -R 777 "$DATA_DIRECTORY"
  mkdir -p "$REPORT_DIRECTORY"; chmod -R 777 "$REPORT_DIRECTORY"
fi
docker run --rm \
  --volume $(pwd):/src \
  --volume "$DATA_DIRECTORY":/usr/share/dependency-check/data \
  --volume "$REPORT_DIRECTORY":/reports \
  hysnsec/dependency-check \
  --scan /src --format "JSON" --project "Webgoat" --failOnCVSS 4 \
  --out /reports --nvdApiKey "$NVD_API" --disableKnownExploited --disableCentral
```
**CI var:** `NVD_API` = your NVD API key.
```yaml
odc-backend:
  stage: test
  image: gitlab/dind:latest
  script:
    - chmod +x ./run-depcheck.sh
    - mkdir -p reports
    - ./run-depcheck.sh > reports/dependency-check-report.json
  artifacts:
    paths:
      - reports/dependency-check-report.json
    when: always
    expire_in: one week
```

### Snyk
```bash
wget -O /usr/local/bin/snyk https://github.com/snyk/cli/releases/download/v1.984.0/snyk-linux
chmod +x /usr/local/bin/snyk
snyk auth YOUR_SNYK_API_TOKEN_HERE      # or: export SNYK_TOKEN=...
# (install Node 20, then) npm install
snyk test --json . > output.json
snyk test --strict-out-of-sync=false --json . > output.json   # if lockfile out of sync
```
Sign up free → select CLI → token at https://app.snyk.io/account . **CI var:** `SNYK_TOKEN`.
```yaml
oast-snyk:
  stage: build
  image: node:alpine3.10
  before_script:
    - wget -O snyk https://github.com/snyk/cli/releases/download/v1.1156.0/snyk-alpine
    - chmod +x snyk
    - mv snyk /usr/local/bin/
  script:
    - npm install
    - snyk auth $SNYK_TOKEN
    - snyk test --json > snyk-results.json
    - cat snyk-results.json
  artifacts:
    paths: [snyk-results.json]
    when: always
    expire_in: one week
  allow_failure: true
```

### AuditJS (Sonatype OSS Index)
```bash
npm install -g auditjs@4.0.46
auditjs config
auditjs ossi -q -j | tee auditjs-output.json
```
Register OSS Index → https://guide.sonatype.com/register . **CI vars:** `OSS_INDEX_USER` (email), `OSS_INDEX_TOKEN` (API token).
```yaml
auditjs:
  image: node:alpine3.10
  stage: test
  before_script:
    - npm install -g auditjs@4.0.46
  script:
    - npm install
    - auditjs ossi --user "${OSS_INDEX_USER}" --password "${OSS_INDEX_TOKEN}" -q -j > auditjs-output.json
  artifacts:
    paths: [auditjs-output.json]
    when: always
    expire_in: one week
  allow_failure: true
```

### Bundler-audit (Ruby)
```bash
curl -fsSL https://github.com/rbenv/rbenv-installer/raw/HEAD/bin/rbenv-installer | bash
export PATH="~/.rbenv/bin:$PATH"
apt update && apt install build-essential libreadline-dev -y
rbenv install --verbose 2.6.5
export PATH="/root/.rbenv/versions/2.6.5/bin:$PATH"
gem install --user-install bundler-audit
export PATH="~/.gem/ruby/2.6.0/bin/:$PATH"
bundle-audit
```
```yaml
bundler-audit:
  stage: test
  script:
    - docker run --rm -v $(pwd):/src -w /src hysnsec/bundle-audit check --format json --output bundle-audit-output.json
  artifacts:
    paths: [bundle-audit-output.json]
    when: always
    expire_in: one week
  allow_failure: true
```

### Composer (PHP)
```bash
git clone https://gitlab.practical-devsecops.training/pdso/php.git && cd php
apt update && apt install -y software-properties-common
add-apt-repository -y ppa:ondrej/php && apt update
apt install -y php7.4 php7.4-gd php7.4-intl php7.4-xsl php7.4-mbstring php7.4-curl
php -r "copy('https://getcomposer.org/installer', 'composer-setup.php');"
php composer-setup.php --version=2.6.6 --install-dir=/usr/local/bin --filename=composer
php -r "unlink('composer-setup.php');"
composer install
composer audit -f json | tee results.json
```
```yaml
oast-backend:
  stage: build
  image: php:7.4
  before_script:
    - php -r "copy('https://getcomposer.org/installer', 'composer-setup.php');"
    - php composer-setup.php --version=2.6.6 --install-dir=/usr/local/bin --filename=composer
    - php -r "unlink('composer-setup.php');"
    - apt update
    - apt install unzip
  script:
    - composer install
    - composer audit -f json | tee composer-output.json
  artifacts:
    paths: [composer-output.json]
    when: always
  allow_failure: true
```

### OSV-Scanner
```bash
apt update && apt install npm -y && npm install
wget -O /usr/bin/osv-scanner https://github.com/google/osv-scanner/releases/download/v1.4.0/osv-scanner_1.4.0_linux_amd64 && sudo chmod +x /usr/bin/osv-scanner
osv-scanner .
```
```yaml
osv-scanner:
  stage: test
  image: golang:1.22-alpine3.19
  before_script:
    - apk add npm
    - npm install
  script:
    - go install github.com/google/osv-scanner/cmd/osv-scanner@v1
    - osv-scanner --json . > osv-report.json
  artifacts:
    paths: [osv-report.json]
    when: always
  allow_failure: true
```

### Trivy (filesystem)
```bash
wget https://github.com/aquasecurity/trivy/releases/download/v0.69.3/trivy_0.69.3_Linux-64bit.deb && dpkg -i trivy_*.deb
trivy filesystem .
# DB error fix:
export TRIVY_DB_REPOSITORY=public.ecr.aws/aquasecurity/trivy-db
```
```yaml
trivy_scanning:
  stage: test
  script:
    - docker run --rm -v $(pwd):/src hysnsec/trivy fs . --exit-code 1 -f json -o trivy-report.json
  artifacts:
    paths: [trivy-report.json]
    when: always
    expire_in: one week
  allow_failure: true
```

### Pip-licenses (license compliance)
```bash
pip install pip-licenses==5.0.0
pip-licenses --format=html
```
```yaml
license:
  stage: test
  image: python:3.10
  before_script:
   - pip3 install --upgrade virtualenv
  script:
    - virtualenv env
    - source env/bin/activate
    - pip install -r requirements.txt
    - pip install pip-licenses==5.0.0
    - pip-licenses --allow-only "MIT License;BSD License" --format=json --output-file=license-results.json
  artifacts:
    paths: [license-results.json]
    when: always
  allow_failure: true
```

---

### SCA tool → ecosystem map

| Tool | Ecosystem | Output flag |
|---|---|---|
| Safety | Python (`requirements.txt`) | `--json` |
| RetireJS | JS/Node | `--outputformat json` |
| Dependency-Check | Java + multi | `--format JSON` |
| Snyk | multi (Node-based) | `--json` |
| AuditJS | Node (OSS Index) | `-j` |
| Bundler-audit | Ruby (`Gemfile`) | `--format json` |
| Composer audit | PHP | `-f json` |
| OSV-Scanner | multi | `--json` |
| Trivy fs | multi + containers | `-f json` |
| Pip-licenses | Python licenses | `--format=json` |

---

## 3. SAST — STATIC APPLICATION SECURITY TESTING

### TruffleHog (secret scanning in git)
```bash
wget https://github.com/trufflesecurity/trufflehog/releases/download/v3.79.0/trufflehog_3.79.0_linux_amd64.tar.gz
tar -xvf trufflehog_3.79.0_linux_amd64.tar.gz
chmod +x trufflehog && mv trufflehog /usr/local/bin/
# scan over HTTP
trufflehog git http://gitlab-ce-1bhwjtpi.lab.practical-devsecops.training/root/django-nv.git --json
```
SSH access setup + scan:
```bash
eval "$(ssh-agent -s)"
chmod 600 ~/.ssh/id_rsa
ssh-add ~/.ssh/id_rsa
cat << EOF > ~/.ssh/config
Host gitlab-ce-1bhwjtpi
    HostName gitlab-ce-1bhwjtpi
    User git
    IdentityFile ~/.ssh/id_rsa
    IdentitiesOnly yes
EOF
trufflehog git git@gitlab-ce-1bhwjtpi:root/django-nv.git --json | tee secret.json
```
```yaml
git-secrets:
  stage: build
  script:
    - docker run -v $(pwd):/src --rm hysnsec/trufflehog git http://gitlab-ce-1bhwjtpi.lab.practical-devsecops.training/root/django-nv.git --fail --json | tee trufflehog-output.json
  artifacts:
    paths: [trufflehog-output.json]
    when: always
    expire_in: one week
  allow_failure: true
```

### detect-secrets (baseline secret scanning)
```bash
pip3 install detect-secrets==1.4.0   # Python 3.6-compatible
detect-secrets scan > .secrets.baseline
detect-secrets scan --all-files > detect-secrets-output.json

# no entropy scanning
detect-secrets scan --disable-plugin Base64HighEntropyString --disable-plugin HexHighEntropyString > .secrets.baseline
detect-secrets scan --all-files --disable-plugin Base64HighEntropyString --disable-plugin HexHighEntropyString > detect-secrets-output.json

detect-secrets audit .secrets.baseline
git ls-files -z | xargs -0 detect-secrets-hook --baseline .secrets.baseline
```
```yaml
detect-secrets:
  stage: build
  image: python:3.6
  script:
    - pip install detect-secrets==1.4.0
    - detect-secrets scan --all-files > detect-secrets-output.json
    # no entropy scanning:
    # - detect-secrets scan --all-files --disable-plugin Base64HighEntropyString --disable-plugin HexHighEntropyString > detect-secrets-output.json
  artifacts:
    paths: [detect-secrets-output.json]
    when: always
    expire_in: one week
  allow_failure: true
```

### Bandit (Python SAST)
```bash
pip3 install bandit==1.8.5
bandit -r . -f json | tee bandit-output.json
```
```yaml
sast:
  stage: build
  script:
    - docker pull hysnsec/bandit
    - docker run --user $(id -u):$(id -g) -v $(pwd):/src --rm hysnsec/bandit -r /src -f json -o /src/bandit-output.json
  artifacts:
    paths: [bandit-output.json]
    when: always
  allow_failure: true
```
**Baseline (mark existing findings as FP):** save a scan as `baseline.json`; everything in it is treated as a known/false positive on the next run (`bandit -r . -b baseline.json`).
```json
{
  "results": [
    {
      "code": "12 username = 'admin'\n13 password = 'secret'\n...",
      "filename": "./flaskblog/config.py",
      "issue_confidence": "MEDIUM",
      "issue_cwe": { "id": 259, "link": "https://cwe.mitre.org/data/definitions/259.html" },
      "issue_severity": "LOW",
      "issue_text": "Possible hardcoded password: 'secret'",
      "line_number": 13,
      "line_range": [13, 14, 15],
      "more_info": "https://bandit.readthedocs.io/en/1.7.4/plugins/b105_hardcoded_password_string.html",
      "test_id": "B105",
      "test_name": "hardcoded_password_string"
    }
  ]
}
```

### GoSec (Go SAST)
```bash
git clone https://gitlab.practical-devsecops.training/pdso/golang.git webapp && cd webapp
curl -s https://dl.google.com/go/go1.17.4.linux-amd64.tar.gz | tar xvz -C /usr/local
export GOROOT=/usr/local/go
export GOPATH=$HOME/go
export PATH=$GOPATH/bin:$GOROOT/bin:$PATH
curl -sfL https://raw.githubusercontent.com/securego/gosec/master/install.sh | sh -s -- -b $(go env GOPATH)/bin v2.4.0
go get -u github.com/securego/gosec/v2/cmd/gosec
gosec ./...
gosec -exclude=G104 ./...        # exclude a rule
```
Push lab repo to local GitLab (for CI):
```bash
git remote rename origin old-origin
git remote add origin git@gitlab-ce-1bhwjtpi:root/golang.git
git push -u origin --all
```
```yaml
sast:
  stage: build
  script:
    - docker run --rm -v $(pwd):/src -w /src securego/gosec -fmt json -out gosec-output.json ./...
  artifacts:
    paths: [gosec-output.json]
    when: always
  allow_failure: true
```

### Semgrep (multi-language, custom rules)
```bash
pip3 install semgrep==1.124.0
pip3 install --upgrade requests
semgrep --config "p/secrets"     # registry ruleset
semgrep --config "p/bandit" .
semgrep login
semgrep -f myrule.yaml .          # run a custom rule file
```
Custom rule examples:
```yaml
# csrf_hunting.yaml
rules:
- id: possible-csrf
  patterns:
  - pattern-inside: |
      @csrf_exempt
      def $FUNC($X):
          ...
  message: "Possible CSRF"
  languages: [python]
  severity: WARNING
- id: no-csrf-middleware
  patterns:
  - pattern: MIDDLEWARE_CLASSES=(...)
  - pattern-not: MIDDLEWARE_CLASSES=(...,'django.middleware.csrf.CsrfViewMiddleware',...)
  message: "No CSRF middleware"
  languages: [python]
  severity: WARNING
```
```yaml
# debug_enable.yaml
rules:
- id: debug-enabled
  patterns:
  - pattern: DEBUG=True
  message: "Django DEBUG=True — leaks info in production."
  metadata:
    cwe: 'CWE-489: Active Debug Code'
    owasp: 'A6: Security Misconfiguration'
  severity: WARNING
  languages: [python]
```
```yaml
# insecure_redirect.yaml
rules:
- id: CWE-601
  pattern: |
    return redirect(request.$M.get(...))
  message: "Insecure Redirect"
  severity: WARNING
  languages: [python]
```
```yaml
semgrep:
  stage: build
  script:
   - docker run --rm -v ${PWD}:/src returntocorp/semgrep semgrep --config auto --output semgrep-output.json --json
  artifacts:
    paths: [semgrep-output.json]
    when: always
    expire_in: one week
  allow_failure: true
```

### Gitleaks (secret scanning)
```bash
wget https://github.com/gitleaks/gitleaks/releases/download/v8.18.1/gitleaks_8.18.1_linux_x64.tar.gz
tar -xvzf gitleaks_8.18.1_linux_x64.tar.gz && mv gitleaks /usr/local/bin
gitleaks detect . --report-path gitleaks-output.txt
gitleaks detect . --report-path gitleaks-redact50.txt --redact=50   # redact 50% of secret
```
```yaml
gitleaks:
  stage: build
  script:
    - docker pull zricethezav/gitleaks
    - docker run --user $(id -u):$(id -g) -v $(pwd):/path -w /path zricethezav/gitleaks detect . --report-path gitleaks-output.json
  artifacts:
    paths: [gitleaks-output.json]
    when: always
    expire_in: one week
  allow_failure: true
```

---

## 4. DAST — DYNAMIC APPLICATION SECURITY TESTING

**CI/CD vars** (Project → Settings → CI/CD → Variables): `PROD_USERNAME=root`, `PROD_HOSTNAME=prod-1bhwjtpi`, `PROD_SSH_PRIVKEY=<prod machine private key>`.
> Storing SSH keys in GitLab vars = plaintext risk. For prod, use a key-management solution (e.g. HashiCorp Vault) for storage/rotation/access control.

Grab the prod private key:
```bash
ssh root@prod-1bhwjtpi
more /root/.ssh/id_rsa
```

### Deploy job (build prod target before scanning)
```yaml
prod:
  stage: deploy
  image: kroniak/ssh-client:3.6
  environment: production
  only:
      - main
  before_script:
   - mkdir -p ~/.ssh
   - echo "$PROD_SSH_PRIVKEY" > ~/.ssh/id_rsa
   - chmod 600 ~/.ssh/id_rsa
   - eval "$(ssh-agent -s)"
   - ssh-add ~/.ssh/id_rsa
   - ssh-keyscan -H $PROD_HOSTNAME >> ~/.ssh/known_hosts
  script:
   - echo
   - |
      ssh $PROD_USERNAME@$PROD_HOSTNAME << EOF
        docker login -u ${CI_REGISTRY_USER} -p ${CI_REGISTRY_PASSWORD} ${CI_REGISTRY}
        docker rm -f django.nv
        docker run -d --name django.nv -p 8000:8000 $CI_REGISTRY_IMAGE:$CI_COMMIT_SHA
      EOF
```

### Nikto (web server scanner)
```bash
apt install -y libnet-ssleay-perl
git clone https://github.com/sullo/nikto
cd nikto/program
git checkout tags/2.1.6
./nikto.pl -output nikto_output.xml -h prod-1bhwjtpi
```
```yaml
nikto:
  stage: test
  script:
    - docker pull hysnsec/nikto
    - docker run --rm -v $(pwd):/tmp hysnsec/nikto -h prod-1bhwjtpi -o /tmp/nikto-output.xml
  artifacts:
    paths: [nikto-output.xml]
    when: always
```

### SSLyze (TLS/SSL config)
```bash
pip3 install sslyze==6.0.0
sslyze --json_out sslyze-output.json prod-1bhwjtpi.lab.practical-devsecops.training:443
```
```yaml
sslyze:
  stage: test
  script:
    - docker pull hysnsec/sslyze
    - docker run --rm -v $(pwd):/tmp hysnsec/sslyze prod-1bhwjtpi.lab.practical-devsecops.training:443 --json_out /tmp/sslyze-output.json
  artifacts:
    paths: [sslyze-output.json]
    when: always
```

### Nmap (port/service scan)
```bash
apt-get update && apt-get install nmap -y
nmap prod-1bhwjtpi -oX nmap_out.xml
```
```yaml
nmap:
  stage: test
  script:
    - docker pull hysnsec/nmap
    - docker run --rm -v $(pwd):/tmp hysnsec/nmap prod-1bhwjtpi -oX /tmp/nmap-output.xml
  artifacts:
    paths: [nmap-output.xml]
    when: always
```

### OWASP ZAP (baseline scan)
```bash
docker run --rm hysnsec/zap:2.16.1 zap-baseline.py -t https://prod-1bhwjtpi.lab.practical-devsecops.training
docker run --user $(id -u):$(id -g) -w /zap -v $(pwd):/zap/wrk:rw --rm hysnsec/zap:2.16.1 zap-baseline.py -t https://prod-1bhwjtpi.lab.practical-devsecops.training -J zap-output.json
```
```yaml
zap-baseline:
  stage: integration
  before_script:
    - docker pull hysnsec/zap:2.16.1
  script:
    - docker run --user $(id -u):$(id -g) -w /zap -v $(pwd):/zap/wrk:rw --rm hysnsec/zap:2.16.1 zap-baseline.py -t https://prod-1bhwjtpi.lab.practical-devsecops.training -J zap-output.json
  after_script:
    - docker rmi hysnsec/zap:2.16.1   # free disk space
  artifacts:
    paths: [zap-output.json]
    when: always
  allow_failure: true
```

### Nuclei (template-based scanner)
```bash
wget https://github.com/projectdiscovery/nuclei/releases/download/v3.4.4/nuclei_3.4.4_linux_amd64.zip
unzip nuclei_3.4.4_linux_amd64.zip
mv nuclei /usr/local/bin/nuclei
nuclei -u https://prod-1bhwjtpi.lab.practical-devsecops.training -j -o nuclei-output.json
# run a specific template set
git clone https://github.com/projectdiscovery/nuclei-templates.git && cd nuclei-templates
nuclei -u https://prod-1bhwjtpi.lab.practical-devsecops.training -t http/misconfiguration/
# via docker
docker pull projectdiscovery/nuclei:v3.4.4
docker run --user $(id -u):$(id -g) -w /nuclei -v $(pwd):/nuclei:rw --rm projectdiscovery/nuclei:v3.4.4 -u https://prod-1bhwjtpi.lab.practical-devsecops.training -j -o nuclei-output.json
```
```yaml
nuclei:
  stage: integration
  script:
    - docker run --user $(id -u):$(id -g) -w /nuclei -v $(pwd):/nuclei:rw --rm projectdiscovery/nuclei:v2.9.6 -u https://prod-1bhwjtpi.lab.practical-devsecops.training -j -o nuclei-output.json
  artifacts:
    paths: [nuclei-output.json]
    when: always
  allow_failure: true
```

---

## 5. IaC — INFRASTRUCTURE AS CODE

### Ansible (config management + hardening)
```bash
pip3 install ansible==9.13.0 ansible-lint==6.8.1
cat > inventory.ini <<EOL
# DevSecOps Studio Inventory
[devsecops]
devsecops-box-1bhwjtpi
[prod]
prod-1bhwjtpi
EOL
ssh-keyscan -H prod-1bhwjtpi devsecops-box-1bhwjtpi >> ~/.ssh/known_hosts

# ad-hoc modules
ansible -i inventory.ini prod -m apt -a "name=ntp state=present"
ansible -i inventory.ini all  -m command -a "bash --version"
ansible -i inventory.ini prod -m shell -a "uptime"
ansible -i inventory.ini all  -m ping
ansible -i inventory.ini gitlab --list-hosts
ansible-doc -l | grep shell
```
Run a playbook:
```bash
cat > playbook.yml <<EOL
---
- name: Example playbook to install firewalld
  hosts: prod
  remote_user: root
  become: yes
  gather_facts: no
  vars:
    state: present
  tasks:
  - name: ensure firewalld is at the latest version
    apt:
      name: firewalld
      update_cache: yes
EOL
ansible-playbook -i inventory.ini playbook.yml
```
Roles via ansible-galaxy:
```bash
ansible-galaxy install secfigo.terraform        # then reference it under `roles:`
ansible-galaxy install dev-sec.os-hardening
```
Global config (`/etc/ansible/ansible.cfg`):
```ini
[defaults]
stdout_callback = yaml
deprecation_warnings = False
host_key_checking = False
retry_files_enabled = False
inventory = /inventory.ini
```
**OS hardening playbook** (`ansible-hardening.yml`):
```yaml
---
- name: Playbook to harden Ubuntu OS.
  hosts: prod
  remote_user: root
  become: yes
  vars:
    os_hardening_sysctl_ignore:   # read-only sysctls in newer Ubuntu — skip them
      - kernel.randomize_va_space
      - kernel.core_uses_pid
      - vm.mmap_rnd_bits
      - vm.mmap_rnd_compat_bits
      - kernel.kexec_load_disabled
      - fs.suid_dumpable
  roles:
    - role: dev-sec.os-hardening
      ignore_errors: yes
```
```yaml
ansible-hardening:
  stage: prod
  image: willhallonline/ansible:2.16-ubuntu-22.04
  before_script:
    - mkdir -p ~/.ssh
    - echo "$DEPLOYMENT_SERVER_SSH_PRIVKEY" | tr -d '\r' > ~/.ssh/id_rsa
    - chmod 600 ~/.ssh/id_rsa
    - eval "$(ssh-agent -s)"
    - ssh-add ~/.ssh/id_rsa
    - ssh-keyscan -H $DEPLOYMENT_SERVER >> ~/.ssh/known_hosts
  script:
    - echo -e "[prod]\n$DEPLOYMENT_SERVER" >> inventory.ini
    - ansible-galaxy install dev-sec.os-hardening
    - ansible-playbook -i inventory.ini ansible-hardening.yml
```

### Ansible Vault (secrets)
```bash
echo "StrongP@ssw0rd" > /secret
ansible-vault encrypt /secret --ask-vault-pass
ansible -i inventory.ini prod --ask-vault-pass -m copy -a "src=/secret dest=/secret"
ssh root@prod-1bhwjtpi "cat /secret"
```

### TFLint (Terraform linter)
```bash
curl https://raw.githubusercontent.com/terraform-linters/tflint/master/install_linux.sh | bash
git clone https://gitlab.practical-devsecops.training/pdso/terraform.git && cd terraform
tflint --chdir=aws
```
**GitHub Actions setup** (TFLint runs on GH, not GitLab): create a `terraform` repo, then use a classic PAT (https://github.com/settings/tokens → scopes `repo` + `workflow`, format `ghp_xxx`) for auth. Vulnerable repos with hardcoded secrets may trip GH Secret Scanning → "Allow me to expose this secret", or use a Private repo.
```bash
git config --global user.email "your_email@gmail.com"
git config --global user.name  "your_username"
git clone https://gitlab.practical-devsecops.training/pdso/terraform.git && cd terraform
git remote rename origin old-origin
git remote add origin https://github.com/username/terraform.git
git push -u origin --all
```
Base workflow (`.github/workflows/main.yaml`):
```yaml
name: Terraform
on:
  push:
    branches: [main]          # ~ "only" in GitLab
jobs:
  build:
    runs-on: ubuntu-22.04     # ~ "image" in GitLab
    steps:
      - run: echo "This is a build step"
  test:
    runs-on: ubuntu-22.04
    needs: build
    steps:
      - run: echo "This is a test step"
  integration:
    runs-on: ubuntu-22.04
    needs: test
    steps:
      - run: echo "This is an integration step"
      - run: exit 1
        continue-on-error: true
  prod:
    runs-on: ubuntu-22.04
    needs: integration
    steps:
      - run: echo "This is a deploy step"
```
TFLint job:
```yaml
  tflint:
    runs-on: ubuntu-22.04
    steps:
      - name: Checkout
        uses: actions/checkout@v2
      - uses: terraform-linters/setup-tflint@v1
        name: Setup TFLint
        with:
          tflint_version: latest
      - name: Run TFLint
        run: tflint --chdir=aws -f json > tflint-output.json
        continue-on-error: true
      - uses: actions/upload-artifact@v4
        with:
          name: TFLint
          path: tflint-output.json
        if: always()
```

### Checkov (IaC misconfig scanner)
```bash
pip3 install checkov==2.3.22
git clone https://gitlab.practical-devsecops.training/pdso/terraform.git
checkov -f terraform/aws/s3.tf
checkov -d /terraform/ -o json > /terraform/scan-result.json
jq ".[0].summary.failed" /terraform/scan-result.json
checkov -d /terraform/ -o json --skip-check CKV_AWS_18,CKV_AWS_21,CKV_AWS_20,CKV_AWS_52,CKV_AWS_19 > /terraform/scan-result-skipped.json
```
```yaml
checkov:
  stage: validate
  script:
    - docker pull bridgecrew/checkov
    - docker run --rm -w /src -v $(pwd):/src bridgecrew/checkov -d aws -o json | tee checkov-output.json
  artifacts:
    paths: [checkov-output.json]
    when: always
  allow_failure: true
```

### Terrascan
```bash
wget https://github.com/tenable/terrascan/releases/download/v1.18.0/terrascan_1.18.0_Linux_x86_64.tar.gz
tar -xvf terrascan_1.18.0_Linux_x86_64.tar.gz
chmod +x terrascan && mv terrascan /usr/local/bin/
terrascan scan -d gcp
terrascan scan -d gcp --severity high
```
```yaml
terrascan:
  stage: validate
  image:
    name: tenable/terrascan:latest
    entrypoint: ["/bin/sh", "-c"]
  script:
    - /go/bin/terrascan scan . -o json > terrascan-output.json
  artifacts:
    paths: [terrascan-output.json]
    when: always
  allow_failure: true
```

### tfsec
```bash
wget -O /usr/local/bin/tfsec https://github.com/aquasecurity/tfsec/releases/download/v0.55.0/tfsec-linux-amd64
chmod +x /usr/local/bin/tfsec
tfsec aws -f json | tee tfsec-output.json
```
```yaml
tfsec:
  stage: validate
  script:
    - docker run --rm -v $(pwd):/src aquasec/tfsec /src -f json | tee tfsec-output.json
  artifacts:
    paths: [tfsec-output.json]
    when: always
  allow_failure: true
```

### KICS (Checkmarx, multi-IaC)
```bash
docker pull checkmarx/kics:v1.7.11
docker run -t -v $(pwd):/path checkmarx/kics:v1.7.11 --help
docker run -t -v $(pwd):/path checkmarx/kics:v1.7.11 scan
```

---

## 6. CaC — COMPLIANCE AS CODE

### Lynis (host audit)
```bash
apt-get install lynis -y
lynis audit system
```

### CinC Auditor (InSpec) — install & basics
```bash
wget https://omnitruck.cinc.sh/install.sh
bash install.sh -P cinc-auditor -v 6
# or one-liner:
curl https://omnitruck.cinc.sh/install.sh | sudo bash -s -- -P cinc-auditor -v 6

echo "StrictHostKeyChecking accept-new" >> ~/.ssh/config
# run an upstream baseline against prod over SSH
cinc-auditor exec https://github.com/dev-sec/linux-baseline.git -t ssh://root@prod-1bhwjtpi -i ~/.ssh/id_rsa --chef-license accept
```
**CI/CD vars:** `DEPLOYMENT_SERVER=prod-1bhwjtpi`, `DEPLOYMENT_SERVER_SSH_PRIVKEY=<prod /root/.ssh/id_rsa>`.
```yaml
cinc-auditor:
  stage: prod
  only:
    - main
  environment: production
  before_script:
    - mkdir -p ~/.ssh
    - echo "$DEPLOYMENT_SERVER_SSH_PRIVKEY" | tr -d '\r' > ~/.ssh/id_rsa
    - chmod 600 ~/.ssh/id_rsa
    - eval "$(ssh-agent -s)"
    - ssh-add ~/.ssh/id_rsa
    - ssh-keyscan -H $DEPLOYMENT_SERVER >> ~/.ssh/known_hosts
  script:
    - docker run --rm -v ~/.ssh:/root/.ssh -v $(pwd):/share cincproject/auditor:6.8.24 exec https://github.com/dev-sec/linux-baseline.git -t ssh://root@$DEPLOYMENT_SERVER -i ~/.ssh/id_rsa --chef-license accept --reporter json:/share/cinc-auditor-output.json
  artifacts:
    paths: [cinc-auditor-output.json]
    when: always
```

**Interactive shell (explore resources):**
```bash
cinc-auditor shell -t ssh://root@prod-1bhwjtpi -i ~/.ssh/id_rsa --chef-license accept
# inside the shell:
file('/tmp').class.superclass.instance_methods(false).sort
file('/tmp').directory?
file('/tmp').exist?
os_env('PATH').content
os_env('PATH').split
```

**Custom profile + run (local, then over SSH):**
```bash
mkdir cinc-profiles && cd cinc-profiles
cinc-auditor init profile ubuntu --chef-license accept
# edit ubuntu/controls/example.rb ... then:
cinc-auditor check ubuntu                                  # validate profile syntax
cinc-auditor exec  ubuntu                                  # run locally
cinc-auditor exec  ubuntu -t ssh://root@prod-1bhwjtpi -i ~/.ssh/id_rsa --chef-license accept
```
Example control (file checks):
```ruby
control 'shadow-1' do
  title 'Ensure /etc/shadow file is properly secured'
  desc 'The /etc/shadow file contains password hashes and should be protected'
  describe file('/etc/shadow') do
    it { should exist }
    it { should be_file }
    it { should be_owned_by 'root' }
  end
end
```

**CIS-style controls (sudo / sshd examples):**
```ruby
control 'ubuntu-1.3.1' do
   title 'Ensure sudo is installed'
   describe package('sudo') do
      it { should be_installed }
   end
end

control 'ubuntu-1.3.2' do
   title 'Ensure sudo commands use pty'
   describe command('grep -Ei "^\s*Defaults\s+([^#]+,\s*)?use_pty(,\s+\S+\s*)*(\s+#.*)?$" /etc/sudoers').stdout do
      it { should include 'Defaults use_pty' }
   end
end

control 'ubuntu-1.3.3' do
   title 'Ensure sudo log file exists'
   describe command('grep -Ei "^\s*Defaults\s+logfile=\S+" /etc/sudoers').stdout do
      it { should include 'Defaults logfile=' }
   end
end

control 'ubuntu-5.2.1' do
   title 'Ensure permissions on /etc/ssh/sshd_config are configured'
   describe file('/etc/ssh/sshd_config') do
     its('owner') { should eq 'root' }
     its('group') { should eq 'root' }
     its('mode')  { should cmp '0600' }
   end
end
```
> Fix sshd perms before testing: `chown root:root /etc/ssh/sshd_config && chmod og-rwx /etc/ssh/sshd_config`

**Profile dependencies (`inspec.yml` + vendor):**
```yaml
depends:
  - name: SSH baseline
    url: https://github.com/dev-sec/ssh-baseline/archive/master.tar.gz
  - name: Linux Baseline
    url: https://github.com/dev-sec/linux-baseline/archive/master.tar.gz
```
```bash
cinc-auditor vendor          # pull dependencies
# then in a control file:  include_controls 'SSH baseline'  /  include_controls 'Linux Baseline'
```

**ASVS web-header controls (HTTP resource):**
```ruby
control 'ASVS-14.4.4' do
    impact 0.7
    title 'Content type Options = nosniff'
    describe http('https://prod-1bhwjtpi.lab.practical-devsecops.training') do
        its ('headers.x-content-type-options') { should cmp 'nosniff' }
    end
end

control 'ASVS-14.4.5' do
    impact 0.7
    title 'HSTS max-age set'
    describe http('https://prod-1bhwjtpi.lab.practical-devsecops.training') do
        its ('headers.Strict-Transport-Security') { should match /\d/ }
    end
end
```
(Other ASVS-14.4.x: safe charset, Content-Disposition, CSP not `none`/no `unsafe-inline`, Referrer-Policy.)

**GitLab CI for a local profile:**
```yaml
services:
  - docker:dind
stages:
  - test
compliance:
  stage: test
  script:
    - docker run -i --rm -v $(pwd):/share cincproject/auditor:6.8.24 check challenge --chef-license accept
    - docker run -i --rm -v $(pwd):/share cincproject/auditor:6.8.24 exec  challenge --chef-license accept
  allow_failure: true
```

**Docker / container benchmarks:**
```bash
docker run -d --name alpine -it alpine /bin/sh
cinc-auditor exec https://github.com/dev-sec/linux-baseline.git --chef-license accept -t docker://alpine
cinc-auditor exec https://github.com/dev-sec/cis-docker-benchmark.git --chef-license accept
```

### Jenkins pipeline (with CinC compliance stage)
```groovy
pipeline {
    agent any
    options { gitLabConnection('gitlab') }
    stages {
        stage("build") {
            agent { docker { image 'python:3.6'; args '-u root' } }
            steps {
                sh """
                pip3 install --user virtualenv
                python3 -m virtualenv env
                . env/bin/activate
                pip3 install -r requirements.txt
                python3 manage.py check
                """
            }
        }
        stage("test") {
            agent { docker { image 'python:3.6'; args '-u root' } }
            steps {
                sh """
                pip3 install --user virtualenv
                python3 -m virtualenv env
                . env/bin/activate
                pip3 install -r requirements.txt
                python3 manage.py test taskManager
                """
            }
        }
        stage("integration") {
            steps {
                catchError(buildResult: 'SUCCESS', stageResult: 'UNSTABLE') {
                    echo "This is an integration step."
                    sh "exit 1"
                }
            }
        }
        stage("cinc-auditor") {
            agent { docker { image 'cincproject/auditor'; args '-u root --entrypoint=' } }
            steps {
                withCredentials([string(credentialsId: 'prod-server', variable: 'SERVER_HOST')]) {
                    sshagent(['ssh-prod']) {
                        catchError(buildResult: 'SUCCESS', stageResult: 'UNSTABLE') {
                            sh "cinc-auditor exec https://github.com/dev-sec/linux-baseline.git -t ssh://root@${SERVER_HOST} --chef-license accept --reporter json:cinc-output.json"
                        }
                    }
                }
            }
            post {
                always { archiveArtifacts artifacts: 'cinc-output.json', fingerprint: true }
            }
        }
        stage("prod") {
            steps {
                timeout(time: 10, unit: 'SECONDS') { input "Deploy to production?" }
                echo "This is a deploy step."
            }
        }
    }
    post {
        failure  { updateGitlabCommitStatus(name: "\${env.STAGE_NAME}", state: 'failed') }
        unstable { updateGitlabCommitStatus(name: "\${env.STAGE_NAME}", state: 'failed') }
        success  { updateGitlabCommitStatus(name: "\${env.STAGE_NAME}", state: 'success') }
        aborted  { updateGitlabCommitStatus(name: "\${env.STAGE_NAME}", state: 'canceled') }
        always {
            deleteDir()
            dir("${WORKSPACE}@tmp")    { deleteDir() }
            dir("${WORKSPACE}@script") { deleteDir() }
        }
    }
}
```

---

## 7. VULNERABILITY MANAGEMENT

### DefectDojo (upload scan results)
Get the upload helper + auth token:
```bash
curl https://gitlab.practical-devsecops.training/-/snippets/28/raw -o upload-results.py
pip3 install requests
export API_KEY=$(curl -s -XPOST -H 'content-type: application/json' \
  https://dojo-1bhwjtpi.lab.practical-devsecops.training/api/v2/api-token-auth/ \
  -d '{"username": "root", "password": "pdso-training"}' | jq -r '.token')
```
Upload a result file (`--scanner` must match a DefectDojo parser name):
```bash
python3 upload-results.py --host dojo-1bhwjtpi.lab.practical-devsecops.training --api_key $API_KEY \
  --engagement_id 1 --product_id 1 --lead_id 1 --environment "Production" \
  --result_file bandit-output.json --scanner "Bandit Scan"

python3 upload-results.py --host dojo-1bhwjtpi.lab.practical-devsecops.training --api_key $API_KEY \
  --engagement_id 2 --product_id 3 --lead_id 1 --environment "Production" \
  --result_file brakeman-result.json --scanner "Brakeman Scan"
```
ZAP → DefectDojo (note `-x` XML output, uploaded as "ZAP Scan"):
```bash
docker run --user $(id -u):$(id -g) -w /zap -v $(pwd):/zap/wrk:rw --rm hysnsec/zap:2.16.1 \
  zap-baseline.py -t https://prod-1bhwjtpi.lab.practical-devsecops.training -d -x zap-output.xml
python3 upload-results.py --host dojo-1bhwjtpi.lab.practical-devsecops.training --api_key $API_KEY \
  --engagement_id 1 --product_id 1 --lead_id 1 --environment "Production" \
  --result_file zap-output.xml --scanner "ZAP Scan"
```

### CI job (scan + auto-upload via `after_script`)
**CI/CD vars:** `DOJO_HOST`, `DOJO_API_TOKEN`.
```yaml
dast-zap:
  stage: integration
  before_script:
    - apk add py-pip py-requests
    - docker pull hysnsec/zap:2.16.1
  script:
    - docker run --user $(id -u):$(id -g) -w /zap -v $(pwd):/zap/wrk:rw --rm hysnsec/zap:2.16.1 zap-baseline.py -t https://prod-1bhwjtpi.lab.practical-devsecops.training -d -x zap-output.xml
  after_script:
    - python3 upload-results.py --host $DOJO_HOST --api_key $DOJO_API_TOKEN --engagement_id 1 --product_id 1 --lead_id 1 --environment "Production" --result_file zap-output.xml --scanner "ZAP Scan"
  artifacts:
    paths: [zap-output.xml]
    when: always
    expire_in: 1 day
```
> The `sast-with-vm` job in §1 shows the same pattern for Bandit: scan in `script`, upload in `after_script`.
