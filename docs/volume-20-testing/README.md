# Volume 20 — Testing

Status: ⬜ Not started (skeleton).

Test strategy, QA process, and release gates spanning every volume — the discipline that keeps 50+ modules and 800+ APIs from regressing as CommerceOS grows.

## Planned modules/pages
- Test strategy & pyramid (unit/integration/e2e mix per volume type — UI-heavy Vol 2/3/4/5 vs. data-heavy Vol 9/11/12)
- Unit & integration testing standards per service (Vol 17)
- End-to-end testing (critical user journeys — checkout, fulfillment, payout — across Vol 2/3/7)
- Performance/load testing (validating the "Performance" targets stated throughout Volume 2, e.g., Dashboard's p95 < 300ms)
- Security testing (validating the "Security" sections throughout Volume 2 — auth, PII redaction, PCI scope)
- Accessibility testing (validating Vol 18's accessibility standards)
- Release gates & QA sign-off process
- App/plugin certification testing (for third-party apps, Vol 2.9/15)

## Dependencies
Every volume's "Performance," "Security," and "Edge cases" sections are effectively the test-case source material for this volume; DevOps (Vol 19) owns where these tests run in the pipeline.

## Next steps
Derive an initial e2e test plan directly from Volume 2's documented workflows (each page's "Workflows" section is close to a test-case outline already) starting with Dashboard and Orders.
