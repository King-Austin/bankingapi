"""
Performance and load testing for the banking application
"""
import time
import random
import threading
from concurrent.futures import ThreadPoolExecutor
from django.test import TestCase, TransactionTestCase
from django.contrib.auth import get_user_model
from rest_framework.test import APIClient
from rest_framework.authtoken.models import Token
from decimal import Decimal
from core.models import AccountType, BankAccount, TransactionCategory

User = get_user_model()


class LoadTestCase(TransactionTestCase):
    """Load testing for concurrent operations"""
    
    def setUp(self):
        self.account_type = AccountType.objects.create(
            name='Savings',
            transaction_limit_daily=Decimal('1000000.00')
        )
        self.category = TransactionCategory.objects.create(name='Transfer')
        
        # Create test users and accounts
        self.users = []
        self.accounts = []
        self.tokens = []
        
        for i in range(10):
            user = User.objects.create_user(
                username=f'user{i}',
                email=f'user{i}@example.com',
                phone_number=f'0812345678{i}',
                password='testpass123'
            )
            account = BankAccount.objects.create(
                user=user,
                account_type=self.account_type,
                balance=Decimal('100000.00')
            )
            token = Token.objects.create(user=user)
            
            self.users.append(user)
            self.accounts.append(account)
            self.tokens.append(token)
    
    def simulate_user_activity(self, user_index):
        """Simulate a user performing various operations"""
        client = APIClient()
        token = self.tokens[user_index]
        client.credentials(HTTP_AUTHORIZATION=f'Token {token.key}')
        
        results = []
        
        # Test various endpoints
        endpoints = [
            '/api/accounts/',
            '/api/transactions/',
            '/api/beneficiaries/',
            '/api/cards/',
            '/api/user/profile/',
        ]
        
        for endpoint in endpoints:
            start_time = time.time()
            try:
                response = client.get(endpoint)
                end_time = time.time()
                results.append({
                    'endpoint': endpoint,
                    'status_code': response.status_code,
                    'response_time': end_time - start_time,
                    'success': response.status_code == 200
                })
            except Exception as e:
                end_time = time.time()
                results.append({
                    'endpoint': endpoint,
                    'status_code': 500,
                    'response_time': end_time - start_time,
                    'success': False,
                    'error': str(e)
                })
        
        return results
    
    def test_concurrent_api_access(self):
        """Test concurrent API access from multiple users"""
        num_concurrent_users = 5
        
        start_time = time.time()
        
        with ThreadPoolExecutor(max_workers=num_concurrent_users) as executor:
            futures = []
            for i in range(num_concurrent_users):
                future = executor.submit(self.simulate_user_activity, i)
                futures.append(future)
            
            all_results = []
            for future in futures:
                results = future.result()
                all_results.extend(results)
        
        end_time = time.time()
        total_time = end_time - start_time
        
        # Analyze results
        successful_requests = sum(1 for r in all_results if r['success'])
        failed_requests = len(all_results) - successful_requests
        avg_response_time = sum(r['response_time'] for r in all_results) / len(all_results)
        
        print(f"\nLoad Test Results:")
        print(f"Total requests: {len(all_results)}")
        print(f"Successful: {successful_requests}")
        print(f"Failed: {failed_requests}")
        print(f"Success rate: {successful_requests/len(all_results)*100:.2f}%")
        print(f"Average response time: {avg_response_time:.3f}s")
        print(f"Total test time: {total_time:.3f}s")
        
        # Assertions
        self.assertGreater(successful_requests / len(all_results), 0.95, 
                          "Success rate should be > 95%")
        self.assertLess(avg_response_time, 1.0, 
                       "Average response time should be < 1 second")
    
    def simulate_concurrent_transfers(self, num_transfers=50):
        """Simulate concurrent money transfers"""
        def perform_transfer():
            sender_idx = random.randint(0, len(self.accounts) - 1)
            recipient_idx = random.randint(0, len(self.accounts) - 1)
            
            # Ensure sender and recipient are different
            while recipient_idx == sender_idx:
                recipient_idx = random.randint(0, len(self.accounts) - 1)
            
            client = APIClient()
            token = self.tokens[sender_idx]
            client.credentials(HTTP_AUTHORIZATION=f'Token {token.key}')
            
            transfer_data = {
                'recipient_account_number': self.accounts[recipient_idx].account_number,
                'amount': f'{random.randint(100, 1000)}.00',
                'description': 'Load test transfer'
            }
            
            start_time = time.time()
            try:
                response = client.post('/api/transfer/', transfer_data, format='json')
                end_time = time.time()
                return {
                    'success': response.status_code == 201,
                    'status_code': response.status_code,
                    'response_time': end_time - start_time,
                    'sender': sender_idx,
                    'recipient': recipient_idx
                }
            except Exception as e:
                end_time = time.time()
                return {
                    'success': False,
                    'status_code': 500,
                    'response_time': end_time - start_time,
                    'error': str(e)
                }
        
        start_time = time.time()
        
        with ThreadPoolExecutor(max_workers=10) as executor:
            futures = [executor.submit(perform_transfer) for _ in range(num_transfers)]
            results = [future.result() for future in futures]
        
        end_time = time.time()
        total_time = end_time - start_time
        
        # Analyze transfer results
        successful_transfers = sum(1 for r in results if r['success'])
        failed_transfers = len(results) - successful_transfers
        avg_response_time = sum(r['response_time'] for r in results) / len(results)
        
        print(f"\nConcurrent Transfer Test Results:")
        print(f"Total transfers: {len(results)}")
        print(f"Successful: {successful_transfers}")
        print(f"Failed: {failed_transfers}")
        print(f"Success rate: {successful_transfers/len(results)*100:.2f}%")
        print(f"Average response time: {avg_response_time:.3f}s")
        print(f"Total test time: {total_time:.3f}s")
        print(f"Transfers per second: {len(results)/total_time:.2f}")
        
        return results
    
    def test_concurrent_money_transfers(self):
        """Test concurrent money transfers maintain data integrity"""
        # Record initial balances
        initial_balances = {}
        for i, account in enumerate(self.accounts):
            initial_balances[i] = account.balance
        
        # Perform concurrent transfers
        results = self.simulate_concurrent_transfers(20)
        
        # Refresh account balances
        for account in self.accounts:
            account.refresh_from_db()
        
        # Verify data integrity
        successful_transfers = [r for r in results if r['success']]
        
        # Calculate expected balance changes
        balance_changes = {i: Decimal('0') for i in range(len(self.accounts))}
        
        for result in successful_transfers:
            if 'sender' in result and 'recipient' in result:
                # This is a simplified check - in reality we'd need to track the actual amounts
                pass
        
        print(f"\nBalance integrity check:")
        for i, account in enumerate(self.accounts):
            print(f"Account {i}: {initial_balances[i]} -> {account.balance}")
        
        # Basic integrity check: total money in system should be conserved
        initial_total = sum(initial_balances.values())
        final_total = sum(account.balance for account in self.accounts)
        
        self.assertEqual(initial_total, final_total, 
                        "Total money in system should be conserved")


