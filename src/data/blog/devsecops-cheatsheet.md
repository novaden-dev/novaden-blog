---
author: Kayra
pubDatetime: 2026-05-27T00:00:00Z
title: DevSecOps Cheat Sheet
slug: devsecops-cheatsheet
featured: false
draft: false
tags:
  - devsecops
  - security
  - cheatsheet
  - notes
description: A growing quick-reference for DevSecOps pipeline jobs, the Docker-based scanner snippets I reach for, and the vulnerability-manager upload pattern.
---

A living quick-reference for the pipeline jobs and scanner invocations I actually use. For the model behind any of this, see [DevSecOps Foundations](/posts/devsecops-foundations).

The examples below are GitLab CI flavoured (`.gitlab-ci.yml` syntax), but the shape (`docker pull`, `docker run -v $(pwd):/src`, capture JSON output as an artifact) ports to GitHub Actions and Jenkins with small changes.

> **Gotcha:** Some keywords don't port directly. GitLab's `allow_failure: true` becomes `continue-on-error: true` in GitHub Actions, and they behave differently: GitLab marks the pipeline green when an allowed-failure job fails; GitHub still marks the workflow red but lets it proceed. `artifacts:`, `stages:`, `only:`, and `rules:` are GitLab-specific in name; map them to `uploads-artifact`, `jobs:` ordering with `needs:`, and `if:` conditions on the GitHub side.

## Pipeline Skeleton

```yaml
services:
  - docker:dind   # Run all jobs against a docker-in-docker daemon

stages:
  - build
  - test
  - release
  - preprod
  - integration
  - prod
```

## Build and Test Jobs

```yaml
# Build job: create the virtualenv, install deps, run sanity checks
build:
  stage: build
  image: python:3.6
  before_script:
    - pip3 install --upgrade virtualenv
  script:
    - virtualenv env
    - source env/bin/activate
    - pip install -r requirements.txt
    - python manage.py check

# Unit test job
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
```

## Software Component Analysis (SCA)

```yaml
# RetireJS for a Node.js frontend
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

# Safety for a Python backend (Docker-packaged scanner)
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
  allow_failure: true   # don't break the pipeline yet, just collect findings
```

> **Note:** `artifacts.when: always` means the report is uploaded even when the job fails. That's exactly what you want for security scans: a failing job is the one whose output you most want to read.

## Secrets Scanning

```yaml
# TruffleHog scan of the working tree
secrets-scanning:
  stage: build
  script:
    - docker run -v $(pwd):/src --rm hysnsec/trufflehog filesystem /src --json | tee trufflehog-output.json
  artifacts:
    paths: [trufflehog-output.json]
    when: always
    expire_in: one week
  allow_failure: true
```

## Static Application Security Testing (SAST)

```yaml
# Bandit (Python) static analysis
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

> **Gotcha:** `--user $(id -u):$(id -g)` makes the scanner write output as the CI user instead of root. Without it, the workspace ends up with root-owned files that the next job can't overwrite.

## Dynamic Application Security Testing (DAST)

```yaml
# Nikto web server scanner
nikto:
  stage: integration
  script:
    - docker pull hysnsec/nikto
    - docker run --rm -v $(pwd):/tmp hysnsec/nikto -h prod-host -o /tmp/nikto-output.xml
  artifacts:
    paths: [nikto-output.xml]
    when: always

# SSLyze: TLS configuration audit
sslscan:
  stage: integration
  script:
    - docker pull hysnsec/sslyze
    - docker run --rm -v $(pwd):/tmp hysnsec/sslyze prod.lab.example.training:443 --json_out /tmp/sslyze-output.json
  artifacts:
    paths: [sslyze-output.json]
    when: always

# Nmap: port and service scan
nmap:
  stage: integration
  script:
    - docker pull hysnsec/nmap
    - docker run --rm -v $(pwd):/tmp hysnsec/nmap prod-host -oX /tmp/nmap-output.xml
  artifacts:
    paths: [nmap-output.xml]
    when: always

