#!/usr/bin/env python3
"""
Test script to verify OAuth flow for MCP Server
"""

import requests
import json
import sys
from urllib.parse import urlparse, parse_qs

def test_oauth_flow(base_url, api_key):
    """Test the complete OAuth flow"""
    
    print(f"Testing OAuth flow for: {base_url}")
    print(f"Using API Key: {'*' * (len(api_key) - 4) + api_key[-4:] if len(api_key) > 4 else '***'}")
    print("-" * 50)
    
    # Test 1: Health check
    print("\n1. Testing health endpoint...")
    try:
        response = requests.get(f"{base_url}/health")
        print(f"   Status: {response.status_code}")
        print(f"   Response: {json.dumps(response.json(), indent=2)}")
    except Exception as e:
        print(f"   ERROR: {e}")
    
    # Test 2: Authorization endpoint
    print("\n2. Testing authorize endpoint...")
    try:
        auth_url = f"{base_url}/authorize?client_id=test&redirect_uri=http://localhost:8080/callback&state=test123"
        response = requests.get(auth_url, allow_redirects=False)
        print(f"   Status: {response.status_code}")
        if response.status_code == 302:
            location = response.headers.get('Location')
            print(f"   Redirect to: {location}")
            parsed = urlparse(location)
            params = parse_qs(parsed.query)
            print(f"   Code: {params.get('code', ['NOT FOUND'])[0]}")
            print(f"   State: {params.get('state', ['NOT FOUND'])[0]}")
    except Exception as e:
        print(f"   ERROR: {e}")
    
    # Test 3: Token exchange
    print("\n3. Testing token endpoint...")
    try:
        token_data = {
            "grant_type": "authorization_code",
            "code": "authorized",
            "client_id": "test",
            "client_secret": api_key
        }
        response = requests.post(
            f"{base_url}/token",
            data=token_data,
            headers={"Content-Type": "application/x-www-form-urlencoded"}
        )
        print(f"   Status: {response.status_code}")
        if response.status_code == 200:
            token_response = response.json()
            print(f"   Token type: {token_response.get('token_type')}")
            print(f"   Access token present: {bool(token_response.get('access_token'))}")
            print(f"   Expires in: {token_response.get('expires_in')}")
            access_token = token_response.get('access_token')
        else:
            print(f"   Response: {response.text}")
            access_token = None
    except Exception as e:
        print(f"   ERROR: {e}")
        access_token = None
    
    # Test 4: MCP Initialize with token
    if access_token:
        print("\n4. Testing MCP initialize with OAuth token...")
        try:
            mcp_data = {
                "jsonrpc": "2.0",
                "id": 1,
                "method": "initialize",
                "params": {
                    "protocolVersion": "2024-11-05",
                    "capabilities": {}
                }
            }
            headers = {
                "Content-Type": "application/json",
                "Authorization": f"Bearer {access_token}"
            }
            response = requests.post(
                base_url,
                json=mcp_data,
                headers=headers
            )
            print(f"   Status: {response.status_code}")
            if response.status_code == 200:
                result = response.json()
                print(f"   Server: {result.get('result', {}).get('serverInfo', {}).get('name')}")
                print(f"   Version: {result.get('result', {}).get('serverInfo', {}).get('version')}")
            else:
                print(f"   Response: {response.text}")
        except Exception as e:
            print(f"   ERROR: {e}")
    
    # Test 5: Tool call with token
    if access_token:
        print("\n5. Testing tool call with OAuth token...")
        try:
            tool_data = {
                "jsonrpc": "2.0",
                "id": 2,
                "method": "tools/call",
                "params": {
                    "name": "company_typeahead",
                    "arguments": {
                        "query": "Microsoft"
                    }
                }
            }
            headers = {
                "Content-Type": "application/json",
                "Authorization": f"Bearer {access_token}"
            }
            response = requests.post(
                base_url,
                json=tool_data,
                headers=headers
            )
            print(f"   Status: {response.status_code}")
            if response.status_code == 200:
                result = response.json()
                if 'error' in result:
                    print(f"   Error: {result['error']}")
                else:
                    content = result.get('result', {}).get('content', [])
                    if content:
                        text = content[0].get('text', '')
                        try:
                            parsed = json.loads(text)
                            if 'error' in parsed:
                                print(f"   API Error: {parsed}")
                            else:
                                print(f"   Success! Data returned: {len(text)} characters")
                        except:
                            print(f"   Response: {text[:200]}...")
            else:
                print(f"   Response: {response.text}")
        except Exception as e:
            print(f"   ERROR: {e}")
    
    print("\n" + "-" * 50)
    print("OAuth flow test complete!")

if __name__ == "__main__":
    if len(sys.argv) != 3:
        print("Usage: python test_oauth.py <server_url> <api_key>")
        print("Example: python test_oauth.py https://your-app.vercel.app your-api-key")
        sys.exit(1)
    
    server_url = sys.argv[1].rstrip('/')
    api_key = sys.argv[2]
    
    test_oauth_flow(server_url, api_key)
