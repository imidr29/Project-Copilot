"""
Token Guard Implementation for API Security

This module provides token-based authentication and authorization for the OEE Co-Pilot API.
It includes functionality for generating, validating, and managing API tokens.
"""

import secrets
import hashlib
import time
from typing import Optional, Dict, Any
from datetime import datetime, timedelta
import logging
import json
import os

logger = logging.getLogger(__name__)


class TokenGuard:
    """
    Token Guard for API authentication and authorization.
    
    Features:
    - Generate secure API tokens
    - Validate token authenticity and expiration
    - Rate limiting per token
    - Token revocation
    - Role-based access control
    """
    
    def __init__(self, secret_key: Optional[str] = None, token_expiry_hours: int = 24):
        """
        Initialize the Token Guard.
        
        Args:
            secret_key: Secret key for token signing (defaults to environment variable)
            token_expiry_hours: Token expiration time in hours
        """
        self.secret_key = secret_key or os.getenv('TOKEN_GUARD_SECRET', 'default-secret-key-change-in-production')
        self.token_expiry_hours = token_expiry_hours
        self.active_tokens: Dict[str, Dict[str, Any]] = {}
        self.rate_limits: Dict[str, Dict[str, Any]] = {}
        self.usage_stats: Dict[str, Dict[str, Any]] = {}  # Track usage statistics
        
        # Rate limiting configuration
        self.rate_limit_requests = 100  # requests per window
        self.rate_limit_window = 3600   # 1 hour in seconds
        
        logger.info("Token Guard initialized")
    
    def generate_token(self, user_id: str, role: str = "user", permissions: list = None) -> str:
        """
        Generate a new API token for a user.
        
        Args:
            user_id: Unique identifier for the user
            role: User role (admin, user, readonly)
            permissions: List of specific permissions
            
        Returns:
            Generated API token
        """
        # Generate a secure random token
        token = secrets.token_urlsafe(32)
        
        # Create token metadata
        token_data = {
            'user_id': user_id,
            'role': role,
            'permissions': permissions or [],
            'created_at': datetime.now().isoformat(),
            'expires_at': (datetime.now() + timedelta(hours=self.token_expiry_hours)).isoformat(),
            'last_used': None,
            'is_revoked': False
        }
        
        # Store token data
        self.active_tokens[token] = token_data
        
        # Initialize rate limiting for this token
        self.rate_limits[token] = {
            'requests': 0,
            'window_start': time.time()
        }
        
        # Initialize usage statistics for this user
        if user_id not in self.usage_stats:
            self.usage_stats[user_id] = {
                'total_requests': 0,
                'total_tokens': 0,
                'daily_requests': 0,
                'last_reset': datetime.now().date().isoformat(),
                'tokens': []
            }
        
        # Add token to user's token list
        self.usage_stats[user_id]['tokens'].append({
            'token': token[:8] + '...',  # Only store partial token for security
            'role': role,
            'created_at': token_data['created_at'],
            'expires_at': token_data['expires_at'],
            'requests': 0
        })
        self.usage_stats[user_id]['total_tokens'] += 1
        
        logger.info(f"Generated token for user {user_id} with role {role}")
        return token
    
    def validate_token(self, token: str, endpoint: str = None) -> Dict[str, Any]:
        """
        Validate an API token and return user information.
        
        Args:
            token: API token to validate
            endpoint: API endpoint being accessed (for usage tracking)
            
        Returns:
            Dictionary with validation result and user info
            
        Raises:
            ValueError: If token is invalid, expired, or revoked
        """
        if not token:
            raise ValueError("Token is required")
        
        # Check if token exists
        if token not in self.active_tokens:
            raise ValueError("Invalid token")
        
        token_data = self.active_tokens[token]
        
        # Check if token is revoked
        if token_data.get('is_revoked', False):
            raise ValueError("Token has been revoked")
        
        # Check if token is expired
        expires_at = datetime.fromisoformat(token_data['expires_at'])
        if datetime.now() > expires_at:
            # Remove expired token
            del self.active_tokens[token]
            if token in self.rate_limits:
                del self.rate_limits[token]
            raise ValueError("Token has expired")
        
        # Update last used timestamp
        token_data['last_used'] = datetime.now().isoformat()
        
        # Check rate limiting
        if not self._check_rate_limit(token):
            raise ValueError("Rate limit exceeded")
        
        # Update usage statistics
        self._update_usage_stats(token_data['user_id'], token, endpoint)
        
        return {
            'valid': True,
            'user_id': token_data['user_id'],
            'role': token_data['role'],
            'permissions': token_data['permissions'],
            'expires_at': token_data['expires_at']
        }
    
    def _check_rate_limit(self, token: str) -> bool:
        """
        Check if token is within rate limits.
        
        Args:
            token: API token to check
            
        Returns:
            True if within limits, False otherwise
        """
        if token not in self.rate_limits:
            return True
        
        current_time = time.time()
        rate_data = self.rate_limits[token]
        
        # Reset window if needed
        if current_time - rate_data['window_start'] > self.rate_limit_window:
            rate_data['requests'] = 0
            rate_data['window_start'] = current_time
        
        # Check if limit exceeded
        if rate_data['requests'] >= self.rate_limit_requests:
            return False
        
        # Increment request count
        rate_data['requests'] += 1
        return True
    
    def _update_usage_stats(self, user_id: str, token: str, endpoint: str = None):
        """Update usage statistics for a user"""
        if user_id not in self.usage_stats:
            return
        
        # Exclude stats endpoints from counting
        excluded_endpoints = [
            '/api/usage/stats',
            '/api/usage/system', 
            '/api/usage/all',
            '/api/usage/token/',
            '/api/tokens',
            '/api/tokens/default',
            '/health'
        ]
        
        if endpoint:
            for excluded in excluded_endpoints:
                if endpoint.startswith(excluded):
                    logger.info(f"Excluding endpoint from usage count: {endpoint}")
                    return
        
        current_date = datetime.now().date().isoformat()
        stats = self.usage_stats[user_id]
        
        # Reset daily counter if it's a new day
        if stats['last_reset'] != current_date:
            stats['daily_requests'] = 0
            stats['last_reset'] = current_date
        
        # Update counters
        stats['total_requests'] += 1
        stats['daily_requests'] += 1
        
        # Update token-specific counter
        token_prefix = token[:8] + '...'
        for token_info in stats['tokens']:
            if token_info['token'] == token_prefix:
                token_info['requests'] += 1
                break
    
    def revoke_token(self, token: str) -> bool:
        """
        Revoke an API token.
        
        Args:
            token: API token to revoke
            
        Returns:
            True if token was revoked, False if token not found
        """
        if token in self.active_tokens:
            self.active_tokens[token]['is_revoked'] = True
            logger.info(f"Token revoked for user {self.active_tokens[token]['user_id']}")
            return True
        return False
    
    def revoke_user_tokens(self, user_id: str) -> int:
        """
        Revoke all tokens for a specific user.
        
        Args:
            user_id: User ID to revoke tokens for
            
        Returns:
            Number of tokens revoked
        """
        revoked_count = 0
        for token, data in self.active_tokens.items():
            if data['user_id'] == user_id and not data.get('is_revoked', False):
                data['is_revoked'] = True
                revoked_count += 1
        
        logger.info(f"Revoked {revoked_count} tokens for user {user_id}")
        return revoked_count
    
    def cleanup_expired_tokens(self) -> int:
        """
        Remove expired tokens from memory.
        
        Returns:
            Number of tokens cleaned up
        """
        current_time = datetime.now()
        expired_tokens = []
        
        for token, data in self.active_tokens.items():
            expires_at = datetime.fromisoformat(data['expires_at'])
            if current_time > expires_at:
                expired_tokens.append(token)
        
        for token in expired_tokens:
            del self.active_tokens[token]
            if token in self.rate_limits:
                del self.rate_limits[token]
        
        if expired_tokens:
            logger.info(f"Cleaned up {len(expired_tokens)} expired tokens")
        
        return len(expired_tokens)
    
    def get_token_info(self, token: str) -> Optional[Dict[str, Any]]:
        """
        Get information about a token without validating it.
        
        Args:
            token: API token
            
        Returns:
            Token information or None if not found
        """
        return self.active_tokens.get(token)
    
    def list_active_tokens(self, user_id: Optional[str] = None) -> list:
        """
        List active tokens, optionally filtered by user.
        
        Args:
            user_id: Optional user ID to filter by
            
        Returns:
            List of active tokens with their metadata
        """
        tokens = []
        for token, data in self.active_tokens.items():
            if data.get('is_revoked', False):
                continue
            
            if user_id and data['user_id'] != user_id:
                continue
            
            # Check if expired
            expires_at = datetime.fromisoformat(data['expires_at'])
            if datetime.now() > expires_at:
                continue
            
            tokens.append({
                'token': token[:8] + '...',  # Only show first 8 characters
                'full_token': token,  # Include full token for internal use
                'user_id': data['user_id'],
                'role': data['role'],
                'created_at': data['created_at'],
                'expires_at': data['expires_at'],
                'last_used': data.get('last_used')
            })
        
        return tokens
    
    def has_permission(self, token: str, permission: str) -> bool:
        """
        Check if a token has a specific permission.
        
        Args:
            token: API token
            permission: Permission to check
            
        Returns:
            True if token has permission, False otherwise
        """
        try:
            token_info = self.validate_token(token)
            user_permissions = token_info.get('permissions', [])
            user_role = token_info.get('role', 'user')
            
            # Admin role has all permissions
            if user_role == 'admin':
                return True
            
            # Check specific permissions
            return permission in user_permissions
            
        except ValueError:
            return False
    
    def get_usage_stats(self, user_id: str) -> Optional[Dict[str, Any]]:
        """
        Get usage statistics for a specific user.
        
        Args:
            user_id: User ID to get stats for
            
        Returns:
            Usage statistics dictionary or None if user not found
        """
        return self.usage_stats.get(user_id)
    
    def get_all_usage_stats(self) -> Dict[str, Dict[str, Any]]:
        """
        Get usage statistics for all users.
        
        Returns:
            Dictionary of all users' usage statistics
        """
        return self.usage_stats.copy()
    
    def get_token_usage(self, token: str) -> Optional[Dict[str, Any]]:
        """
        Get usage statistics for a specific token.
        
        Args:
            token: Token to get stats for
            
        Returns:
            Token usage information or None if token not found
        """
        if token not in self.active_tokens:
            return None
        
        token_data = self.active_tokens[token]
        user_id = token_data['user_id']
        
        if user_id not in self.usage_stats:
            return None
        
        # Find the specific token in user's token list
        token_prefix = token[:8] + '...'
        for token_info in self.usage_stats[user_id]['tokens']:
            if token_info['token'] == token_prefix:
                return {
                    'user_id': user_id,
                    'role': token_data['role'],
                    'created_at': token_data['created_at'],
                    'expires_at': token_data['expires_at'],
                    'last_used': token_data.get('last_used'),
                    'requests': token_info['requests'],
                    'is_revoked': token_data.get('is_revoked', False)
                }
        
        return None
    
    def reset_daily_counters(self):
        """Reset daily counters for all users (typically called at midnight)"""
        current_date = datetime.now().date().isoformat()
        for user_id, stats in self.usage_stats.items():
            stats['daily_requests'] = 0
            stats['last_reset'] = current_date
        logger.info("Daily counters reset for all users")
    
    def get_system_stats(self) -> Dict[str, Any]:
        """
        Get overall system statistics.
        
        Returns:
            System-wide usage statistics
        """
        total_users = len(self.usage_stats)
        total_requests = sum(stats['total_requests'] for stats in self.usage_stats.values())
        total_tokens = sum(stats['total_tokens'] for stats in self.usage_stats.values())
        active_tokens = len(self.active_tokens)
        
        # Calculate daily totals
        today = datetime.now().date().isoformat()
        daily_requests = sum(
            stats['daily_requests'] 
            for stats in self.usage_stats.values() 
            if stats['last_reset'] == today
        )
        
        return {
            'total_users': total_users,
            'total_requests': total_requests,
            'total_tokens': total_tokens,
            'active_tokens': active_tokens,
            'daily_requests': daily_requests,
            'rate_limit_per_hour': self.rate_limit_requests,
            'token_expiry_hours': self.token_expiry_hours
        }