# OWASP ZAP baseline scan
zap-baseline:
  stage: integration
  script:
    - docker pull hysnsec/zap:2.16.1
    - docker run --user $(id -u):$(id -g) --rm -v $(pwd):/zap/wrk:rw hysnsec/zap:2.16.1 zap-baseline.py -t https://prod.lab.example.training -J zap-output.json
  after_script:
    - docker rmi hysnsec/zap:2.16.1   # free disk on the runner
  artifacts:
    paths: [zap-output.json]
    when: always
  allow_failure: true
```

## Infrastructure as Code (Ansible Hardening)

```yaml
# Apply the dev-sec.os-hardening role against the prod host
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

> **Note:** `DEPLOYMENT_SERVER_SSH_PRIVKEY` and `DEPLOYMENT_SERVER` are CI variables. Keep the key in masked/protected CI variables, never in the repo.

## Compliance as Code (InSpec)

```yaml
# Run the dev-sec/linux-baseline against the prod host on main only
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
```

## Vulnerability Management (DefectDojo Upload)

```yaml
# Run SAST and push the report into DefectDojo via API
sast-with-vm:
  stage: build
  before_script:
    - apk add py-pip py-requests curl
    - curl https://gitlab.example.training/-/snippets/28/raw -o upload-results.py
  script:
    - docker pull hysnsec/bandit
    - docker run --user $(id -u):$(id -g) -v $(pwd):/src --rm hysnsec/bandit -r /src -f json -o /src/bandit-output.json
  after_script:
    - python3 upload-results.py --host $DOJO_HOST --api_key $DOJO_API_TOKEN --engagement_id 1 --product_id 1 --lead_id 1 --environment "Production" --result_file bandit-output.json --scanner "Bandit Scan"
  artifacts:
    paths: [bandit-output.json]
    when: always
```

> **Gotcha:** `after_script` runs even when `script` fails, which is what you want for upload: a failed scan with findings still needs to land in DefectDojo. Don't move the upload into `script` or you'll silently drop reports the day a scan crashes.

## SSH Bootstrap for Runners

```bash
# Pre-populate known_hosts so SSH doesn't prompt mid-pipeline
ssh-keyscan -H build-host staging-host prod-host >> ~/.ssh/known_hosts

# Accept new host keys on first connection (less strict, useful in ephemeral runners)
echo "StrictHostKeyChecking accept-new" >> ~/.ssh/config
```

## Common Scanner Invocations (Out of Pipeline)

```bash
# RetireJS: scan a Node.js project's dependencies, emit JSON
retire --outputformat json --outputpath retirejs-report.json --severity high

# Safety: scan a requirements.txt for known CVEs in Python deps
docker run --rm -v $(pwd):/src hysnsec/safety check -r requirements.txt --json

# TruffleHog: secrets scan of a directory
docker run --rm -v $(pwd):/src hysnsec/trufflehog filesystem /src --json

# Bandit: SAST on a Python codebase
docker run --rm -v $(pwd):/src hysnsec/bandit -r /src -f json -o /src/bandit-output.json

# Nikto: quick web server scan
docker run --rm -v $(pwd):/tmp hysnsec/nikto -h <target> -o /tmp/nikto-output.xml

# SSLyze: TLS configuration audit
docker run --rm -v $(pwd):/tmp hysnsec/sslyze <host>:443 --json_out /tmp/sslyze-output.json

# Nmap: XML output for tooling
docker run --rm -v $(pwd):/tmp hysnsec/nmap <target> -oX /tmp/nmap-output.xml

# ZAP baseline against a deployed app
docker run --user $(id -u):$(id -g) --rm -v $(pwd):/zap/wrk:rw hysnsec/zap:2.16.1 zap-baseline.py -t https://<target> -J zap-output.json
```

## Job Configuration Knobs

```yaml
# Allow a job to fail without breaking the pipeline
my-job:
  allow_failure: true

# Run only on the main branch
my-job:
  only:
    - main

# Run only when a specific file changes
my-job:
  rules:
    - changes:
        - requirements.txt

# Require a human click before running
deploy-prod:
  when: manual

# Keep artifacts for a fixed window
my-job:
  artifacts:
    paths: [report.json]
    expire_in: one week
    when: always   # upload even on failure
```
