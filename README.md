# Nummary MCP Server with Interactive Login

A Model Context Protocol (MCP) server for the Nummary API with interactive OAuth authentication, deployed on Vercel.

## Features

- **Interactive Login**: Users authenticate by entering their Nummary API key through a secure web form
- **OAuth 2.0 Flow**: Standard OAuth flow for secure authentication
- **MCP Tools**:
  - `company_typeahead`: Search for companies by name
  - `find_competitors`: Find competitors based on context

## How It Works

### Authentication Flow

1. **User initiates connection** in Claude Desktop
2. **Redirected to login page** where they enter their Nummary API key
3. **API key is securely passed** through OAuth token exchange
4. **Authenticated session** established for all API calls

### Interactive Login Page

When users connect through Claude, they'll see a clean login interface:
- Secure form to enter their Nummary API key
- Link to Nummary if they need to get an API key
- Session-based security for the OAuth flow

## Setup

### Deployment on Vercel

1. **Deploy to Vercel**:
   ```bash
   git push origin main
   ```

2. **Optional Environment Variables**:
   - `API_URL`: Nummary API URL (defaults to `https://api.nummary.co`)
   - `NUMMARY_AUTH_URL`: Link to Nummary login page (defaults to `https://app.nummary.com/login`)
   - `API_KEY`: Fallback API key (optional - users can authenticate interactively)

### Configuring in Claude Desktop

1. Open Claude Desktop
2. Click "Add custom connector"
3. Configure:
   - **Name**: `Nummary API`
   - **Remote MCP server URL**: `https://companyprospect-mcp.vercel.app`
   - **OAuth Client ID**: (leave empty or enter any value)
   - **OAuth Client Secret**: (leave empty - authentication is interactive)

4. When you connect, you'll be redirected to enter your API key

## Local Development

```bash
# Install dependencies
pip install -r requirements.txt

# Run with Vercel
vercel dev

# Access at http://localhost:3000
```

## Security

- API keys are never stored permanently on the server
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

- **Can't connect**: Ensure the server is deployed and accessible
- **Authentication fails**: Check that your API key is valid
- **API errors**: Verify your API key has the necessary permissions

## License

MIT