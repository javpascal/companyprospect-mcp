# MCP Server

A Python-based Model Context Protocol (MCP) server for the Nummary API, deployed on Vercel.

## Features

- **`company_typeahead`**: Search for companies by name.
- **`find_competitors`**: Find competitors based on context.

## Setup

### Environment Variables

Configure these in your Vercel project settings:

- `API_KEY`: Your Nummary API key (required)
- `API_URL`: API URL (defaults to `https://api.nummary.co`)

### Local Development

1. Clone the repo
2. Set environment variables:
   ```bash
   export API_KEY=your-api-key
   export API_URL=https://api.nummary.co
   ```
3. Install dependencies: `pip install -r requirements.txt`
4. Run with Vercel: `vercel dev`

## Deployment

Push to the `main` branch to trigger a Vercel deployment.