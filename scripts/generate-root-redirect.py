#!/usr/bin/env python3
"""
Generate root /index.html that redirects to /p/ with cache busting.
"""

import os
import time


def main():
    script_dir = os.path.dirname(os.path.abspath(__file__))
    project_root = os.path.dirname(script_dir)

    ts = int(time.time())

    page = f'''<!DOCTYPE html>
<html>
<head>
    <meta charset="UTF-8">
    <meta http-equiv="refresh" content="0;url=/p/?ts={ts}">
    <title>Redirecting…</title>
</head>
<body>
    <p>Redirecting to <a href="/p/?ts={ts}">/p/</a>…</p>
    <script>
        var url = '/p/';
        if (location.search.indexOf('ts=') === -1) {{
            url += '?ts={ts}';
        }}
        window.location.replace(url);
    </script>
</body>
</html>'''

    out_path = os.path.join(project_root, 'root-index.html')
    with open(out_path, 'w', encoding='utf-8') as f:
        f.write(page)

    print(f'Generated {out_path} (ts={ts})')


if __name__ == '__main__':
    main()
