#!/usr/bin/env python3
"""
Test script to verify credentials and application functionality
"""

import asyncio
import sys
import traceback
from config_loader import config
from database import Database
from langchain_agent import LangChainSQLAgent

async def test_credentials():
    """Test all credentials and basic functionality"""
    print("🔍 Testing OEE Co-Pilot Credentials and Functionality")
    print("=" * 60)
    
    # Test 1: Configuration Loading
    print("\n1. Testing Configuration Loading...")
    try:
        cred_status = config.test_credentials()
        print(f"   ✅ Google API Key: {'Available' if cred_status['google_api_key'] else '❌ Missing'}")
        print(f"   ✅ Pinecone API Key: {'Available' if cred_status['pinecone_api_key'] else '⚠️  Optional (not set)'}")
        print(f"   ✅ Database Config: {'Available' if cred_status['database_config'] else '❌ Missing'}")
    except Exception as e:
        print(f"   ❌ Configuration loading failed: {e}")
        return False
    
    # Test 2: Database Connection
    print("\n2. Testing Database Connection...")
    try:
        db = Database()
        db.test_connection()
        print("   ✅ Database connection successful")
        
        # Test basic query
        tables = db.get_all_tables()
        print(f"   ✅ Found {len(tables)} tables: {', '.join(tables[:3])}{'...' if len(tables) > 3 else ''}")
    except Exception as e:
        print(f"   ❌ Database connection failed: {e}")
        return False
    
    # Test 3: LangChain Agent Initialization
    print("\n3. Testing LangChain Agent...")
    try:
        agent = LangChainSQLAgent(db)
        print("   ✅ LangChain agent initialized successfully")
        
        # Test if LLM is working
        if agent.llm:
            print("   ✅ Google Gemini LLM initialized")
        else:
            print("   ❌ Google Gemini LLM failed to initialize")
            return False
            
        if agent.genai_client:
            print("   ✅ Google Gemini embeddings client initialized")
        else:
            print("   ⚠️  Google Gemini embeddings client not available (optional)")
            
        if agent.index:
            print("   ✅ Pinecone vector database initialized")
        else:
            print("   ⚠️  Pinecone vector database not available (optional)")
            
    except Exception as e:
        print(f"   ❌ LangChain agent initialization failed: {e}")
        traceback.print_exc()
        return False
    
    # Test 4: Simple Query Test
    print("\n4. Testing Simple Query...")
    try:
        test_query = "How many records are in the Factory_Equipment_Logs table?"
        print(f"   Query: {test_query}")
        
        result = await agent.process_query(test_query)
        
        if result and "natural_language_response" in result:
            print(f"   ✅ Query executed successfully")
            print(f"   Response: {result['natural_language_response'][:100]}...")
            
            if result.get("sql_query"):
                print(f"   SQL: {result['sql_query']}")
                
            if result.get("results"):
                print(f"   Results: {len(result['results'])} rows returned")
            else:
                print("   ⚠️  No results returned")
        else:
            print("   ❌ Query execution failed")
            return False
            
    except Exception as e:
        print(f"   ❌ Query test failed: {e}")
        traceback.print_exc()
        return False
    
    print("\n" + "=" * 60)
    print("🎉 All tests passed! The application is ready to use.")
    print("=" * 60)
    return True

async def main():
    """Main test function"""
    try:
        success = await test_credentials()
        if success:
            print("\n✅ Credentials and application are working correctly!")
            sys.exit(0)
        else:
            print("\n❌ Some tests failed. Please check the configuration.")
            sys.exit(1)
    except KeyboardInterrupt:
        print("\n\n⏹️  Test interrupted by user")
        sys.exit(1)
    except Exception as e:
        print(f"\n❌ Unexpected error: {e}")
        traceback.print_exc()
        sys.exit(1)

if __name__ == "__main__":
    asyncio.run(main())
