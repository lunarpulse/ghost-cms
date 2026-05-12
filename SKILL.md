---
name: ghost-cms
title: Ghost CMS Admin API
version: 2.3.0
description: Manage multiple Ghost CMS blogs via Admin API. Multi-site support, LLM-generated featured images, membership/tier management, newsletter support, SEO optimization.
author: Hermes
---

# Ghost CMS Admin API Skill

Manage one or more Ghost blogs programmatically via the Admin API.

## Multi-Site Architecture

```
┌─────────────────┐     ┌──────────────────┐     ┌─────────────┐
│   sites.json    │────▶│   ghost.py CLI   │────▶│  Ghost Admin│
│  (site configs) │     │ (JWT + curl)     │     │  API        │
└─────────────────┘     └──────────────────┘     └─────────────┘
         ▲
         │ reads secrets
    ┌────┴────┐
    │ ~/.hermes/.env  (API keys)
    └─────────┘
```

**Per-site configuration** (in `sites.json`):
| Field | Purpose |
|-------|---------|
| `domain` | Ghost site URL |
| `admin_key_env` | Env var name for Admin API key |
| `content_key_env` | Env var name for Content API key (optional) |
| `api_version` | Ghost API version (default: v5.0) |
| `http_version` | `1.1` or `2` (default: 1.1; Cloudflare needs 1.1) |

## Setup

### 1. Configure Sites

Copy the template and edit with your site details:

```bash
cp ~/.hermes/skills/productivity/ghost-cms/sites.json.template \
   ~/.hermes/skills/productivity/ghost-cms/sites.json
```

Edit `sites.json`:

```json
{
  "sites": {
    "myblog": {
      "domain": "blog.example.com",
      "admin_key_env": "GHOST_MYBLOG_ADMIN_KEY",
      "content_key_env": "GHOST_MYBLOG_CONTENT_KEY",
      "api_version": "v5.0",
      "http_version": "1.1",
      "description": "My blog"
    },
    "personal": {
      "domain": "personal.example.com",
      "admin_key_env": "GHOST_PERSONAL_ADMIN_KEY",
      "api_version": "v5.82",
      "http_version": "1.1",
      "description": "Personal blog"
    }
  },
  "default_site": "myblog"
}
```

### 2. Store Secrets

Add keys to `~/.hermes/.env`:

```bash
# My blog
echo 'GHOST_MYBLOG_ADMIN_KEY=your_id:your_secret' >> ~/.hermes/.env
echo 'GHOST_MYBLOG_CONTENT_KEY=your_content_key' >> ~/.hermes/.env

# Personal blog
echo 'GHOST_PERSONAL_ADMIN_KEY=your_id:your_secret' >> ~/.hermes/.env
```

> **Legacy support**: If `GHOST_ADMIN_KEY` exists without site prefix, it works as fallback for the default site.

## CLI Usage

```bash
# List configured sites
python3 ~/.hermes/skills/productivity/ghost-cms/scripts/ghost.py --list-sites

# Use default site
python3 ~/.hermes/skills/productivity/ghost-cms/scripts/ghost.py token
python3 ~/.hermes/skills/productivity/ghost-cms/scripts/ghost.py list-posts

# Use specific site
python3 ~/.hermes/skills/productivity/ghost-cms/scripts/ghost.py techblog token
python3 ~/.hermes/skills/productivity/ghost-cms/scripts/ghost.py personal list-posts

# Commands
python3 ~/.hermes/skills/productivity/ghost-cms/scripts/ghost.py [site] <command> [args]
```

### Commands

| Command | Args | Description |
|---------|------|-------------|
| `token` | — | Generate JWT token |
| `list-posts` | `[filters]` | List all posts |
| `get-post` | `\u003cid|slug\u003e` | Get post by ID or slug |
| `create-post` | `\u003cfile.json\u003e` | Create post from JSON |
| `update-post` | `\u003cid\u003e \u003cfile.json\u003e` | Update post |
| `publish-post` | `\u003cid\u003e \u003cupdated_at\u003e` | Publish draft |
| `delete-post` | `\u003cid\u003e` | Delete post |
| `list-tags` | — | List all tags |
| `list-pages` | — | List all pages |
| `upload-image` | `\u003cfile\u003e [purpose] [ref]` | Upload image (purpose: image/profile_image/icon) |
| `list-images` | — | List posts with feature images |
| `site-info` | — | Get site information |
| `seo-check` | `[--fix]` | Audit posts for SEO issues (auto-fix with --fix) |
| `list-tiers` | — | List all membership tiers |
| `list-members` | `[limit]` | List members (default: 20) |
| `get-member` | `\u003cid|email\u003e` | Get member by ID or email |
| `create-member` | `\u003cfile.json\u003e` | Create member from JSON |
| `update-member` | `\u003cid\u003e \u003cfile\u003e` | Update member |
| `delete-member` | `\u003cid\u003e` | Delete member |
| `comp-member` | `\u003cid\u003e` | Comp a member (free paid access) |
| `uncomp-member` | `\u003cid\u003e` | Remove comp from member |
| `list-newsletters` | — | List all newsletters |
| `get-settings` | — | Get site settings |
| `update-settings` | `\u003cfile\u003e` | Update site settings |

