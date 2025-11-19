from http.server import BaseHTTPRequestHandler
import json
import requests

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
        # Health check for root path
        if self.path == '/' or self.path == '/health':
            self.send_response(200)
            self.send_header('Content-Type', 'text/plain')
            self.send_header('Access-Control-Allow-Origin', '*')
            self.end_headers()
            self.wfile.write(b"Nummary MCP Server is running")
            return

        # SSE Handshake
        self.send_response(200)
        self.send_header('Content-Type', 'text/event-stream')
        self.send_header('Cache-Control', 'no-cache')
        self.send_header('Connection', 'keep-alive')
        self.send_header('Access-Control-Allow-Origin', '*')
        self.end_headers()
        
        # Send endpoint event for MCP SSE
        host = self.headers.get('Host', 'localhost')
        proto = 'https' if 'localhost' not in host else 'http'
        
        # Force the endpoint to be /messages to avoid ambiguity
        endpoint = f"{proto}://{host}/messages"
        
        data = f"event: endpoint\ndata: {endpoint}\n\n"
        self.wfile.write(data.encode('utf-8'))

    def do_POST(self):
        try:
            content_length = int(self.headers.get('Content-Length', 0))
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
                
                if tool_name == "company_typeahead":
                    query = args.get("query", "")
                    result = call_nummary_api("/app/type/company", {"query": query.strip()})
                    response = {
                        "jsonrpc": "2.0",
                        "id": request_id,
                        "result": {
                            "content": [{"type": "text", "text": json.dumps(result, indent=2)}]
                        }
                    }
                elif tool_name == "find_competitors":
                    context = args.get("context", [])
                    result = call_nummary_api("/app/naturalsearch", {"context": context})
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
            self.end_headers()
            self.wfile.write(json.dumps(response).encode())
            
        except Exception as e:
            self.send_response(500)
            self.send_header('Content-Type', 'application/json')
            self.end_headers()
            self.wfile.write(json.dumps({"error": str(e)}).encode())

def call_nummary_api(endpoint, body):
    try:
        url = f"{API_URL}{endpoint}"
        headers = {
            "X-Api-Key": API_KEY,
            "X-User-Id": API_USER,
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
