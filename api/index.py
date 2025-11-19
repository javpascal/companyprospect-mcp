from http.server import BaseHTTPRequestHandler
import json
import requests
import os
from urllib.parse import urlparse, parse_qs

# API configuration
API_URL = os.environ.get("API_URL", "https://api.nummary.co")
API_KEY = os.environ.get("API_KEY")

class handler(BaseHTTPRequestHandler):
    def do_OPTIONS(self):
        self.send_response(200)
        self.send_header('Access-Control-Allow-Origin', '*')
        self.send_header('Access-Control-Allow-Methods', 'GET, POST, OPTIONS')
        self.send_header('Access-Control-Allow-Headers', 'Content-Type, Authorization')
        self.send_header('Access-Control-Allow-Credentials', 'true')
        self.end_headers()
    
    def do_GET(self):
        # Handle OAuth authorize endpoint
        if self.path.startswith('/authorize'):
            query = urlparse(self.path).query
            params = parse_qs(query)
            
            redirect_uri = params.get('redirect_uri', [None])[0]
            state = params.get('state', [None])[0]
            
            if redirect_uri:
                # Auto-approve and redirect with a dummy code
                sep = '&' if '?' in redirect_uri else '?'
                target = f"{redirect_uri}{sep}code=auth_code"
                if state:
                    target += f"&state={state}"
                
                self.send_response(302)
                self.send_header('Location', target)
                self.end_headers()
                return

        self.send_response(200)
        self.send_header('Content-Type', 'text/event-stream')
        self.send_header('Cache-Control', 'no-cache')
        self.send_header('Connection', 'keep-alive')
        self.send_header('Access-Control-Allow-Origin', '*')
        self.end_headers()
        
        # Send endpoint event for MCP SSE
        host = self.headers.get('Host', 'localhost')
        proto = 'https' if 'localhost' not in host else 'http'
        endpoint = f"{proto}://{host}{self.path}"
        
        data = f"event: endpoint\ndata: {endpoint}\n\n"
        self.wfile.write(data.encode('utf-8'))
        self.wfile.flush()
        
    def do_POST(self):
        # Handle OAuth token endpoint
        if self.path.startswith('/token'):
            content_length = int(self.headers.get('Content-Length', 0))
            post_data = self.rfile.read(content_length)
            
            # Parse form data
            params = parse_qs(post_data.decode('utf-8'))
            
            # Extract client_secret (which is the API Key)
            client_secret = params.get('client_secret', [None])[0]
            
            if not client_secret:
                self.send_response(400)
                self.end_headers()
                self.wfile.write(b'{"error": "invalid_request", "error_description": "Missing client_secret"}')
                return

            # Return it as access_token
            response = {
                "access_token": client_secret,
                "token_type": "Bearer",
                "expires_in": 3600
            }
            
            self.send_response(200)
            self.send_header('Content-Type', 'application/json')
            self.send_header('Access-Control-Allow-Origin', '*')
            self.send_header('Access-Control-Allow-Credentials', 'true')
            self.end_headers()
            self.wfile.write(json.dumps(response).encode())
            return

        # Extract API Key from Authorization header if present
        auth_header = self.headers.get('Authorization')
        request_api_key = None
        if auth_header:
            parts = auth_header.split()
            if len(parts) == 2 and parts[0].lower() == 'bearer':
                request_api_key = parts[1]

        content_length = int(self.headers['Content-Length'])
        post_data = self.rfile.read(content_length)
        data = json.loads(post_data.decode('utf-8'))
        
        method = data.get('method')
        params = data.get('params', {})
        request_id = data.get('id')
        
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
                            "description": "Busca empresas que coincidan con el query proporcionado",
                            "inputSchema": {
                                "type": "object",
                                "properties": {
                                    "query": {"type": "string", "description": "Término de búsqueda"}
                                },
                                "required": ["query"]
                            }
                        },
                        {
                            "name": "find_competitors",
                            "description": "Busca competidores basándose en una lista de empresas y palabras clave",
                            "inputSchema": {
                                "type": "object",
                                "properties": {
                                    "context": {
                                        "type": "array",
                                        "description": "Lista de empresas y palabras clave",
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
            
            # Pass all headers for debugging if needed
            debug_headers = dict(self.headers)
            
            if tool_name == "company_typeahead":
                query = args.get("query", "")
                result = call_nummary_api("/app/type/company", {"query": query.strip()}, request_api_key, debug_headers)
                response = {
                    "jsonrpc": "2.0",
                    "id": request_id,
                    "result": {
                        "content": [{"type": "text", "text": json.dumps(result, indent=2)}]
                    }
                }
            elif tool_name == "find_competitors":
                context = args.get("context", [])
                result = call_nummary_api("/app/naturalsearch", {"context": context}, request_api_key, debug_headers)
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
        self.send_header('Access-Control-Allow-Origin', '*')
        self.send_header('Access-Control-Allow-Credentials', 'true')
        self.end_headers()
        self.wfile.write(json.dumps(response).encode())
        return

def call_nummary_api(endpoint, body, request_key=None, debug_headers=None):
    # Use request key if provided (from OAuth), otherwise fallback to env var
    api_key = request_key or API_KEY
    
    # Check if API credentials are configured
    if not api_key:
        debug_msg = " (Auth Header found)" if request_key else " (No Auth Header)"
        headers_dump = f" Headers received: {list(debug_headers.keys())}" if debug_headers else ""
        return {
            "error": "Configuration error",
            "message": f"API Key missing{debug_msg}.{headers_dump} Please provide it via OAuth Client Secret or configure API_KEY environment variable."
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
            return {"error": f"API error: {response.status_code}", "message": response.text}
    except Exception as e:
        return {"error": "API call failed", "message": str(e)}
