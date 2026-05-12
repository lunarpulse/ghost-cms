#!/usr/bin/env python3
"""
Ghost CMS Admin API Python CLI — Multi-Site Support
Usage: python3 ghost.py [site] <command> [options]

Sites are defined in ../sites.json. Secrets are in ~/.hermes/.env.

Examples:
    python3 ghost.py techblog token
    python3 ghost.py techblog list-posts
    python3 ghost.py techblog create-post /tmp/post.json
    python3 ghost.py --list-sites

If [site] is omitted, uses the default_site from sites.json.
"""

import os
import sys
import json
import base64
import hmac
import hashlib
import subprocess
import time

# ── Paths ──────────────────────────────────────────────────────────
SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
SITES_FILE = os.path.join(SCRIPT_DIR, '..', 'sites.json')
ENV_FILE = os.path.expanduser('~/.hermes/.env')

# ── Site Registry ──────────────────────────────────────────────────
def load_sites():
    with open(SITES_FILE) as f:
        return json.load(f)

def resolve_site(site_name=None):
    sites = load_sites()
    if site_name is None:
        site_name = sites.get('default_site')
    if site_name not in sites.get('sites', {}):
        available = ', '.join(sites.get('sites', {}).keys())
        print(f"Error: Unknown site '{site_name}'. Available: {available}", file=sys.stderr)
        sys.exit(1)
    return site_name, sites['sites'][site_name]

def load_env():
    env = {}
    if os.path.exists(ENV_FILE):
        with open(ENV_FILE) as f:
            for line in f:
                line = line.strip()
                if line and not line.startswith('#') and '=' in line:
                    k, v = line.split('=', 1)
                    env[k] = v
    return env

def get_secret(site_config, key_type='admin'):
    env = load_env()
    env_key = site_config.get(f'{key_type}_key_env')
    if not env_key:
        print(f"Error: No {key_type}_key_env configured for this site", file=sys.stderr)
        sys.exit(1)
    value = env.get(env_key)
    # Fallback to legacy key names for backward compatibility
    if not value and key_type == 'admin':
        value = env.get('GHOST_ADMIN_KEY')
    if not value and key_type == 'content':
        value = env.get('GHOST_CONTENT_KEY')
    if not value:
        print(f"Error: {env_key} (or legacy fallback) not found in {ENV_FILE}", file=sys.stderr)
        sys.exit(1)
    return value

# ── JWT Token Generation ───────────────────────────────────────────
def generate_token(site_config):
    admin_key = get_secret(site_config, 'admin')
    
    if ':' not in admin_key:
        print("Error: Admin key must be in 'id:secret' format", file=sys.stderr)
        sys.exit(1)
    
    key_id, secret = admin_key.split(':', 1)
    
    header = base64.urlsafe_b64encode(json.dumps({
        "alg": "HS256",
        "typ": "JWT",
        "kid": key_id
    }).encode()).decode().rstrip('=')
    
    now = int(time.time())
    payload = base64.urlsafe_b64encode(json.dumps({
        "iat": now,
        "exp": now + 300,
        "aud": "/admin/"
    }).encode()).decode().rstrip('=')
    
    message = f"{header}.{payload}"
    # Ghost Admin API secrets are hex-encoded; decode before signing
    try:
        secret_bytes = bytes.fromhex(secret)
    except ValueError:
        # Fallback: treat as raw string if not valid hex
        secret_bytes = secret.encode()
    signature = base64.urlsafe_b64encode(
        hmac.new(secret_bytes, message.encode(), hashlib.sha256).digest()
    ).decode().rstrip('=')
    
    return f"{message}.{signature}"

