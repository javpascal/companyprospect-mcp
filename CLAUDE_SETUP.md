# Claude MCP Configuration Guide

## Important: Avoiding Vercel OAuth Redirect

When adding this MCP server to Claude, you might encounter a Vercel OAuth consent screen. This happens when Claude detects a Vercel URL and tries to use Vercel's platform authentication instead of our custom OAuth flow.

## Solution Options

### Option 1: Use Custom Domain (Recommended)
If you have a custom domain, configure it in Vercel:
1. Go to your Vercel project settings
2. Add a custom domain
3. Use that domain in Claude instead of the `.vercel.app` URL

### Option 2: Direct Configuration
When adding the connector in Claude:

1. **DON'T** click on any Vercel-specific integration options
2. Use the **"Add custom connector"** option specifically
3. Configure as follows:
   - **Name**: `Nummary API`
   - **Remote MCP server URL**: `https://companyprospect-mcp.vercel.app`
   - **OAuth Client ID**: `nummary-client`
   - **OAuth Client Secret**: `placeholder`

### Option 3: Use Environment Variable Authentication
If the OAuth flow continues to redirect to Vercel:

1. Set your API key directly in Vercel environment variables:
   - Go to Vercel project settings
   - Add environment variable: `API_KEY = your-nummary-api-key`
   - Redeploy

2. The server will use this API key for all requests (less secure but simpler)

## Testing Without Claude

To verify your server is working correctly before adding to Claude:

```bash
# Test the authorize endpoint
curl https://companyprospect-mcp.vercel.app/authorize?redirect_uri=http://localhost:8080/callback

# Should return HTML with the login instructions page
```

## If You Still See Vercel OAuth

This means Claude is intercepting the connection. Try:

1. **Clear Claude's cache/cookies** and try again
2. **Use a proxy or tunnel service** like ngrok to mask the Vercel URL:
   ```bash
   ngrok http https://companyprospect-mcp.vercel.app
   ```
   Then use the ngrok URL in Claude instead

3. **Deploy to a different platform** (Railway, Render, etc.)

## Direct API Key Method (Fallback)

If OAuth continues to be problematic, we can simplify to direct API key:

1. Set `API_KEY` in Vercel environment variables
2. Remove OAuth flow from the code
3. Use the server without authentication in Claude

The server will use the environment variable for all API calls.
