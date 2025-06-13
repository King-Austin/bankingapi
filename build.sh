#!/bin/bash

# Render Build Script for Django Banking API
# This script runs during the build phase on Render

set -o errexit  # exit on error

echo "🚀 Starting SecureCipher Banking API build..."

# Install dependencies
echo "📦 Installing Python dependencies..."
pip install --upgrade pip
pip install -r requirements.txt

# Collect static files
echo "📁 Collecting static files..."
python manage.py collectstatic --noinput

# Run database migrations
echo "🗄️ Running database migrations..."
python manage.py migrate

# Create superuser if it doesn't exist (for initial setup)
echo "👤 Setting up admin user..."
python manage.py shell << EOF
from django.contrib.auth import get_user_model
from decouple import config

User = get_user_model()
username = config('DJANGO_SUPERUSER_USERNAME', default='admin')
email = config('DJANGO_SUPERUSER_EMAIL', default='admin@securecipher.com')
password = config('DJANGO_SUPERUSER_PASSWORD', default='change-this-password')

if not User.objects.filter(username=username).exists():
    User.objects.create_superuser(username=username, email=email, password=password)
    print(f"Superuser '{username}' created successfully!")
else:
    print(f"Superuser '{username}' already exists.")
EOF

# Create demo data if needed
echo "🎭 Setting up demo data..."
python manage.py shell << EOF
from core.models import AccountType, TransactionCategory
from decimal import Decimal

# Create default account types if they don't exist
account_types = [
    {'name': 'Savings', 'description': 'Standard savings account', 'minimum_balance': Decimal('100.00')},
    {'name': 'Current', 'description': 'Current account for businesses', 'minimum_balance': Decimal('500.00')},
    {'name': 'Fixed Deposit', 'description': 'Fixed deposit account', 'minimum_balance': Decimal('10000.00')},
]

for at_data in account_types:
    account_type, created = AccountType.objects.get_or_create(
        name=at_data['name'],
        defaults=at_data
    )
    if created:
        print(f"Created account type: {account_type.name}")

# Create default transaction categories if they don't exist
categories = [
    {'name': 'Transfer', 'description': 'Money transfers'},
    {'name': 'Payment', 'description': 'Bill payments'},
    {'name': 'Deposit', 'description': 'Cash deposits'},
    {'name': 'Withdrawal', 'description': 'Cash withdrawals'},
    {'name': 'Interest', 'description': 'Interest payments'},
    {'name': 'Fee', 'description': 'Bank fees and charges'},
]

for cat_data in categories:
    category, created = TransactionCategory.objects.get_or_create(
        name=cat_data['name'],
        defaults=cat_data
    )
    if created:
        print(f"Created transaction category: {category.name}")

print("Demo data setup complete!")
EOF

echo "✅ Build completed successfully!"
