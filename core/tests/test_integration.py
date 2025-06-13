"""
Integration tests for the banking application
"""
from django.test import TestCase, TransactionTestCase
from django.contrib.auth import get_user_model
from django.test import Client
from django.urls import reverse
from rest_framework.test import APITestCase, APIClient
from rest_framework import status
from rest_framework.authtoken.models import Token
from decimal import Decimal
from datetime import date, timedelta
from core.models import (
    AccountType, BankAccount, TransactionCategory, 
    Transaction, Beneficiary, Card, AuditLog
)

User = get_user_model()


class FullWorkflowIntegrationTest(APITestCase):
    """Test complete banking workflow from registration to transactions"""
    
    def setUp(self):
        self.client = APIClient()
        # Create account type and transaction category
        self.account_type = AccountType.objects.create(
            name='Savings',
            minimum_balance=Decimal('1000.00'),
            transaction_limit_daily=Decimal('50000.00')
        )
        self.transfer_category = TransactionCategory.objects.create(
            name='Transfer',
            description='Money transfer between accounts'
        )
    
    def test_complete_banking_workflow(self):
        """Test complete workflow: register -> login -> transfer -> view transactions"""
        
        # Step 1: Register two users
        user1_data = {
            'username': 'user1',
            'email': 'user1@example.com',
            'phone_number': '08123456789',
            'first_name': 'User',
            'last_name': 'One',
            'password': 'testpass123'
        }
        
        user2_data = {
            'username': 'user2',
            'email': 'user2@example.com',
            'phone_number': '08123456790',
            'first_name': 'User',
            'last_name': 'Two',
            'password': 'testpass123'
        }
        
        # Register user 1
        response = self.client.post(reverse('register'), user1_data, format='json')
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        user1_token = response.data['token']
        
        # Register user 2
        response = self.client.post(reverse('register'), user2_data, format='json')
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        user2_token = response.data['token']
        
        # Verify both users have accounts with demo funds
        user1 = User.objects.get(username='user1')
        user2 = User.objects.get(username='user2')
        
        user1_account = BankAccount.objects.get(user=user1)
        user2_account = BankAccount.objects.get(user=user2)
        
        self.assertEqual(user1_account.balance, Decimal('50000.00'))
        self.assertEqual(user2_account.balance, Decimal('50000.00'))
        self.assertEqual(user1_account.account_number, '8123456789')
        self.assertEqual(user2_account.account_number, '8123456790')
        
        # Step 2: Login as user1 and check profile
        self.client.credentials(HTTP_AUTHORIZATION='Token ' + user1_token)
        
        response = self.client.get(reverse('user-profile'))
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data['username'], 'user1')
        
        # Step 3: Check accounts
        response = self.client.get(reverse('accounts'))
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.data), 1)
        self.assertEqual(response.data[0]['balance'], '50000.00')
        
        # Step 4: Validate recipient account
        response = self.client.post(
            reverse('validate-account'),
            {'account_number': user2_account.account_number},
            format='json'
        )
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertTrue(response.data['exists'])
        self.assertEqual(response.data['account_name'], 'User Two')
        
        # Step 5: Transfer money
        transfer_data = {
            'recipient_account_number': user2_account.account_number,
            'amount': '5000.00',
            'description': 'Test transfer'
        }
        
        response = self.client.post(reverse('transfer'), transfer_data, format='json')
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        
        # Step 6: Verify balances updated
        user1_account.refresh_from_db()
        user2_account.refresh_from_db()
        
        self.assertEqual(user1_account.balance, Decimal('45000.00'))
        self.assertEqual(user2_account.balance, Decimal('55000.00'))
        
        # Step 7: Check transactions for user1
        response = self.client.get(reverse('transactions'))
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        # Should have welcome transaction + transfer debit
        self.assertGreaterEqual(len(response.data), 2)
        
        # Step 8: Switch to user2 and check their transactions
        self.client.credentials(HTTP_AUTHORIZATION='Token ' + user2_token)
        
        response = self.client.get(reverse('transactions'))
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        # Should have welcome transaction + transfer credit
        self.assertGreaterEqual(len(response.data), 2)
        
        # Step 9: Add beneficiary
        beneficiary_data = {
            'account_number': user1_account.account_number,
            'account_name': 'User One',
            'bank_name': 'SecureCipher Bank',
            'nickname': 'Friend'
        }
        
        response = self.client.post(reverse('beneficiaries'), beneficiary_data, format='json')
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        
        # Step 10: List beneficiaries
        response = self.client.get(reverse('beneficiaries'))
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.data), 1)
        self.assertEqual(response.data[0]['nickname'], 'Friend')


