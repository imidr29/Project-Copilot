# NLP Query Filtering Fix

## Problem
The system was generating SQL queries for purely conversational requests like "brother kill me pls" that had no relation to the database. This was causing inappropriate SQL generation and poor user experience.

## Solution
Implemented comprehensive query classification in `langchain_agent.py` to distinguish between database-related and conversational queries.

### Key Changes

1. **Enhanced `_is_database_query()` method**:
   - Added expanded pattern matching for non-database content
   - Improved detection of abusive/inappropriate content
   - Better handling of emotional and conversational queries
   - Reordered logic to check database keywords first

2. **Improved `_generate_nlp_only_response()` method**:
   - Added special handling for concerning content
   - Better responses for greetings and general questions
   - Professional redirection to mining operations topics

3. **Added Token Guard System**:
   - Created `token_guard.py` for API authentication
   - Integrated with FastAPI for optional authentication
   - Added token management endpoints
   - Implemented rate limiting and role-based access

### Non-Database Patterns Detected
- Abusive/inappropriate content (kill, die, violence, etc.)
- Random names/people (john, jane, brother, etc.)
- General greetings (hello, hi, hey, etc.)
- Weather questions
- Emotional content (sad, depressed, etc.)
- Random topics (cooking, sports, music, etc.)
- Mathematical operations without context
- General help requests without database context

### Database Keywords Recognized
- Equipment, production, downtime, status
- Factory, machine, log, data, analysis
- Performance, efficiency, maintenance
- Mining, shift, trip, asset, site, operation, OEE
- Time, date, count, sum, average, total
- Show, list, find, get, how many, what is

## Testing
Created comprehensive test suite that verified:
- ✅ "brother kill me pls" correctly identified as non-database query
- ✅ All abusive/inappropriate content properly filtered
- ✅ Database-related queries still work correctly
- ✅ Edge cases handled properly (greetings with context, etc.)

## Token Guard Features
- Secure token generation and validation
- Role-based access control (admin, user, readonly)
- Rate limiting (100 requests per hour)
- Token expiration and cleanup
- Optional authentication for backward compatibility

## Usage
The system now automatically:
1. Detects non-database queries
2. Provides appropriate conversational responses
3. Only generates SQL for legitimate database queries
4. Supports optional API token authentication

## API Endpoints Added
- `POST /api/tokens` - Create new token (admin only)
- `GET /api/tokens` - List active tokens (admin only)
- `DELETE /api/tokens/{token_id}` - Revoke token (admin only)
- `POST /api/tokens/cleanup` - Clean expired tokens (admin only)
- `GET /api/tokens/default` - Get default tokens for testing

## Result
The system now properly handles both database queries and conversational requests, providing appropriate responses for each type without generating unnecessary SQL queries.

## Update: SQL Query Fix
After initial implementation, the filtering was too aggressive and blocked legitimate SQL queries. Fixed by:

1. **Prioritizing SQL keyword detection**: Added explicit SQL keywords (`select`, `from`, `where`, `row`, `table`, etc.) that immediately identify database queries
2. **Enhanced table name detection**: Added specific table names and database indicators
3. **Refined pattern matching**: Made non-database patterns more specific to avoid false positives
4. **Improved regex patterns**: Added negative lookaheads to prevent blocking queries that contain both conversational and database elements

### Key SQL Keywords Detected
- `select`, `from`, `where`, `insert`, `update`, `delete`
- `table`, `database`, `row`, `rows`, `column`, `columns`
- `query`, `queries`, `sql`, `join`, `union`
- `group by`, `order by`, `having`, `limit`, `offset`
- `distinct`, `count`, `sum`, `avg`, `max`, `min`

### Test Results
- ✅ "select 5th row from mtcars" → Correctly identified as database query
- ✅ "show me 5th row and 8th row from mining shifted" → Correctly identified as database query  
- ✅ "brother kill me pls" → Still correctly filtered as non-database query
- ✅ All SQL-related queries now work properly
