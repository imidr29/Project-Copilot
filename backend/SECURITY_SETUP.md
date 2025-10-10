# Security Setup Guide

## 🔒 Security Features Implemented

### 1. **API Key Protection**
- ✅ API keys moved from config.json to environment variables
- ✅ Tokens are truncated in logs (only first 8 characters shown)
- ✅ Environment variables take priority over config file

### 2. **Rate Limiting**
- ✅ Token endpoints limited to 10 requests per minute per IP
- ✅ Prevents brute force attacks on token endpoints
- ✅ Returns 429 status code when limit exceeded

### 3. **CORS Security**
- ✅ Restricted to specific localhost origins only
- ✅ Removed wildcard (*) origins
- ✅ Limited allowed headers and methods

### 4. **Security Headers**
- ✅ X-Content-Type-Options: nosniff
- ✅ X-Frame-Options: DENY
- ✅ X-XSS-Protection: 1; mode=block
- ✅ Referrer-Policy: strict-origin-when-cross-origin
- ✅ Permissions-Policy: geolocation=(), microphone=(), camera=()

### 5. **Trusted Host Protection**
- ✅ Only allows localhost and 127.0.0.1 connections
- ✅ Prevents host header injection attacks

## 🚀 Setup Instructions

### Step 1: Create Environment File
```bash
# Copy the template
cp env_template.txt .env

# Edit .env with your actual values
nano .env
```

### Step 2: Set Environment Variables
```bash
# Required variables
export GOOGLE_API_KEY="your_actual_google_api_key"
export DB_HOST="your_database_host"
export DB_USER="your_database_user"
export DB_PASSWORD="your_database_password"
export DB_NAME="your_database_name"

# Optional variables
export PINECONE_API_KEY="your_pinecone_api_key"
export TOKEN_GUARD_SECRET="your_secure_secret_key"
```

### Step 3: Verify Security
```bash
# Test that API keys are not exposed
python3 test_credentials.py

# Check that tokens are truncated in logs
python3 main.py
```

## ⚠️ Security Best Practices

### 1. **Never Commit Secrets**
- ✅ .env file is in .gitignore
- ✅ config.json has empty values
- ✅ Use environment variables in production

### 2. **Token Management**
- ✅ Tokens expire after 24 hours
- ✅ Rate limiting prevents abuse
- ✅ Tokens are truncated in logs

### 3. **Network Security**
- ✅ CORS restricted to localhost only
- ✅ Trusted host middleware enabled
- ✅ Security headers prevent common attacks

### 4. **Production Deployment**
- ✅ Use HTTPS in production
- ✅ Set strong TOKEN_GUARD_SECRET
- ✅ Use proper database credentials
- ✅ Enable firewall rules
- ✅ Regular security updates

## 🔍 Security Monitoring

### Log Analysis
- Monitor for rate limit violations
- Check for failed authentication attempts
- Review token usage patterns

### Regular Maintenance
- Rotate API keys periodically
- Update dependencies regularly
- Review access logs
- Test security configurations

## 🚨 Security Alerts

If you see these in logs, investigate immediately:
- Multiple 401 errors from same IP
- Rate limit violations (429 errors)
- Invalid token attempts
- Unusual request patterns

## 📞 Security Issues

If you discover a security vulnerability:
1. Do NOT commit the fix to public repository
2. Contact the development team immediately
3. Follow responsible disclosure practices
4. Test fixes thoroughly before deployment