class DatabaseIntegrityTest(TransactionTestCase):
    """Test database integrity and constraints"""
    
    def test_unique_constraints(self):
        """Test unique constraints are enforced"""
        # Create first user
        User.objects.create_user(
            username='user1',
            email='test@example.com',
            phone_number='08123456789',
            password='testpass123'
        )
        
        # Try to create user with same email
        with self.assertRaises(Exception):
            User.objects.create_user(
                username='user2',
                email='test@example.com',  # Duplicate email
                phone_number='08123456790',
                password='testpass123'
            )
        
        # Try to create user with same phone
        with self.assertRaises(Exception):
            User.objects.create_user(
                username='user3',
                email='test2@example.com',
                phone_number='08123456789',  # Duplicate phone
                password='testpass123'
            )
    
    def test_cascade_relationships(self):
        """Test cascade delete relationships"""
        user = User.objects.create_user(
            username='testuser',
            email='test@example.com',
            phone_number='08123456789',
            password='testpass123'
        )
        
        account_type = AccountType.objects.create(name='Savings')
        account = BankAccount.objects.create(
            user=user,
            account_type=account_type
        )
        
        category = TransactionCategory.objects.create(name='Transfer')
        transaction = Transaction.objects.create(
            account=account,
            transaction_type='CREDIT',
            category=category,
            amount=Decimal('1000.00'),
            balance_before=Decimal('0.00'),
            balance_after=Decimal('1000.00'),
            description='Test transaction'
        )
        
        beneficiary = Beneficiary.objects.create(
            user=user,
            account_number='1234567890',
            account_name='John Doe'
        )
        
        # Delete user should cascade to account, transactions, and beneficiaries
        user_id = user.id
        account_id = account.id
        transaction_id = transaction.id
        beneficiary_id = beneficiary.id
        
        user.delete()
        
        # Check related objects are deleted
        self.assertFalse(BankAccount.objects.filter(id=account_id).exists())
        self.assertFalse(Transaction.objects.filter(id=transaction_id).exists())
        self.assertFalse(Beneficiary.objects.filter(id=beneficiary_id).exists())


class SecurityTest(APITestCase):
    """Test security features of the application"""
    
    def setUp(self):
        self.client = APIClient()
        self.user = User.objects.create_user(
            username='testuser',
            email='test@example.com',
            phone_number='08123456789',
            password='testpass123'
        )
        self.token = Token.objects.create(user=self.user)
    
    def test_unauthorized_access_protection(self):
        """Test that protected endpoints require authentication"""
        protected_endpoints = [
            reverse('accounts'),
            reverse('transactions'),
            reverse('beneficiaries'),
            reverse('cards'),
            reverse('user-profile'),
            reverse('transfer'),
        ]
        
        for endpoint in protected_endpoints:
            response = self.client.get(endpoint)
            self.assertIn(response.status_code, [401, 403])
    
    def test_token_authentication(self):
        """Test token authentication works correctly"""
        # Without token - should fail
        response = self.client.get(reverse('user-profile'))
        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)
        
        # With valid token - should succeed
        self.client.credentials(HTTP_AUTHORIZATION='Token ' + self.token.key)
        response = self.client.get(reverse('user-profile'))
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        
        # With invalid token - should fail
        self.client.credentials(HTTP_AUTHORIZATION='Token invalidtoken')
        response = self.client.get(reverse('user-profile'))
        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)
    
    def test_user_data_isolation(self):
        """Test users can only access their own data"""
        # Create another user
        other_user = User.objects.create_user(
            username='otheruser',
            email='other@example.com',
            phone_number='08123456790',
            password='testpass123'
        )
        
        account_type = AccountType.objects.create(name='Savings')
        other_account = BankAccount.objects.create(
            user=other_user,
            account_type=account_type
        )
        
        # Login as first user
        self.client.credentials(HTTP_AUTHORIZATION='Token ' + self.token.key)
        
        # Try to access other user's account details
        response = self.client.get(
            reverse('account-detail', kwargs={'account_id': other_account.id})
        )
        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)


class PerformanceTest(APITestCase):
    """Test performance aspects of the application"""
    
    def setUp(self):
        self.client = APIClient()
        self.user = User.objects.create_user(
            username='testuser',
            email='test@example.com',
            phone_number='08123456789',
            password='testpass123'
        )
        self.token = Token.objects.create(user=self.user)
        self.client.credentials(HTTP_AUTHORIZATION='Token ' + self.token.key)
        
        self.account_type = AccountType.objects.create(name='Savings')
        self.account = BankAccount.objects.create(
            user=self.user,
            account_type=self.account_type,
            balance=Decimal('100000.00')
        )
        self.category = TransactionCategory.objects.create(name='Transfer')
    
    def test_bulk_transaction_creation(self):
        """Test creating multiple transactions doesn't degrade performance significantly"""
        import time
        
        start_time = time.time()
        
        # Create 100 transactions
        transactions = []
        for i in range(100):
            transactions.append(Transaction(
                account=self.account,
                transaction_type='DEBIT',
                category=self.category,
                amount=Decimal('10.00'),
                balance_before=Decimal('100000.00'),
                balance_after=Decimal('99990.00'),
                description=f'Test transaction {i}'
            ))
        
        Transaction.objects.bulk_create(transactions)
        
        end_time = time.time()
        creation_time = end_time - start_time
        
        # Should complete within reasonable time (adjust threshold as needed)
        self.assertLess(creation_time, 5.0, "Bulk transaction creation took too long")
        
        # Verify all transactions were created
        self.assertEqual(Transaction.objects.filter(account=self.account).count(), 100)
    
    def test_transaction_list_pagination(self):
        """Test transaction list endpoint with large number of records"""
        # Create many transactions
        transactions = []
        for i in range(50):
            transactions.append(Transaction(
                account=self.account,
                transaction_type='DEBIT',
                category=self.category,
                amount=Decimal('10.00'),
                balance_before=Decimal('100000.00'),
                balance_after=Decimal('99990.00'),
                description=f'Test transaction {i}'
            ))
        
        Transaction.objects.bulk_create(transactions)
        
        # Test API response time
        import time
        start_time = time.time()
        
        response = self.client.get(reverse('transactions'))
        
        end_time = time.time()
        response_time = end_time - start_time
        
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        # Should respond within reasonable time
        self.assertLess(response_time, 2.0, "Transaction list endpoint too slow")
