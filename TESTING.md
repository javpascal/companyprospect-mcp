# Testing Guide for MCP Server

This guide shows multiple ways to test your MCP server without going through Claude.

## Quick Testing Options

### 1. 🚀 Interactive Testing (Recommended)

The easiest way with a menu-driven interface:

```bash
python3 test_interactive.py https://your-app.vercel.app YOUR_API_KEY
```

Or run without arguments for interactive prompts:
```bash
python3 test_interactive.py
```

Features:
- Interactive menu system
- Test individual endpoints
- Run all tests at once
- Custom MCP method calls
- Pretty-printed results

### 2. 🧪 Quick Shell Script

For rapid testing with bash:

```bash
./test_quick.sh https://your-app.vercel.app YOUR_API_KEY
```

This runs through all endpoints automatically and shows formatted output.

### 3. 📝 Comprehensive Python Test

For detailed testing with full output:

```bash
python3 test_oauth.py https://your-app.vercel.app YOUR_API_KEY
```

### 4. 🛠️ Manual cURL Commands

Test individual endpoints directly:

#### Health Check
```bash
curl https://your-app.vercel.app/health | python3 -m json.tool
```

#### Get OAuth Token
```bash
curl -X POST https://your-app.vercel.app/token \
  -H "Content-Type: application/x-www-form-urlencoded" \
  -d "grant_type=authorization_code&code=test&client_secret=YOUR_API_KEY"
```

#### Initialize MCP (use token from above)
```bash
curl -X POST https://your-app.vercel.app \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer YOUR_API_KEY" \
  -d '{"jsonrpc":"2.0","id":1,"method":"initialize","params":{"protocolVersion":"2024-11-05"}}'
```

#### List Tools
```bash
curl -X POST https://your-app.vercel.app \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer YOUR_API_KEY" \
  -d '{"jsonrpc":"2.0","id":2,"method":"tools/list","params":{}}'
```

#### Call a Tool
```bash
curl -X POST https://your-app.vercel.app \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer YOUR_API_KEY" \
  -d '{"jsonrpc":"2.0","id":3,"method":"tools/call","params":{"name":"company_typeahead","arguments":{"query":"Microsoft"}}}'
```

## Local Development Testing

For local testing with Vercel:

```bash
# Install Vercel CLI if not already installed
npm i -g vercel

# Run locally
vercel dev

# Then test against http://localhost:3000
python3 test_interactive.py http://localhost:3000 YOUR_API_KEY
```

## Environment Variables

You can set your API key as an environment variable to avoid typing it:

```bash
export API_KEY=your-api-key-here
python3 test_interactive.py https://your-app.vercel.app
```

## Expected Test Results

✅ **Successful tests should show:**
- Health endpoint returns server status
- Token exchange returns access_token
- Initialize returns server info
- Tools list shows 2 tools (company_typeahead, find_competitors)
- Tool calls return data from the Nummary API

❌ **Common issues:**
- Missing API key → Authentication error
- Wrong URL → Connection error
- Invalid API key → API error responses

## Debugging Tips

1. Check the health endpoint first - it shows if auth is configured
2. Use the interactive tester to test step by step
3. Check Vercel function logs for server-side errors
4. Ensure your API key is valid for the Nummary API

## Quick Test Command

For the fastest test of everything working:

```bash
# This one command tests the full flow
curl -s https://your-app.vercel.app/health | grep '"ready": true' && echo "✅ Server is ready!" || echo "❌ Server not ready"
```
