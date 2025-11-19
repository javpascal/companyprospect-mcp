# Claude Desktop Configuration

## Method 1: Set API Key in Vercel (Simplest for Claude Desktop)

Since Claude Desktop doesn't properly pass URL parameters through SSE connections, the most reliable method is:

1. **Set your API key in Vercel:**
   - Go to Vercel Dashboard → Settings → Environment Variables
   - Add: `API_KEY = nm_9xxxxx` (your full Nummary API key)
   - Redeploy the project

2. **Configure Claude Desktop:**
   
   Find your Claude Desktop config file:
   - **macOS**: `~/Library/Application Support/Claude/claude_desktop_config.json`
   - **Windows**: `%APPDATA%\Claude\claude_desktop_config.json`
   - **Linux**: `~/.config/Claude/claude_desktop_config.json`

   Add this configuration:
   ```json
   {
     "mcpServers": {
       "nummary": {
         "url": "https://companyprospect-mcp.vercel.app/sse"
       }
     }
   }
   ```

3. **Restart Claude Desktop**

## Method 2: Use a Local Proxy (If You Want Per-User Keys)

If you need each user to have their own API key without setting it in Vercel, you need a local proxy:

1. **Install mcp-server-sse:**
   ```bash
   npm install -g @modelcontextprotocol/server-sse
   ```

2. **Configure Claude Desktop:**
   ```json
   {
     "mcpServers": {
       "nummary": {
         "command": "npx",
         "args": [
           "@modelcontextprotocol/server-sse",
           "https://companyprospect-mcp.vercel.app?api_key=YOUR_API_KEY_HERE"
         ]
       }
     }
   }
   ```

## Method 3: URL Parameter (Test if it works)

Try this configuration with your API key in the URL:
```json
{
  "mcpServers": {
    "nummary": {
      "url": "https://companyprospect-mcp.vercel.app?api_key=nm_9xxxxx"
    }
  }
}
```

Then check Vercel logs to see if the API key is being received.

## Troubleshooting

### Check Vercel Logs
1. Go to Vercel Dashboard → Functions → Logs
2. Look for `[DEBUG]` messages
3. You should see:
   - `[DEBUG] GET request has api_key in query` (if URL params work)
   - `[DEBUG] Found API key in...` (shows where key was found)
   - `[DEBUG] NO API KEY FOUND ANYWHERE!` (if key isn't reaching server)

### Common Issues

**"Authentication required" error:**
- Claude Desktop might not be passing the URL parameters
- Solution: Use Method 1 (Vercel environment variable)

**Connection fails:**
- Make sure the URL is exactly correct
- Try adding `/sse` to the end: `https://companyprospect-mcp.vercel.app/sse`

## Why URL Parameters Don't Work Well in Claude Desktop

Claude Desktop establishes an SSE (Server-Sent Events) connection:
1. Initial GET request might have the API key in URL
2. But subsequent POST requests for MCP methods don't preserve it
3. The Referer header might not be set consistently

This is why setting the API key in Vercel environment variables is the most reliable method for Claude Desktop.
