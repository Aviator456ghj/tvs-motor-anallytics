# 2.12 Content

## Purpose
Lightweight CMS for storefront content that isn't a product: pages (About, FAQ, Policies), blog posts, and navigation menus — keeping marketing copy editable without developer involvement.

## Navigation
Sidebar `Content`. Sub-tabs: Pages, Blog Posts, Navigation Menus, Media Library, Metaobjects (custom structured content, for advanced/headless use).

## User roles
Owner/Manager: full CRUD + publish. Marketing: full CRUD + publish. Support: view-only (to reference policy content when helping customers).

## Permissions
`content.view`, `content.create`, `content.edit`, `content.publish`, `content.delete`, `content.manage_navigation`.

## Fields
Page/Post: title, slug/handle, body (rich text/blocks), status (Draft/Scheduled/Published), author, publish date, featured image, SEO title/description, tags/category (blog). Navigation menu: label, link (internal/external), nesting, position.

## Buttons
Create page/post, Save draft, Publish, Schedule, Preview, Duplicate, Delete, Add menu item, Reorder (drag-and-drop), Upload media.

## Tables
Pages/Posts list: title, status, author, last updated, visibility. Media library: thumbnail, filename, type, size, usage count (where referenced).

## Filters
Status, author, tag/category, date range.

## Search
Title, body content (full-text), slug.

## Bulk actions
Bulk publish/unpublish, bulk delete (unpublished only), bulk tag (blog).

## Workflows
1. Create page → write content (block-based or rich text editor) → set SEO fields → preview on storefront theme → publish or schedule.
2. Build navigation menu → add items (pages, collections, products, external links) → nest into dropdowns → assign menu to a theme location (header/footer) → changes reflect on storefront immediately.
3. Blog post publishing pipeline mirrors pages, plus category/tag taxonomy and an RSS feed auto-generated per store.

## Business rules
- Deleting a page that's referenced in an active navigation menu is blocked (or requires confirming menu-item removal first) to avoid broken links.
- Scheduled content publishes automatically at the specified time via a background job; publish failures (e.g., validation regression) alert the author rather than silently not-publishing.
- Slug/handle must be unique per content type per store; changing a published page's slug creates an automatic redirect from the old slug (SEO preservation).

## Validation
Title and slug required; slug must be URL-safe (auto-generated from title, editable); scheduled publish date must be in the future.

## Notifications
Scheduled content published, scheduled publish failed, page referenced-and-deleted warning, broken link detected in menu (background link checker).

## Audit logs
`page.created/edited/published/deleted`, `navigation.menu_changed`, `media.uploaded/deleted`.

## Database schema
```
content_pages(id, store_id, type[page|blog_post], title, slug, body jsonb, status,
              author_id, published_at, seo_title, seo_description, created_at, updated_at)
content_redirects(id, store_id, from_path, to_path, created_at)
navigation_menus(id, store_id, name, location[header|footer|custom])
navigation_menu_items(id, menu_id, parent_item_id null, label, link_type, link_target, position)
media_assets(id, store_id, url, filename, type, size_bytes, alt_text, created_at)
```

## APIs
`GET/POST /api/v1/content/pages`, `GET/PATCH/DELETE /api/v1/content/pages/{id}`, `POST /api/v1/content/pages/{id}/publish`, `GET/POST /api/v1/content/navigation`, `POST /api/v1/content/media`.

## Events
`page.published`, `page.unpublished`, `navigation.updated`, `media.uploaded` — consumed by Storefront (cache invalidation/CDN purge), Analytics (content performance).

## Edge cases
Circular navigation nesting (blocked at save time); page slug collision with a system route (e.g., `/cart`) — reserved-word validation; content referencing a deleted product/collection link (link checker flags, doesn't hard-break).

## Error handling
Rich content editor autosave failure → local draft retained client-side until save succeeds, user warned before navigating away with unsaved changes; media upload failure → per-file retry without losing the rest of a multi-file upload batch.

## Performance
Published content served via CDN with cache invalidated only for changed pages (not a full-site purge per edit); media library paginated/lazy-loaded with thumbnail generation on upload, not on-demand.

## Security
Rich text editor output sanitized server-side (XSS prevention) regardless of client-side sanitization; media uploads type/size validated server-side; external link items in navigation flagged with `rel="noopener"` automatically.

## AI opportunities
AI-drafted page/blog copy from a brief; auto-generated SEO title/description/alt text; AI-suggested internal linking; broken-link and thin-content detection with fix suggestions.

## UX improvements
Visual drag-and-drop page builder (blocks) rather than raw rich text only; live storefront preview pane while editing; version history with one-click revert.

## Estimated scope
~6 sub-views, ~8 API endpoints, 5 DB tables, ~25 functional requirements.
