"""
Vercel Serverless Function for MCP
"""
import json
import requests

# Nummary API configuration
API_URL = "https://api.nummary.co"
API_KEY = "nm_92051a269374f2c79569b3e07231dbd5"
API_USER = "bba3be65-fe5e-4ff9-9951-24a0cb2c912c"

def handler(request, response):
    """Vercel serverless function handler"""
    
    # Set CORS headers
    response.headers = {
        'Access-Control-Allow-Origin': '*',
        'Access-Control-Allow-Methods': 'GET, POST, OPTIONS',
        'Access-Control-Allow-Headers': 'Content-Type',
        'Content-Type': 'application/json'
    }
    
    # Handle OPTIONS for CORS
    if request.method == 'OPTIONS':
        response.status_code = 200
        return ""
    
    # Handle GET for SSE (simplified for now)
    if request.method == 'GET':
        return json.dumps({
            "type": "connection",
            "status": "connected"
        })
    
    # Handle POST for MCP RPC
    if request.method == 'POST':
        try:
            data = json.loads(request.body)
            method = data.get('method')
            params = data.get('params', {})
            request_id = data.get('id')
            
            result = handle_method(method, params, request_id)
            return json.dumps(result)
            
        except Exception as e:
            return json.dumps({
                "jsonrpc": "2.0",
                "id": None,
                "error": {
                    "code": -32603,
                    "message": str(e)
                }
            })
    
    # Method not allowed
    response.status_code = 405
    return json.dumps({"error": "Method not allowed"})

def handle_method(method, params, request_id):
    """Handle MCP methods"""
    
    # Initialize
    if method == "initialize":
        return {
            "jsonrpc": "2.0",
            "id": request_id,
            "result": {
                "protocolVersion": "2024-11-05",
                "capabilities": {
                    "tools": {},
                    "prompts": {}
                },
                "serverInfo": {
                    "name": "nummary-mcp",
                    "version": "1.0.0"
                }
            }
        }
    
    # Notifications/initialized
    if method == "notifications/initialized":
        return {
            "jsonrpc": "2.0",
            "id": request_id,
            "result": {}
        }
    
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
                                "query": {
                                    "type": "string",
                                    "description": "Término de búsqueda para encontrar empresas"
                                }
                            },
                            "required": ["query"]
                        }
                    }
                ]
            }
        }
    
    # Prompts/list
    if method == "prompts/list":
        return {
            "jsonrpc": "2.0",
            "id": request_id,
            "result": {
                "prompts": []
            }
        }
    
    # Tools/call
    if method == "tools/call":
        tool_name = params.get("name")
        args = params.get("arguments", {})
        
        if tool_name == "company_typeahead":
            query = args.get("query", "")
            result = call_nummary_api(query)
            
            return {
                "jsonrpc": "2.0",
                "id": request_id,
                "result": {
                    "content": [
                        {
                            "type": "text",
                            "text": json.dumps(result, indent=2)
                        }
                    ]
                }
            }
        
        # Tool not found
        return {
            "jsonrpc": "2.0",
            "id": request_id,
            "error": {
                "code": -32601,
                "message": f"Tool '{tool_name}' not found"
            }
        }
    
    # Method not found
    return {
        "jsonrpc": "2.0",
        "id": request_id,
        "error": {
            "code": -32601,
            "message": f"Method '{method}' not found"
        }
    }

def call_nummary_api(query):
    """Call Nummary API"""
    try:
        url = f"{API_URL}/app/type/company"
        headers = {
            "X-Api-Key": API_KEY,
            "X-User-Id": API_USER,
            "Accept": "application/json",
            "Content-Type": "application/json"
        }
        
        response = requests.post(
            url,
            headers=headers,
            json={"query": query.strip()}
        )
        
        if response.ok:
            return response.json()
        else:
            return {
                "error": f"API error: {response.status_code}",
                "message": response.text
            }
            
    except Exception as e:
        return {
            "error": "API call failed",
            "message": str(e)
        }