# ── API Request via curl (HTTP/1.1 for Cloudflare) ─────────────────
def api_request(site_config, method, endpoint, data=None, content_type="application/json"):
    token = generate_token(site_config)
    domain = site_config['domain']
    api_version = site_config.get('api_version', 'v5.0')
    http_version = site_config.get('http_version', '1.1')
    
    url = f"https://{domain}/ghost/api/admin{endpoint}"
    
    cmd = ['curl', f'--http{http_version}', '-s', '-X', method]
    cmd.extend(['-H', f'Authorization: Ghost {token}'])
    cmd.extend(['-H', f'Accept-Version: {api_version}'])
    
    if data:
        cmd.extend(['-H', f'Content-Type: {content_type}'])
        if isinstance(data, dict):
            cmd.extend(['-d', json.dumps(data)])
        else:
            cmd.extend(['-d', data])
    
    cmd.append(url)
    
    result = subprocess.run(cmd, capture_output=True, text=True)
    
    if result.returncode != 0:
        print(f"curl error: {result.stderr}", file=sys.stderr)
        sys.exit(1)
    
    try:
        return json.loads(result.stdout)
    except json.JSONDecodeError:
        return {"raw": result.stdout}

# ── Commands ───────────────────────────────────────────────────────
def cmd_token(site_config):
    print(generate_token(site_config))

def cmd_list_posts(site_config, args):
    params = "?limit=all&include=tags,authors"
    if args:
        params += "&" + "&".join(args)
    result = api_request(site_config, 'GET', f'/posts/{params}')
    posts = result.get('posts', [])
    for p in posts:
        print(f"{p['id']} | {p['status']:9} | {p['title']}")
        print(f"  slug: {p['slug']} | updated: {p['updated_at']}")
        print()

def cmd_get_post(site_config, identifier):
    if len(identifier) == 24:
        endpoint = f'/posts/{identifier}/?include=tags,authors'
    else:
        endpoint = f'/posts/slug/{identifier}/?include=tags,authors'
    result = api_request(site_config, 'GET', endpoint)
    print(json.dumps(result, indent=2))

def cmd_create_post(site_config, filepath):
    with open(filepath) as f:
        data = json.load(f)
    result = api_request(site_config, 'POST', '/posts/?source=html', data)
    
    if 'posts' in result:
        p = result['posts'][0]
        print(f"Created: {p['title']}")
        print(f"  ID: {p['id']}")
        print(f"  Slug: {p['slug']}")
        print(f"  Status: {p['status']}")
        print(f"  URL: https://{site_config['domain']}/{p['slug']}/")
    else:
        print(json.dumps(result, indent=2))

def cmd_update_post(site_config, post_id, filepath):
    with open(filepath) as f:
        data = json.load(f)
    result = api_request(site_config, 'PUT', f'/posts/{post_id}/?source=html', data)
    print(json.dumps(result, indent=2))

def cmd_publish_post(site_config, post_id, updated_at):
    data = {"posts": [{"status": "published", "updated_at": updated_at}]}
    result = api_request(site_config, 'PUT', f'/posts/{post_id}/?source=html', data)
    
    if 'posts' in result:
        p = result['posts'][0]
        print(f"Published: {p['title']}")
        print(f"  URL: https://{site_config['domain']}/{p['slug']}/")
        print(f"  Status: {p['status']}")
    else:
        print(json.dumps(result, indent=2))

def cmd_delete_post(site_config, post_id):
    result = api_request(site_config, 'DELETE', f'/posts/{post_id}/')
    print(json.dumps(result, indent=2))

def cmd_list_tags(site_config):
    result = api_request(site_config, 'GET', '/tags/?limit=all')
    tags = result.get('tags', [])
    for t in tags:
        print(f"{t['id']} | {t['name']} | slug: {t['slug']}")

def cmd_list_pages(site_config):
    result = api_request(site_config, 'GET', '/pages/?limit=all')
    pages = result.get('pages', [])
    for p in pages:
        print(f"{p['id']} | {p['status']:9} | {p['title']}")

def cmd_site_info(site_config):
    domain = site_config['domain']
    result = api_request(site_config, 'GET', '/site/')
    print(json.dumps(result, indent=2))

