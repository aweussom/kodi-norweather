# -*- coding: utf-8 -*-
"""Build an installable Kodi addon zip (forward-slash paths, addon dir at root)."""
import os
import re
import zipfile

BASE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
ADDON = 'weather.metno'
ADDON_DIR = os.path.join(BASE, ADDON)

with open(os.path.join(ADDON_DIR, 'addon.xml'), encoding='utf-8') as f:
    version = re.search(r'<addon[^>]*version="([^"]+)"', f.read()).group(1)

out = os.path.join(BASE, '%s-%s.zip' % (ADDON, version))
with zipfile.ZipFile(out, 'w', zipfile.ZIP_DEFLATED) as zf:
    for root, dirs, files in os.walk(ADDON_DIR):
        dirs[:] = [d for d in dirs if d not in ('__pycache__', '.git')]
        for name in files:
            if name.endswith(('.pyc', '.pyo')):
                continue
            full = os.path.join(root, name)
            arc = ADDON + '/' + os.path.relpath(full, ADDON_DIR).replace(os.sep, '/')
            zf.write(full, arc)
            print('  +', arc)
print('wrote %s' % out)
