#!/bin/bash

# Setup script for SecureCipher Banking API
# This script sets up the development environment

set -e

echo "🚀 Setting up SecureCipher Banking API..."

# Check if Python is installed
if ! command -v python3 &> /dev/null; then
    echo "❌ Python 3 is required but not installed."
    exit 1
fi

# Check if pip is installed
if ! command -v pip &> /dev/null; then
    echo "❌ pip is required but not installed."
    exit 1
fi

# Install dependencies
echo "📦 Installing Python dependencies..."
pip install -r requirements.txt

# Check if .env file exists
if [ ! -f ".env" ]; then
    echo "📝 Creating .env file from template..."
    cp .env.example .env
    echo "⚠️  Please edit .env file with your configuration before continuing"
fi

# Setup database
echo "🗄️ Setting up database..."
python manage.py makemigrations
python manage.py migrate

# Create superuser
echo "👤 Setting up admin user..."
python manage.py shell << EOF
from django.contrib.auth import get_user_model
from decouple import config

User = get_user_model()
username = config('DJANGO_SUPERUSER_USERNAME', default='admin')
email = config('DJANGO_SUPERUSER_EMAIL', default='admin@securecipher.com')
password = config('DJANGO_SUPERUSER_PASSWORD', default='admin123')

if not User.objects.filter(username=username).exists():
    User.objects.create_superuser(username=username, email=email, password=password)
    print(f"Superuser '{username}' created successfully!")
    print(f"Email: {email}")
    print(f"Password: {password}")
    print("⚠️  Please change the password after first login!")
else:
    print(f"Superuser '{username}' already exists.")
EOF

# Setup demo data
echo "🎭 Setting up demo data..."
python manage.py shell << EOF
from core.models import AccountType, TransactionCategory
from decimal import Decimal

# Create default account types
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

# Create default transaction categories
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

# Collect static files
echo "📁 Collecting static files..."
python manage.py collectstatic --noinput

echo "✅ Setup complete!"
echo ""
echo "🎉 SecureCipher Banking API is ready!"
echo ""
echo "To start the development server:"
echo "  python manage.py runserver"
echo ""
echo "To access the admin panel:"
echo "  http://localhost:8000/admin/"
echo ""
echo "To test the API:"
echo "  http://localhost:8000/api/health/"
echo ""
echo "📖 For deployment instructions, see RENDER_DEPLOYMENT.md"
