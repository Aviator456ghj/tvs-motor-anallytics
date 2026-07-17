# Volume 18 — UI Design System

Status: 🚧 Skeleton — partially implemented in code (`/web`), not yet documented as a formal system.

Tokens, components, and interaction patterns used across every UI surface (Merchant Admin, Storefront, Customer Portal, Vendor Portal). The `/web` reference implementation is the first concrete instance; this volume should formalize it into a reusable, documented system.

## Extracted from the current implementation (starting point for formal docs)
- **Color tokens**: brand gradient (`--brand-start` #6366f1 → `--brand-end` #8b5cf6), sidebar dark palette, semantic success/warning/danger/info pairs — see `/web/src/app/globals.css`.
- **Layout primitives**: `AppShell` (sidebar + topbar + content + footer), `Card`/`CardHeader` — see `/web/src/components/layout/` and `/web/src/components/ui/`.
- **Components in use**: stat card w/ sparkline, data table, donut/line charts (Recharts), badge/status pill, avatar, icon button, gradient CTA button, suggestion chip.
- **Iconography**: lucide-react, 17px default stroke size in nav/lists, 14–16px in compact widgets.
- **Typography**: system sans stack (Geist), 11–22px scale used across the Dashboard.

## Planned modules/pages
- Formal design token spec (color/spacing/typography/radius/shadow scales)
- Component library documentation (props, states, accessibility notes) generated from `/web/src/components`
- Interaction patterns (loading/empty/error states — referenced in every Volume 2 page's "Edge cases"/"Error handling" sections)
- Theming/white-label support (for Storefront Vol 3 theme editor)
- Accessibility standards (WCAG target level, keyboard nav, screen reader support)
- Responsive/mobile breakpoint strategy (current `/web` implementation is desktop-first per Vol 2.1's noted UX improvement)

## Dependencies
Consumed by every UI-bearing volume (2, 3, 4, 5); should be authored by reverse-engineering and formalizing the existing `/web` implementation rather than starting from a blank slate.

## Next steps
Audit `/web/src/components` and `globals.css` into a formal token/component spec — most of the "component" work already exists as code, it needs documentation and gap-filling (states, accessibility) rather than invention.
