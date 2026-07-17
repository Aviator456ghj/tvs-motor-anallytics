# Volume 19 — DevOps

Status: ⬜ Not started (skeleton).

CI/CD, environments, infrastructure-as-code, and observability — how CommerceOS gets built, deployed, and kept healthy in production.

## Planned modules/pages
- Environment strategy (local/dev/staging/production, per-tenant vs. shared infra decisions from Vol 16)
- CI/CD pipeline (build, test gates from Vol 20, deployment strategy — blue/green, canary)
- Infrastructure as code (provisioning for the services defined in Vol 17)
- Observability (logging, metrics, tracing — feeding the "Performance" sections throughout Volume 2, and the Store Health widget in Vol 2.1)
- Incident response & on-call
- Secrets management (relevant to Vol 2.8's bank-account tokenization, Vol 2.9's API key storage)
- Cost/capacity planning

## Dependencies
Microservices (Vol 17) for what's being deployed, Database (Vol 16) for data-tier ops, Testing (Vol 20) for release gates.

## Next steps
Define the environment strategy and CI/CD pipeline shape first, using `/web`'s current build (`npm run build`, Next.js/Turbopack) as the first real deployable artifact to design pipelines around.
