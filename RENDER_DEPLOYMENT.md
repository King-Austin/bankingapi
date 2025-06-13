# SecureCipher Banking - Render Deployment Guide

This guide covers deploying both the Django backend API and React frontend to Render.com.

## Prerequisites

1. GitHub repository with your code
2. Render.com account
3. PostgreSQL database (will be created on Render)

## Backend Deployment (Django API)

### 1. Environment Variables Setup

On Render, set the following environment variables for your backend service:

```bash
# Core Django Settings
SECRET_KEY=<generate-a-secure-key>
DEBUG=false
ENVIRONMENT=production
ALLOWED_HOSTS=.onrender.com

# Database (automatically set by Render when you connect a database)
DATABASE_URL=<automatically-provided-by-render>

# Security
SECURE_SSL_REDIRECT=true
SECURE_HSTS_SECONDS=31536000
SECURE_HSTS_INCLUDE_SUBDOMAINS=true
SECURE_HSTS_PRELOAD=true

# CORS - Update with your frontend URL
CORS_ALLOWED_ORIGINS=https://your-frontend-app.onrender.com

# Banking Configuration
TRANSACTION_DAILY_LIMIT=50000.00
MINIMUM_BALANCE=100.00
DEMO_ACCOUNT_BALANCE=50000.00
DEFAULT_CURRENCY=NGN

# File Storage
STATIC_ROOT=/opt/render/project/src/staticfiles
MEDIA_ROOT=/opt/render/project/src/media

# Admin User (for initial setup)
DJANGO_SUPERUSER_USERNAME=admin
DJANGO_SUPERUSER_EMAIL=admin@yourcompany.com
DJANGO_SUPERUSER_PASSWORD=<secure-password>

# Optional: Email Configuration
EMAIL_HOST=smtp.gmail.com
EMAIL_PORT=587
EMAIL_USE_TLS=true
EMAIL_HOST_USER=your-email@gmail.com
EMAIL_HOST_PASSWORD=your-app-password

# Optional: Error Monitoring
SENTRY_DSN=<your-sentry-dsn>
```

### 2. Render Service Configuration

Create a new Web Service on Render with these settings:

- **Build Command**: `./build.sh`
- **Start Command**: `gunicorn bankingapi.wsgi:application`
- **Environment**: `Python 3`
- **Plan**: `Starter` (upgrade as needed)
- **Health Check Path**: `/api/health/`

### 3. Database Setup

1. Create a PostgreSQL database on Render
2. Connect it to your web service
3. The `DATABASE_URL` will be automatically set

### 4. Deployment Steps

1. Push your code to GitHub
2. Connect your GitHub repository to Render
3. Deploy using the `render.yaml` file or manual configuration
4. Monitor the build logs for any issues
5. Once deployed, visit `/api/health/` to verify the API is running

## Frontend Deployment (React App)

### 1. Environment Variables Setup

Set these environment variables for your frontend static site:

```bash
# API Configuration - Update with your backend URL
VITE_API_URL=https://your-backend-api.onrender.com/api

# Application Settings
VITE_APP_NAME=SecureCipher Bank
VITE_APP_VERSION=1.0.0
VITE_NODE_ENV=production

# Feature Flags
VITE_ENABLE_DEBUG=false
VITE_ENABLE_ANALYTICS=true
VITE_ENABLE_ERROR_REPORTING=true

# Banking Configuration
VITE_DEFAULT_CURRENCY=NGN
VITE_CURRENCY_SYMBOL=₦

# Build Configuration
NODE_ENV=production
```

### 2. Render Static Site Configuration

Create a new Static Site on Render with these settings:

- **Build Command**: `npm ci && npm run build:production`
- **Publish Directory**: `dist`
- **Auto-Deploy**: Yes
- **Pull Request Previews**: Enabled (recommended)

### 3. Custom Headers (Optional but Recommended)

Add these security headers in your Render dashboard:

```
X-Frame-Options: DENY
X-Content-Type-Options: nosniff
Referrer-Policy: strict-origin-when-cross-origin
Permissions-Policy: camera=(), microphone=(), geolocation=()
```

### 4. Deployment Steps

1. Push your frontend code to GitHub
2. Create a new Static Site on Render
3. Connect your GitHub repository
4. Configure the build settings above
5. Deploy and test

## Post-Deployment Configuration

### 1. Update CORS Settings

After both services are deployed, update the backend's `CORS_ALLOWED_ORIGINS` environment variable with your frontend URL:

```bash
CORS_ALLOWED_ORIGINS=https://your-frontend-app.onrender.com
```

### 2. Update Frontend API URL

Update the frontend's `VITE_API_URL` environment variable with your backend URL:

```bash
VITE_API_URL=https://your-backend-api.onrender.com/api
```

### 3. Test the Integration

1. Visit your frontend URL
2. Register a new user account
3. Login and test the banking features
4. Verify API calls are working properly

## Troubleshooting

### Common Backend Issues

1. **Build Failures**: Check that all dependencies are in `requirements.txt`
2. **Database Errors**: Ensure PostgreSQL database is connected and migrations have run
3. **Static Files**: Verify `STATIC_ROOT` is set correctly and `collectstatic` runs during build
4. **CORS Errors**: Double-check `CORS_ALLOWED_ORIGINS` includes your frontend URL

### Common Frontend Issues

1. **Build Failures**: Remove `bootstrap-icons` dependency (we use CDN)
2. **API Connection**: Verify `VITE_API_URL` points to the correct backend
3. **Environment Variables**: Ensure all `VITE_` prefixed variables are set
4. **Routing Issues**: Make sure redirect rules are configured for SPA

### Health Checks

- **Backend**: `https://your-backend.onrender.com/api/health/`
- **Frontend**: Check the console for any JavaScript errors

## Security Considerations

1. **Environment Variables**: Never commit sensitive data to Git
2. **HTTPS**: Both services should use HTTPS (automatic on Render)
3. **CORS**: Only allow your frontend domain
4. **Admin Access**: Use strong passwords for Django admin
5. **Database**: Use the provided PostgreSQL, not SQLite in production

## Performance Optimization

1. **Static Files**: Use WhiteNoise for serving static files (already configured)
2. **Caching**: Consider adding Redis for caching (upgrade plan required)
3. **Database**: Use connection pooling (configured in settings)
4. **Frontend**: Gzip compression is handled by Render
5. **CDN**: Consider using a CDN for better global performance

## Monitoring

1. **Logs**: Monitor Render logs for errors
2. **Health Checks**: Set up monitoring for your health check endpoints
3. **Error Reporting**: Configure Sentry for error tracking
4. **Performance**: Monitor response times and database queries

## Backup Strategy

1. **Database**: Render provides automated backups for PostgreSQL
2. **Code**: Ensure your code is backed up in version control
3. **Environment Variables**: Document all configuration securely

## Support

For issues specific to this banking application, check:
1. Django admin panel for backend issues
2. Browser console for frontend issues
3. Render logs for deployment issues
4. GitHub repository for code-related problems
