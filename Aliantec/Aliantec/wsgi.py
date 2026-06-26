"""
WSGI config for Aliantec project.

It exposes the WSGI callable as a module-level variable named ``application``.

For more information on this file, see
https://docs.djangoproject.com/en/6.0/howto/deployment/wsgi/
"""

import os
import sys

# Force UTF-8 encoding globally.
# On Linux with Apache/mod_wsgi the process locale is often 'C' (ASCII),
# which causes UnicodeEncodeError when reading files with French characters
# such as ç (U+00E7).  Setting these variables before importing Django
# ensures that open() calls without an explicit encoding default to UTF-8.
os.environ.setdefault('PYTHONIOENCODING', 'utf-8')
os.environ.setdefault('LANG', 'en_US.UTF-8')
os.environ.setdefault('LC_ALL', 'en_US.UTF-8')

# Reconfigure stdout/stderr for UTF-8 (Python 3.7+)
if hasattr(sys.stdout, 'reconfigure'):
    sys.stdout.reconfigure(encoding='utf-8', errors='replace')
if hasattr(sys.stderr, 'reconfigure'):
    sys.stderr.reconfigure(encoding='utf-8', errors='replace')

from django.core.wsgi import get_wsgi_application

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'Aliantec.settings')

application = get_wsgi_application()
