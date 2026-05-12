#!/usr/bin/env bash
#
# Ghost CMS Skill Installer for Hermes Agent
# Usage: curl -fsSL https://raw.githubusercontent.com/YOURUSER/hermes-ghost-cms/main/install.sh | bash
#

set -euo pipefail

SKILL_NAME="ghost-cms"
CATEGORY="productivity"
REPO_URL="${REPO_URL:-https://github.com/cosmohub/hermes-ghost-cms}"
BRANCH="${BRANCH:-main}"
HERMES_SKILLS_DIR="${HOME}/.hermes/skills"
TARGET_DIR="${HERMES_SKILLS_DIR}/${CATEGORY}/${SKILL_NAME}"

echo "=== Ghost CMS Skill Installer ==="
echo ""

# Check Python
if ! command -v python3 &> /dev/null; then
    echo "Error: Python 3 is required but not installed."
    exit 1
fi

# Check pip
if ! command -v pip3 &> /dev/null && ! python3 -m pip --version &> /dev/null; then
    echo "Error: pip is required but not installed."
    exit 1
fi

# Install PyJWT if needed
if ! python3 -c "import jwt" 2>/dev/null; then
    echo "Installing PyJWT..."
    pip3 install --user pyjwt || python3 -m pip install --user pyjwt
fi

# Check curl
if ! command -v curl &> /dev/null; then
    echo "Error: curl is required but not installed."
    exit 1
fi

# Create target directory
mkdir -p "${TARGET_DIR}"

# Download skill files
echo "Downloading skill files from ${REPO_URL}..."

FILES=(
    "SKILL.md"
    "README.md"
    "sites.json.template"
    "scripts/ghost.py"
    "scripts/seo-check.py"
    "scripts/export-site.py"
    "scripts/ghost-auth.sh"
    "templates/post-template.md"
)

for file in "${FILES[@]}"; do
    url="${REPO_URL}/raw/${BRANCH}/${file}"
    target="${TARGET_DIR}/${file}"
    mkdir -p "$(dirname "${target}")"
    echo "  Fetching ${file}..."
    curl -fsSL "${url}" -o "${target}" || {
        echo "Error: Failed to download ${file}"
        exit 1
    }
done

# Make scripts executable
chmod +x "${TARGET_DIR}/scripts/"*.py
chmod +x "${TARGET_DIR}/scripts/"*.sh

# Copy template to sites.json if it doesn't exist
if [[ ! -f "${TARGET_DIR}/sites.json" ]]; then
    cp "${TARGET_DIR}/sites.json.template" "${TARGET_DIR}/sites.json"
    echo ""
    echo "Created sites.json from template."
fi

echo ""
echo "=== Installation Complete ==="
echo "Skill installed to: ${TARGET_DIR}"
echo ""
echo "Next steps:"
echo "1. Edit ${TARGET_DIR}/sites.json with your Ghost site details"
echo "2. Add your Admin API key to ~/.hermes/.env:"
echo "   echo 'GHOST_MYBLOG_ADMIN_KEY=your_id:your_secret' >> ~/.hermes/.env"
echo "3. Test: python3 ${TARGET_DIR}/scripts/ghost.py myblog site-info"
echo ""
echo "For help: python3 ${TARGET_DIR}/scripts/ghost.py --help"
