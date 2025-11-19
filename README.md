# Nummary MCP Server

A Model Context Protocol (MCP) server for the Nummary API, deployed on Vercel.

## Quick Setup

### 1. Get Your Nummary API Key

1. Log in to Nummary at [https://app.nummary.co/login/](https://app.nummary.co/login/)
2. In your browser's developer console (F12), run:
   ```javascript
   document.cookie.split(';').find(c => c.trim().startsWith('AUTH_APIKEY='))?.split('=')[1]
   ```
3. Copy the API key that appears

### 2. Deploy to Vercel

1. Deploy this project to Vercel
2. In Vercel dashboard, go to **Project Settings → Environment Variables**
3. Add: `API_KEY` = `your-nummary-api-key`
4. Redeploy for changes to take effect

### 3. Configure in Claude Desktop

Add to your Claude Desktop configuration:

```json
{
  "mcpServers": {
    "nummary": {
      "url": "https://your-project.vercel.app"
    }
  }
}
```

**Note**: If Claude tries to use Vercel OAuth (shows Vercel login), you may need to use a custom domain or alternative deployment platform.

## Features

### MCP Tools Available

- **`company_typeahead`**: Search for companies by name
  ```json
  {"query": "Microsoft"}
  ```

- **`find_competitors`**: Find competitors based on companies and keywords
  ```json
  {
    "context": [
      {"type": "company", "text": "Microsoft"},
      {"type": "keyword", "text": "cloud computing"}
    ]
  }
  ```

## Local Development

```bash
# Install dependencies
pip install -r requirements.txt

# Set environment variable
export API_KEY=your-nummary-api-key

# Run with Vercel
vercel dev
```

## Troubleshooting

### Vercel OAuth Redirect Issue
If Claude Desktop shows a Vercel login screen instead of connecting directly:
- This happens because Claude detects `.vercel.app` domains
- Solution: Use a custom domain or deploy to a different platform

### API Key Not Working
- Ensure you copied the complete API key from the cookie
- Verify the API key is correctly set in Vercel environment variables
- Check that your Nummary account has API access enabled

### Getting Your API Key from Nummary
After logging into Nummary, the `AUTH_APIKEY` cookie contains your API key. You can extract it using the browser console command provided above.

## Architecture

This server:
1. Receives MCP requests from Claude
2. Authenticates using the API key from environment variables
3. Forwards requests to Nummary API
4. Returns formatted responses to Claude

## Security

- API key is stored securely in Vercel environment variables
- All API calls use HTTPS
- No credentials are logged or exposed

## License

MIT