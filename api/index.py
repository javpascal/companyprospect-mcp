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
    
    def do_GET(self):
        parsed_url = urlparse(self.path)
        
        # Extract API key from query parameters if present
        query_params = parse_qs(parsed_url.query)
        api_key_from_query = query_params.get('api_key', [None])[0]
        
        if api_key_from_query:
            print(f"[DEBUG] GET request has api_key in query: {api_key_from_query[:8]}...", file=sys.stderr)
        
        # SSE endpoint - IMPORTANT: preserve API key in the endpoint URL
        self.send_response(200)
        self.send_header('Content-Type', 'text/event-stream')
        self.send_header('Cache-Control', 'no-cache')
        self.send_header('Connection', 'keep-alive')
        origin = self.headers.get('Origin', '*')
        self.send_header('Access-Control-Allow-Origin', origin)
        self.send_header('Access-Control-Allow-Credentials', 'true')
        # Set API key as a custom header that will be echoed back
        if api_key_from_query:
            self.send_header('X-Api-Key', api_key_from_query)
        self.end_headers()
        
        host = self.headers.get('Host', 'localhost')
        proto = 'https' if 'localhost' not in host else 'http'
        
        # CRITICAL: Include the API key in the SSE endpoint data
        # This ensures subsequent POST requests know about the API key
        if api_key_from_query:
            endpoint = f"{proto}://{host}{parsed_url.path}?api_key={api_key_from_query}"
        else:
            endpoint = f"{proto}://{host}{parsed_url.path}"
        
        # Send endpoint with API key preserved
        data = f"event: endpoint\ndata: {endpoint}\n\n"
        
        # Also send API key as a separate event for clients that can handle it
        if api_key_from_query:
            data += f"event: auth\ndata: {api_key_from_query}\n\n"
        
        self.wfile.write(data.encode('utf-8'))
        self.wfile.flush()
        
    def do_POST(self):
        # Debug logging
        print(f"[DEBUG] POST request to: {self.path}", file=sys.stderr)
        print(f"[DEBUG] Headers: {dict(self.headers)}", file=sys.stderr)
        
        # Extract API key from multiple possible sources
        api_key = None
        
        # 1. Check URL query parameters FIRST (most reliable for our use case)
        if '?' in self.path:
            query_params = parse_qs(self.path.split('?')[1])
            api_key = query_params.get('api_key', [None])[0]
            if api_key:
                print(f"[DEBUG] Found API key in URL query params", file=sys.stderr)
        
        # 2. Check Referer header for API key (SSE connections might have it here)
        if not api_key:
            referer = self.headers.get('Referer', '')
            if 'api_key=' in referer:
                parsed_referer = urlparse(referer)
                referer_params = parse_qs(parsed_referer.query)
                api_key = referer_params.get('api_key', [None])[0]
                if api_key:
                    print(f"[DEBUG] Found API key in Referer header", file=sys.stderr)
        
        # 3. Check custom X-Api-Key header
        if not api_key:
            api_key = self.headers.get('X-Api-Key')
            if api_key:
                print(f"[DEBUG] Found API key in X-Api-Key header", file=sys.stderr)
        
        # 4. Check Authorization header (Bearer token)
        if not api_key:
            auth_header = self.headers.get('Authorization', '')
            if auth_header.startswith('Bearer '):
                api_key = auth_header[7:].strip()
                if api_key and api_key != "no_token":
                    print(f"[DEBUG] Found API key in Bearer token", file=sys.stderr)
                else:
                    api_key = None
        
        # 5. Check Authorization header (Basic auth)
        if not api_key and auth_header.startswith('Basic '):
            try:
                decoded = base64.b64decode(auth_header[6:]).decode('utf-8')
                if ':' in decoded:
                    _, api_key = decoded.split(':', 1)
                    print(f"[DEBUG] Found API key in Basic auth", file=sys.stderr)
                else:
                    api_key = decoded
            except:
                pass
        
        # 6. Parse request body
        content_length = int(self.headers.get('Content-Length', 0))
        post_data = self.rfile.read(content_length)
        
        try:
            data = json.loads(post_data.decode('utf-8'))
        except:
            print(f"[DEBUG] Failed to parse JSON body", file=sys.stderr)
            data = {}
        
        # 7. Check if API key is embedded in the request params
        if not api_key and isinstance(data.get('params'), dict):
            api_key = data['params'].pop('api_key', None)
            if api_key:
                print(f"[DEBUG] Found API key in request params", file=sys.stderr)
        
        # 8. Fall back to environment variable
        if not api_key:
            api_key = FALLBACK_API_KEY
            if api_key:
                print(f"[DEBUG] Using fallback API key from environment", file=sys.stderr)
            else:
                print(f"[DEBUG] NO API KEY FOUND ANYWHERE!", file=sys.stderr)
                print(f"[DEBUG] Path: {self.path}", file=sys.stderr)
                print(f"[DEBUG] Referer: {self.headers.get('Referer', 'None')}", file=sys.stderr)
        
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
            "message": "API key not found. Check Vercel logs for [DEBUG] messages.",
            "troubleshooting": [
                "1. Make sure your Claude config URL includes ?api_key=YOUR_KEY",
                "2. Check Vercel function logs for debug output",
                "3. Try setting API_KEY in Vercel environment variables as fallback"
            ],
            "claude_config": {
                "correct_format": {
                    "url": "https://companyprospect-mcp.vercel.app?api_key=nm_9xxxxx"
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