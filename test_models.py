#!/usr/bin/env python
import os
import sys
import django

# Add the project directory to Python path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

# Set Django settings module
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'bankingapi.settings')

try:
    # Setup Django
    django.setup()
    
    # Try importing models
    from core.models import User, BankAccount, Transaction
    print("✓ Models imported successfully")
    
    # Check if migrations are needed
    from django.core.management import call_command
    call_command('makemigrations', verbosity=2, dry_run=True)
    
except Exception as e:
    print(f"✗ Error: {e}")
    import traceback
    traceback.print_exc()
