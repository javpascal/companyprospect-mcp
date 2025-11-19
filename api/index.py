from http.server import BaseHTTPRequestHandler
import json
import requests
import os
from urllib.parse import parse_qs
import sys

# API configuration
API_URL = os.environ.get("API_URL", "https://api.nummary.co")
FALLBACK_API_KEY = os.environ.get("API_KEY")  # Optional fallback

class handler(BaseHTTPRequestHandler):
    def do_OPTIONS(self):
        self.send_response(200)
        origin = self.headers.get('Origin', '*')
        self.send_header('Access-Control-Allow-Origin', origin)
        self.send_header('Access-Control-Allow-Methods', 'GET, POST, OPTIONS')
        self.send_header('Access-Control-Allow-Headers', 'Content-Type, Authorization')
        self.send_header('Access-Control-Allow-Credentials', 'true')
        self.end_headers()
    
    def do_GET(self):
        # Handle OAuth authorize endpoint - auto-approve
        if self.path.startswith('/authorize'):
            print(f"[DEBUG] Authorize called: {self.path}", file=sys.stderr)
            # Extract redirect_uri and state from query params
            query = self.path.split('?')[1] if '?' in self.path else ''
            params = parse_qs(query)
            redirect_uri = params.get('redirect_uri', [''])[0]
            state = params.get('state', [''])[0]
            
            if redirect_uri:
                # Immediately redirect back with a dummy code
                sep = '&' if '?' in redirect_uri else '?'
                location = f"{redirect_uri}{sep}code=dummy"
                if state:
                    location += f"&state={state}"
                
                print(f"[DEBUG] Redirecting to: {location}", file=sys.stderr)
                self.send_response(302)
                self.send_header('Location', location)
                self.end_headers()
                return
        
        # SSE endpoint
        self.send_response(200)
        self.send_header('Content-Type', 'text/event-stream')
        self.send_header('Cache-Control', 'no-cache')
        self.send_header('Connection', 'keep-alive')
        origin = self.headers.get('Origin', '*')
        self.send_header('Access-Control-Allow-Origin', origin)
        self.send_header('Access-Control-Allow-Credentials', 'true')
        self.end_headers()
        
        host = self.headers.get('Host', 'localhost')
        proto = 'https' if 'localhost' not in host else 'http'
        endpoint = f"{proto}://{host}{self.path}"
        
        data = f"event: endpoint\ndata: {endpoint}\n\n"
        self.wfile.write(data.encode('utf-8'))
        self.wfile.flush()
        
    def do_POST(self):
        # Handle OAuth token endpoint
        if self.path.startswith('/token'):
            print(f"[DEBUG] Token endpoint called", file=sys.stderr)
            content_length = int(self.headers.get('Content-Length', 0))
            post_data = self.rfile.read(content_length)
            print(f"[DEBUG] Token request body: {post_data.decode('utf-8')[:200]}", file=sys.stderr)
            
            # Parse both JSON and form-encoded data
            content_type = self.headers.get('Content-Type', '')
            client_secret = None
            
            if 'application/json' in content_type:
                try:
                    data = json.loads(post_data.decode('utf-8'))
                    client_secret = data.get('client_secret')
                    print(f"[DEBUG] JSON client_secret found: {bool(client_secret)}", file=sys.stderr)
                except:
                    pass
            else:
                # Form-encoded
                params = parse_qs(post_data.decode('utf-8'))
                client_secret = params.get('client_secret', [None])[0]
                print(f"[DEBUG] Form client_secret found: {bool(client_secret)}", file=sys.stderr)
            
            # Return the client_secret as the access token
            # This is where the user's API key comes through
            response = {
                "access_token": client_secret or "no_token",
                "token_type": "Bearer",
                "expires_in": 3600
            }
            
            print(f"[DEBUG] Returning access_token: {bool(client_secret)}", file=sys.stderr)
            
            self.send_response(200)
            self.send_header('Content-Type', 'application/json')
            origin = self.headers.get('Origin', '*')
            self.send_header('Access-Control-Allow-Origin', origin)
            self.send_header('Access-Control-Allow-Credentials', 'true')
            self.end_headers()
            self.wfile.write(json.dumps(response).encode())
            return
        
        # Handle MCP requests
        # Log all headers for debugging
        print(f"[DEBUG] MCP Request Headers:", file=sys.stderr)
        for header, value in self.headers.items():
            if header.lower() == 'authorization':
                # Mask the token for security
                if value.startswith('Bearer '):
                    token = value[7:]
                    masked = f"Bearer {token[:4]}...{token[-4:]}" if len(token) > 8 else f"Bearer {token}"
                    print(f"[DEBUG]   {header}: {masked}", file=sys.stderr)
                else:
                    print(f"[DEBUG]   {header}: {value}", file=sys.stderr)
            else:
                print(f"[DEBUG]   {header}: {value}", file=sys.stderr)
        
        # Extract API Key from Authorization header (passed via OAuth)
        auth_header = self.headers.get('Authorization')
        api_key = None
        if auth_header and auth_header.startswith('Bearer '):
            api_key = auth_header.replace('Bearer ', '').strip()
            # Skip if it's a dummy token
            if api_key == "no_token":
                print(f"[DEBUG] No valid token found in Authorization header", file=sys.stderr)
                api_key = None
            else:
                print(f"[DEBUG] Found API key in Authorization header", file=sys.stderr)
        else:
            print(f"[DEBUG] No Authorization header or not Bearer type", file=sys.stderr)
        
        # Fall back to environment variable if no API key provided
        if not api_key:
            api_key = FALLBACK_API_KEY
            if api_key:
                print(f"[DEBUG] Using fallback API key from environment", file=sys.stderr)
            else:
                print(f"[DEBUG] No API key available (no auth header, no env var)", file=sys.stderr)
        
        content_length = int(self.headers['Content-Length'])
        post_data = self.rfile.read(content_length)
        data = json.loads(post_data.decode('utf-8'))
        
        method = data.get('method')
        params = data.get('params', {})
        request_id = data.get('id')
        
        print(f"[DEBUG] MCP method: {method}", file=sys.stderr)
        
        # Handle initialize
        if method == "initialize":
            response = {
                "jsonrpc": "2.0",
                "id": request_id,
                "result": {
                    "protocolVersion": "2024-11-05",
                    "capabilities": {"tools": {}, "prompts": {}},
                    "serverInfo": {"name": "nummary-mcp", "version": "1.0.0"}
                }
            }
        # Handle notifications/initialized
        elif method == "notifications/initialized":
            response = {"jsonrpc": "2.0", "id": request_id, "result": {}}
        # Handle tools/list
        elif method == "tools/list":
            response = {
                "jsonrpc": "2.0",
                "id": request_id,
                "result": {
                    "tools": [
                        {
                            "name": "company_typeahead",
                            "description": "Search for companies by name",
                            "inputSchema": {
                                "type": "object",
                                "properties": {
                                    "query": {"type": "string", "description": "Search term"}
                                },
                                "required": ["query"]
                            }
                        },
                        {
                            "name": "find_competitors",
                            "description": "Find competitors based on companies and keywords",
                            "inputSchema": {
                                "type": "object",
                                "properties": {
                                    "context": {
                                        "type": "array",
                                        "description": "List of companies and keywords",
                                        "items": {
                                            "type": "object",
                                            "properties": {
                                                "type": {"type": "string", "enum": ["company", "keyword"]},
                                                "id": {"type": "integer"},
                                                "text": {"type": "string"}
                                            },
                                            "required": ["type", "text"]
                                        }
                                    }
                                },
                                "required": ["context"]
                            }
                        }
                    ]
                }
            }
        # Handle prompts/list
        elif method == "prompts/list":
            response = {"jsonrpc": "2.0", "id": request_id, "result": {"prompts": []}}
        # Handle tools/call
        elif method == "tools/call":
            tool_name = params.get("name")
            args = params.get("arguments", {})
            
            print(f"[DEBUG] Tool call: {tool_name}, has API key: {bool(api_key)}", file=sys.stderr)
            
            if tool_name == "company_typeahead":
                query = args.get("query", "")
                result = call_nummary_api("/app/type/company", {"query": query.strip()}, api_key)
                response = {
                    "jsonrpc": "2.0",
                    "id": request_id,
                    "result": {
                        "content": [{"type": "text", "text": json.dumps(result, indent=2)}]
                    }
                }
            elif tool_name == "find_competitors":
                context = args.get("context", [])
                result = call_nummary_api("/app/naturalsearch", {"context": context}, api_key)
                response = {
                    "jsonrpc": "2.0",
                    "id": request_id,
                    "result": {
                        "content": [{"type": "text", "text": json.dumps(result, indent=2)}]
                    }
                }
            else:
                response = {
                    "jsonrpc": "2.0",
                    "id": request_id,
                    "error": {"code": -32601, "message": f"Tool '{tool_name}' not found"}
                }
        else:
            response = {
                "jsonrpc": "2.0",
                "id": request_id,
                "error": {"code": -32601, "message": f"Method '{method}' not found"}
            }
        
        self.send_response(200)
        self.send_header('Content-Type', 'application/json')
        origin = self.headers.get('Origin', '*')
        self.send_header('Access-Control-Allow-Origin', origin)
        self.send_header('Access-Control-Allow-Credentials', 'true')
        self.end_headers()
        self.wfile.write(json.dumps(response).encode())
        return

def call_nummary_api(endpoint, body, api_key=None):
    if not api_key:
        return {
            "error": "Authentication required",
            "message": "Please provide your Nummary API key in the OAuth Client Secret field when configuring the MCP connector.",
            "instructions": [
                "1. Get your API key from Nummary (after logging in, check the AUTH_APIKEY cookie)",
                "2. In Claude's connector settings, enter it in 'OAuth Client Secret'",
                "3. Leave 'OAuth Client ID' empty or enter any value"
            ],
            "debug": "Check Vercel logs for [DEBUG] messages to see OAuth flow"
        }
    
    try:
        url = f"{API_URL}{endpoint}"
        headers = {
            "X-Api-Key": api_key,
            "Accept": "application/json",
            "Content-Type": "application/json"
        }
        response = requests.post(url, headers=headers, json=body)
        if response.ok:
            return response.json()
        else:
            return {
                "error": f"API error: {response.status_code}",
                "message": response.text,
                "hint": "Check if your API key is valid"
            }
    except Exception as e:
        return {"error": "API call failed", "message": str(e)}