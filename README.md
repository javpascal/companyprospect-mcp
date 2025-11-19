# Nummary MCP Server

A Model Context Protocol (MCP) server for the Nummary API where each user provides their own API key.

## How It Works

Each user provides their own Nummary API key when configuring the connection in Claude. The server uses this key for all API calls during their session.

## Setup Instructions

### 1. Deploy to Vercel

Deploy this project to Vercel:
```bash
git push origin main
```

Your server will be available at: `https://your-project.vercel.app`

### 2. Get Your Nummary API Key

Each user needs their own Nummary API key:

1. Log in to Nummary at [https://app.nummary.co/login/](https://app.nummary.co/login/)
2. Open browser developer console (F12)
3. Run this command to extract your API key:
   ```javascript
   document.cookie.split(';').find(c => c.trim().startsWith('AUTH_APIKEY='))?.split('=')[1]
   ```
4. Copy the API key that appears

### 3. Configure in Claude Desktop

Each user configures their own connection:

1. Open Claude Desktop
2. Go to Settings → Developer → Edit Config
3. Add this configuration:

```json
{
  "mcpServers": {
    "nummary": {
      "url": "https://your-project.vercel.app",
      "auth": {
        "type": "oauth",
        "client_id": "user",
        "client_secret": "YOUR_NUMMARY_API_KEY_HERE"
      }
    }
  }
}
```

**Important**: Replace `YOUR_NUMMARY_API_KEY_HERE` with your actual Nummary API key from step 2.

## Available Tools

### company_typeahead
Search for companies by name:
```json
{
  "query": "Microsoft"
}
```

### find_competitors
Find competitors based on companies and keywords:
```json
{
  "context": [
    {"type": "company", "text": "Microsoft"},
    {"type": "keyword", "text": "cloud computing"}
  ]
}
```

## How Authentication Works

1. **User provides API key**: Each user enters their Nummary API key in the `client_secret` field
2. **OAuth flow**: The server implements a simplified OAuth flow that accepts the API key
3. **Per-session authentication**: Each Claude session uses the user's own API key
4. **No shared credentials**: No API keys are stored on the server

## Troubleshooting

### "Authentication required" error
- Make sure you've entered your API key in the `client_secret` field
- Verify your API key is correct (copy it again from Nummary)

### Getting your API key
- The API key is in the `AUTH_APIKEY` cookie after logging into Nummary
- Use the browser console command provided above to extract it

### Vercel OAuth redirect
If Claude shows a Vercel login screen:
- Make sure you're using the configuration format shown above
- The `auth` section with `client_secret` is required

## Local Development

```bash
# Install dependencies
pip install -r requirements.txt

# Run with Vercel (no API key needed - users provide their own)
vercel dev
```

## Security

- **User-specific keys**: Each user provides their own API key
- **No server storage**: API keys are never stored on the server
- **Session-based**: Keys are only used for the duration of the Claude session
- **HTTPS only**: All communication is encrypted

## Optional: Fallback API Key

If you want to provide a default API key (for testing or shared use), you can set it in Vercel:
- Add `API_KEY` environment variable in Vercel settings
- This will be used only if a user doesn't provide their own key

## License

MIT