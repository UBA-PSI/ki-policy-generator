#!/bin/bash
# Usage: ./deploy.sh <version>
# Example: ./deploy.sh 3.3.0
#
# Updates version numbers, regenerates preset pages, and deploys to ki-policy.org

set -e

VERSION=$1
if [ -z "$VERSION" ]; then
    echo "Usage: ./deploy.sh <version>"
    exit 1
fi

REMOTE="root@bew"
REMOTE_ROOT="/var/www/ki-policy.org"
SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"

echo "=== Preparing version ${VERSION} ==="

# Update version.js
echo "window.APP_VERSION = '${VERSION}';" > version.js

# Update LOCAL_VERSION in index.html
sed -i '' "s/var LOCAL_VERSION = '[^']*'/var LOCAL_VERSION = '${VERSION}'/" index.html

# Update ?v= parameters on script tags in index.html
sed -i '' "s/pako\.min\.js?v=[^\"']*/pako.min.js?v=${VERSION}/" index.html
sed -i '' "s/js-yaml\.min\.js?v=[^\"']*/js-yaml.min.js?v=${VERSION}/" index.html
sed -i '' "s/policy-loader\.js?v=[^\"']*/policy-loader.js?v=${VERSION}/" index.html

# Update hardcoded fallback in policy-loader.js
sed -i '' "s/window\.APP_VERSION || '[^']*'/window.APP_VERSION || '${VERSION}'/" policy-loader.js

# Generate static preset pages
echo "Generating static preset pages…"
python3 scripts/generate-preset-pages.py

# Update cache-bust timestamp in root-index.html
TS=$(date +%s)
sed -i '' "s/ts=[0-9]*/ts=${TS}/g" root-index.html

echo "=== Deploying to ${REMOTE}:${REMOTE_ROOT} ==="

# Create remote backup before overwriting anything
BACKUP_TS=$(date +%Y%m%d-%H%M%S)
BACKUP_FILE="backup-pre-${VERSION}-${BACKUP_TS}.tar.gz"
echo "Creating remote backup ${BACKUP_FILE}…"
ssh "${REMOTE}" "mkdir -p ${REMOTE_ROOT}/backups && tar -czf ${REMOTE_ROOT}/backups/${BACKUP_FILE} --exclude='backups' -C ${REMOTE_ROOT} ."

# Deploy generator to /v3/
echo "Syncing /v3/ (generator)…"
rsync -avz --delete \
    --exclude='.git' \
    --exclude='.claude' \
    --exclude='.playwright-mcp' \
    --exclude='scripts' \
    --exclude='presets-audit' \
    --exclude='root-index.html' \
    --exclude='deploy.sh' \
    --exclude='CLAUDE.md' \
    --exclude='README.md' \
    --exclude='LICENSE' \
    --exclude='*.png' \
    --exclude='p/' \
    "${SCRIPT_DIR}/" "${REMOTE}:${REMOTE_ROOT}/v3/"

# Deploy preset pages to /p/
echo "Syncing /p/ (preset pages)…"
rsync -avz --delete \
    "${SCRIPT_DIR}/p/" "${REMOTE}:${REMOTE_ROOT}/p/"

# Deploy root index.html
echo "Syncing root index.html…"
rsync -avz \
    "${SCRIPT_DIR}/root-index.html" "${REMOTE}:${REMOTE_ROOT}/index.html"

echo "=== Deployed version ${VERSION} to ki-policy.org ==="
