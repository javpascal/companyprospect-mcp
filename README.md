# Nummary MCP Server with Interactive Login

A Model Context Protocol (MCP) server for the Nummary API with interactive authentication via Nummary's login page, deployed on Vercel.

## Features

- **Interactive Nummary Login**: Users authenticate through the official Nummary login page
- **Secure API Key Extraction**: Simple process to get API key from Nummary cookies
- **OAuth 2.0 Flow**: Standard OAuth flow for secure authentication
- **MCP Tools**:
  - `company_typeahead`: Search for companies by name
  - `find_competitors`: Find competitors based on context

## How It Works

### Authentication Flow

1. **User initiates connection** in Claude Desktop
2. **Opens Nummary login page** at [https://app.nummary.co/login/](https://app.nummary.co/login/)
3. **Logs in to Nummary** with their credentials
4. **Extracts API key** from the `AUTH_APIKEY` cookie using provided JavaScript
5. **Enters API key** in the secure form
6. **Authenticated session** established for all API calls

### Step-by-Step Process

When users connect through Claude, they'll see a guided process:

1. **Login to Nummary**: Click to open the Nummary login page in a new tab
2. **Get API Key**: After logging in, run the provided JavaScript snippet in the browser console:
   ```javascript
   document.cookie.split(';').find(c => c.trim().startsWith('AUTH_APIKEY='))?.split('=')[1] || 'API Key not found'
   ```
3. **Connect to Claude**: Paste the API key in the secure form to complete authentication

## Setup

### Deployment on Vercel

1. **Deploy to Vercel**:
   ```bash
   git push origin main
   ```

2. **Optional Environment Variables**:
   - `API_URL`: Nummary API URL (defaults to `https://api.nummary.co`)
   - `API_KEY`: Fallback API key (optional - users authenticate interactively)

### Configuring in Claude Desktop

1. Open Claude Desktop
2. Click "Add custom connector"
3. Configure:
   - **Name**: `Nummary API`
   - **Remote MCP server URL**: `https://companyprospect-mcp.vercel.app`
   - **OAuth Client ID**: (leave empty or enter any value)
   - **OAuth Client Secret**: (leave empty - authentication is interactive)

4. When you connect, follow the step-by-step instructions to authenticate

## Local Development

```bash
# Install dependencies
pip install -r requirements.txt

# Run with Vercel
vercel dev

# Access at http://localhost:3000
```

## Security

- API keys are extracted from secure Nummary cookies
- Keys are never stored permanently on the server
- Session-based authentication with unique session IDs
- Secure OAuth 2.0 token exchange
- HTTPS encryption for all communications

## API Tools

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

## Troubleshooting

### Can't get API key
1. Make sure you're logged into Nummary first
2. Open browser developer console (F12)
3. Run the provided JavaScript snippet
4. The API key should appear - copy it

### Authentication fails
- Verify your API key is valid
- Ensure you're copying the complete API key
- Check that you're logged into Nummary

### API errors
- Verify your Nummary account has API access
- Check that your API key has the necessary permissions

## How the Cookie Extraction Works

After logging into Nummary at [https://app.nummary.co/login/](https://app.nummary.co/login/), Nummary sets two important cookies:
- `AUTH_APIKEY`: Your API key for making API calls
- `AUTH_USER`: Your user information

The provided JavaScript snippet safely extracts the `AUTH_APIKEY` cookie value, which is then used for API authentication.

## License

MIT