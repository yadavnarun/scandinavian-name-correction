"""
Fly.io specific settings overrides
"""

# Allow all hosts to connect
ALLOWED_HOSTS = ['*', '172.19.3.66', '172.19.3.65', 'localhost', '.fly.dev']

# Make sure debug is off in production
DEBUG = False