def cmd_upload_image(site_config, filepath, purpose='image', ref=None):
    """Upload an image to Ghost. Purpose: image|profile_image|icon"""
    token = generate_token(site_config)
    domain = site_config['domain']
    api_version = site_config.get('api_version', 'v5.0')
    http_version = site_config.get('http_version', '1.1')
    
    if not os.path.exists(filepath):
        print(f"Error: File not found: {filepath}", file=sys.stderr)
        sys.exit(1)
    
    url = f"https://{domain}/ghost/api/admin/images/upload/"
    
    # Build curl command with multipart form data
    cmd = ['curl', f'--http{http_version}', '-s', '-X', 'POST']
    cmd.extend(['-H', f'Authorization: Ghost {token}'])
    cmd.extend(['-H', f'Accept-Version: {api_version}'])
    cmd.extend(['-F', f'file=@{filepath}'])
    cmd.extend(['-F', f'purpose={purpose}'])
    
    if ref:
        cmd.extend(['-F', f'ref={ref}'])
    else:
        # Use filename as ref by default
        cmd.extend(['-F', f'ref={os.path.basename(filepath)}'])
    
    cmd.append(url)
    
    result = subprocess.run(cmd, capture_output=True, text=True)
    
    if result.returncode != 0:
        print(f"curl error: {result.stderr}", file=sys.stderr)
        sys.exit(1)
    
    try:
        data = json.loads(result.stdout)
        if 'images' in data:
            img = data['images'][0]
            print(f"Uploaded: {img.get('ref', os.path.basename(filepath))}")
            print(f"  URL: {img['url']}")
            print(f"  Ref: {img.get('ref', 'N/A')}")
        else:
            print(json.dumps(data, indent=2))
    except json.JSONDecodeError:
        print("Raw response:", result.stdout[:500])

def cmd_list_images(site_config):
    """List images by querying posts with feature_image field"""
    result = api_request(site_config, 'GET', '/posts/?limit=all&fields=title,feature_image,slug')
    posts = result.get('posts', [])
    for p in posts:
        if p.get('feature_image'):
            print(f"{p['slug']}: {p['feature_image']}")

def cmd_list_tiers(site_config):
    result = api_request(site_config, 'GET', '/tiers/?limit=all')
    tiers = result.get('tiers', [])
    for t in tiers:
        price_info = ""
        if t.get('type') == 'paid':
            monthly = t.get('monthly_price')
            yearly = t.get('yearly_price')
            currency = t.get('currency', '').upper()
            if monthly:
                price_info = f" | Monthly: {monthly/100:.0f} {currency}"
            if yearly:
                price_info += f" | Yearly: {yearly/100:.0f} {currency}"
        print(f"{t['id']} | {t['name']} | Type: {t.get('type', 'unknown')} | Active: {t.get('active', False)}{price_info}")

def cmd_list_members(site_config, limit='20'):
    result = api_request(site_config, 'GET', f'/members/?limit={limit}&include=tiers')
    members = result.get('members', [])
    total = result.get('meta', {}).get('pagination', {}).get('total', '?')
    print(f"Showing {len(members)} of {total} members")
    for m in members:
        tiers = m.get('tiers', [])
        tier_names = ', '.join(t['name'] for t in tiers) if tiers else 'Free'
        status = "✓ Comped" if m.get('comped') else m.get('status', 'free')
        print(f"{m['id']} | {m.get('name', 'N/A')} | {m['email']} | {tier_names} | {status}")

def cmd_get_member(site_config, identifier):
    # Try ID first (24 hex chars), then email
    if len(identifier) == 24:
        endpoint = f'/members/{identifier}/?include=tiers'
    else:
        # Email needs to be URL-encoded
        import urllib.parse
        email = urllib.parse.quote(identifier, safe='')
        endpoint = f'/members/?filter=email:{email}&include=tiers'
    
    result = api_request(site_config, 'GET', endpoint)
    if 'members' in result:
        if result['members']:
            print(json.dumps({'members': [result['members'][0]]}, indent=2))
        else:
            print("Member not found")
    else:
        print(json.dumps(result, indent=2))

