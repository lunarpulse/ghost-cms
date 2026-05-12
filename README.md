# Ghost CMS Skill for Hermes Agent

Manage one or more Ghost blogs via the Admin API. Features multi-site support, LLM-generated featured images, membership/tier management, SEO optimization, and on-demand backups.

## Quick Start

1. **Install dependency:**
   ```bash
   pip install pyjwt
   ```

2. **Copy the site template:**
   ```bash
   cp sites.json.template sites.json
   ```

3. **Edit `sites.json`** with your Ghost site domain and API key env var names.

4. **Add your Admin API key to `~/.hermes/.env`:**
   ```bash
   echo 'GHOST_MYBLOG_ADMIN_KEY=your_id:your_secret' >> ~/.hermes/.env
   ```

5. **Test:**
   ```bash
   python3 scripts/ghost.py myblog site-info
   ```

## Features

- **Multi-site** — Manage multiple blogs from one CLI
- **Post CRUD** — Create, read, update, publish, delete posts
- **Image upload** — Upload featured images with custom purposes
- **LLM-generated images** — Context-aware featured images via `image_generate`
- **Membership** — List tiers, manage members, comp/uncomp access
- **SEO check** — Audit posts and auto-fix meta tags
- **Export** — On-demand backup to markdown with YAML frontmatter

## Files

| File | Purpose |
|------|---------|
| `SKILL.md` | Full documentation |
| `scripts/ghost.py` | Main CLI for all operations |
| `scripts/seo-check.py` | SEO audit and auto-fix |
| `scripts/export-site.py` | On-demand site backup |
| `scripts/ghost-auth.sh` | Bash JWT token generator (fallback) |
| `sites.json.template` | Site configuration template |
| `templates/post-template.md` | Post YAML frontmatter template |

## Requirements

- Python 3.8+
- PyJWT library
- curl with HTTP/1.1 support
- Ghost Admin API key (from Ghost Admin → Integrations)
- Hermes Agent with `image_generate` tool (optional, for featured images)

## License

MIT — Use freely. No warranty.
