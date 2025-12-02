# CompanyProspect MCP Server

A Model Context Protocol (MCP) server for the CompanyProspect API where each user provides their own API Key.

## Setup for Claude Desktop

Since Claude Desktop doesn't properly pass URL query parameters through SSE connections, embed your API Key in the URL path:

### 1. Deploy to Vercel

```bash
git push origin main
```

### 2. Get Your CompanyProspect Key

Log in to [CompanyProspect](https://companyprospect.co/account) and run this in browser console:
```javascript
document.cookie.split(';').find(c => c.trim().startsWith('AUTH_API_KEY='))?.split('=')[1]
```

### 3. Configure Claude Desktop

Find your Claude Desktop config file:
- **macOS**: `~/Library/Application Support/Claude/claude_desktop_config.json`
- **Windows**: `%APPDATA%\Claude\claude_desktop_config.json`
- **Linux**: `~/.config/Claude/claude_desktop_config.json`

Add your configuration with your API Key **in the URL path**:

```json
{
  "mcpServers": {
    "companyprospect": {
      "url": "https://companyprospect-mcp.vercel.app/abcd123xxx"
    }
  }
}
```

Replace `abcd123xxx` with your actual full CompanyProspect API Key.

### 4. Restart Claude Desktop

Close and reopen Claude Desktop for the changes to take effect.

## How It Works

- **Path-based API Key**: Your API Key is embedded in the URL path (e.g., `/abcd123xxx`)
- **Per-user authentication**: Each user configures their own API Key
- **No shared credentials**: No environment variables or shared keys on the server
- **Claude Desktop compatible**: Path segments are preserved through SSE connections

## Available Tools

### company_typeahead
Search for companies by name:
```
"Search for Microsoft"
```

### find_competitors
Find competitors based on companies and keywords:
```
"Find competitors of Microsoft in cloud computing"
```

## Troubleshooting

### Check Vercel Logs
1. Go to Vercel Dashboard → Functions → Logs
2. Look for `[DEBUG]` messages:
   - `[DEBUG] Found API Key in path: /nm_9xxx***` - Good! API Key is being received
   - `[DEBUG] POST: NO API Key FOUND!` - API Key isn't reaching the server

### Common Issues

**"Authentication required" error:**
- Make sure your API key is in the URL path, not as a query parameter
- Format: `https://companyprospect-mcp.vercel.app/abcd123xxx`
- NOT: `https://companyprospect-mcp.vercel.app?api_key=abcd123xxx`

**Connection fails:**
- Ensure you're using the full API key, not truncated
- Restart Claude Desktop after config changes

## For Web-based Claude

If using Claude in a web browser instead of desktop app, try:

```json
{
  "mcpServers": {
    "companyprospect": {
      "url": "https://companyprospect-mcp.vercel.app?api_key=abcd123xxx"
    }
  }
}
```

## Security Notes

- API keys are visible in Claude's configuration file
- Each user manages their own API key
- No keys are stored on the server
- Keys are only used for the duration of the session

## Local Development

```bash
# Install dependencies
pip install -r requirements.txt

# Test locally with your API key
export API_KEY=abcd123xxx
vercel dev
```

## License

MIT