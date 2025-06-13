# SecureCipher Banking API

A comprehensive Django REST API for a modern banking application with secure transaction management, user authentication, and account management features.

## 🏦 Features

### Core Banking Features
- **User Management**: Custom user model with profile management
- **Account Management**: Multiple account types (Savings, Checking, Business, Premium)
- **Transactions**: Secure money transfers with audit trails
- **Beneficiary Management**: Save and manage transfer recipients
- **Card Management**: Debit/Credit card operations
- **Security**: Two-factor authentication, transaction limits, audit logs

### API Endpoints

#### Authentication
- `POST /api/auth/register/` - User registration
- `POST /api/auth/login/` - User login
- `POST /api/auth/logout/` - User logout

#### User Management
- `GET /api/user/profile/` - Get user profile
- `PUT /api/user/update_profile/` - Update user profile
- `POST /api/user/change_password/` - Change password

#### Account Management
- `GET /api/accounts/` - List user's bank accounts
- `GET /api/accounts/{id}/` - Get account details
- `GET /api/accounts/{id}/transactions/` - Get account transaction history
- `GET /api/accounts/{id}/balance/` - Get account balance

#### Transactions
- `GET /api/transactions/` - List user's transactions
- `POST /api/transactions/transfer/` - Transfer money between accounts

#### Beneficiaries
- `GET /api/beneficiaries/` - List beneficiaries
- `POST /api/beneficiaries/` - Add new beneficiary
- `PUT /api/beneficiaries/{id}/` - Update beneficiary
- `DELETE /api/beneficiaries/{id}/` - Delete beneficiary

#### Cards
- `GET /api/cards/` - List user's cards
- `POST /api/cards/{id}/block_card/` - Block a card
- `POST /api/cards/{id}/unblock_card/` - Unblock a card

## 🛠️ Technology Stack

- **Backend**: Django 5.2.2, Django REST Framework
- **Database**: SQLite (development), PostgreSQL (production ready)
- **Authentication**: Token-based authentication
- **Security**: Password validation, audit logging, transaction encryption

## 📋 Models Architecture

### 1. User Model (Custom)
- Extends Django's AbstractUser
- Additional fields: phone_number, date_of_birth, address, national_id
- Security features: is_verified, two_factor_enabled

### 2. Account Types
- Different account categories with varying features
- Configurable minimum balance, interest rates, fees
- Transaction limits per account type

### 3. Bank Accounts
- User's banking accounts
- Account number generation
- Balance tracking (available vs actual)
- Status management (Active, Inactive, Suspended, Closed)

### 4. Transactions
- Complete transaction history
- Debit/Credit tracking
- Reference number generation
- Audit trail with IP address and user agent
- Balance before/after tracking

### 5. Beneficiaries
- Saved recipients for easy transfers
- Nickname support
- Favorite beneficiaries

### 6. Cards
- Debit/Credit card management
- Card number generation and masking
- Status management and limits
- Contactless and online payment controls

### 7. Audit Logs
- Complete audit trail of user actions
- Security monitoring
- IP address and user agent tracking

## 🚀 Setup Instructions

### Prerequisites
- Python 3.8+
- pip
- Virtual environment (recommended)

### Installation

1. **Clone the repository**
   ```bash
   cd /home/kingaustin/Documents/securecipher/bankingapi
   ```

2. **Create and activate virtual environment**
   ```bash
   python -m venv banking_env
   source banking_env/bin/activate  # On Windows: banking_env\Scripts\activate
   ```

3. **Install dependencies**
   ```bash
   pip install -r requirements.txt
   ```

4. **Run migrations**
   ```bash
   python manage.py makemigrations
   python manage.py migrate
   ```

5. **Populate initial data**
   ```bash
   python manage.py populate_initial_data
   ```

6. **Create superuser**
   ```bash
   python manage.py createsuperuser
   ```

7. **Run the development server**
   ```bash
   python manage.py runserver
   ```

The API will be available at `http://localhost:8000/api/`

## 🔐 Security Features

### Authentication & Authorization
- Token-based authentication
- User verification system
- Role-based permissions

### Transaction Security
- PIN verification for transfers
- Balance validation
- Transaction limits
- Audit logging with IP tracking

### Data Protection
- Sensitive data fields (PIN, CVV) should be encrypted in production
- Audit trails for all operations
- Session management

## 🧪 Testing

### Sample API Usage

1. **Register a new user**
   ```bash
   curl -X POST http://localhost:8000/api/auth/register/ \
   -H "Content-Type: application/json" \
   -d '{
     "username": "john_doe",
     "email": "john@example.com",
     "password": "SecurePassword123!",
     "password_confirm": "SecurePassword123!",
     "first_name": "John",
     "last_name": "Doe",
     "phone_number": "+1234567890"
   }'
   ```

2. **Login**
   ```bash
   curl -X POST http://localhost:8000/api/auth/login/ \
   -H "Content-Type: application/json" \
   -d '{
     "username": "john_doe",
     "password": "SecurePassword123!"
   }'
   ```

3. **Get user profile** (with token)
   ```bash
   curl -X GET http://localhost:8000/api/user/profile/ \
   -H "Authorization: Token YOUR_TOKEN_HERE"
   ```

## 📊 Database Schema

### Key Relationships
- User ← One-to-Many → BankAccount
- BankAccount ← One-to-Many → Transaction
- BankAccount ← One-to-Many → Card
- User ← One-to-Many → Beneficiary
- User ← One-to-Many → AuditLog

## 🔧 Configuration

### Environment Variables (Production)
```bash
SECRET_KEY=your-secret-key
DEBUG=False
ALLOWED_HOSTS=your-domain.com
DATABASE_URL=postgresql://user:password@localhost/bankingdb
```

### Banking Settings
- `TRANSACTION_DAILY_LIMIT`: Default daily transaction limit
- `MINIMUM_BALANCE`: Minimum account balance
- `ACCOUNT_NUMBER_LENGTH`: Length of generated account numbers

## 📈 Future Enhancements

### Planned Features
1. **Mobile Banking**
   - Mobile API endpoints
   - Push notifications
   - QR code payments

2. **Advanced Security**
   - Biometric authentication
   - Fraud detection
   - Multi-factor authentication

3. **Financial Services**
   - Loan management
   - Investment tracking
   - Credit score monitoring

4. **Analytics**
   - Spending analytics
   - Financial reports
   - Budget tracking

### Technical Improvements
1. **Performance**
   - Redis caching
   - Database optimization
   - API rate limiting

2. **Monitoring**
   - Error tracking (Sentry)
   - Performance monitoring
   - Health checks

3. **Deployment**
   - Docker containerization
   - CI/CD pipeline
   - Cloud deployment

## 📝 API Documentation

### Response Format
All API responses follow this structure:
```json
{
  "data": {},
  "message": "Success message",
  "status": "success|error",
  "timestamp": "2025-06-13T10:30:00Z"
}
```

### Error Handling
- 400: Bad Request (validation errors)
- 401: Unauthorized (authentication required)
- 403: Forbidden (insufficient permissions)
- 404: Not Found
- 500: Internal Server Error

## 🤝 Contributing

1. Fork the repository
2. Create a feature branch
3. Make your changes
4. Add tests
5. Submit a pull request

## 📄 License

This project is licensed under the MIT License.

## 📞 Support

For support and questions:
- Email: support@securecipher.com
- Documentation: [API Docs](http://localhost:8000/api/)
- Admin Panel: [Django Admin](http://localhost:8000/admin/)

---

**SecureCipher Banking API** - Building the future of digital banking 🏦
