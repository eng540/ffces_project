#!/usr/bin/env python3
import os
import re
import sys

url = os.environ.get('DATABASE_URL', '')
if not url:
    sys.exit(1)

url = re.sub(r'\}\}+$', '', url)
url = re.sub(r'\{\{?$', '', url)
url = re.sub(r'\$\{[^}]*\}', '', url)
url = url.strip()

if url:
    print(url)
    sys.exit(0)
else:
    sys.exit(1)