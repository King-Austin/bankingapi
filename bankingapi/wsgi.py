"""
WSGI config for bankingapi project.

It exposes the WSGI callable as a module-level variable named ``application``.

For more information on this file, see
https://docs.djangoproject.com/en/5.2/howto/deployment/wsgi/
"""

import os
from django.core.wsgi import get_wsgi_application

# Set default settings module
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'bankingapi.settings')

# Get the WSGI application
application = get_wsgi_application()

# Optionally wrap with WhiteNoise for static files (handled in settings.py middleware)