## Authentication

Ghost Admin API uses **JWT with HS256**:
1. Split Admin key by `:` → `id` and `secret`
2. Header: `{alg: "HS256", typ: "JWT", kid: id}`
3. Payload: `{iat: now, exp: now+300, aud: "/admin/"}`
4. Sign with **hex-decoded secret** using HMAC-SHA256
5. Send as: `Authorization: Ghost $token`

> **Critical**: The secret portion is hex-encoded. Must be decoded before HMAC.

## Core Workflows

### Publish a New Post

```bash
SITE=techblog
TOKEN=$(python3 ~/.hermes/skills/productivity/ghost-cms/scripts/ghost.py $SITE token)
DOMAIN=$(python3 -c "import json; d=json.load(open('$HOME/.hermes/skills/productivity/ghost-cms/sites.json')); print(d['sites']['$SITE']['domain'])")

# Create as draft
curl --http1.1 -X POST "https://$DOMAIN/ghost/api/admin/posts/?source=html" \
  -H "Authorization: Ghost $TOKEN" \
  -H "Accept-Version: v5.0" \
  -H "Content-Type: application/json" \
  -d '{
    "posts": [{
      "title": "My New Post",
      "html": "<p>Content...</p>",
      "status": "draft",
      "tags": ["Tutorial"]
    }]
  }'
```

### Update and Publish

```bash
# Get current updated_at first
python3 ~/.hermes/skills/productivity/ghost-cms/scripts/ghost.py myblog get-post <POST_ID>

# Then publish
python3 ~/.hermes/skills/productivity/ghost-cms/scripts/ghost.py myblog publish-post <POST_ID> "2026-05-12T00:00:41.000Z"
```

### Upload Images

Images can come from two sources:

**Option A: Upload existing image**
```bash
python3 ~/.hermes/skills/productivity/ghost-cms/scripts/ghost.py techblog upload-image /path/to/image.png
```

**Option B: Generate context-aware featured image via LLM**

Hermes crafts a prompt based on the post's key concepts, generates the image, uploads it, and attaches it:

```
┌──────────────────┐     ┌──────────────────┐     ┌─────────────┐
│  Post Content    │────▶│  image_generate  │────▶│  Ghost Admin│
│  (key concepts)  │     │  (context-aware) │     │  API        │
└──────────────────┘     └──────────────────┘     └─────────────┘
```

**Example prompt for a web scraping post:**
> A cinematic dark-themed technical illustration of a web scraping infrastructure. A glowing neural network spider made of light blue and amber energy threads crawls across a digital landscape of server racks and data streams. In the background, ghostly web pages are being extracted and processed into structured data. Cyberpunk aesthetic with deep navy blues, electric cyan highlights, and warm amber accents. Professional tech blog header image, wide format, clean composition with space for text overlay on the left side.

**The generated image is then:**
1. Saved to `~/.hermes/cache/images/`
2. Uploaded via `ghost.py upload-image`
3. Attached via `ghost.py update-post` with the returned URL

**Upload with custom purpose (image|profile_image|icon):**
```bash
python3 ~/.hermes/skills/productivity/ghost-cms/scripts/ghost.py myblog upload-image /path/to/avatar.png profile_image
```

**Upload with custom ref:**
```bash
python3 ~/.hermes/skills/productivity/ghost-cms/scripts/ghost.py myblog upload-image /path/to/image.png image "my-ref"
```

**Response:**
```
Uploaded: image.png
  URL: https://blog.example.com/content/images/2026/05/image.png
  Ref: image.png
```

### Set Featured Image on a Post

