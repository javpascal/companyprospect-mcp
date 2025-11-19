#!/bin/bash

# Quick test script for MCP OAuth flow
# Usage: ./test_quick.sh <server_url> <api_key>

SERVER_URL="${1:-http://localhost:3000}"
API_KEY="${2:-your-api-key-here}"

echo "🧪 Testing MCP Server at: $SERVER_URL"
echo "📝 Using API Key: ${API_KEY:0:4}***${API_KEY: -4}"
echo "================================================"

# Test 1: Health check
echo -e "\n✅ 1. Health Check:"
curl -s "$SERVER_URL/health" | python3 -m json.tool

# Test 2: Get OAuth token
echo -e "\n🔐 2. Getting OAuth Token:"
TOKEN_RESPONSE=$(curl -s -X POST "$SERVER_URL/token" \
  -H "Content-Type: application/x-www-form-urlencoded" \
  -d "grant_type=authorization_code&code=test&client_secret=$API_KEY")

echo "$TOKEN_RESPONSE" | python3 -m json.tool

# Extract token
ACCESS_TOKEN=$(echo "$TOKEN_RESPONSE" | python3 -c "import sys, json; print(json.load(sys.stdin).get('access_token', ''))")

if [ -z "$ACCESS_TOKEN" ]; then
  echo "❌ Failed to get access token"
  exit 1
fi

echo "✅ Got access token!"

# Test 3: Initialize MCP
echo -e "\n🚀 3. Initialize MCP:"
curl -s -X POST "$SERVER_URL" \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer $ACCESS_TOKEN" \
  -d '{
    "jsonrpc": "2.0",
    "id": 1,
    "method": "initialize",
    "params": {"protocolVersion": "2024-11-05"}
  }' | python3 -m json.tool

# Test 4: List tools
echo -e "\n🛠️ 4. List Available Tools:"
curl -s -X POST "$SERVER_URL" \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer $ACCESS_TOKEN" \
  -d '{
    "jsonrpc": "2.0",
    "id": 2,
    "method": "tools/list",
    "params": {}
  }' | python3 -m json.tool

# Test 5: Call a tool
echo -e "\n🔍 5. Testing Tool Call (company_typeahead):"
RESULT=$(curl -s -X POST "$SERVER_URL" \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer $ACCESS_TOKEN" \
  -d '{
    "jsonrpc": "2.0",
    "id": 3,
    "method": "tools/call",
    "params": {
      "name": "company_typeahead",
      "arguments": {"query": "Microsoft"}
    }
  }')

# Pretty print the result
echo "$RESULT" | python3 -c "
import sys, json
data = json.load(sys.stdin)
if 'result' in data and 'content' in data['result']:
    content = data['result']['content'][0]['text']
    try:
        parsed = json.loads(content)
        print(json.dumps(parsed, indent=2)[:500] + '...' if len(json.dumps(parsed)) > 500 else json.dumps(parsed, indent=2))
    except:
        print(content[:500] + '...' if len(content) > 500 else content)
else:
    print(json.dumps(data, indent=2))
"

echo -e "\n✅ Test complete!"
