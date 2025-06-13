# Banking API Test Suite Documentation

## Overview

This comprehensive test suite covers all aspects of the SecureCipher Banking API application. The tests are organized into multiple categories to ensure thorough coverage of functionality, performance, and security.

## Test Structure

### Test Organization

Tests are organized in the `core/tests/` folder to avoid conflicts and maintain clean separation:

```
core/
├── tests/
│   ├── __init__.py
│   ├── test_models.py           # Model layer tests
│   ├── test_views.py            # API endpoint tests  
│   ├── test_serializers.py      # Data serialization tests
│   ├── test_admin.py            # Django admin functionality tests
│   ├── test_integration.py      # End-to-end integration tests
│   ├── test_performance.py      # Load and performance tests
│   ├── test_factories.py        # Test data factories and utilities
│   └── test_config.py           # Test configuration and base classes
├── tests.py                     # Main test module (imports from tests/)
└── ...
```

### Test Files

1. **`test_models.py`** - Model layer tests
2. **`test_views.py`** - API endpoint tests  
3. **`test_serializers.py`** - Data serialization tests
4. **`test_admin.py`** - Django admin functionality tests
5. **`test_integration.py`** - End-to-end integration tests
6. **`test_performance.py`** - Load and performance tests
7. **`test_factories.py`** - Test data factories and utilities
8. **`test_config.py`** - Test configuration and base classes

### Test Categories

#### 1. Model Tests (`test_models.py`)
- **User Model**: Registration, unique constraints, string representation
- **Account Type Model**: Creation, validation, business rules
- **Bank Account Model**: Account number generation, balance management
- **Transaction Model**: Reference number generation, transaction types
- **Beneficiary Model**: Account management, user relationships
- **Card Model**: Card number generation, security features
- **Audit Log Model**: Activity tracking, permissions

#### 2. API Tests (`test_views.py`)
- **Authentication**: Login, logout, token management
- **User Registration**: Account creation with demo funds
- **Account Management**: List accounts, account details, validation
- **Transactions**: Transfer money, transaction history
- **Beneficiaries**: Add, list, manage beneficiaries
- **Cards**: Card management and operations
- **Security**: Unauthorized access protection

#### 3. Serializer Tests (`test_serializers.py`)
- **Data Validation**: Input validation, error handling
- **User Registration**: Duplicate prevention, password handling
- **Transfer Validation**: Amount limits, account verification
- **Account Validation**: Real-time account number checking
- **Data Transformation**: Proper serialization/deserialization

#### 4. Admin Tests (`test_admin.py`)
- **Admin Interface**: All model admin functionality
- **Permissions**: Proper access controls
- **Display Fields**: Correct field visibility
- **Readonly Fields**: Security restrictions
- **List Filters**: Search and filtering capabilities

#### 5. Integration Tests (`test_integration.py`)
- **Full Workflow**: Complete user journey testing
- **Database Integrity**: Cascade relationships, constraints
- **Security Testing**: Data isolation, token authentication
- **Cross-component**: End-to-end feature testing

#### 6. Performance Tests (`test_performance.py`)
- **Load Testing**: Concurrent user simulation
- **Stress Testing**: High-volume operations
- **Database Performance**: Connection handling, query optimization
- **Memory Usage**: Resource consumption monitoring
- **Response Times**: API performance benchmarking

## Running Tests

### Run All Tests
```bash
python manage.py test core
```

### Run Specific Test Categories
```bash
# Model tests only
python manage.py test core.tests.test_models

# API tests only
python manage.py test core.tests.test_views

# Integration tests only
python manage.py test core.tests.test_integration

# Performance tests only
python manage.py test core.tests.test_performance

# Admin tests only
python manage.py test core.tests.test_admin

# Serializer tests only
python manage.py test core.tests.test_serializers
```

### Run Tests with Custom Runner
```bash
# Interactive test runner
python run_tests.py interactive

# All tests with default settings
python run_tests.py
```

### Run Tests with Coverage
```bash
python core/test_config.py
```

## Test Data Management

### Test Factories
The `test_factories.py` file provides factory classes for creating test data:

```python
# Create test user
user = UserFactory()

# Create test account with specific balance
account = BankAccountFactory(balance=Decimal('50000.00'))

# Create test transaction
transaction = TransactionFactory(account=account)
```

### Test Data Mixins
Use provided mixins for common test data scenarios:

```python
class MyTestCase(TestCase, TestDataMixin):
    def test_something(self):
        user = self.create_test_user()
        account = self.create_test_account(user=user)
```

## Test Configuration

