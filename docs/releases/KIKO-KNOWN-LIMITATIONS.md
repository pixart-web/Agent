# Known limitations

## Release gates outside the repository

- No authorized isolated staging environment or registry was available in this completion run.
  Locally built image IDs are evidence of reproducible Dockerfiles, not deployable registry digests.
- Gmail, Google Calendar, SMTP delivery, GitHub, Codex, OpenAI, and billing-provider journeys were not
  invoked with real credentials. They remain disabled until least-privilege test-account validation.
- DNS, TLS, private networking, managed database/Redis failover, secret manager, alert routing, and
  named on-call ownership require the target infrastructure owner.
- Legal/privacy approval, support procedures, commercial pricing approval, and customer contracts
  are business gates, not code assertions.

## Product limitations

- MFA is not yet available; privileged accounts require compensating identity-provider and access
  controls in the deployment environment.
- The CSP retains `'unsafe-inline'` for styles for current Next.js rendering compatibility. Scripts
  do not allow `unsafe-eval` in production; development does for the framework runtime.
- Automated WCAG checks reduce risk but do not replace keyboard, screen-reader, contrast, zoom, and
  cognitive usability review by humans.
- AI and provider quality gates require representative staging samples; fake providers prove policy
  and failure handling, not external service reliability or answer quality.
- Retention execution deliberately removes only eligible notification/invitation ephemera. Business
  and audit records require an approved lifecycle and legal basis rather than bulk deletion.

There are no known BLOCKER or HIGH code-security defects in the tested repository state. This is not
a claim of zero bugs or production authorization.
