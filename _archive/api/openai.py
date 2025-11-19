from http.server import BaseHTTPRequestHandler
import json
import requests
from urllib.parse import urlparse, parse_qs

# Nummary API configuration
API_URL = "https://api.nummary.co"
API_KEY = "nm_92051a269374f2c79569b3e07231dbd5"
API_USER = "bba3be65-fe5e-4ff9-9951-24a0cb2c912c"

class handler(BaseHTTPRequestHandler):
    def do_OPTIONS(self):
        self.send_response(200)
        self.send_header('Access-Control-Allow-Origin', '*')
        self.send_header('Access-Control-Allow-Methods', 'GET, POST, OPTIONS')
        self.send_header('Access-Control-Allow-Headers', 'Content-Type')
        self.end_headers()
        
    def do_GET(self):
        """Handle GET request for OpenAPI spec"""
        parsed_path = urlparse(self.path)
        
        # Return OpenAPI specification
        if parsed_path.path == '/api/openai/spec':
            spec = {
                "openapi": "3.0.0",
                "info": {
                    "title": "Nummary Company Search API",
                    "version": "1.0.0",
                    "description": "Search for companies using Nummary API"
                },
                "servers": [
                    {
                        "url": "https://mcp-test-lilac.vercel.app"
                    }
                ],
                "paths": {
                    "/api/openai/search": {
                        "post": {
                            "operationId": "searchCompanies",
                            "summary": "Search for companies",
                            "description": "Search for companies that match the given query",
                            "requestBody": {
                                "required": True,
                                "content": {
                                    "application/json": {
                                        "schema": {
                                            "type": "object",
                                            "properties": {
                                                "query": {
                                                    "type": "string",
                                                    "description": "Search query for finding companies"
                                                }
                                            },
                                            "required": ["query"]
                                        }
                                    }
                                }
                            },
                            "responses": {
                                "200": {
                                    "description": "Successful response",
                                    "content": {
                                        "application/json": {
                                            "schema": {
                                                "type": "object",
                                                "properties": {
                                                    "data": {
                                                        "type": "array",
                                                        "items": {
                                                            "type": "object"
                                                        }
                                                    }
                                                }
                                            }
                                        }
                                    }
                                }
                            }
                        }
                    }
                }
            }
            
            self.send_response(200)
            self.send_header('Content-Type', 'application/json')
            self.send_header('Access-Control-Allow-Origin', '*')
            self.end_headers()
            self.wfile.write(json.dumps(spec).encode())
            return
            
        # Default response
        self.send_response(404)
        self.end_headers()
        
    def do_POST(self):
        """Handle POST request for company search"""
        parsed_path = urlparse(self.path)
        
        if parsed_path.path == '/api/openai/search':
            content_length = int(self.headers['Content-Length'])
            post_data = self.rfile.read(content_length)
            data = json.loads(post_data.decode('utf-8'))
            
            query = data.get('query', '')
            
            # Call Nummary API
            result = self.call_nummary_api(query)
            
            self.send_response(200)
            self.send_header('Content-Type', 'application/json')
            self.send_header('Access-Control-Allow-Origin', '*')
            self.end_headers()
            self.wfile.write(json.dumps(result).encode())
            return
            
        # Default response
        self.send_response(404)
        self.end_headers()
    
    def call_nummary_api(self, query):
        try:
            url = f"{API_URL}/app/type/company"
            headers = {
                "X-Api-Key": API_KEY,
                "X-User-Id": API_USER,
                "Accept": "application/json",
                "Content-Type": "application/json"
            }
            response = requests.post(url, headers=headers, json={"query": query.strip()})
            if response.ok:
                return response.json()
            else:
                return {"error": f"API error: {response.status_code}", "message": response.text}
        except Exception as e:
            return {"error": "API call failed", "message": str(e)}

