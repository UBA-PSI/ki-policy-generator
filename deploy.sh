#!/bin/bash
# Usage: ./deploy.sh 3.2.0

VERSION=$1
if [ -z "$VERSION" ]; then
    echo "Usage: ./deploy.sh <version>"
    exit 1
fi

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

echo "Updated to version ${VERSION}"
