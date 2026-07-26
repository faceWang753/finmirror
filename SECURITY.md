# Security Policy

## Supported version

The latest tagged release receives security fixes. Before the first tag, use the current
default branch.

## Reporting

Do not open a public issue for:

- code execution or path traversal;
- secret leakage;
- report HTML injection that escapes existing encoding;
- dependency or release-chain compromise;
- accidental inclusion of confidential or unlicensed data.

Use GitHub’s private security advisory feature after the repository is published. If it
is unavailable, contact the maintainer through the private address added to the release
metadata. This local scaffold intentionally does not invent a security email.

Include affected version, reproduction, impact, and the smallest safe proof. Do not
access data that is not yours.

## Threat model

FinMirror treats benchmark documents and model strings as untrusted. Reports HTML-escape
display fields and safely embed JSON. Formula verification uses an allow-list and never
executes submitted code. Dataset manifests detect accidental or malicious modification
but are not signed attestations.

Adapters may send evidence to external model providers. Users are responsible for provider
terms, data classification, credentials, retention, and cost. Synthetic v0.1 contains no
confidential data.

