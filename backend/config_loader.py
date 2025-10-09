import json
import os
import pymysql.cursors
from typing import Dict, Any, Optional

class ConfigLoader:
    def __init__(self, config_file: str = "config.json"):
        self.config_file = config_file
        self._config = None
        self._load_config()
    
    def _load_config(self):
        """Load configuration from JSON file"""
        try:
            if os.path.exists(self.config_file):
                with open(self.config_file, 'r') as f:
                    self._config = json.load(f)
                print(f"✅ Loaded configuration from {self.config_file}")
            else:
                print(f"⚠️  Config file {self.config_file} not found, using environment variables")
                self._config = {}
        except Exception as e:
            print(f"❌ Error loading config file: {e}")
            self._config = {}
    
    def get(self, key: str, default: Any = None) -> Any:
        """Get configuration value with fallback to environment variable"""
        # First try config file
        if self._config and key in self._config:
            return self._config[key]
        
        # Fallback to environment variable
        env_key = key.upper()
        return os.getenv(env_key, default)
    
    def get_google_api_key(self) -> Optional[str]:
        """Get Google API key from config or environment"""
        return self.get("google_api_key") or os.getenv("GOOGLE_API_KEY")
    
    def get_pinecone_api_key(self) -> Optional[str]:
        """Get Pinecone API key from config or environment"""
        return self.get("pinecone_api_key") or os.getenv("PINECONE_API_KEY")
    
    def get_database_config(self) -> Dict[str, Any]:
        """Get database configuration"""
        db_config = self.get("database", {})
        return {
            'host': db_config.get('host', os.getenv('DB_HOST', '127.0.0.1')),
            'user': db_config.get('user', os.getenv('DB_USER', 'root')),
            'password': db_config.get('password', os.getenv('DB_PASSWORD', 'rootpass')),
            'database': db_config.get('database', os.getenv('DB_NAME', 'MiningAndFactoryData')),
            'port': int(db_config.get('port', os.getenv('DB_PORT', 3307))),
            'charset': 'utf8mb4',
            'cursorclass': pymysql.cursors.DictCursor
        }
    
    def test_credentials(self) -> Dict[str, bool]:
        """Test if credentials are available"""
        results = {
            'google_api_key': bool(self.get_google_api_key()),
            'pinecone_api_key': bool(self.get_pinecone_api_key()),
            'database_config': bool(self.get_database_config())
        }
        return results

# Global config instance
config = ConfigLoader()
