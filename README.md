# MCP Server

A Python-based Model Context Protocol (MCP) server for the API, deployed on Vercel.

## Features

- **`company_typeahead`**: Search for companies by name.
- **`find_competitors`**: Find competitors based on context.

## Setup

### Environment Variables

Configure these in your Vercel project settings:

- `API_KEY`: Your API key.
- `API_URL`: Your API URL.

### Local Development

1.  Clone the repo.
2.  Copy `.env.example` to `.env` and fill in your credentials.
3.  Install dependencies: `pip install -r requirements.txt`.
4.  Run with a WSGI server or for testing: `python3 api/index.py` (Note: `api/index.py` is designed for Vercel serverless, so local testing might require adaptation).

## Deployment

Push to the `main` branch to trigger a Vercel deployment.