"""Clean DATABASE_URL from template artifacts (Railway compatibility).

IMPORTANT: stdout is captured by entrypoint.sh, so ONLY the clean URL goes to stdout.
All debug/warning messages MUST go to stderr.
"""
import os
import re
import sys


def clean_database_url():
    url = os.environ.get('DATABASE_URL', '')
    if not url:
        print('  WARNING: DATABASE_URL is not set!', file=sys.stderr)
        sys.exit(1)

    # Remove template artifacts like }} ${{ }} ${} etc
    url = re.sub(r'\}\}+$', '', url)
    url = re.sub(r'\{\{?$', '', url)
    url = re.sub(r'\$\{[^}]*\}', '', url)

    # Remove trailing/leading whitespace
    url = url.strip()

    if url:
        # Print masked URL for debug to stderr (NOT stdout!)
        safe = re.sub(r'(:\/\/[^:]+:)[^@]+(@)', r'\1****\2', url)
        print(f'  URL: {safe}', file=sys.stderr)
        # Print ONLY the clean URL to stdout (captured by entrypoint.sh)
        print(url)
    else:
        print('  WARNING: DATABASE_URL is empty after cleanup!', file=sys.stderr)
        sys.exit(1)


if __name__ == '__main__':
    clean_database_url()
