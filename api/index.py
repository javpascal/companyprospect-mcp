from http.server import BaseHTTPRequestHandler
import json
import requests
import os
from urllib.parse import urlparse, parse_qs, quote
import uuid

# API configuration
API_URL = os.environ.get("API_URL", "https://api.nummary.co")
NUMMARY_LOGIN_URL = "https://app.nummary.co/login/"

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
            
            # Return an HTML page that handles the Nummary login flow
            html_content = f"""
            <!DOCTYPE html>
            <html>
            <head>
                <title>Connect to Nummary</title>
                <style>
                    * {{
                        margin: 0;
                        padding: 0;
                        box-sizing: border-box;
                    }}
                    body {{
                        font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, Oxygen, Ubuntu, sans-serif;
                        background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
                        min-height: 100vh;
                        display: flex;
                        justify-content: center;
                        align-items: center;
                        padding: 20px;
                    }}
                    .container {{
                        background: white;
                        padding: 40px;
                        border-radius: 10px;
                        box-shadow: 0 20px 60px rgba(0,0,0,0.3);
                        max-width: 500px;
                        width: 100%;
                    }}
                    h2 {{
                        color: #333;
                        margin-bottom: 10px;
                        display: flex;
                        align-items: center;
                        gap: 10px;
                    }}
                    .subtitle {{
                        color: #666;
                        margin-bottom: 30px;
                        line-height: 1.5;
                    }}
                    .step {{
                        background: #f8f9fa;
                        border-left: 4px solid #667eea;
                        padding: 20px;
                        margin-bottom: 20px;
                        border-radius: 5px;
                    }}
                    .step-header {{
                        font-weight: 600;
                        color: #333;
                        margin-bottom: 10px;
                        display: flex;
                        align-items: center;
                        gap: 10px;
                    }}
                    .step-number {{
                        background: #667eea;
                        color: white;
                        width: 28px;
                        height: 28px;
                        border-radius: 50%;
                        display: flex;
                        align-items: center;
                        justify-content: center;
                        font-size: 14px;
                    }}
                    .step-content {{
                        color: #666;
                        margin-left: 38px;
                        line-height: 1.6;
                    }}
                    .button {{
                        background: #667eea;
                        color: white;
                        border: none;
                        padding: 12px 24px;
                        border-radius: 5px;
                        font-size: 16px;
                        cursor: pointer;
                        text-decoration: none;
                        display: inline-block;
                        margin: 10px 0;
                        transition: background 0.2s;
                    }}
                    .button:hover {{
                        background: #5a67d8;
                    }}
                    .code-block {{
                        background: #2d3748;
                        color: #68d391;
                        padding: 15px;
                        border-radius: 5px;
                        font-family: 'Monaco', 'Courier New', monospace;
                        font-size: 14px;
                        margin: 10px 0;
                        position: relative;
                        overflow-x: auto;
                    }}
                    .copy-button {{
                        position: absolute;
                        top: 10px;
                        right: 10px;
                        background: #4a5568;
                        color: white;
                        border: none;
                        padding: 5px 10px;
                        border-radius: 3px;
                        cursor: pointer;
                        font-size: 12px;
                    }}
                    .copy-button:hover {{
                        background: #5a6578;
                    }}
                    .input-group {{
                        margin: 20px 0;
                    }}
                    label {{
                        display: block;
                        margin-bottom: 8px;
                        color: #333;
                        font-weight: 500;
                    }}
                    input[type="password"] {{
                        width: 100%;
                        padding: 12px;
                        border: 2px solid #e2e8f0;
                        border-radius: 5px;
                        font-size: 16px;
                        transition: border-color 0.2s;
                    }}
                    input[type="password"]:focus {{
                        outline: none;
                        border-color: #667eea;
                    }}
                    .submit-button {{
                        width: 100%;
                        background: #48bb78;
                        color: white;
                        border: none;
                        padding: 14px;
                        border-radius: 5px;
                        font-size: 16px;
                        font-weight: 600;
                        cursor: pointer;
                        margin-top: 10px;
                    }}
                    .submit-button:hover {{
                        background: #38a169;
                    }}
                    .success-message {{
                        display: none;
                        background: #c6f6d5;
                        border: 1px solid #9ae6b4;
                        color: #22543d;
                        padding: 12px;
                        border-radius: 5px;
                        margin: 10px 0;
                    }}
                    .divider {{
                        height: 1px;
                        background: #e2e8f0;
                        margin: 30px 0;
                    }}
                </style>
            </head>
            <body>
                <div class="container">
                    <h2>🔐 Connect Nummary to Claude</h2>
                    <p class="subtitle">Follow these steps to securely connect your Nummary account</p>
                    
                    <div class="step">
                        <div class="step-header">
                            <span class="step-number">1</span>
                            Log in to Nummary
                        </div>
                        <div class="step-content">
                            Click the button below to open Nummary in a new tab and log in with your credentials.
                            <br>
                            <a href="{NUMMARY_LOGIN_URL}" target="_blank" class="button">
                                Open Nummary Login →
                            </a>
                        </div>
                    </div>
                    
                    <div class="step">
                        <div class="step-header">
                            <span class="step-number">2</span>
                            Get Your API Key
                        </div>
                        <div class="step-content">
                            After logging in, run this command in your browser's developer console (F12) on the Nummary page:
                            <div class="code-block">
                                <button class="copy-button" onclick="copyCode()">Copy</button>
                                <code id="codeSnippet">document.cookie.split(';').find(c => c.trim().startsWith('AUTH_APIKEY='))?.split('=')[1] || 'API Key not found'</code>
                            </div>
                            This will display your API key. Copy it for the next step.
                        </div>
                    </div>
                    
                    <div class="step">
                        <div class="step-header">
                            <span class="step-number">3</span>
                            Enter Your API Key
                        </div>
                        <div class="step-content">
                            <form method="POST" action="/callback" onsubmit="handleSubmit(event)">
                                <input type="hidden" name="session_id" value="{session_id}">
                                <div class="input-group">
                                    <label for="api_key">Paste your API key here:</label>
                                    <input type="password" id="api_key" name="api_key" required 
                                           placeholder="Your Nummary API key" 
                                           autocomplete="off">
                                </div>
                                <button type="submit" class="submit-button">
                                    Connect to Claude
                                </button>
                            </form>
                            <div class="success-message" id="successMsg">
                                ✅ Connecting... You will be redirected shortly.
                            </div>
                        </div>
                    </div>
                    
                    <div class="divider"></div>
                    
                    <div style="text-align: center; color: #718096; font-size: 14px;">
                        <p>💡 <strong>Tip:</strong> Your API key is securely transmitted and not stored permanently.</p>
                        <p style="margin-top: 10px;">Having trouble? Make sure you're logged into Nummary first.</p>
                    </div>
                </div>
                
                <script>
                    function copyCode() {{
                        const code = document.getElementById('codeSnippet').textContent;
                        navigator.clipboard.writeText(code);
                        const button = document.querySelector('.copy-button');
                        button.textContent = 'Copied!';
                        setTimeout(() => {{
                            button.textContent = 'Copy';
                        }}, 2000);
                    }}
                    
                    function handleSubmit(e) {{
                        const apiKey = document.getElementById('api_key').value;
                        if (apiKey) {{
                            document.getElementById('successMsg').style.display = 'block';
                        }}
                    }}
                </script>
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
            
            # Use the API key as the authorization code
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
            
            # The code IS the API key in our flow
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