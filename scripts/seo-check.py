#!/usr/bin/env python3
"""
SEO Check for Ghost posts
Usage: python3 seo-check.py [site] [--fix]

Analyzes published posts for SEO issues and optionally auto-fixes them.
"""
import subprocess, json, sys, os, re

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

def generate_meta_description(html, max_len=160):
    text = strip_html(html)
    sentences = text.split('.')
    desc = sentences[0].strip() if sentences else text[:max_len]
    if len(desc) > max_len:
        desc = desc[:max_len-3] + '...'
    return desc

def check_post_seo(post):
    issues = []
    warnings = []
    suggestions = {}
    
    title = post.get('title', '')
    meta_title = post.get('meta_title', '') or title
    meta_desc = post.get('meta_description', '')
    feature_image = post.get('feature_image', '')
    html = post.get('html', '')
    slug = post.get('slug', '')
    canonical = post.get('canonical_url', '')
    
    plain_text = strip_html(html)
    word_count = len(plain_text.split())
    
    if len(title) < 20:
        issues.append(f"Title too short ({len(title)} chars)")
    elif len(title) > 70:
        warnings.append(f"Title may be truncated ({len(title)} chars)")
    
    if not post.get('meta_title'):
        warnings.append("Missing meta_title")
        suggestions['meta_title'] = title[:60]
    
    if not meta_desc:
        issues.append("Missing meta_description")
        suggestions['meta_description'] = generate_meta_description(html)
    elif len(meta_desc) < 120:
        warnings.append(f"Meta description short ({len(meta_desc)} chars)")
        suggestions['meta_description'] = generate_meta_description(html)
    elif len(meta_desc) > 170:
        warnings.append(f"Meta description may be truncated ({len(meta_desc)} chars)")
    
    if not feature_image:
        issues.append("Missing feature_image")
    
    if not canonical:
        warnings.append("Missing canonical_url")
        suggestions['canonical_url'] = f"https://{post.get('_domain', 'example.com')}/{slug}/"
    
    if word_count < 300:
        warnings.append(f"Content thin ({word_count} words)")
    
    if len(slug.split('-')) < 3:
        warnings.append(f"Slug '{slug}' is short")
    
    if '<img' not in html and not feature_image:
        warnings.append("No images in post")
    
    has_h2 = '<h2' in html or '<h3' in html
    if not has_h2:
        warnings.append("No subheadings (h2/h3)")
    
    return issues, warnings, suggestions, word_count

def apply_fixes(site_config, post_id, updated_at, suggestions):
    if not suggestions:
        return True
    
    data = {"posts": [{"updated_at": updated_at, **suggestions}]}
    result = api_request(site_config, 'PUT', f'/posts/{post_id}/?source=html', data)
    return 'posts' in result

def main():
    args = sys.argv[1:]
    do_fix = '--fix' in args
    if do_fix:
        args.remove('--fix')
    
    site_name = args[0] if args else None
    _, cfg = resolve_site(site_name)
    cfg['_domain'] = cfg['domain']  # For canonical URL generation
    
    result = api_request(cfg, 'GET', f'/posts/?limit=all&formats=html&fields=id,title,slug,meta_title,meta_description,feature_image,html,canonical_url,status,visibility,updated_at')
    posts = result.get('posts', [])
    
    print(f"=== SEO Audit: {len(posts)} posts ===\n")
    
    total_issues = 0
    total_warnings = 0
    fixed_count = 0
    
    for post in posts:
        if post.get('status') != 'published':
            continue
        
        post['_domain'] = cfg['domain']
        title = post.get('title', 'Untitled')
        slug = post.get('slug', '')
        
        issues, warnings, suggestions, word_count = check_post_seo(post)
        total_issues += len(issues)
        total_warnings += len(warnings)
        
        if issues or warnings:
            print(f"📄 {title}")
            print(f"   Words: {word_count}")
            
            for issue in issues:
                print(f"   ❌ {issue}")
            for warning in warnings:
                print(f"   ⚠️  {warning}")
            
            if suggestions:
                if do_fix:
                    success = apply_fixes(cfg, post['id'], post['updated_at'], suggestions)
                    if success:
                        print(f"   ✅ Fixed: {', '.join(suggestions.keys())}")
                        fixed_count += 1
                    else:
                        print(f"   ❌ Failed to fix")
                else:
                    print(f"   💡 Suggested: {', '.join(suggestions.keys())}")
            print()
    
    print(f"=== Summary ===")
    print(f"Issues: {total_issues} | Warnings: {total_warnings}")
    if do_fix:
        print(f"Fixed: {fixed_count} posts")
    else:
        print(f"\nRun with --fix to auto-apply suggested changes")

if __name__ == '__main__':
    main()
