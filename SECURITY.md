# Security policy

## Supported versions

Security fixes are applied to the latest code on the `main` branch.

## Reporting a vulnerability

Please do **not** disclose suspected vulnerabilities in a public issue. Use GitHub's private vulnerability-reporting feature from the repository's **Security** tab. If private reporting is unavailable, contact the repository owner through their GitHub profile and include only the minimum information needed to establish contact.

Do not include real API keys, cookies, proxy credentials, personal URLs, or other secrets in a report. Rotate any credential that may have been exposed before reporting it.

Useful reports include a clear description, affected area, safe reproduction steps, impact, and a suggested mitigation when available.

## Scope

The most relevant areas include URL validation and SSRF protections, download streaming, temporary-file cleanup, rate limiting, CORS configuration, dependency vulnerabilities, logging, and accidental credential exposure.
