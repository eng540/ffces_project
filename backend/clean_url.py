"""Clean DATABASE_URL from template artifacts (Railway compatibility)."""
import os
import re
import sys


def clean_database_url():
    url = os.environ.get('DATABASE_URL', '')
    if not url:
        print('  WARNING: DATABASE_URL is not set!')
        sys.exit(1)

    # Remove template artifacts like }} ${{ }} ${} etc
    url = re.sub(r'\}\}+$', '', url)
    url = re.sub(r'\{\{?$', '', url)
    url = re.sub(r'\$\{[^}]*\}', '', url)

    # Remove trailing/leading whitespace
    url = url.strip()

    if url:
        os.environ['DATABASE_URL'] = url
        # Print masked URL for debug (hide password)
        safe = re.sub(r'(:\/\/[^:]+:)[^@]+(@)', r'\1****\2', url)
        print(f'  URL: {safe}')
    else:
        print('  WARNING: DATABASE_URL is empty after cleanup!')
        sys.exit(1)


if __name__ == '__main__':
    clean_database_url()
