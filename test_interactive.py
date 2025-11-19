#!/usr/bin/env python3
"""
Interactive MCP Server Tester
Test your MCP server without going through Claude
"""

import requests
import json
import sys
import os
from typing import Optional

class MCPTester:
    def __init__(self, server_url: str, api_key: str):
        self.server_url = server_url.rstrip('/')
        self.api_key = api_key
        self.access_token: Optional[str] = None
        
    def get_token(self) -> bool:
        """Get OAuth access token"""
        print("\n🔐 Getting OAuth token...")
        try:
            response = requests.post(
                f"{self.server_url}/token",
                data={
                    "grant_type": "authorization_code",
                    "code": "test",
                    "client_secret": self.api_key
                },
                headers={"Content-Type": "application/x-www-form-urlencoded"}
            )
            if response.status_code == 200:
                token_data = response.json()
                self.access_token = token_data.get('access_token')
                print("✅ Token obtained successfully!")
                return True
            else:
                print(f"❌ Failed to get token: {response.text}")
                return False
        except Exception as e:
            print(f"❌ Error: {e}")
            return False
    
    def call_mcp(self, method: str, params: dict = None) -> dict:
        """Call MCP method"""
        if not self.access_token and not self.get_token():
            return {"error": "Failed to get access token"}
        
        headers = {
            "Content-Type": "application/json",
            "Authorization": f"Bearer {self.access_token}"
        }
        
        data = {
            "jsonrpc": "2.0",
            "id": 1,
            "method": method,
            "params": params or {}
        }
        
        try:
            response = requests.post(self.server_url, json=data, headers=headers)
            return response.json()
        except Exception as e:
            return {"error": str(e)}
    
    def test_health(self):
        """Test health endpoint"""
        print("\n🏥 Testing health endpoint...")
        try:
            response = requests.get(f"{self.server_url}/health")
            print(json.dumps(response.json(), indent=2))
        except Exception as e:
            print(f"❌ Error: {e}")
    
    def test_initialize(self):
        """Test MCP initialization"""
        print("\n🚀 Testing MCP initialization...")
        result = self.call_mcp("initialize", {"protocolVersion": "2024-11-05"})
        print(json.dumps(result, indent=2))
    
    def test_list_tools(self):
        """List available tools"""
        print("\n🛠️ Listing available tools...")
        result = self.call_mcp("tools/list")
        if 'result' in result and 'tools' in result['result']:
            tools = result['result']['tools']
            print(f"Found {len(tools)} tools:")
            for tool in tools:
                print(f"  - {tool['name']}: {tool['description']}")
        else:
            print(json.dumps(result, indent=2))
    
    def test_company_search(self):
        """Test company typeahead"""
        query = input("\n🔍 Enter company name to search: ").strip()
        if not query:
            query = "Microsoft"
            print(f"Using default: {query}")
        
        print(f"\nSearching for '{query}'...")
        result = self.call_mcp("tools/call", {
            "name": "company_typeahead",
            "arguments": {"query": query}
        })
        
        if 'result' in result and 'content' in result['result']:
            content = result['result']['content'][0]['text']
            try:
                data = json.loads(content)
                print(json.dumps(data, indent=2)[:1000])
                if len(json.dumps(data)) > 1000:
                    print("... (truncated)")
            except:
                print(content[:500])
        else:
            print(json.dumps(result, indent=2))
    
    def test_find_competitors(self):
        """Test find competitors"""
        print("\n🎯 Testing find competitors...")
        
        # Get company input
        company = input("Enter a company name (or press Enter for 'Microsoft'): ").strip() or "Microsoft"
        keyword = input("Enter a keyword (or press Enter for 'cloud'): ").strip() or "cloud"
        
        context = [
            {"type": "company", "text": company},
            {"type": "keyword", "text": keyword}
        ]
        
        print(f"\nSearching competitors for context: {context}")
        result = self.call_mcp("tools/call", {
            "name": "find_competitors",
            "arguments": {"context": context}
        })
        
        if 'result' in result and 'content' in result['result']:
            content = result['result']['content'][0]['text']
            try:
                data = json.loads(content)
                print(json.dumps(data, indent=2)[:1500])
                if len(json.dumps(data)) > 1500:
                    print("... (truncated)")
            except:
                print(content[:500])
        else:
            print(json.dumps(result, indent=2))
    
    def run_all_tests(self):
        """Run all tests in sequence"""
        print("\n🧪 Running all tests...")
        self.test_health()
        input("\nPress Enter to continue...")
        
        self.test_initialize()
        input("\nPress Enter to continue...")
        
        self.test_list_tools()
        input("\nPress Enter to continue...")
        
        self.test_company_search()
        input("\nPress Enter to continue...")
        
        self.test_find_competitors()
    
    def interactive_menu(self):
        """Interactive testing menu"""
        while True:
            print("\n" + "="*50)
            print("MCP Server Interactive Tester")
            print("="*50)
            print(f"Server: {self.server_url}")
            print(f"Token: {'✅ Obtained' if self.access_token else '❌ Not obtained'}")
            print("\nOptions:")
            print("1. Test health endpoint")
            print("2. Get/refresh OAuth token")
            print("3. Initialize MCP")
            print("4. List available tools")
            print("5. Test company search")
            print("6. Test find competitors")
            print("7. Run all tests")
            print("8. Custom MCP method call")
            print("0. Exit")
            
            choice = input("\nSelect option: ").strip()
            
            if choice == '0':
                print("Goodbye! 👋")
                break
            elif choice == '1':
                self.test_health()
            elif choice == '2':
                self.get_token()
            elif choice == '3':
                self.test_initialize()
            elif choice == '4':
                self.test_list_tools()
            elif choice == '5':
                self.test_company_search()
            elif choice == '6':
                self.test_find_competitors()
            elif choice == '7':
                self.run_all_tests()
            elif choice == '8':
                method = input("Enter MCP method: ").strip()
                params_str = input("Enter params as JSON (or press Enter for {}): ").strip()
                try:
                    params = json.loads(params_str) if params_str else {}
                    result = self.call_mcp(method, params)
                    print(json.dumps(result, indent=2))
                except json.JSONDecodeError:
                    print("❌ Invalid JSON")
            else:
                print("❌ Invalid option")
            
            if choice != '0':
                input("\nPress Enter to continue...")

def main():
    print("🚀 MCP Server Interactive Tester")
    print("-" * 40)
    
    # Get server URL and API key
    if len(sys.argv) > 2:
        server_url = sys.argv[1]
        api_key = sys.argv[2]
    else:
        server_url = input("Enter server URL (or press Enter for http://localhost:3000): ").strip()
        if not server_url:
            server_url = "http://localhost:3000"
        
        api_key = os.environ.get('API_KEY', '')
        if not api_key:
            api_key = input("Enter your API key: ").strip()
    
    if not api_key:
        print("❌ API key is required!")
        sys.exit(1)
    
    # Create tester and run
    tester = MCPTester(server_url, api_key)
    tester.interactive_menu()

if __name__ == "__main__":
    main()