Upload the image first, then update the post with the returned URL:

```bash
# 1. Upload image
python3 ~/.hermes/skills/productivity/ghost-cms/scripts/ghost.py myblog upload-image /tmp/my-image.png
# → Returns: https://blog.example.com/content/images/2026/05/my-image.png

# 2. Create/update post with feature_image
python3 ~/.hermes/skills/productivity/ghost-cms/scripts/ghost.py myblog update-post <POST_ID> <<'EOF'
{"posts": [{"feature_image": "https://blog.example.com/content/images/2026/05/my-image.png"}]}
EOF
```

## End-to-End Publishing Workflow

This workflow uses **Hermes Agent's own knowledge** — distilled from session memories, Obsidian vault notes, and Honcho observations — to write blog posts. No external LLM call is needed for content generation.

### How It Works

```
┌─────────────────┐     ┌──────────────────┐     ┌─────────────┐
│  Session Memory │────▶│  Hermes Agent    │────▶│  Ghost Admin│
│  + Obsidian     │     │  (writes post)   │     │  API        │
│  + Honcho       │     │                  │     │  (publishes)│
└─────────────────┘     └──────────────────┘     └─────────────┘
```

1. **Knowledge retrieval** — Hermes reads from:
   - Session memories — past conversations and decisions
   - Knowledge sources — documentation, notes, research
   - Previous session transcripts — via `session_search`

2. **Content synthesis** — Hermes writes the post directly using its own understanding

3. **Publishing** — Ghost Admin API with JWT authentication

### Complete Workflow: Post + Featured Image

When you ask: *"Create a blog post about [topic]"*

Hermes will:
1. Search its memory for relevant sessions (if available)
2. Read any configured knowledge sources
3. **Write the post** using its own understanding. Use first person ("I", "my") — but **this is the human author's voice** (Gordon/Cosmo), not the agent's. The agent accurately attributes work: "I asked my AI agent to build X" not "I built X." The agent represents who actually did what — the human directed, the AI executed. Never have the agent claim credit in the human's voice for work the agent performed.
4. **Generate a context-aware featured image** based on the post's key concepts
5. **Create the post as a draft** on Ghost with the image attached
6. Provide the draft URL for your review

```
┌─────────────────┐     ┌──────────────────┐     ┌──────────────┐     ┌─────────────┐
│  Agent Memory   │────▶│  Hermes Agent    │────▶│  image_generate│───▶│  Ghost Admin│
│  + Knowledge    │     │  (writes post)   │     │  (featured img)│    │  API        │
└─────────────────┘     └──────────────────┘     └──────────────┘     └─────────────┘
```

### Content Generation Strategy

**DO NOT use external LLM APIs for content generation.** The value is in Hermes' accumulated knowledge:

- **Session memories** — What you tried, what failed, what worked
- **Knowledge sources** — Structured notes, documentation, research
- **Error logs** — Real troubleshooting with actual error messages

This produces authentic, experience-based posts — not generic AI-generated content.

### Blog Post Authenticity Rules (CRITICAL)

These rules prevent the most common failure mode: a blog post that sounds polished but is factually wrong about who did what.

1. **Voice attribution**: When the post says "I," it speaks as the human author (Gordon/Cosmo). The agent must accurately represent agency — "I asked my AI agent to build..." not "I built..." when the agent did the building. "I provided the API key" not "I configured the JWT auth."

2. **Honest timeline**: State when things actually happened. If the skill was built in one session on May 10 and the post written May 12, say that. Don't imply a long, considered build.

3. **Bug fixes ≠ design decisions**: Don't frame ad-hoc workarounds as intentional choices. "HTTP/1.1 enforced" was a Cloudflare 403 error — describe what broke and how you fixed it.

4. **Don't advertise untested features**: If the knowledge-driven content workflow hasn't produced any published posts yet, say so. "This post is the first test" is honest. "Knowledge lives in the agent's memory" is marketing when zero such posts exist.

5. **Reference real sources**: Name the vault files and session dates the post draws from. This grounds the post in evidence.

6. **Include what's not done**: A post that admits gaps is more credible than one that implies everything works.

**Pitfall — May 12, 2026**: The first Ghost CMS blog post was rejected because it claimed "I built" when the agent did the building, framed bug fixes as "design decisions," presented a 38-hour-old skill as mature, and advertised untested features. The rewrite worked because it attributed work honestly, showed the real debugging sequence, referenced actual vault files by name, and positioned itself as the first test.

