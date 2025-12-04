from http.server import BaseHTTPRequestHandler
import json
import requests
import os
from urllib.parse import parse_qs, urlparse
import base64
import sys

# API configuration
API_URL = os.environ.get("API_URL", "https://api.companyprospect.com")
FALLBACK_API_KEY=''

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
        """Extract API Key if embedded in path like /key/abcd123xxx/... or /abcd123xxx/..."""
        parts = path.strip('/').split('/')
        
        if len(parts) >= 2 and parts[0] == 'key':
            api_key = parts[1]
            remaining_path = '/' + '/'.join(parts[2:]) if len(parts) > 2 else '/'
            return api_key, remaining_path
        
        # Check if path starts with /API_KEY/...
        if len(parts) >= 1:
            api_key = parts[0]
            remaining_path = '/' + '/'.join(parts[1:]) if len(parts) > 1 else '/'
            return api_key, remaining_path
        
        return None, path
    
    def do_GET(self):
        # Extract API key from path
        api_key_from_path, clean_path = self.extract_api_key_from_path(self.path)
        
        # Also check query parameters as backup
        parsed_url = urlparse(self.path)
        query_params = parse_qs(parsed_url.query)
        api_key_from_query = query_params.get('key', [None])[0]
        
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
            endpoint = f"{proto}://{host}{parsed_url.path}?key={api_key_from_query}"
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
            print(f"[DEBUG] POST: Found API Key in path", file=sys.stderr)
        
        # If no API key in path, try other sources
        if not api_key:
            # Check URL query parameters
            if '?' in self.path:
                query_params = parse_qs(self.path.split('?')[1])
                api_key = query_params.get('api_key', [None])[0]
                if api_key:
                    print(f"[DEBUG] POST: Found API Key in query params", file=sys.stderr)
        
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
            api_key = os.environ.get('FALLBACK_API_KEY')
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
                    "serverInfo": {"name": "companyprospect-mcp", "version": "1.0.0"}
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
                            "name": "ping",
                            "description": "IMPORTANT: Call this FIRST to wake up the server before using other tools. The server may be sleeping to save costs and needs ~10-30 seconds to wake up. Returns {status: 'ok'} when ready.",
                            "inputSchema": {
                                "type": "object",
                                "properties": {},
                                "required": []
                            }
                        },
                        {
                            "name": "lookup",
                            "description": "Quick company typeahead - returns autocompleted companies ranked by relevance. Returns: comp_id, comp_slug, comp_name, comp_web, dist. NOTE: Call 'ping' first if server may be sleeping.",
                            "inputSchema": {
                                "type": "object",
                                "properties": {
                                    "query": {"type": "string", "description": "Company name or search term"},
                                    "limit": {"type": "integer", "description": "Maximum results to return (default 10, max 100)"},
                                    "size_weight": {"type": "number", "description": "Bias toward larger companies (0.0-0.3, default 0.1). 0.0 = pure similarity, 0.1 = light bias, 0.2 = pronounced, 0.3 = heavy"}
                                },
                                "required": ["query"]
                            }
                        },
                        {
                            "name": "lookup_many",
                            "description": "Async company typeahead for multiple search terms - returns autocompleted companies per search term, deduplicated by company ID. Returns: comp_id, comp_slug, comp_name, comp_web, dist",
                            "inputSchema": {
                                "type": "object",
                                "properties": {
                                    "queries": {
                                        "type": "array",
                                        "description": "List of search terms/keywords",
                                        "items": {"type": "string"}
                                    },
                                    "limit": {"type": "integer", "description": "Maximum results per query (default 10, max 100)"},
                                    "size_weight": {"type": "number", "description": "Bias toward larger companies (0.0-0.3, default 0.1)"}
                                },
                                "required": ["queries"]
                            }
                        },
                        {
                            "name": "embed_many",
                            "description": "Generate semantic embeddings (768-dim vectors) for a list of text inputs. Useful for similarity comparisons, clustering, or search applications.",
                            "inputSchema": {
                                "type": "object",
                                "properties": {
                                    "inputs": {
                                        "type": "array",
                                        "description": "List of text strings to embed (company names, descriptions, keywords)",
                                        "items": {"type": "string"}
                                    }
                                },
                                "required": ["inputs"]
                            }
                        },
                        {
                            "name": "lookup_title",
                            "description": "Search job titles using semantic similarity. Finds matching titles from taxonomy based on search term. Returns: title_id, title_name, supertitle_id, function_id, function_name, dist",
                            "inputSchema": {
                                "type": "object",
                                "properties": {
                                    "query": {"type": "string", "description": "Search term for job title (e.g., 'founder', 'data scientist', 'sales manager', 'ceo')"},
                                    "limit": {"type": "integer", "description": "Maximum results to return (default 10, max 100)"}
                                },
                                "required": ["query"]
                            }
                        },
                        {
                            "name": "lookup_title_many",
                            "description": "Batch search job titles using semantic similarity. Searches multiple titles concurrently, deduplicated by title_id. Returns: title_id, title_name, supertitle_id, function_id, function_name, dist",
                            "inputSchema": {
                                "type": "object",
                                "properties": {
                                    "queries": {
                                        "type": "array",
                                        "description": "List of search terms for job titles",
                                        "items": {"type": "string"}
                                    },
                                    "limit": {"type": "integer", "description": "Maximum results per query (default 10, max 100)"}
                                },
                                "required": ["queries"]
                            }
                        },
                        {
                            "name": "lookalike_from_term",
                            "description": "Find similar/lookalike companies based on a search term or description using semantic embeddings. Returns: comp_id, comp_slug, comp_name, comp_web, dist",
                            "inputSchema": {
                                "type": "object",
                                "properties": {
                                    "query": {"type": "string", "description": "Search term or description to find similar companies (e.g., 'enterprise SaaS', 'fintech payments')"},
                                    "size_weight": {
                                        "type": "number",
                                        "description": "Bias toward larger companies (0.0-0.3, default 0.20). 0.0 = pure similarity, 0.1 = light bias, 0.2 = pronounced, 0.3 = heavy"
                                    },
                                    "limit": {"type": "integer", "description": "Maximum results to return (default 100, max 1000)"}
                                },
                                "required": ["query"]
                            }
                        },
                        {
                            "name": "lookalike_from_ids",
                            "description": "Find similar/lookalike companies based on a list of known company IDs. Supports optional filters for headcount and country. Returns: comp_id, comp_slug, comp_name, comp_web, dist",
                            "inputSchema": {
                                "type": "object",
                                "properties": {
                                    "company_ids": {
                                        "type": "array",
                                        "description": "List of company IDs (comp_id) to find lookalikes for",
                                        "items": {"type": "integer"}
                                    },
                                    "filter_hc": {
                                        "type": "integer",
                                        "description": "Minimum headcount filter - only return companies with headcount >= this value (optional)"
                                    },
                                    "filter_cc2": {
                                        "type": "array",
                                        "description": "Country code filter (ISO 2-letter codes) - only return companies in these countries (optional, e.g. ['es', 'fr', 'de'])",
                                        "items": {"type": "string"}
                                    },
                                    "size_weight": {
                                        "type": "number",
                                        "description": "Bias toward larger companies (0.0-0.3, default 0.20). 0.0 = pure similarity, 0.1 = light bias, 0.2 = pronounced, 0.3 = heavy"
                                    },
                                    "limit": {"type": "integer", "description": "Maximum results to return (default 100, max 1000)"}
                                },
                                "required": ["company_ids"]
                            }
                        },
                        {
                            "name": "parse_query",
                            "description": "Parse a natural language query into structured JSON for company searches. Extracts industry summary, competitor IDs, filters (headcount, country, job titles), and finds similar companies via semantic search.",
                            "inputSchema": {
                                "type": "object",
                                "properties": {
                                    "query": {
                                        "type": "string",
                                        "description": "Natural language query (e.g., 'startups en online payments en españa con >10 empleados, similar a Stripe')"
                                    }
                                },
                                "required": ["query"]
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
            
            if tool_name == "ping":
                result = call_companyprospect_api_get("/ping", {}, api_key)
                response = {
                    "jsonrpc": "2.0",
                    "id": request_id,
                    "result": {
                        "content": [{"type": "text", "text": json.dumps(result, indent=2)}]
                    }
                }
            elif tool_name == "lookup":
                query = args.get("query", "")
                limit = args.get("limit", 10)
                size_weight = args.get("size_weight", 0.1)
                result = call_companyprospect_api_get("/v01/lookup", {"query": query.strip(), "limit": limit, "size_weight": size_weight}, api_key)
                response = {
                    "jsonrpc": "2.0",
                    "id": request_id,
                    "result": {
                        "content": [{"type": "text", "text": json.dumps(result, indent=2)}]
                    }
                }
            elif tool_name == "lookup_many":
                queries = args.get("queries", [])
                limit = args.get("limit", 10)
                size_weight = args.get("size_weight", 0.1)
                result = call_companyprospect_api_post("/v01/lookup_many", {"queries": queries, "limit": limit, "size_weight": size_weight}, api_key)
                response = {
                    "jsonrpc": "2.0",
                    "id": request_id,
                    "result": {
                        "content": [{"type": "text", "text": json.dumps(result, indent=2)}]
                    }
                }
            elif tool_name == "embed_many":
                inputs = args.get("inputs", [])
                # API expects comma-separated string for query param
                query_string = ",".join(inputs) if inputs else ""
                result = call_companyprospect_api_get("/v01/embed_many", {"query": query_string}, api_key)
                response = {
                    "jsonrpc": "2.0",
                    "id": request_id,
                    "result": {
                        "content": [{"type": "text", "text": json.dumps(result, indent=2)}]
                    }
                }
            elif tool_name == "lookup_title":
                query = args.get("query", "")
                limit = args.get("limit", 10)
                result = call_companyprospect_api_get("/v01/lookup_title", {"query": query.strip(), "limit": limit}, api_key)
                response = {
                    "jsonrpc": "2.0",
                    "id": request_id,
                    "result": {
                        "content": [{"type": "text", "text": json.dumps(result, indent=2)}]
                    }
                }
            elif tool_name == "lookup_title_many":
                queries = args.get("queries", [])
                limit = args.get("limit", 10)
                result = call_companyprospect_api_post("/v01/lookup_title_many", {"queries": queries, "limit": limit}, api_key)
                response = {
                    "jsonrpc": "2.0",
                    "id": request_id,
                    "result": {
                        "content": [{"type": "text", "text": json.dumps(result, indent=2)}]
                    }
                }
            elif tool_name == "lookalike_from_term":
                query = args.get("query", "")
                size_weight = args.get("size_weight")
                limit = args.get("limit")
                
                # Build request body
                body = {"query": query.strip()}
                if size_weight is not None:
                    body["size_weight"] = size_weight
                if limit is not None:
                    body["limit"] = limit
                
                result = call_companyprospect_api_post("/v01/lookalike_from_term", body, api_key)
                response = {
                    "jsonrpc": "2.0",
                    "id": request_id,
                    "result": {
                        "content": [{"type": "text", "text": json.dumps(result, indent=2)}]
                    }
                }
            elif tool_name == "lookalike_from_ids":
                company_ids = args.get("company_ids", [])
                filter_hc = args.get("filter_hc")
                filter_cc2 = args.get("filter_cc2")
                size_weight = args.get("size_weight")
                limit = args.get("limit")
                
                # Build request body
                body = {"company_ids": company_ids}
                
                # Add optional filters
                if filter_hc is not None:
                    body["filter_hc"] = filter_hc
                if filter_cc2:
                    body["filter_cc2"] = filter_cc2
                if size_weight is not None:
                    body["size_weight"] = size_weight
                if limit is not None:
                    body["limit"] = limit
                
                result = call_companyprospect_api_post("/v01/lookalike_from_ids", body, api_key)
                response = {
                    "jsonrpc": "2.0",
                    "id": request_id,
                    "result": {
                        "content": [{"type": "text", "text": json.dumps(result, indent=2)}]
                    }
                }
            elif tool_name == "parse_query":
                query = args.get("query", "")
                
                result = call_companyprospect_api_post("/v01/parse_query", {"query": query}, api_key)
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

def _check_api_key(api_key):
    """Check if API key is present and return error dict if not."""
    if not api_key:
        return {
            "error": "Authentication required",
            "message": "API Key not found. For Claude Desktop, use the path-based format.",
            "instructions": [
                "Configure Claude Desktop with your API Key in the URL path:",
                "https://companyprospect-mcp.vercel.app/abcd123xxx",
            ],
            "troubleshooting": "Check Vercel logs for [DEBUG] messages to see what's being received"
        }
    return None

def call_companyprospect_api_get(endpoint, params, api_key=None):
    """Call CompanyProspect API using GET method with query parameters."""
    auth_error = _check_api_key(api_key)
    if auth_error:
        return auth_error
    
    try:
        url = f"{API_URL}{endpoint}"
        headers = {
            "X-Api-Key": api_key,
            "Accept": "application/json"
        }
        response = requests.get(url, headers=headers, params=params)
        if response.ok:
            return response.json()
        else:
            print(f"[DEBUG] CompanyProspect API error: {response.status_code}", file=sys.stderr)
            return {
                "error": f"API error: {response.status_code}",
                "message": response.text,
                "hint": "Check if your API Key is valid"
            }
    except Exception as e:
        print(f"[DEBUG] CompanyProspect API exception: {str(e)}", file=sys.stderr)
        return {"error": "API call failed", "message": str(e)}

def call_companyprospect_api_post(endpoint, body, api_key=None):
    """Call CompanyProspect API using POST method with JSON body."""
    auth_error = _check_api_key(api_key)
    if auth_error:
        return auth_error
    
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
            print(f"[DEBUG] CompanyProspect API error: {response.status_code}", file=sys.stderr)
            return {
                "error": f"API error: {response.status_code}",
                "message": response.text,
                "hint": "Check if your API Key is valid"
            }
    except Exception as e:
        print(f"[DEBUG] CompanyProspect API exception: {str(e)}", file=sys.stderr)
        return {"error": "API call failed", "message": str(e)}