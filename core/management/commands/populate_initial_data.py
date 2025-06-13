from django.core.management.base import BaseCommand
from core.models import AccountType, TransactionCategory


class Command(BaseCommand):
    help = 'Populate initial data for the banking application'

    def handle(self, *args, **options):
        self.stdout.write('Starting initial data population...')

        # Create Account Types
        account_types = [
            {
                'name': 'Savings Account',
                'description': 'Standard savings account with interest',
                'minimum_balance': 100.00,
                'interest_rate': 2.50,
                'monthly_fee': 0.00,
                'transaction_limit_daily': 10000.00
            },
            {
                'name': 'Checking Account',
                'description': 'Standard checking account for daily transactions',
                'minimum_balance': 50.00,
                'interest_rate': 0.50,
                'monthly_fee': 5.00,
                'transaction_limit_daily': 25000.00
            },
            {
                'name': 'Business Account',
                'description': 'Business account with higher limits',
                'minimum_balance': 500.00,
                'interest_rate': 1.75,
                'monthly_fee': 15.00,
                'transaction_limit_daily': 100000.00
            },
            {
                'name': 'Premium Account',
                'description': 'Premium account with exclusive benefits',
                'minimum_balance': 5000.00,
                'interest_rate': 3.25,
                'monthly_fee': 25.00,
                'transaction_limit_daily': 250000.00
            }
        ]

        for account_type_data in account_types:
            account_type, created = AccountType.objects.get_or_create(
                name=account_type_data['name'],
                defaults=account_type_data
            )
            if created:
                self.stdout.write(
                    self.style.SUCCESS(f'Created account type: {account_type.name}')
                )
            else:
                self.stdout.write(f'Account type already exists: {account_type.name}')

        # Create Transaction Categories
        categories = [
            {
                'name': 'Transfer',
                'description': 'Money transfers between accounts',
                'icon': 'transfer'
            },
            {
                'name': 'Deposit',
                'description': 'Cash or check deposits',
                'icon': 'deposit'
            },
            {
                'name': 'Withdrawal',
                'description': 'Cash withdrawals',
                'icon': 'withdrawal'
            },
            {
                'name': 'Payment',
                'description': 'Bill payments and purchases',
                'icon': 'payment'
            },
            {
                'name': 'Fee',
                'description': 'Bank fees and charges',
                'icon': 'fee'
            },
            {
                'name': 'Interest',
                'description': 'Interest earned or charged',
                'icon': 'interest'
            },
            {
                'name': 'Refund',
                'description': 'Transaction refunds',
                'icon': 'refund'
            },
            {
                'name': 'Salary',
                'description': 'Salary and wage deposits',
                'icon': 'salary'
            }
        ]

        for category_data in categories:
            category, created = TransactionCategory.objects.get_or_create(
                name=category_data['name'],
                defaults=category_data
            )
            if created:
                self.stdout.write(
                    self.style.SUCCESS(f'Created transaction category: {category.name}')
                )
            else:
                self.stdout.write(f'Transaction category already exists: {category.name}')

        self.stdout.write(
            self.style.SUCCESS('Successfully populated initial data!')
        )
