from http.server import BaseHTTPRequestHandler
import json
import requests
import os
from urllib.parse import parse_qs, urlparse
import base64

# API configuration
API_URL = os.environ.get("API_URL", "https://api.nummary.co")
FALLBACK_API_KEY = os.environ.get("API_KEY")  # Optional fallback

class handler(BaseHTTPRequestHandler):
    def do_OPTIONS(self):
        self.send_response(200)
        origin = self.headers.get('Origin', '*')
        self.send_header('Access-Control-Allow-Origin', origin)
        self.send_header('Access-Control-Allow-Methods', 'GET, POST, OPTIONS')
        self.send_header('Access-Control-Allow-Headers', 'Content-Type, Authorization, X-Api-Key')
        self.send_header('Access-Control-Allow-Credentials', 'true')
        self.end_headers()
    
    def do_GET(self):
        parsed_url = urlparse(self.path)
        
        # Extract API key from query parameters if present
        query_params = parse_qs(parsed_url.query)
        api_key_from_query = query_params.get('api_key', [None])[0]
        
        # SSE endpoint with API key support
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
        
        # Include API key in the endpoint if provided via query
        if api_key_from_query:
            # Pass it through in the SSE endpoint URL
            endpoint = f"{proto}://{host}{parsed_url.path}?api_key={api_key_from_query}"
        else:
            endpoint = f"{proto}://{host}{parsed_url.path}"
        
        data = f"event: endpoint\ndata: {endpoint}\n\n"
        self.wfile.write(data.encode('utf-8'))
        self.wfile.flush()
        
    def do_POST(self):
        # Extract API key from multiple possible sources
        api_key = None
        
        # 1. Check Authorization header (Bearer token)
        auth_header = self.headers.get('Authorization', '')
        if auth_header.startswith('Bearer '):
            api_key = auth_header[7:].strip()
            if api_key == "no_token" or not api_key:
                api_key = None
        
        # 2. Check Authorization header (Basic auth)
        elif auth_header.startswith('Basic '):
            try:
                decoded = base64.b64decode(auth_header[6:]).decode('utf-8')
                # Format is typically username:password, we use the password as API key
                if ':' in decoded:
                    _, api_key = decoded.split(':', 1)
                else:
                    api_key = decoded
            except:
                pass
        
        # 3. Check custom X-Api-Key header
        if not api_key:
            api_key = self.headers.get('X-Api-Key')
        
        # 4. Check URL query parameters
        if not api_key and '?' in self.path:
            query_params = parse_qs(self.path.split('?')[1])
            api_key = query_params.get('api_key', [None])[0]
        
        # 5. Parse request body for embedded API key
        content_length = int(self.headers.get('Content-Length', 0))
        post_data = self.rfile.read(content_length)
        data = json.loads(post_data.decode('utf-8'))
        
        # Check if API key is embedded in the request
        if not api_key and isinstance(data.get('params'), dict):
            api_key = data['params'].pop('api_key', None)
        
        # 6. Fall back to environment variable
        if not api_key:
            api_key = FALLBACK_API_KEY
        
        method = data.get('method')
        params = data.get('params', {})
        request_id = data.get('id')
        
        # Log for debugging
        import sys
        print(f"[DEBUG] Method: {method}, Has API Key: {bool(api_key)}", file=sys.stderr)
        if not api_key:
            print(f"[DEBUG] Auth header: {auth_header[:20] if auth_header else 'None'}", file=sys.stderr)
            print(f"[DEBUG] X-Api-Key header: {self.headers.get('X-Api-Key', 'None')}", file=sys.stderr)
            print(f"[DEBUG] Query params: {self.path if '?' in self.path else 'None'}", file=sys.stderr)
        
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
            "message": "API key not found. Please configure it in one of these ways:",
            "options": [
                "1. Set API_KEY in Vercel environment variables",
                "2. Add ?api_key=YOUR_KEY to the URL in Claude config",
                "3. Use Basic auth in Claude config (password field)",
                "4. Check Vercel logs for debugging info"
            ],
            "claude_config_examples": {
                "option1_env_var": {
                    "url": "https://companyprospect-mcp.vercel.app"
                },
                "option2_query_param": {
                    "url": "https://companyprospect-mcp.vercel.app?api_key=YOUR_KEY"
                },
                "option3_basic_auth": {
                    "url": "https://companyprospect-mcp.vercel.app",
                    "auth": {
                        "type": "basic",
                        "username": "user",
                        "password": "YOUR_KEY"
                    }
                }
            }
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