def cmd_create_member(site_config, filepath):
    with open(filepath) as f:
        data = json.load(f)
    result = api_request(site_config, 'POST', '/members/?include=tiers', data)
    if 'members' in result:
        m = result['members'][0]
        print(f"Created: {m.get('name', 'N/A')} ({m['email']})")
        print(f"  ID: {m['id']}")
        print(f"  Status: {m.get('status')}")
    else:
        print(json.dumps(result, indent=2))

def cmd_update_member(site_config, member_id, filepath):
    with open(filepath) as f:
        data = json.load(f)
    result = api_request(site_config, 'PUT', f'/members/{member_id}/?include=tiers', data)
    print(json.dumps(result, indent=2))

def cmd_delete_member(site_config, member_id):
    result = api_request(site_config, 'DELETE', f'/members/{member_id}/')
    print(json.dumps(result, indent=2))

def cmd_comp_member(site_config, member_id):
    """Comp a member — give them free paid tier access"""
    data = {"members": [{"comped": True}]}
    result = api_request(site_config, 'PUT', f'/members/{member_id}/?include=tiers', data)
    if 'members' in result:
        m = result['members'][0]
        print(f"Comped: {m.get('name', 'N/A')} ({m['email']})")
        tiers = m.get('tiers', [])
        tier_names = ', '.join(t['name'] for t in tiers) if tiers else 'Free'
        print(f"  Tiers: {tier_names}")
    else:
        print(json.dumps(result, indent=2))

def cmd_uncomp_member(site_config, member_id):
    """Remove comp from a member"""
    data = {"members": [{"comped": False}]}
    result = api_request(site_config, 'PUT', f'/members/{member_id}/?include=tiers', data)
    if 'members' in result:
        m = result['members'][0]
        print(f"Uncomped: {m.get('name', 'N/A')} ({m['email']})")
    else:
        print(json.dumps(result, indent=2))

def cmd_list_newsletters(site_config):
    result = api_request(site_config, 'GET', '/newsletters/?limit=all')
    newsletters = result.get('newsletters', [])
    for n in newsletters:
        status = "✓ Active" if n.get('status') == 'active' else n.get('status', 'inactive')
        print(f"{n['id']} | {n['name']} | {status}")

def cmd_get_settings(site_config):
    result = api_request(site_config, 'GET', '/settings/')
    print(json.dumps(result, indent=2))

def cmd_update_settings(site_config, filepath):
    with open(filepath) as f:
        data = json.load(f)
    result = api_request(site_config, 'PUT', '/settings/', data)
    print(json.dumps(result, indent=2))

def cmd_list_sites():
    sites = load_sites()
    default = sites.get('default_site', 'none')
    print(f"Default site: {default}")
    print()
    for name, cfg in sites.get('sites', {}).items():
        marker = " *" if name == default else ""
        print(f"{name}{marker}")
        print(f"  Domain: {cfg['domain']}")
        print(f"  API: {cfg.get('api_version', 'v5.0')}")
        print(f"  HTTP: {cfg.get('http_version', '1.1')}")
        print(f"  Description: {cfg.get('description', 'N/A')}")
        print()

