from http.server import BaseHTTPRequestHandler
import json
import requests
import os
from urllib.parse import urlparse, parse_qs
import logging

# Set up logging for debugging
logging.basicConfig(level=logging.DEBUG)
logger = logging.getLogger(__name__)

# API configuration
API_URL = os.environ.get("API_URL", "https://api.nummary.co")
API_KEY = os.environ.get("API_KEY")

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
        # Handle health check endpoint
        if self.path == '/health' or self.path == '/':
            auth_header = self.headers.get('Authorization')
            has_auth = bool(auth_header and 'bearer' in auth_header.lower())
            has_env_key = bool(API_KEY)
            
            status = {
                "status": "healthy",
                "server": "nummary-mcp",
                "version": "1.0.0",
                "authentication": {
                    "oauth_token_present": has_auth,
                    "env_api_key_present": has_env_key,
                    "ready": has_auth or has_env_key
                },
                "endpoints": {
                    "oauth_authorize": "/authorize",
                    "oauth_token": "/token",
                    "mcp": "/mcp"
                }
            }
            
            self.send_response(200)
            self.send_header('Content-Type', 'application/json')
            origin = self.headers.get('Origin', '*')
            self.send_header('Access-Control-Allow-Origin', origin)
            self.send_header('Access-Control-Allow-Credentials', 'true')
            self.end_headers()
            self.wfile.write(json.dumps(status, indent=2).encode())
            return
        
        # Handle OAuth authorize endpoint
        if self.path.startswith('/authorize'):
            query = urlparse(self.path).query
            params = parse_qs(query)
            
            redirect_uri = params.get('redirect_uri', [None])[0]
            state = params.get('state', [None])[0]
            
            logger.info(f"OAuth authorize request - redirect_uri: {redirect_uri}, state: {state}")
            
            if redirect_uri:
                # Auto-approve and redirect with authorization code
                from urllib.parse import quote
                sep = '&' if '?' in redirect_uri else '?'
                # Use a fixed code that the token endpoint will accept
                target = f"{redirect_uri}{sep}code=authorized"
                if state:
                    # Properly encode the state parameter
                    target += f"&state={quote(state)}"
                
                logger.info(f"Redirecting to: {target}")
                
                self.send_response(302)
                self.send_header('Location', target)
                self.send_header('Cache-Control', 'no-store')
                self.end_headers()
                return

        self.send_response(200)
        self.send_header('Content-Type', 'text/event-stream')
        self.send_header('Cache-Control', 'no-cache')
        self.send_header('Connection', 'keep-alive')
        origin = self.headers.get('Origin', '*')
        self.send_header('Access-Control-Allow-Origin', origin)
        self.send_header('Access-Control-Allow-Credentials', 'true')
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
            
            # Log the incoming request for debugging
            logger.debug(f"Token endpoint called with headers: {dict(self.headers)}")
            logger.debug(f"Token endpoint body: {post_data}")
            
            # Parse data based on content type
            content_type = self.headers.get('Content-Type', '')
            client_secret = None
            
            if 'application/json' in content_type:
                try:
                    json_data = json.loads(post_data.decode('utf-8'))
                    client_secret = json_data.get('client_secret')
                    logger.debug(f"Parsed JSON, client_secret found: {bool(client_secret)}")
                except json.JSONDecodeError:
                    logger.error("Failed to parse JSON body")
            else:
                # Assume form-encoded data
                params = parse_qs(post_data.decode('utf-8'))
                client_secret = params.get('client_secret', [None])[0]
                logger.debug(f"Parsed form data, client_secret found: {bool(client_secret)}")
            
            if not client_secret:
                logger.error("Missing client_secret in token request")
                self.send_response(400)
                self.send_header('Content-Type', 'application/json')
                origin = self.headers.get('Origin', '*')
                self.send_header('Access-Control-Allow-Origin', origin)
                self.send_header('Access-Control-Allow-Credentials', 'true')
                self.end_headers()
                self.wfile.write(json.dumps({
                    "error": "invalid_request", 
                    "error_description": "Missing client_secret"
                }).encode())
                return

            # Return it as access_token
            response = {
                "access_token": client_secret,
                "token_type": "Bearer",
                "expires_in": 3600,
                "scope": "default",
                "refresh_token": client_secret
            }
            
            logger.info(f"Token issued successfully")
            
            self.send_response(200)
            self.send_header('Content-Type', 'application/json')
            origin = self.headers.get('Origin', '*')
            self.send_header('Access-Control-Allow-Origin', origin)
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
                logger.debug(f"Bearer token found in Authorization header")
        else:
            logger.debug(f"No Authorization header found in MCP request")

        content_length = int(self.headers['Content-Length'])
        post_data = self.rfile.read(content_length)
        data = json.loads(post_data.decode('utf-8'))
        
        method = data.get('method')
        params = data.get('params', {})
        request_id = data.get('id')
        
        logger.info(f"MCP method called: {method}")
        
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
        origin = self.headers.get('Origin', '*')
        self.send_header('Access-Control-Allow-Origin', origin)
        self.send_header('Access-Control-Allow-Credentials', 'true')
        self.end_headers()
        self.wfile.write(json.dumps(response).encode())
        return

def call_nummary_api(endpoint, body, request_key=None, debug_headers=None):
    # Use request key if provided (from OAuth), otherwise fallback to env var
    api_key = request_key or API_KEY
    
    logger.debug(f"API call to {endpoint}, OAuth key present: {bool(request_key)}, Env key present: {bool(API_KEY)}")
    
    # Check if API credentials are configured
    if not api_key:
        error_details = []
        if not request_key:
            error_details.append("No OAuth token in Authorization header")
        if not API_KEY:
            error_details.append("No API_KEY environment variable configured")
        
        error_message = {
            "error": "Authentication Required",
            "message": "API Key is missing. Please provide it via OAuth Client Secret when configuring the MCP connector in Claude.",
            "details": error_details,
            "instructions": [
                "1. In Claude's MCP connector dialog, enter your API key in the 'OAuth Client Secret' field",
                "2. Leave the 'OAuth Client ID' field empty or enter any value",
                "3. The API key will be passed securely through the OAuth flow"
            ]
        }
        logger.error(f"API authentication failed: {error_details}")
        return error_message
    
    try:
        url = f"{API_URL}{endpoint}"
        headers = {
            "X-Api-Key": api_key,
            "Accept": "application/json",
            "Content-Type": "application/json"
        }
        logger.info(f"Calling Nummary API: {url}")
        response = requests.post(url, headers=headers, json=body)
        
        if response.ok:
            logger.info(f"API call successful: {response.status_code}")
            return response.json()
        else:
            logger.error(f"API call failed: {response.status_code} - {response.text}")
            return {
                "error": f"API Error {response.status_code}",
                "message": response.text,
                "endpoint": endpoint
            }
    except Exception as e:
        logger.error(f"API call exception: {str(e)}")
        return {"error": "API call failed", "message": str(e), "endpoint": endpoint}

