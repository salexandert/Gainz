# Security Policy

## Supported versions

Security fixes are applied to the latest published Gainz release. Older
releases may not receive security updates, so users should upgrade before
reporting an issue that has already been corrected.

| Version | Supported |
| --- | --- |
| Latest release | Yes |
| Older releases | No |

## Reporting a vulnerability

Please do not open a public issue for a suspected vulnerability or include
private transaction, tax, credential, or local-file data in a report.

Use GitHub's private **Report a vulnerability** option on the Gainz Security
page:

https://github.com/salexandert/Gainz/security/advisories/new

Include only the minimum information needed to reproduce the issue:

- the affected Gainz version and operating system;
- the security impact and affected workflow;
- reproduction steps using synthetic data where possible; and
- any suggested mitigation or fix.

You should receive an acknowledgement within seven days. Please allow time for
a fix and public release before disclosing the issue publicly.

## Protecting local data

Gainz is designed to run offline, but its local saves, uploads, logs, exports,
and audit packets may contain sensitive financial information. Redact personal
data before sharing diagnostic material. Never attach real tax records,
credentials, wallet secrets, seed phrases, or private keys to a report.

Gainz does not provide legal, financial, or tax advice. Security reports should
focus on software behavior, data exposure, authentication, packaging, or other
technical risks.
