# Claude Desktop Configuration

Since Claude Desktop doesn't properly pass URL parameters through SSE connections, the most reliable method is:

## Method 1: URL Parameter (Test if it works)

Try this configuration with your API Key in the URL:
```json
{
  "mcpServers": {
    "nummary": {
      "url": "https://companyprospect-mcp.vercel.app/abcd123xxx"
    }
  }
}
```
### Common Issues

**Connection fails:**
- Make sure the URL is exactly correct, replacing "abcd123xxx" with your API key:
"https://companyprospect-mcp.vercel.app/abcd123xxx"


## Why URL Parameters Don't Work Well in Claude 
Claude Desktop establishes an SSE (Server-Sent Events) connection:
1. Initial GET request might have the API Key in URL
2. But subsequent POST requests for MCP methods don't preserve it
3. The Referer header might not be set consistently

This is why setting the API Key in Vercel environment variables is the most reliable method for Claude Desktop.


## Troubleshooting
1. Email hello@nummary.co