### Image Generation Strategy

Featured images are generated via multimodal LLM with **context-aware prompts**:

| Post Topic | Image Concept |
|------------|--------------|
| Web scraping | Neural spider crawling server racks, data extraction |
| Agent memory | Glowing neural brain with data streams, satellite nodes |
| Database comparison | Two storage towers — rigid grid vs flowing streams |
| System comparison | Five distinct monoliths, each representing a system |
| Publishing pipeline | Robotic figure at holographic desk, memory crystals |

**Prompt pattern:**
```
A cinematic dark-themed illustration of [topic]. [Key visual elements]. 
[Color palette] with [accent colors]. Professional tech blog header, 
wide format, clean composition with space for text overlay.
```

The generated image is saved to `~/.hermes/cache/images/`, uploaded to Ghost, and attached to the post automatically.

### Adding a New Site

1. Add site to `sites.json` with domain and env key names
2. Add the Admin API key to `~/.hermes/.env` with the configured env var name
3. Test: `python3 ghost.py newsite site-info`

## Requirements

- Python 3.8+
- `PyJWT` library (`pip install pyjwt`)
- `curl` with HTTP/1.1 support
- Ghost Admin API key (from Ghost Admin → Integrations)
- Hermes Agent with `image_generate` tool (for featured images)

## Post Object Fields

| Field | Type | Description |
|-------|------|-------------|
| `title` | string | **Required**. Post title |
| `html` | string | HTML content (converted to Lexical if `?source=html`) |
| `lexical` | JSON | Native Ghost format (preferred) |
| `status` | string | `draft`, `published`, `scheduled`, `sent` |
| `visibility` | string | `public`, `members`, `paid`, `tiers` |
| `featured` | boolean | Highlight on homepage |
| `tags` | array | Tag names (strings) or objects |
| `authors` | array | Author emails (strings) or objects |
| `feature_image` | string | URL to featured image |
| `meta_title` | string | SEO title |
| `meta_description` | string | SEO description |
| `canonical_url` | string | Override canonical URL |
| `published_at` | ISO date | Schedule publish time |
| `tiers` | array | Tier objects for tier-specific access |
| `newsletters` | array | Newsletter IDs to send this post to |

## Error Handling

| Status | Meaning |
|--------|---------|
| 200 | Success |
| 201 | Created |
| 400 | Bad Request — check JSON format |
| 401 | Unauthorized — invalid/expired JWT |
| 403 | Forbidden — insufficient permissions |
| 404 | Not Found |
| 422 | Validation Error — check field values |
| 500 | Server Error |

## Full Endpoint Reference

### Posts
- `GET /admin/posts/` — Browse
- `GET /admin/posts/{id}/` — Read by ID
- `GET /admin/posts/slug/{slug}/` — Read by slug
- `POST /admin/posts/` — Create
- `PUT /admin/posts/{id}/` — Update
- `DELETE /admin/posts/{id}/` — Delete
- `POST /admin/posts/{id}/copy` — Duplicate

### Pages
- `GET /admin/pages/` — Browse
- `GET /admin/pages/{id}/` — Read
- `POST /admin/pages/` — Create
- `PUT /admin/pages/{id}/` — Update
- `DELETE /admin/pages/{id}/` — Delete

### Tags
- `GET /admin/tags/` — Browse
- `POST /admin/tags/` — Create
- `PUT /admin/tags/{id}/` — Update
- `DELETE /admin/tags/{id}/` — Delete

### Images
- `POST /admin/images/upload/` — Upload (multipart/form-data)
  - Fields: `file` (Blob/File), `purpose` (image|profile_image|icon), `ref` (optional string)
  - Returns: `{images: [{url, ref}]}`

### Members
- `GET /admin/members/` — Browse
- `GET /admin/members/{id}/` — Read by ID
- `GET /admin/members/?filter=email:{email}` — Read by email
- `POST /admin/members/` — Create
- `PUT /admin/members/{id}/` — Update (including `comped: true/false`)
- `DELETE /admin/members/{id}/` — Delete

### Tiers
- `GET /admin/tiers/` — Browse all tiers
- `PUT /admin/tiers/{id}/` — Update tier (name, price, description)

### Newsletters
- `GET /admin/newsletters/` — Browse
- `POST /admin/newsletters/` — Create
- `PUT /admin/newsletters/{id}/` — Update