### Database Settings
Tests use in-memory SQLite database for speed:
```python
TEST_DATABASE_CONFIG = {
    'default': {
        'ENGINE': 'django.db.backends.sqlite3',
        'NAME': ':memory:',
    }
}
```

### Performance Optimizations
- MD5 password hasher for faster user creation
- Local memory cache backend
- Synchronous task execution
- Disabled unnecessary middleware

## Coverage Requirements

### Target Coverage Metrics
- **Overall Coverage**: > 90%
- **Model Coverage**: > 95%
- **View Coverage**: > 90%
- **Critical Paths**: 100%

### Coverage Areas
1. **User Authentication & Registration**
2. **Account Management**
3. **Money Transfer Operations** 
4. **Transaction Recording**
5. **Security & Authorization**
6. **Data Validation**
7. **Error Handling**

## Test Best Practices

### 1. Test Isolation
- Each test is independent
- Database is reset between tests
- No shared state between test methods

### 2. Meaningful Test Names
```python
def test_user_registration_creates_account_with_demo_funds(self):
def test_transfer_validates_insufficient_funds(self):
def test_account_number_generated_from_phone_number(self):
```

### 3. Test Data
- Use factories for consistent test data
- Create minimal required data for each test
- Clean up resources in tearDown methods

### 4. Assertions
- Use specific assertion methods
- Include meaningful error messages
- Test both positive and negative cases

### 5. API Testing
```python
# Test successful case
response = self.client.post(url, valid_data)
self.assertEqual(response.status_code, 201)
self.assertIn('id', response.data)

# Test error case
response = self.client.post(url, invalid_data)
self.assertEqual(response.status_code, 400)
self.assertIn('error_field', response.data)
```

## Security Testing

### Authentication Tests
- Token-based authentication
- Unauthorized access prevention
- User data isolation
- Session management

### Authorization Tests
- Role-based access control
- Resource ownership validation
- Admin permission restrictions
- Cross-user data access prevention

### Input Validation Tests
- SQL injection prevention
- XSS protection
- CSRF token validation
- Input sanitization

## Performance Testing

### Load Test Scenarios
1. **Concurrent Users**: 10-50 simultaneous users
2. **API Endpoints**: All major endpoints under load
3. **Database Operations**: Bulk operations, connection pooling
4. **Memory Usage**: Resource consumption monitoring

### Performance Benchmarks
- **API Response Time**: < 500ms for 95% of requests
- **Database Queries**: < 100ms for individual queries
- **Concurrent Transfers**: > 95% success rate
- **Memory Usage**: < 100MB increase for 1000 operations

## Continuous Integration

### Test Pipeline
1. **Unit Tests**: Fast, isolated tests
2. **Integration Tests**: Cross-component testing
3. **Performance Tests**: Load and stress testing
4. **Security Tests**: Vulnerability scanning
5. **Coverage Report**: Code coverage analysis

### Quality Gates
- All tests must pass
- Coverage > 90%
- Performance benchmarks met
- Security scans clean
- No critical linting issues

## Debugging Tests

### Common Issues
1. **Database State**: Ensure proper test isolation
2. **Authentication**: Check token setup for API tests
3. **Async Operations**: Use appropriate test decorators
4. **Mock Data**: Verify test data consistency

### Debugging Tools
```bash
# Run single test with verbose output
python manage.py test core.test_models.UserModelTest.test_create_user -v 2

# Run tests with pdb debugging
python manage.py test core.test_models --debug-mode

# Check test database state
python manage.py test core.test_models --keepdb
```

## Contributing to Tests

### Adding New Tests
1. Follow existing naming conventions
2. Add docstrings explaining test purpose
3. Use appropriate base classes and mixins
4. Include both positive and negative test cases
5. Update documentation

### Test Review Checklist
- [ ] Test covers all code paths
- [ ] Appropriate assertions used
- [ ] Test data properly isolated
- [ ] Performance considerations addressed
- [ ] Security implications tested
- [ ] Error cases handled
- [ ] Documentation updated

## Monitoring and Reporting

### Test Metrics
- Test execution time
- Coverage percentages
- Performance benchmarks
- Failure rates
- Resource usage

### Reports Generated
- HTML coverage report (`htmlcov/`)
- Performance test results
- Security scan results
- Test execution logs

## Future Enhancements

### Planned Improvements
1. **Visual Regression Testing**: UI component testing
2. **API Contract Testing**: Schema validation
3. **Database Migration Testing**: Schema change validation
4. **Accessibility Testing**: WCAG compliance
5. **Mobile Testing**: Responsive design validation
