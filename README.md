# MCP Server for Nummary API

A Python-based Model Context Protocol (MCP) server for the Nummary API, deployed on Vercel with OAuth authentication support.

## Features

- **`company_typeahead`**: Search for companies by name.
- **`find_competitors`**: Find competitors based on context.
- **OAuth Authentication**: Secure API key handling through OAuth flow
- **Health Check Endpoint**: Verify server status and authentication

## Setup

### Environment Variables (Optional)

You can configure these in your Vercel project settings as a fallback:

- `API_KEY`: Your Nummary API key (optional if using OAuth)
- `API_URL`: API URL (defaults to `https://api.nummary.co`)

### Configuring in Claude Desktop

1. Open Claude Desktop
2. Click on "Add custom connector" 
3. Fill in the following:
   - **Name**: `Nummary API` (or any name you prefer)
   - **Remote MCP server URL**: Your Vercel deployment URL (e.g., `https://your-app.vercel.app`)
   - **OAuth Client ID**: Leave empty or enter any value
   - **OAuth Client Secret**: **Enter your Nummary API key here**

The API key you enter in the OAuth Client Secret field will be securely passed through the OAuth flow and used to authenticate your API requests.

### OAuth Flow Details

The server implements a simplified OAuth 2.0 flow:

1. **Authorization**: `/authorize` endpoint automatically approves and redirects
2. **Token Exchange**: `/token` endpoint exchanges the client secret (your API key) for an access token
3. **Authentication**: The access token is then used as a Bearer token for all MCP requests

### Testing the Connection

You can verify the server is working by visiting the health check endpoint:

```bash
curl https://your-app.vercel.app/health
```

This will return the server status and authentication state.

### Local Development

1. Clone the repo
2. Create a `.env` file with your credentials (optional):
   ```
   API_KEY=your-api-key
   API_URL=https://api.nummary.co
   ```
3. Install dependencies: `pip install -r requirements.txt`
4. Run locally: `vercel dev` or adapt for local testing

## Troubleshooting

### OAuth Not Working

If the OAuth flow is not working:

1. Check that you've entered your API key in the "OAuth Client Secret" field in Claude
2. Verify your Vercel deployment is running (check the `/health` endpoint)
3. Check the Vercel function logs for any error messages
4. Ensure CORS is not blocking requests (the server includes proper CORS headers)

### API Key Issues

The server supports two authentication methods:
- **OAuth Flow** (recommended): API key passed via OAuth Client Secret in Claude
- **Environment Variable**: API_KEY set in Vercel (fallback method)

The OAuth method is preferred as it allows you to securely manage your API key directly in Claude.

## Deployment

Push to the `main` branch to trigger a Vercel deployment. The server will automatically be available at your Vercel URL.