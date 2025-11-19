from http.server import BaseHTTPRequestHandler
import json
import requests
import os
from urllib.parse import parse_qs, urlparse
import base64
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
        self.send_header('Access-Control-Allow-Headers', 'Content-Type, Authorization, X-Api-Key')
        self.send_header('Access-Control-Allow-Credentials', 'true')
        self.end_headers()
    
    def extract_api_key_from_path(self, path):
        """Extract API key if embedded in path like /key/nm_xxx/... or /nm_xxx/..."""
        parts = path.strip('/').split('/')
        
        # Check if path starts with /key/API_KEY/...
        if len(parts) >= 2 and parts[0] == 'key':
            api_key = parts[1]
            if api_key.startswith('nm_'):
                remaining_path = '/' + '/'.join(parts[2:]) if len(parts) > 2 else '/'
                print(f"[DEBUG] Found API key in path: /key/{api_key[:8]}***", file=sys.stderr)
                return api_key, remaining_path
        
        # Check if path starts with /API_KEY/... (where API_KEY starts with nm_)
        if len(parts) >= 1 and parts[0].startswith('nm_'):
            api_key = parts[0]
            remaining_path = '/' + '/'.join(parts[1:]) if len(parts) > 1 else '/'
            print(f"[DEBUG] Found API key in path: /{api_key[:8]}***", file=sys.stderr)
            return api_key, remaining_path
        
        return None, path
    
    def do_GET(self):
        # Extract API key from path
        api_key_from_path, clean_path = self.extract_api_key_from_path(self.path)
        
        # Also check query parameters as backup
        parsed_url = urlparse(self.path)
        query_params = parse_qs(parsed_url.query)
        api_key_from_query = query_params.get('api_key', [None])[0]
        
        # Use path API key first, then query param
        api_key = api_key_from_path or api_key_from_query
        
        if api_key:
            print(f"[DEBUG] GET request has API key: {api_key[:8]}***", file=sys.stderr)
        
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
        
        # CRITICAL: Preserve the API key in the endpoint URL
        if api_key_from_path:
            # Keep the API key in the path for subsequent requests
            endpoint = f"{proto}://{host}{self.path}"
        elif api_key_from_query:
            endpoint = f"{proto}://{host}{parsed_url.path}?api_key={api_key_from_query}"
        else:
            endpoint = f"{proto}://{host}{self.path}"
        
        # Send endpoint with API key preserved
        data = f"event: endpoint\ndata: {endpoint}\n\n"
        
        # Also send API key as a separate event
        if api_key:
            data += f"event: auth\ndata: {api_key}\n\n"
        
        self.wfile.write(data.encode('utf-8'))
        self.wfile.flush()
        
    def do_POST(self):
        original_path = self.path
        
        # Extract API key from path FIRST
        api_key_from_path, clean_path = self.extract_api_key_from_path(self.path)
        api_key = api_key_from_path
        
        if api_key:
            print(f"[DEBUG] POST: Found API key in path", file=sys.stderr)
        
        # If no API key in path, try other sources
        if not api_key:
            # Check URL query parameters
            if '?' in self.path:
                query_params = parse_qs(self.path.split('?')[1])
                api_key = query_params.get('api_key', [None])[0]
                if api_key:
                    print(f"[DEBUG] POST: Found API key in query params", file=sys.stderr)
        
        # Check Referer header for API key
        if not api_key:
            referer = self.headers.get('Referer', '')
            # Check if API key is in the referer path
            if referer:
                parsed_referer = urlparse(referer)
                api_key_from_referer_path, _ = self.extract_api_key_from_path(parsed_referer.path)
                if api_key_from_referer_path:
                    api_key = api_key_from_referer_path
                    print(f"[DEBUG] POST: Found API key in Referer path", file=sys.stderr)
                elif 'api_key=' in referer:
                    referer_params = parse_qs(parsed_referer.query)
                    api_key = referer_params.get('api_key', [None])[0]
                    if api_key:
                        print(f"[DEBUG] POST: Found API key in Referer query", file=sys.stderr)
        
        # Check custom X-Api-Key header
        if not api_key:
            api_key = self.headers.get('X-Api-Key')
            if api_key:
                print(f"[DEBUG] POST: Found API key in X-Api-Key header", file=sys.stderr)
        
        # Check Authorization header
        if not api_key:
            auth_header = self.headers.get('Authorization', '')
            if auth_header.startswith('Bearer ') and auth_header[7:] != 'no_token':
                api_key = auth_header[7:].strip()
                if api_key:
                    print(f"[DEBUG] POST: Found API key in Bearer token", file=sys.stderr)
        
        # Parse request body
        content_length = int(self.headers.get('Content-Length', 0))
        post_data = self.rfile.read(content_length)
        
        try:
            data = json.loads(post_data.decode('utf-8'))
        except:
            print(f"[DEBUG] Failed to parse JSON body", file=sys.stderr)
            data = {}
        
        # Check if API key is embedded in request params
        if not api_key and isinstance(data.get('params'), dict):
            api_key = data['params'].pop('api_key', None)
            if api_key:
                print(f"[DEBUG] POST: Found API key in request params", file=sys.stderr)
        
        # Fall back to environment variable
        if not api_key:
            api_key = FALLBACK_API_KEY
            if api_key:
                print(f"[DEBUG] POST: Using fallback API key from environment", file=sys.stderr)
            else:
                print(f"[DEBUG] POST: NO API KEY FOUND!", file=sys.stderr)
                print(f"[DEBUG] POST: Original path: {original_path}", file=sys.stderr)
                print(f"[DEBUG] POST: Referer: {self.headers.get('Referer', 'None')}", file=sys.stderr)
        
        method = data.get('method')
        params = data.get('params', {})
        request_id = data.get('id')
        
        print(f"[DEBUG] MCP Method: {method}, Has API Key: {bool(api_key)}", file=sys.stderr)
        
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
            
            print(f"[DEBUG] Tool call: {tool_name}, API key present: {bool(api_key)}", file=sys.stderr)
            
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
                print(f"[DEBUG] find_competitors context: {json.dumps(context)}", file=sys.stderr)
                print(f"[DEBUG] find_competitors full args: {json.dumps(args)}", file=sys.stderr)
                
                # Call the API with the context
                body = {"context": context}
                print(f"[DEBUG] Sending to naturalsearch API: {json.dumps(body)}", file=sys.stderr)
                
                result = call_nummary_api("/app/naturalsearch", body, api_key)
                
                print(f"[DEBUG] naturalsearch API response: {json.dumps(result)[:500] if isinstance(result, dict) else str(result)[:500]}", file=sys.stderr)
                
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
            "message": "API key not found. For Claude Desktop, use the path-based format.",
            "instructions": [
                "Configure Claude Desktop with your API key in the URL path:",
                "https://companyprospect-mcp.vercel.app/nm_9xxxxx",
                "or",
                "https://companyprospect-mcp.vercel.app/key/nm_9xxxxx"
            ],
            "troubleshooting": "Check Vercel logs for [DEBUG] messages to see what's being received"
        }
    
    try:
        url = f"{API_URL}{endpoint}"
        headers = {
            "X-Api-Key": api_key,
            "Accept": "application/json",
            "Content-Type": "application/json"
        }
        print(f"[DEBUG] Calling Nummary API: {url}", file=sys.stderr)
        response = requests.post(url, headers=headers, json=body)
        if response.ok:
            print(f"[DEBUG] Nummary API call successful", file=sys.stderr)
            return response.json()
        else:
            print(f"[DEBUG] Nummary API error: {response.status_code}", file=sys.stderr)
            return {
                "error": f"API error: {response.status_code}",
                "message": response.text,
                "hint": "Check if your API key is valid"
            }
    except Exception as e:
        print(f"[DEBUG] Nummary API exception: {str(e)}", file=sys.stderr)
        return {"error": "API call failed", "message": str(e)}