# Global token guard instance
token_guard = TokenGuard()


def require_token(required_permission: Optional[str] = None):
    """
    Decorator to require valid token for API endpoints.
    
    Args:
        required_permission: Optional specific permission required
    """
    def decorator(func):
        async def wrapper(*args, **kwargs):
            # This would be implemented in the FastAPI middleware
            # For now, this is a placeholder for the decorator pattern
            return await func(*args, **kwargs)
        return wrapper
    return decorator


def create_default_tokens():
    """
    Create default tokens for testing and initial setup.
    """
    # Create admin token
    admin_token = token_guard.generate_token(
        user_id="admin",
        role="admin",
        permissions=["read", "write", "admin"]
    )
    
    # Create user token
    user_token = token_guard.generate_token(
        user_id="user",
        role="user",
        permissions=["read", "write"]
    )
    
    # Create readonly token
    readonly_token = token_guard.generate_token(
        user_id="readonly",
        role="readonly",
        permissions=["read"]
    )
    
    logger.info("Default tokens created:")
    logger.info(f"Admin token: {admin_token[:8]}...")
    logger.info(f"User token: {user_token}")  # Full token for easy access
    logger.info(f"Readonly token: {readonly_token[:8]}...")
    
    return {
        "admin": admin_token,
        "user": user_token,
        "readonly": readonly_token
    }


if __name__ == "__main__":
    # Test the token guard
    guard = TokenGuard()
    
    # Generate test tokens
    tokens = create_default_tokens()
    
    # Test validation
    try:
        result = guard.validate_token(tokens["admin"])
        print(f"Admin token validation: {result}")
    except ValueError as e:
        print(f"Admin token validation failed: {e}")
    
    # Test rate limiting
    for i in range(5):
        try:
            guard.validate_token(tokens["user"])
            print(f"User token validation {i+1}: OK")
        except ValueError as e:
            print(f"User token validation {i+1} failed: {e}")
    
    # List active tokens
    active_tokens = guard.list_active_tokens()
    print(f"Active tokens: {len(active_tokens)}")
