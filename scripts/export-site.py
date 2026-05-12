#!/usr/bin/env python3
"""
On-demand Ghost site export
Usage: python3 export-site.py [site] [output_dir]

Exports all posts, pages, tags, and settings to local markdown files.
Images are referenced by URL, not downloaded (they're on Ghost CDN).
"""
import os, sys, json, re
from datetime import datetime

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, SCRIPT_DIR)
from ghost import resolve_site, api_request

def strip_html(html):
    if not html:
        return ""
    text = re.sub(r'<(script|style)[^>]*>.*?</\1>', ' ', html, flags=re.DOTALL)
    text = re.sub(r'<[^>]+>', ' ', text)
    text = text.replace('&nbsp;', ' ').replace('&lt;', '<').replace('&gt;', '>')
    text = text.replace('&amp;', '&').replace('&quot;', '"')
    return text

def post_to_markdown(post, domain):
    """Convert a Ghost post to markdown with YAML frontmatter"""
    lines = []
    lines.append('---')
    lines.append(f'title: "{post.get("title", "").replace(chr(34), chr(92)+chr(34))}"')
    lines.append(f'slug: {post.get("slug", "")}')
    lines.append(f'status: {post.get("status", "draft")}')
    lines.append(f'visibility: {post.get("visibility", "public")}')
    lines.append(f'published_at: {post.get("published_at", "")}')
    
    if post.get('feature_image'):
        lines.append(f'feature_image: {post["feature_image"]}')
    
    if post.get('meta_title'):
        lines.append(f'meta_title: "{post["meta_title"].replace(chr(34), chr(92)+chr(34))}"')
    if post.get('meta_description'):
        lines.append(f'meta_description: "{post["meta_description"].replace(chr(34), chr(92)+chr(34))}"')
    
    tags = post.get('tags', [])
    if tags:
        tag_names = [t['name'] if isinstance(t, dict) else t for t in tags]
        lines.append(f'tags: [{", ".join(tag_names)}]')
    
    lines.append(f'url: https://{domain}/{post.get("slug", "")}/')
    lines.append('---')
    lines.append('')
    
    # Add HTML content as-is (can be converted to markdown later if needed)
    html = post.get('html', '')
    if html:
        lines.append(html)
    
    return '\n'.join(lines)

def main():
    args = sys.argv[1:]
    site_name = args[0] if args else None
    output_dir = args[1] if len(args) > 1 else None
    
    _, cfg = resolve_site(site_name)
    domain = cfg['domain']
    
    # Default output dir
    if not output_dir:
        timestamp = datetime.now().strftime('%Y-%m-%d')
        output_dir = os.path.expanduser(f'~/Backups/ghost/{domain}/{timestamp}')
    
    os.makedirs(output_dir, exist_ok=True)
    print(f"Exporting to: {output_dir}\n")
    
    # Export posts
    print("Fetching posts...")
    posts_result = api_request(cfg, 'GET', '/posts/?limit=all&formats=html&include=tags')
    posts = posts_result.get('posts', [])
    
    posts_dir = os.path.join(output_dir, 'posts')
    os.makedirs(posts_dir, exist_ok=True)
    
    for post in posts:
        md = post_to_markdown(post, domain)
        filename = f"{post.get('slug', 'untitled')}.md"
        filepath = os.path.join(posts_dir, filename)
        with open(filepath, 'w', encoding='utf-8') as f:
            f.write(md)
    
    print(f"  {len(posts)} posts exported to {posts_dir}/")
    
    # Export pages
    print("Fetching pages...")
    pages_result = api_request(cfg, 'GET', '/pages/?limit=all&formats=html&include=tags')
    pages = pages_result.get('pages', [])
    
    pages_dir = os.path.join(output_dir, 'pages')
    os.makedirs(pages_dir, exist_ok=True)
    
    for page in pages:
        md = post_to_markdown(page, domain)
        filename = f"{page.get('slug', 'untitled')}.md"
        filepath = os.path.join(pages_dir, filename)
        with open(filepath, 'w', encoding='utf-8') as f:
            f.write(md)
    
    print(f"  {len(pages)} pages exported to {pages_dir}/")
    
    # Export tags
    print("Fetching tags...")
    tags_result = api_request(cfg, 'GET', '/tags/?limit=all')
    tags = tags_result.get('tags', [])
    
    tags_file = os.path.join(output_dir, 'tags.json')
    with open(tags_file, 'w', encoding='utf-8') as f:
        json.dump(tags, f, indent=2, ensure_ascii=False)
    
    print(f"  {len(tags)} tags exported to {tags_file}")
    
    # Export settings (read-only, no sensitive data)
    print("Fetching settings...")
    settings_result = api_request(cfg, 'GET', '/settings/')
    settings = settings_result.get('settings', [])
    
    # Filter to non-sensitive settings
    safe_keys = ['title', 'description', 'icon', 'cover_image', 'default_content_visibility',
                 'members_signup_access', 'paid_members_enabled', 'meta_title', 'meta_description',
                 'og_image', 'og_title', 'og_description', 'twitter_image', 'twitter_title',
                 'twitter_description', 'lang', 'timezone', 'codeinjection_head', 'codeinjection_foot']
    safe_settings = [s for s in settings if s.get('key') in safe_keys]
    
    settings_file = os.path.join(output_dir, 'settings.json')
    with open(settings_file, 'w', encoding='utf-8') as f:
        json.dump(safe_settings, f, indent=2, ensure_ascii=False)
    
    print(f"  {len(safe_settings)} settings exported to {settings_file}")
    
    # Export member count (not emails, for privacy)
    print("Fetching member stats...")
    members_result = api_request(cfg, 'GET', '/members/?limit=1')
    member_count = members_result.get('meta', {}).get('pagination', {}).get('total', 0)
    
    stats = {
        'exported_at': datetime.now().isoformat(),
        'domain': domain,
        'posts_count': len(posts),
        'pages_count': len(pages),
        'tags_count': len(tags),
        'members_count': member_count,
        'tiers': []
    }
    
    # Export tier info (public info only)
    tiers_result = api_request(cfg, 'GET', '/tiers/?limit=all')
    tiers = tiers_result.get('tiers', [])
    for tier in tiers:
        stats['tiers'].append({
            'name': tier.get('name'),
            'type': tier.get('type'),
            'active': tier.get('active'),
            'monthly_price': tier.get('monthly_price'),
            'yearly_price': tier.get('yearly_price')
        })
    
    stats_file = os.path.join(output_dir, 'stats.json')
    with open(stats_file, 'w', encoding='utf-8') as f:
        json.dump(stats, f, indent=2, ensure_ascii=False)
    
    print(f"  Stats exported to {stats_file}")
    
    # Summary
    print(f"\n=== Export Complete ===")
    print(f"Posts: {len(posts)}")
    print(f"Pages: {len(pages)}")
    print(f"Tags: {len(tags)}")
    print(f"Members: {member_count}")
    print(f"Location: {output_dir}")
    print(f"\nTo restore: posts are markdown with YAML frontmatter.")
    print(f"Images are NOT downloaded — they remain at {domain}/content/images/")

if __name__ == '__main__':
    main()
