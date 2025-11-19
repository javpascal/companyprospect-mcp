# Nummary MCP Server

A Model Context Protocol (MCP) server for the Nummary API. Each user provides their own API key.

## Quick Setup

### 1. Deploy to Vercel

```bash
git push origin main
```

### 2. Get Your Nummary API Key

Log in to [Nummary](https://app.nummary.co/login/) and run this in browser console:
```javascript
document.cookie.split(';').find(c => c.trim().startsWith('AUTH_APIKEY='))?.split('=')[1]
```

### 3. Configure in Claude Desktop

Since OAuth doesn't work properly with Vercel URLs in Claude, use one of these methods:

#### Method 1: URL with API Key (Simplest!)
```json
{
  "mcpServers": {
    "nummary": {
      "url": "https://companyprospect-mcp.vercel.app?api_key=YOUR_API_KEY_HERE"
    }
  }
}
```

#### Method 2: Basic Authentication
```json
{
  "mcpServers": {
    "nummary": {
      "url": "https://companyprospect-mcp.vercel.app",
      "auth": {
        "type": "basic",
        "username": "user",
        "password": "YOUR_API_KEY_HERE"
      }
    }
  }
}
```

#### Method 3: Environment Variable (Shared API Key)
Set `API_KEY` in Vercel environment variables, then use:
```json
{
  "mcpServers": {
    "nummary": {
      "url": "https://companyprospect-mcp.vercel.app"
    }
  }
}
```

## Available Tools

### company_typeahead
Search for companies by name:
```
Query: "Microsoft"
```

### find_competitors
Find competitors based on companies and keywords:
```
Context: 
- Company: "Microsoft"
- Keyword: "cloud computing"
```

## Troubleshooting

### Authentication Issues
- **Method 1** (URL param) is the most reliable with Claude
- Check Vercel function logs for debug messages
- Ensure your API key is valid and complete

### Vercel OAuth Redirect
Claude detects Vercel domains and may try to use Vercel's platform OAuth. This is why we use alternative authentication methods above.

## Security Notes

- **Method 1**: API key is visible in Claude's config (okay for personal use)
- **Method 2**: API key is slightly obscured in basic auth
- **Method 3**: API key is stored server-side (best for shared deployments)

Choose based on your security requirements.

## License

MIT