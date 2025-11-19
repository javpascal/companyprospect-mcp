from http.server import BaseHTTPRequestHandler
import json
import requests
import os
from urllib.parse import urlparse, parse_qs, quote
import uuid

# API configuration
API_URL = os.environ.get("API_URL", "https://api.nummary.co")
NUMMARY_AUTH_URL = os.environ.get("NUMMARY_AUTH_URL", "https://app.nummary.com/login")

# Store active sessions (in production, use a proper database or Redis)
sessions = {}

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
        parsed_path = urlparse(self.path)
        
        # Handle OAuth authorize endpoint
        if parsed_path.path == '/authorize':
            query = parse_qs(parsed_path.query)
            redirect_uri = query.get('redirect_uri', [None])[0]
            state = query.get('state', [None])[0]
            client_id = query.get('client_id', [None])[0]
            
            if not redirect_uri:
                self.send_error(400, "Missing redirect_uri parameter")
                return
            
            # Generate a session ID
            session_id = str(uuid.uuid4())
            sessions[session_id] = {
                'redirect_uri': redirect_uri,
                'state': state,
                'client_id': client_id
            }
            
            # Return an HTML page with login form
            html_content = f"""
            <!DOCTYPE html>
            <html>
            <head>
                <title>Login to Nummary</title>
                <style>
                    body {{
                        font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, Oxygen, Ubuntu, sans-serif;
                        background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
                        display: flex;
                        justify-content: center;
                        align-items: center;
                        height: 100vh;
                        margin: 0;
                    }}
                    .login-container {{
                        background: white;
                        padding: 40px;
                        border-radius: 10px;
                        box-shadow: 0 20px 60px rgba(0,0,0,0.3);
                        width: 400px;
                    }}
                    h2 {{
                        margin-top: 0;
                        color: #333;
                        text-align: center;
                    }}
                    .form-group {{
                        margin-bottom: 20px;
                    }}
                    label {{
                        display: block;
                        margin-bottom: 5px;
                        color: #666;
                        font-weight: 500;
                    }}
                    input {{
                        width: 100%;
                        padding: 12px;
                        border: 1px solid #ddd;
                        border-radius: 5px;
                        font-size: 16px;
                        box-sizing: border-box;
                    }}
                    input:focus {{
                        outline: none;
                        border-color: #667eea;
                    }}
                    button {{
                        width: 100%;
                        padding: 12px;
                        background: #667eea;
                        color: white;
                        border: none;
                        border-radius: 5px;
                        font-size: 16px;
                        cursor: pointer;
                        font-weight: 600;
                    }}
                    button:hover {{
                        background: #5a67d8;
                    }}
                    .info {{
                        background: #f7f7f7;
                        border-left: 4px solid #667eea;
                        padding: 15px;
                        margin-bottom: 20px;
                        border-radius: 5px;
                    }}
                    .error {{
                        color: #e74c3c;
                        text-align: center;
                        margin-top: 10px;
                    }}
                </style>
            </head>
            <body>
                <div class="login-container">
                    <h2>🔐 Connect to Nummary API</h2>
                    <div class="info">
                        Enter your Nummary API key to authorize this connection.
                    </div>
                    <form method="POST" action="/callback">
                        <input type="hidden" name="session_id" value="{session_id}">
                        <div class="form-group">
                            <label for="api_key">API Key:</label>
                            <input type="password" id="api_key" name="api_key" required 
                                   placeholder="Enter your Nummary API key">
                        </div>
                        <button type="submit">Authorize Connection</button>
                    </form>
                    <div style="margin-top: 20px; text-align: center; color: #999; font-size: 14px;">
                        Don't have an API key? 
                        <a href="{NUMMARY_AUTH_URL}" target="_blank" style="color: #667eea;">
                            Get one from Nummary
                        </a>
                    </div>
                </div>
            </body>
            </html>
            """
            
            self.send_response(200)
            self.send_header('Content-Type', 'text/html')
            self.end_headers()
            self.wfile.write(html_content.encode())
            return
        
        # Handle SSE endpoint for MCP
        self.send_response(200)
        self.send_header('Content-Type', 'text/event-stream')
        self.send_header('Cache-Control', 'no-cache')
        self.send_header('Connection', 'keep-alive')
        self.send_header('Access-Control-Allow-Origin', '*')
        self.end_headers()
        
        host = self.headers.get('Host', 'localhost')
        proto = 'https' if 'localhost' not in host else 'http'
        endpoint = f"{proto}://{host}{self.path}"
        
        data = f"event: endpoint\ndata: {endpoint}\n\n"
        self.wfile.write(data.encode('utf-8'))
        self.wfile.flush()
        
    def do_POST(self):
        parsed_path = urlparse(self.path)
        
        # Handle OAuth callback (form submission)
        if parsed_path.path == '/callback':
            content_length = int(self.headers.get('Content-Length', 0))
            post_data = self.rfile.read(content_length)
            params = parse_qs(post_data.decode('utf-8'))
            
            session_id = params.get('session_id', [None])[0]
            api_key = params.get('api_key', [None])[0]
            
            if not session_id or session_id not in sessions:
                self.send_error(400, "Invalid session")
                return
            
            session = sessions[session_id]
            redirect_uri = session['redirect_uri']
            state = session['state']
            
            # Clean up session
            del sessions[session_id]
            
            # Generate authorization code (in this case, we'll use the API key as the code)
            # In production, you'd store this mapping securely
            auth_code = api_key
            
            # Redirect back to the client with the authorization code
            sep = '&' if '?' in redirect_uri else '?'
            target = f"{redirect_uri}{sep}code={quote(auth_code)}"
            if state:
                target += f"&state={quote(state)}"
            
            self.send_response(302)
            self.send_header('Location', target)
            self.end_headers()
            return
        
        # Handle OAuth token endpoint
        if parsed_path.path == '/token':
            content_length = int(self.headers.get('Content-Length', 0))
            post_data = self.rfile.read(content_length)
            
            # Parse data (support both JSON and form-encoded)
            content_type = self.headers.get('Content-Type', '')
            if 'application/json' in content_type:
                params = json.loads(post_data.decode('utf-8'))
                code = params.get('code')
            else:
                params = parse_qs(post_data.decode('utf-8'))
                code = params.get('code', [None])[0]
            
            if not code:
                self.send_response(400)
                self.send_header('Content-Type', 'application/json')
                self.end_headers()
                self.wfile.write(json.dumps({
                    "error": "invalid_request",
                    "error_description": "Missing authorization code"
                }).encode())
                return
            
            # The code IS the API key in our simplified flow
            response = {
                "access_token": code,
                "token_type": "Bearer",
                "expires_in": 3600
            }
            
            self.send_response(200)
            self.send_header('Content-Type', 'application/json')
            origin = self.headers.get('Origin', '*')
            self.send_header('Access-Control-Allow-Origin', origin)
            self.send_header('Access-Control-Allow-Credentials', 'true')
            self.end_headers()
            self.wfile.write(json.dumps(response).encode())
            return
        
        # Handle MCP requests
        # Extract API Key from Authorization header
        auth_header = self.headers.get('Authorization')
        api_key = None
        if auth_header:
            parts = auth_header.split()
            if len(parts) == 2 and parts[0].lower() == 'bearer':
                api_key = parts[1]
        
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
    # Use provided API key or fall back to environment variable
    key = api_key or os.environ.get("API_KEY")
    
    if not key:
        return {
            "error": "Authentication required",
            "message": "Please authenticate through the OAuth flow to use this tool."
        }
    
    try:
        url = f"{API_URL}{endpoint}"
        headers = {
            "X-Api-Key": key,
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