# ── Main ───────────────────────────────────────────────────────────
def show_usage():
    print("""Usage: ghost.py [site] <command> [args...]

Sites:
    --list-sites              List all configured sites
    [site]                    Site name (omit for default)

Commands:
    token                     Generate JWT token
    list-posts [filters]      List all posts
    get-post <id|slug>        Get post by ID or slug
    create-post <file.json>   Create post from JSON file
    update-post <id> <file>   Update post from JSON file
    publish-post <id> <time>  Publish a draft (updated_at ISO format)
    delete-post <id>          Delete post
    upload-image <file> [purpose] [ref]  Upload an image (purpose: image|profile_image|icon)
    list-images               List posts with feature images
    list-pages                List all pages
    site-info                 Get site information

    list-tiers                List all membership tiers
    list-members [limit]      List members (default: 20)
    get-member <id|email>     Get member by ID or email
    create-member <file.json> Create member from JSON
    update-member <id> <file> Update member
    delete-member <id>        Delete member
    comp-member <id>          Comp a member (give free paid access)
    uncomp-member <id>        Remove comp from member

    list-newsletters          List all newsletters
    get-settings              Get site settings
    update-settings <file>    Update site settings

Examples:
    ghost.py techblog token
    ghost.py techblog list-posts
    ghost.py techblog create-post /tmp/post.json
    ghost.py techblog list-members 50
    ghost.py techblog comp-member member-id-here
    ghost.py --list-sites
""")

def main():
    args = sys.argv[1:]
    
    if not args or args[0] in ('-h', '--help'):
        show_usage()
        sys.exit(0)
    
    if args[0] == '--list-sites':
        cmd_list_sites()
        sys.exit(0)
    
    # Determine if first arg is a site name or command
    sites = load_sites()
    site_name = None
    
    if args[0] in sites.get('sites', {}):
        site_name = args[0]
        args = args[1:]
    
    site_name, site_config = resolve_site(site_name)
    
    if not args:
        show_usage()
        sys.exit(1)
    
    command = args[0]
    cmd_args = args[1:]
    
    commands = {
        'token': lambda: cmd_token(site_config),
        'list-posts': lambda: cmd_list_posts(site_config, cmd_args),
        'get-post': lambda: cmd_get_post(site_config, cmd_args[0]),
        'create-post': lambda: cmd_create_post(site_config, cmd_args[0]),
        'update-post': lambda: cmd_update_post(site_config, cmd_args[0], cmd_args[1]),
        'publish-post': lambda: cmd_publish_post(site_config, cmd_args[0], cmd_args[1]),
        'delete-post': lambda: cmd_delete_post(site_config, cmd_args[0]),
        'list-tags': lambda: cmd_list_tags(site_config),
        'list-pages': lambda: cmd_list_pages(site_config),
        'upload-image': lambda: cmd_upload_image(site_config, cmd_args[0], cmd_args[1] if len(cmd_args) > 1 else 'image', cmd_args[2] if len(cmd_args) > 2 else None),
        'list-images': lambda: cmd_list_images(site_config),
        'site-info': lambda: cmd_site_info(site_config),
        'list-tiers': lambda: cmd_list_tiers(site_config),
        'list-members': lambda: cmd_list_members(site_config, cmd_args[0] if cmd_args else '20'),
        'get-member': lambda: cmd_get_member(site_config, cmd_args[0]),
        'create-member': lambda: cmd_create_member(site_config, cmd_args[0]),
        'update-member': lambda: cmd_update_member(site_config, cmd_args[0], cmd_args[1]),
        'delete-member': lambda: cmd_delete_member(site_config, cmd_args[0]),
        'comp-member': lambda: cmd_comp_member(site_config, cmd_args[0]),
        'uncomp-member': lambda: cmd_uncomp_member(site_config, cmd_args[0]),
        'list-newsletters': lambda: cmd_list_newsletters(site_config),
        'get-settings': lambda: cmd_get_settings(site_config),
        'update-settings': lambda: cmd_update_settings(site_config, cmd_args[0]),
    }
    
    if command not in commands:
        print(f"Unknown command: {command}", file=sys.stderr)
        show_usage()
        sys.exit(1)
    
    try:
        commands[command]()
    except IndexError:
        print(f"Error: Missing arguments for command '{command}'", file=sys.stderr)
        show_usage()
        sys.exit(1)

if __name__ == '__main__':
    main()