### Settings
- `GET /admin/settings/` — Read all settings
- `PUT /admin/settings/` — Update settings (title, description, etc.)

### Site
- `GET /admin/site/` — Read site info (unauthenticated)

### SEO Optimization

Check all published posts for SEO issues:

```bash
# Audit only
python3 ~/.hermes/skills/productivity/ghost-cms/scripts/seo-check.py myblog

# Audit and auto-fix
python3 ~/.hermes/skills/productivity/ghost-cms/scripts/seo-check.py myblog --fix
```

**Checks performed:**
| Check | Issue Level | Auto-fixable |
|-------|------------|--------------|
| Title length | Warning if >70 chars | No |
| Meta title | Warning if missing | Yes (copies post title) |
| Meta description | Error if missing, warning if <120 chars | Yes (generates from first paragraph) |
| Featured image | Error if missing | No |
| Canonical URL | Warning if missing | Yes (generates from slug) |
| Content length | Warning if <300 words | No |
| Slug quality | Warning if <3 words | No |
| Subheadings | Warning if no h2/h3 | No |
| Images | Warning if no images | No |

**What auto-fix does:**
- Generates `meta_description` from first paragraph (truncated to 160 chars)
- Sets `meta_title` to post title if missing
- Sets `canonical_url` to `https://domain/slug/`

**What requires manual fix:**
- Title too long/short — edit the post
- Missing feature image — upload and attach
- Thin content — write more
- No subheadings — add h2/h3 sections

## Membership & Tier Management

Ghost has built-in membership with two default tiers: **Free** and **Paid**. The skill can manage members, tiers, and newsletters.

### View Tiers

```bash
python3 ~/.hermes/skills/productivity/ghost-cms/scripts/ghost.py myblog list-tiers
```

**Example output:**
```
6a01f4c9... | Free | Type: free | Active: True
6a01f4c9... | Tech Notes | Type: paid | Active: True | Monthly: 5 USD | Yearly: 50 USD
```

### Manage Members

```bash
# List members (default 20)
python3 ~/.hermes/skills/productivity/ghost-cms/scripts/ghost.py myblog list-members
python3 ~/.hermes/skills/productivity/ghost-cms/scripts/ghost.py myblog list-members 100

# Get member by ID or email
python3 ~/.hermes/skills/productivity/ghost-cms/scripts/ghost.py myblog get-member <member-id>
python3 ~/.hermes/skills/productivity/ghost-cms/scripts/ghost.py myblog get-member user@example.com

# Create member
cat > /tmp/member.json <<'EOF'
{"members": [{"name": "John Doe", "email": "john@example.com", "subscribed": true}]}
EOF
python3 ~/.hermes/skills/productivity/ghost-cms/scripts/ghost.py myblog create-member /tmp/member.json

# Comp a member (give free paid access)
python3 ~/.hermes/skills/productivity/ghost-cms/scripts/ghost.py myblog comp-member <member-id>

# Remove comp
python3 ~/.hermes/skills/productivity/ghost-cms/scripts/ghost.py myblog uncomp-member <member-id>

# Delete member
python3 ~/.hermes/skills/productivity/ghost-cms/scripts/ghost.py myblog delete-member <member-id>
```

### Member JSON Format

```json
{
  "members": [{
    "name": "John Doe",
    "email": "john@example.com",
    "subscribed": true,
    "labels": ["beta-tester", "vip"],
    "note": "Early adopter",
    "tiers": [{"id": "tier-id-here"}]
  }]
}
```

### Content Visibility

Control who can see posts:

| `visibility` | Who Can See |
|-------------|-------------|
| `public` | Everyone |
| `members` | Signed-in members only |
| `paid` | Paid members only |
| `tiers` | Specific tier members (use `tiers` array) |

Set when creating/updating a post:
```json
{"posts": [{"visibility": "paid", "tiers": [{"id": "paid-tier-id"}]}]}
```

### Newsletters

```bash
# List newsletters
python3 ~/.hermes/skills/productivity/ghost-cms/scripts/ghost.py myblog list-newsletters
```

**Send a post as newsletter:** Include `newsletters` array when creating/updating:
```json
{"posts": [{
  "title": "Weekly Update",
  "html": "<p>This week's updates...</p>",
  "status": "published",
  "newsletters": [{"id": "newsletter-id-here"}]
}]}
```

**Note**: The post must be `published` or `sent` to trigger newsletter delivery. Drafts won't send.

### Site Settings

