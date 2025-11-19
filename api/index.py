from flask import Flask, request, Response, jsonify
import json
import requests
import time

app = Flask(__name__)

# Nummary API configuration
API_URL = "https://api.nummary.co"
API_KEY = "nm_92051a269374f2c79569b3e07231dbd5"
API_USER = "bba3be65-fe5e-4ff9-9951-24a0cb2c912c"

@app.route('/', methods=['GET'])
@app.route('/health', methods=['GET'])
def health():
    return "Nummary MCP Server is running (Flask)", 200

@app.route('/sse', methods=['GET'])
def handle_sse():
    def generate():
        # Send the endpoint event
        host = request.headers.get('Host', 'localhost')
        proto = 'https' if 'localhost' not in host else 'http'
        endpoint = f"{proto}://{host}/messages"
        
        yield f"event: endpoint\ndata: {endpoint}\n\n"
        
        # Keep-alive loop
        # Vercel will kill this eventually, but Flask's generator handles buffering better
        while True:
            time.sleep(5)
            yield ": ping\n\n"

    return Response(generate(), mimetype='text/event-stream')

@app.route('/messages', methods=['POST'])
def handle_messages():
    try:
        data = request.json
        method = data.get('method')
        params = data.get('params', {})
        request_id = data.get('id')
        
        result = handle_method(method, params, request_id)
        return jsonify(result)
    except Exception as e:
        return jsonify({
            "jsonrpc": "2.0",
            "id": None,
            "error": {"code": -32603, "message": str(e)}
        }), 500

def handle_method(method, params, request_id):
    # Initialize
    if method == "initialize":
        return {
            "jsonrpc": "2.0",
            "id": request_id,
            "result": {
                "protocolVersion": "2024-11-05",
                "capabilities": {"tools": {}, "prompts": {}},
                "serverInfo": {"name": "nummary-mcp", "version": "1.0.0"}
            }
        }
    
    # Notifications/initialized
    if method == "notifications/initialized":
        return {"jsonrpc": "2.0", "id": request_id, "result": {}}
    
    # Tools/list
    if method == "tools/list":
        return {
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
    
    # Prompts/list
    if method == "prompts/list":
        return {"jsonrpc": "2.0", "id": request_id, "result": {"prompts": []}}
    
    # Tools/call
    if method == "tools/call":
        tool_name = params.get("name")
        args = params.get("arguments", {})
        
        if tool_name == "company_typeahead":
            query = args.get("query", "")
            result = call_nummary_api("/app/type/company", {"query": query.strip()})
            return {
                "jsonrpc": "2.0",
                "id": request_id,
                "result": {
                    "content": [{"type": "text", "text": json.dumps(result, indent=2)}]
                }
            }
        elif tool_name == "find_competitors":
            context = args.get("context", [])
            result = call_nummary_api("/app/naturalsearch", {"context": context})
            return {
                "jsonrpc": "2.0",
                "id": request_id,
                "result": {
                    "content": [{"type": "text", "text": json.dumps(result, indent=2)}]
                }
            }
        else:
            return {
                "jsonrpc": "2.0",
                "id": request_id,
                "error": {"code": -32601, "message": f"Tool '{tool_name}' not found"}
            }
    
    # Method not found
    return {
        "jsonrpc": "2.0",
        "id": request_id,
        "error": {"code": -32601, "message": f"Method '{method}' not found"}
    }

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

# Vercel expects the 'app' object to be available