class StressTestCase(TransactionTestCase):
    """Stress testing for high load scenarios"""
    
    def test_database_connection_handling(self):
        """Test database can handle many concurrent connections"""
        from django.db import connections
        
        def test_db_query():
            """Perform a simple database query"""
            return User.objects.count()
        
        # Test with many concurrent database queries
        start_time = time.time()
        
        with ThreadPoolExecutor(max_workers=20) as executor:
            futures = [executor.submit(test_db_query) for _ in range(100)]
            results = [future.result() for future in futures]
        
        end_time = time.time()
        
        # All queries should succeed
        self.assertEqual(len(results), 100)
        self.assertTrue(all(isinstance(r, int) for r in results))
        
        print(f"100 concurrent DB queries completed in {end_time - start_time:.3f}s")
    
    def test_memory_usage_under_load(self):
        """Test memory usage doesn't grow excessively under load"""
        import psutil
        import os
        
        process = psutil.Process(os.getpid())
        initial_memory = process.memory_info().rss / 1024 / 1024  # MB
        
        # Create many objects
        users = []
        for i in range(1000):
            user = User(
                username=f'memtest{i}',
                email=f'memtest{i}@example.com',
                phone_number=f'081234{i:05d}',
            )
            users.append(user)
        
        # Bulk create to avoid individual database hits
        User.objects.bulk_create(users, batch_size=100)
        
        final_memory = process.memory_info().rss / 1024 / 1024  # MB
        memory_increase = final_memory - initial_memory
        
        print(f"Memory usage: {initial_memory:.2f}MB -> {final_memory:.2f}MB")
        print(f"Memory increase: {memory_increase:.2f}MB")
        
        # Memory increase should be reasonable (adjust threshold as needed)
        self.assertLess(memory_increase, 100, 
                       "Memory increase should be less than 100MB for 1000 users")