> **Note**: Integration tokens cannot update settings that affect billing or membership (like `paid_members_enabled`). These require a **Staff Access Token** (user-level auth). Use Ghost Admin UI for those changes.

```bash
# View settings (works with integration token)
python3 ~/.hermes/skills/productivity/ghost-cms/scripts/ghost.py myblog get-settings

# Update settings (may fail for billing-related settings)
cat > /tmp/settings.json <<'EOF'
{"settings": [{"key": "title", "value": "New Blog Title"}]}
EOF
python3 ~/.hermes/skills/productivity/ghost-cms/scripts/ghost.py myblog update-settings /tmp/settings.json
```

**Settings that require Staff Access Token (not integration token):**
- `paid_members_enabled` — Enable/disable paid memberships
- Stripe connection keys
- Tier pricing changes

**Settings that work with integration token:**
- `title`, `description`, `icon`, `cover_image`
- `default_content_visibility`
- `meta_title`, `meta_description`
- `codeinjection_head`, `codeinjection_foot`

## Multilingual Posts

Ghost has no native multilingual support. The best approach for a Hermes-managed blog is **separate posts with language tags**.

### Approach: Tagged Language Versions

When you say *"Write this post in Korean"*:

1. Hermes writes the Korean version
2. Creates it with slug `original-slug-ko`
3. Tags it `#korean` and `#translation`
4. Links to English version via canonical URL
5. Both posts live on the same site

**Example:**
| Post | Slug | Tags | Language |
|------|------|------|----------|
| Self-Hosting Firecrawl | `self-hosting-firecrawl` | `english` | English |
| Firecrawl 자체 호스팅 | `self-hosting-firecrawl-ko` | `korean`, `translation` | Korean |

**Benefits:**
- No extra Ghost installs or subscriptions
- SEO-friendly (separate URLs, hreflang possible)
- Readers find content via tag filters
- Hermes manages both versions

**Limitations:**
- No automatic language switcher in theme
- Manual translation (not auto-translated)
- Each language is a separate post

### Alternative: Weglot Integration

For automatic translation, integrate [Weglot](https://weglot.com/) (€79+/mo). Ghost theme adds a language switcher, Weglot translates content on-the-fly. Best for high-traffic sites.

### Alternative: Separate Ghost Installs

Run `blog.example.com` (English) and `ko.blog.example.com` (Korean) as separate Ghost instances. Requires $25+/mo per language on Ghost Pro. Best for full localization (different themes, navigation, etc.).

## Efficiency Tips

### Combine Image Attachment + Publish in One Call

The skill shows uploading images and publishing as separate steps, but you can combine them into a single `update-post` call after getting `updated_at`:

```bash
# 1. Upload image (returns URL)
python3 ghost.py myblog upload-image /tmp/image.png

# 2. Get current updated_at
python3 ghost.py myblog get-post <id>

# 3. Combine image + publish in one call (saves an API round-trip)
echo '{"posts": [{"updated_at": "2026-05-12T03:21:07.000Z", "feature_image": "https://...image.png", "status": "published"}]}' > /tmp/publish.json
python3 ghost.py myblog update-post <id> /tmp/publish.json
```

This avoids a separate `publish-post` call and a second `updated_at` fetch.

### SEO Audit Applies to All Posts

`seo-check.py` audits ALL published posts on the site, not just the one you specify. After publishing a new post, running `--fix` will also repair SEO issues on older posts. Use this to your advantage — run it after every publish to keep the whole site healthy.

## Tips

- **JWT expires in 5 minutes** — generate fresh tokens per request batch
- Use `--http1.1` with curl — HTTP/2 can cause issues with Cloudflare
- Use `?source=html` when sending HTML for automatic Lexical conversion
- Tags in short form (`["name1", "name2"]`) are auto-created if missing
- Always wrap payloads in `{"posts": [{...}]}` or `{"pages": [{...}]}`
- **Members-only posts**: Set `"visibility": "members"` for member-gated content
- **Paid posts**: Set `"visibility": "paid"` for paid-tier-only content
- **Tier-specific posts**: Set `"visibility": "tiers"` with `"tiers": [{"id": "..."}]`
- **Comping members**: Use `comp-member` to give free paid access without Stripe payment
- **Settings limits**: Integration tokens can't change billing-related settings — use Staff Access Token or Ghost Admin UI
- **SEO**: Run `seo-check.py --fix` after publishing to auto-optimize meta tags
