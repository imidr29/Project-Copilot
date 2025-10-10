from typing import Dict, Any, List, Optional
from datetime import datetime, timedelta, date
import re
import logging
import os
from decimal import Decimal

from langchain.prompts import PromptTemplate
from langchain.chains import LLMChain
from langchain_google_genai import ChatGoogleGenerativeAI
from database import Database
from pinecone import Pinecone
from google import genai
from google.genai import types
from config_loader import config

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class LangChainSQLAgent:
    def __init__(self, database: Database):
        self.db = database
        
        self.llm = ChatGoogleGenerativeAI(
            model="gemini-2.0-flash",
            temperature=0,
            api_key=config.get_google_api_key()
        )
        
        try:
            self.genai_client = genai.Client(api_key=config.get_google_api_key())
        except Exception as e:
            logger.warning(f"Gemini embeddings failed: {e}")
            self.genai_client = None
        
        try:
            pc = Pinecone(api_key=config.get_pinecone_api_key())
            self.index = pc.Index("oee-semantic")
        except Exception as e:
            logger.warning(f"Pinecone failed: {e}")
            self.index = None
        
        self._initialize_schema()
        self._setup_sql_keywords()

    def _setup_sql_keywords(self):
        """Define SQL keywords and functions that should NOT be wrapped in backticks"""
        self.sql_keywords = {
            'SELECT', 'FROM', 'WHERE', 'GROUP', 'BY', 'ORDER', 'HAVING',
            'LIMIT', 'AS', 'AND', 'OR', 'NOT', 'IN', 'BETWEEN', 'LIKE',
            'COUNT', 'SUM', 'AVG', 'MAX', 'MIN', 'ROUND', 'COALESCE',
            'JOIN', 'LEFT', 'RIGHT', 'INNER', 'OUTER', 'ON', 'DISTINCT',
            'ASC', 'DESC', 'NULL', 'IS', 'EXISTS', 'CASE', 'WHEN',
            'THEN', 'ELSE', 'END', 'CAST', 'INTERVAL', 
            # CRITICAL: Date/time functions
            'DATE', 'CURDATE', 'NOW', 'TIMESTAMPDIFF', 'DATE_SUB', 'DATE_ADD',
            'SECOND', 'MINUTE', 'HOUR', 'DAY', 'WEEK', 'MONTH', 'YEAR',
            'DAYOFWEEK', 'DAYOFMONTH', 'DAYOFYEAR', 'WEEKDAY',
            'TIME', 'TIMESTAMP', 'CURRENT_DATE', 'CURRENT_TIME', 'CURRENT_TIMESTAMP'
        }

    def _initialize_schema(self):
        self._refresh_schema()
    
    def _refresh_schema(self):
        """Refresh database schema information to include new tables"""
        try:
            tables_query = "SELECT TABLE_NAME FROM INFORMATION_SCHEMA.TABLES WHERE TABLE_SCHEMA = DATABASE()"
            tables = self.db.execute_query(tables_query)
            self.tables_info = {}
            
            for table_row in tables:
                table_name = table_row['TABLE_NAME']
                columns_query = f"SELECT COLUMN_NAME, DATA_TYPE FROM INFORMATION_SCHEMA.COLUMNS WHERE TABLE_SCHEMA = DATABASE() AND TABLE_NAME = '{table_name}' ORDER BY ORDINAL_POSITION"
                columns = self.db.execute_query(columns_query)
                
                try:
                    sample_query = f"SELECT * FROM `{table_name}` LIMIT 2"
                    samples = self.db.execute_query(sample_query)
                except Exception:
                    samples = []
                
                self.tables_info[table_name] = {'columns': columns, 'samples': samples}
            
            logger.info(f"Schema refreshed: {len(self.tables_info)} tables")
            
        except Exception as e:
            logger.error(f"Schema refresh failed: {e}")
            self.tables_info = {}

    def _build_schema_context(self) -> str:
        if not self.tables_info:
            return self.db.get_schema_description()
        
        parts = ["DATABASE SCHEMA:"]
        for table_name, info in self.tables_info.items():
            parts.append(f"\nTable: {table_name}")
            if info['columns']:
                parts.append("Columns:")
                for col in info['columns']:
                    parts.append(f"  - {col['COLUMN_NAME']} ({col['DATA_TYPE']})")
            if info['samples']:
                sample = info['samples'][0]
                sample_str = ", ".join([f"{k}={str(v)[:15]}" for k, v in list(sample.items())[:4]])
                parts.append(f"Sample: {sample_str}")
        return "\n".join(parts)

    def _format_timedelta(self, td: timedelta) -> str:
        total_seconds = int(td.total_seconds())
        hours = total_seconds // 3600
        minutes = (total_seconds % 3600) // 60
        seconds = total_seconds % 60
        return f"{hours:02d}:{minutes:02d}:{seconds:02d}"

    def _serialize_value(self, value: Any) -> Any:
        if isinstance(value, (datetime, date)):
            return value.isoformat()
        if isinstance(value, timedelta):
            return self._format_timedelta(value)
        if isinstance(value, Decimal):
            return float(value)
        if isinstance(value, bytes):
            return value.decode('utf-8', errors='replace')
        return value

    def _serialize_results(self, results: List[Dict]) -> List[Dict]:
        return [{k: self._serialize_value(v) for k, v in row.items()} for row in results]

    def _wrap_identifiers(self, sql: str) -> str:
        """Wrap column/table names in backticks, but preserve SQL keywords and functions"""
        all_identifiers = set()
        for table_name, info in self.tables_info.items():
            all_identifiers.add(table_name)
            for col in info['columns']:
                all_identifiers.add(col['COLUMN_NAME'])
        
        # Sort by length (longest first) to handle multi-word identifiers
        sorted_identifiers = sorted(all_identifiers, key=len, reverse=True)
        
        # Remove existing backticks
        sql = sql.replace('`', '')
        
        # Wrap each identifier that's NOT a SQL keyword
        for identifier in sorted_identifiers:
            if identifier.upper() not in self.sql_keywords:
                pattern = rf'\b{re.escape(identifier)}\b'
                sql = re.sub(pattern, f'`{identifier}`', sql, flags=re.IGNORECASE)
        
        # Remove backticks from SQL keywords/functions (cleanup pass)
        for keyword in self.sql_keywords:
            sql = re.sub(rf'`{keyword}`', keyword, sql, flags=re.IGNORECASE)
        
        return sql

    async def _enhance_with_semantic_search(self, query: str) -> str:
        if not self.genai_client or not self.index:
            return query
        try:
            result = self.genai_client.models.embed_content(model="gemini-embedding-001", contents=query, config=types.EmbedContentConfig(task_type="RETRIEVAL_QUERY", output_dimensionality=1536))
            embedding = result.embeddings[0].values
            pine_result = self.index.query(vector=embedding, top_k=3, include_metadata=True)
            similar = [m.get('metadata', {}).get('query', '') for m in pine_result.get('matches', []) if m.get('metadata', {}).get('query')]
            if similar:
                return f"{query}\n[Context: {', '.join(similar[:2])}]"
        except Exception as e:
            logger.warning(f"Semantic search failed: {e}")
        return query

    async def process_query(self, query: str, conversation_history: List[Dict[str, str]] = None) -> Dict[str, Any]:
        try:
            # Check if query is database-related
            if not self._is_database_query(query):
                logger.info(f"Non-database query detected: {query}")
                nlp_response = await self._generate_nlp_only_response(query)
                return {"sql_query": None, "results": [], "natural_language_response": nlp_response, "execution_time_ms": 0, "chart_data": None}
            
            # Refresh schema to include any new tables
            self._refresh_schema()
            
            enhanced_query = await self._enhance_with_semantic_search(query)
            sql_query = await self._generate_sql(enhanced_query, conversation_history)
            logger.info(f"Generated SQL: {sql_query}")
            
            # Normalize SQL before validation
            sql_normalized = ' '.join(sql_query.split())
            
            if not self.db.validate_sql(sql_normalized):
                logger.warning("SQL validation failed, attempting fix...")
                sql_query = self._attempt_sql_fix(sql_query)
                sql_normalized = ' '.join(sql_query.split())
                if not self.db.validate_sql(sql_normalized):
                    logger.error(f"Failed SQL: {sql_normalized}")
                    raise Exception("SQL validation failed")
            
            start_time = datetime.now()
            try:
                results = self.db.execute_query(sql_query)
                execution_time = (datetime.now() - start_time).total_seconds() * 1000.0
                serialized_results = self._serialize_results(results)
                explanation = await self._generate_explanation(query, sql_query, serialized_results)
                chart_data = self._detect_chart_request(query, serialized_results)
                
                return {"sql_query": sql_query, "results": serialized_results, "natural_language_response": explanation, "execution_time_ms": execution_time, "chart_data": chart_data}
            except Exception as sql_error:
                logger.error(f"SQL execution failed: {sql_error}")
                # Generate a fallback response using LLM
                fallback_response = await self._generate_fallback_response(query, str(sql_error))
                return {"sql_query": sql_query, "results": [], "natural_language_response": fallback_response, "execution_time_ms": 0, "chart_data": None}
        except Exception as e:
            logger.error(f"Error: {e}")
            raise

    async def _generate_sql(self, query: str, conversation_history: List[Dict[str, str]] = None) -> str:
        schema_context = self._build_schema_context()
        history_context = ""
        if conversation_history:
            history_context = "\nPrevious:\n"
            for msg in conversation_history[-3:]:
                history_context += f"- {msg.get('query', '')}\n"
        
        prompt = f"""You are a MySQL expert. Convert this natural language question into a SQL query.

{schema_context}

CRITICAL RULES:
1. Output ONLY ONE SQL query (no explanations, no markdown, no code blocks)
2. Do NOT use backticks around column/table names (they are added automatically)
3. Always include LIMIT 1000
4. For date filtering use: DATE(column) >= DATE_SUB(CURDATE(), INTERVAL N DAY)
5. For durations use: COALESCE(duration_minutes, TIMESTAMPDIFF(MINUTE, start_time, end_time))
6. For aggregations always use GROUP BY
7. SQL must start with SELECT keyword
8. NEVER generate SQL like "SELECT 'Pie Chart'" - always query actual data from tables
9. For chart requests, generate SQL that returns the actual data needed for the chart
10. NEVER use semicolons or multiple statements - output only ONE SELECT statement

EXAMPLES:
Q: Top 5 assets by trips
A: SELECT Asset Name, Total Trips FROM Mining_Production_Site ORDER BY Total Trips DESC LIMIT 5

Q: Downtime last week
A: SELECT Asset Name, SUM(duration_minutes) as total FROM Factory_Equipment_Logs WHERE status='inactive' AND DATE(date) >= DATE_SUB(CURDATE(), INTERVAL 7 DAY) GROUP BY Asset Name ORDER BY total DESC LIMIT 1000

Q: Daily active vs inactive time for last 27 days
A: SELECT DATE(date) as day, status, SUM(duration_minutes) as minutes FROM Factory_Equipment_Logs WHERE DATE(date) >= DATE_SUB(CURDATE(), INTERVAL 27 DAY) GROUP BY DATE(date), status ORDER BY day, status LIMIT 1000

Q: How many INACTIVE episodes were < 60 seconds?
A: SELECT COUNT(*) AS episode_count FROM Factory_Equipment_Logs WHERE status = 'Inactive' AND duration_minutes < 1 LIMIT 1000

Q: Pie chart of active vs inactive equipment
A: SELECT status, COUNT(*) as count FROM Factory_Equipment_Logs GROUP BY status LIMIT 1000

Q: Pie chart of downtime reasons
A: SELECT reason, SUM(duration_minutes) as total_downtime FROM Factory_Equipment_Logs WHERE status='Inactive' GROUP BY reason ORDER BY total_downtime DESC LIMIT 1000

{history_context}

USER QUESTION: {query}

SQL QUERY:"""
        
        try:
            response = await self.llm.apredict(prompt)
            sql_clean = self._clean_sql_response(response)
            sql_final = self._wrap_identifiers(sql_clean)
            logger.info(f"Cleaned: {sql_final}")
            return sql_final
        except Exception as e:
            logger.error(f"SQL gen failed: {e}")
            raise

    def _clean_sql_response(self, response: str) -> str:
        sql = response.strip()
        sql = sql.replace('``````', '')
        lines = [line.strip() for line in sql.split('\n') if line.strip() and not line.strip().startswith('#') and not line.strip().startswith('--')]
        sql = ' '.join(lines)
        sql = sql.rstrip(';').strip().replace('`', '')
        
        # Handle multiple SQL statements - take only the first one
        if ';' in sql:
            sql = sql.split(';')[0].strip()
            logger.warning(f"Multiple SQL statements detected, using first one: {sql}")
        
        return sql

    def _attempt_sql_fix(self, sql: str) -> str:
        # Normalize whitespace
        sql = ' '.join(sql.split())
        
        # Check for invalid SQL patterns
        if sql.upper().startswith("SELECT '") or "SELECT 'Pie Chart'" in sql.upper():
            logger.warning(f"Detected invalid SQL pattern: {sql}")
            return "SELECT status, COUNT(*) as count FROM `Factory_Equipment_Logs` GROUP BY status LIMIT 1000"
        
        # Ensure starts with SELECT
        if not sql.upper().startswith('SELECT'):
            return "SELECT * FROM `Factory_Equipment_Logs` LIMIT 1000"
        
        # Add LIMIT if missing
        if 'LIMIT' not in sql.upper():
            sql += ' LIMIT 1000'
        
        # Re-wrap identifiers
        sql = self._wrap_identifiers(sql)
        
        return sql

    async def _generate_explanation(self, query: str, sql: str, results: List[Dict]) -> str:
        count = len(results)
        if count == 0:
            return f"No results found for: '{query}'"
        
        # Check for NULL handling in rankings/counts
        null_note = self._check_null_handling(query, sql, results)
        
        summary = str(results[:5]) if count <= 5 else f"{count} records. Sample: {results[:3]}"
        prompt = f"Explain in 2-3 sentences.\nQuestion: {query}\nData ({count} rows): {summary}\nExplanation:"
        try:
            explanation = await self.llm.apredict(prompt)
            if null_note:
                explanation += f" {null_note}"
            return explanation.strip()
        except Exception as e:
            logger.error(f"Explanation failed: {e}")
            base_response = f"Query returned {count} results."
            if null_note:
                base_response += f" {null_note}"
            return base_response
    
    def _check_null_handling(self, query: str, sql: str, results: List[Dict]) -> str:
        """Check if NULL values need special handling in rankings/counts"""
        try:
            query_lower = query.lower()
            sql_lower = sql.lower()
            
            # Check if this is a ranking/top/highest query
            is_ranking_query = any(keyword in query_lower for keyword in [
                'top', 'highest', 'maximum', 'max', 'best', 'largest', 'greatest'
            ])
            
            # Check if this is a counting query
            is_counting_query = any(keyword in query_lower for keyword in [
                'count', 'how many', 'number of', 'total number'
            ])
            
            if not (is_ranking_query or is_counting_query) or not results:
                return ""
            
            # Check if first result has NULL values in key columns
            first_result = results[0]
            null_columns = []
            
            for key, value in first_result.items():
                if value is None or (isinstance(value, str) and value.lower() in ['null', 'none', '']):
                    null_columns.append(key)
            
            if null_columns:
                if is_ranking_query:
                    return f"Note: NULL values were found in the top result for columns: {', '.join(null_columns)}. The displayed result may not represent the actual highest value."
                elif is_counting_query:
                    return f"Note: NULL values are included in the count for columns: {', '.join(null_columns)}."
            
            return ""
            
        except Exception as e:
            logger.error(f"NULL handling check failed: {e}")
            return ""

    def _detect_chart_request(self, query: str, results: List[Dict]) -> Optional[Dict]:
        if not results or len(results) == 0:
            return None
        query_lower = query.lower()
        if any(word in query_lower for word in ['pie', 'percentage', '%']):
            return self._format_chart_data(results, 'pie')
        if any(word in query_lower for word in ['bar', 'top', 'compare', 'stacked']):
            return self._format_chart_data(results, 'bar')
        if any(word in query_lower for word in ['line', 'trend', 'over time']):
            return self._format_chart_data(results, 'line')
        return None

    def _format_chart_data(self, results: List[Dict], chart_type: str) -> Optional[Dict]:
        if not results or len(results) == 0:
            return None
        keys = list(results[0].keys())
        if len(keys) < 1:
            return None
        label_key = keys[0]
        value_key = keys[-1] if len(keys) > 1 else keys[0]
        data = []
        for row in results[:20]:
            try:
                data.append({"label": str(row.get(label_key, '')), "value": float(row.get(value_key, 0) or 0)})
            except (ValueError, TypeError):
                continue
        return {"type": chart_type, "data": data}

    def _is_database_query(self, query: str) -> bool:
        """Check if the query is related to database operations"""
        query_lower = query.lower().strip()
        
        # First, check for explicit SQL keywords or database operations
        sql_keywords = [
            'select', 'from', 'where', 'insert', 'update', 'delete', 'create', 'drop',
            'table', 'database', 'row', 'rows', 'column', 'columns', 'query', 'queries',
            'sql', 'join', 'union', 'group by', 'order by', 'having', 'limit', 'offset',
            'distinct', 'count', 'sum', 'avg', 'max', 'min', 'as', 'alias'
        ]
        
        # If query contains SQL keywords, it's definitely database-related
        for keyword in sql_keywords:
            if keyword in query_lower:
                logger.info(f"SQL keyword found: {keyword} in query: {query}")
                return True
        
        # Check for table names or database references
        table_indicators = [
            'table', 'tables', 'database', 'db', 'schema', 'from', 'into', 'mtcars',
            'mining_shift_data', 'factory_equipment_logs', 'mining_production_site'
        ]
        
        for indicator in table_indicators:
            if indicator in query_lower:
                logger.info(f"Table/database indicator found: {indicator} in query: {query}")
                return True
        
        # List of non-database related patterns (more specific)
        non_db_patterns = [
            # Abusive/inappropriate content (expanded)
            r'\b(fuck|shit|damn|hell|bitch|asshole|stupid|idiot|moron|kill|die|death|suicide|murder|violence|hate|angry|mad)\b',
            # Random names/people (but not if they're part of a database query)
            r'\b(john|jane|mike|sarah|alex|chris|david|emma|james|lisa|brother|sister|mom|dad|mother|father)\b(?!.*from|.*table|.*select)',
            # General greetings (without database context)
            r'\b(hello|hi|hey|good morning|good afternoon|good evening|greetings|howdy)\b(?!.*equipment|.*production|.*downtime|.*data|.*analysis|.*from|.*table)',
            # Weather
            r'\b(weather|rain|sunny|cloudy|temperature|hot|cold|snow|wind|storm)\b(?!.*from|.*table)',
            # Time/date without context
            r'\b(what time|what date|today|tomorrow|yesterday)\b(?!.*equipment|.*production|.*downtime|.*from|.*table)',
            # General questions
            r'\b(how are you|who are you|what are you|tell me about yourself|what can you do)\b',
            # Random topics (but not if they're part of a database query)
            r'\b(cooking|sports|music|movie|book|game|travel|food|recipe|restaurant|car|house|home|family|friend|love|relationship)\b(?!.*from|.*table)',
            # Mathematical operations without context
            r'\b(calculate|math|add|subtract|multiply|divide|plus|minus|times)\b(?!.*equipment|.*production|.*downtime|.*from|.*table)',
            # Emotional/psychological content
            r'\b(sad|happy|depressed|anxious|worried|scared|afraid|lonely|tired|exhausted|stressed)\b',
            # Random requests
            r'\b(help me|save me|rescue me|please help|can you help|i need help)\b(?!.*equipment|.*production|.*downtime|.*from|.*table)',
            # Nonsensical or random phrases
            r'\b(asdf|qwerty|random|nonsense|gibberish|test|testing|hello world)\b',
        ]
        
        # Check for non-database patterns
        for pattern in non_db_patterns:
            if re.search(pattern, query_lower):
                logger.info(f"Non-database pattern matched: {pattern} for query: {query}")
                return False
        
        # List of database-related keywords
        db_keywords = [
            'equipment', 'production', 'downtime', 'status', 'active', 'inactive',
            'factory', 'machine', 'log', 'data', 'analysis', 'report', 'performance',
            'efficiency', 'maintenance', 'breakdown', 'alert', 'reason', 'duration',
            'time', 'date', 'count', 'sum', 'average', 'total', 'show', 'list',
            'find', 'get', 'how many', 'what is', 'which', 'when', 'where',
            'mining', 'shift', 'trip', 'asset', 'site', 'operation', 'oee'
        ]
        
        # Check if query contains database-related keywords
        for keyword in db_keywords:
            if keyword in query_lower:
                logger.info(f"Database keyword found: {keyword} in query: {query}")
                return True
        
        # Additional checks for obviously non-database queries
        # Check for very short queries that are likely conversational
        if len(query.split()) <= 2:
            # If it's a very short query without any database context, it's likely not database-related
            db_context_words = ['equipment', 'production', 'downtime', 'status', 'active', 'inactive', 
                              'factory', 'machine', 'log', 'data', 'analysis', 'report', 'performance',
                              'efficiency', 'maintenance', 'breakdown', 'alert', 'reason', 'duration',
                              'mining', 'shift', 'trip', 'asset', 'site', 'operation', 'oee']
            if not any(word in query_lower for word in db_context_words):
                logger.info(f"Short query without DB context: {query}")
                return False
        
        # Check for queries that are clearly conversational or emotional
        conversational_indicators = ['please', 'thank you', 'thanks', 'sorry', 'excuse me', 'pardon me']
        if any(indicator in query_lower for indicator in conversational_indicators):
            # Only consider it database-related if it also contains database keywords
            if not any(keyword in query_lower for keyword in db_keywords):
                logger.info(f"Conversational query without DB context: {query}")
                return False
        
        # If we get here, it's likely not a database query
        logger.info(f"No database context found for query: {query}")
        return False
    
    async def _generate_nlp_only_response(self, query: str) -> str:
        """Generate a natural language response for non-database queries"""
        query_lower = query.lower().strip()
        
        # Check for inappropriate or concerning content
        concerning_patterns = [
            r'\b(kill|die|death|suicide|murder|violence|hate|angry|mad|hurt|harm)\b',
            r'\b(depressed|sad|lonely|tired|exhausted|stressed|anxious|worried|scared|afraid)\b'
        ]
        
        is_concerning = any(re.search(pattern, query_lower) for pattern in concerning_patterns)
        
        if is_concerning:
            return "I'm CogniMine, your mining operations assistant. I'm here to help with equipment performance, downtime analysis, and production data. If you're experiencing difficulties, please consider reaching out to appropriate support resources. How can I assist you with your mining operations today?"
        
        # Check for general greetings
        greeting_patterns = [
            r'\b(hello|hi|hey|good morning|good afternoon|good evening|greetings|howdy)\b'
        ]
        
        is_greeting = any(re.search(pattern, query_lower) for pattern in greeting_patterns)
        
        if is_greeting:
            return "Hello! I'm CogniMine, your intelligent mining operations assistant. I can help you analyze equipment performance, downtime patterns, and production data. What would you like to know about your mining operations?"
        
        # Default response for other non-database queries
        prompt = f"""You are CogniMine, an intelligent mining operations assistant. The user asked: "{query}"

This query doesn't appear to be related to mining operations, equipment data, or production analysis. 

Please provide a friendly, helpful response that:
1. Acknowledges their question politely
2. Gently redirects them to mining operations topics
3. Suggests some example questions they could ask about equipment performance, downtime analysis, or production data

Be professional but friendly. Keep the response concise (2-3 sentences)."""
        
        try:
            response = await self.llm.apredict(prompt)
            return response.strip()
        except Exception as e:
            logger.error(f"Failed to generate NLP-only response: {e}")
            return "I'm CogniMine, your mining operations assistant! I specialize in helping with equipment performance, downtime analysis, and production data. Could you ask me something about your mining operations instead?"

    async def _generate_fallback_response(self, query: str, error_message: str) -> str:
        """Generate a fallback response when SQL execution fails"""
        try:
            prompt = f"""The user asked: "{query}"

However, there was a database error: {error_message}

Please provide a helpful response explaining that the specific data requested might not be available in the current database schema, and suggest alternative queries they could try. Be helpful and suggest what data IS available.

Available tables:
- Factory_Equipment_Logs (equipment status, downtime reasons, durations)
- Mining_Shift_Data (shift data, trip counts)
- Mining_Production_Site (production data, asset information)

Response:"""
            
            response = await self.llm.apredict(prompt)
            return response.strip()
        except Exception as e:
            logger.error(f"Fallback response generation failed: {e}")
            return f"I encountered an error processing your query: '{query}'. The database error was: {error_message}. Please try rephrasing your question or ask about data that's available in the Factory_Equipment_Logs, Mining_Shift_Data, or Mining_Production_Site tables."
