

API_URL = 'https://api.nummary.co'
API_KEY = 'nm_92051a269374f2c79569b3e07231dbd5'
API_USER = 'bba3be65-fe5e-4ff9-9951-24a0cb2c912c'


import os, requests
from fastmcp import FastMCP

mcp = FastMCP("nummary-mcp")

def _get(path, params=None):
    r = requests.get(
        f"{API_URL.rstrip('/')}/{path.lstrip('/')}",
        params=params or {},
        headers={
            # "Authorization": f"Bearer {API_KEY}", "Accept": "application/json"
            'X-Api-Key':API_KEY,
            'X-User-Id':API_USER,
        },
        timeout=20,
    )
    r.raise_for_status()
    return r.json()

def _post(path: str, data=None):
    r = requests.post(
        f"{API_URL.rstrip('/')}/{path.lstrip('/')}",
        json=data or {},
        headers={
            # "Authorization": f"Bearer {API_KEY}", "Accept": "application/json"
            'X-Api-Key':API_KEY,
            'X-User-Id':API_USER,
        },
        timeout=20,
    )
    r.raise_for_status()
    return r.json()


@mcp.tool()
def company_typeahead(query: str):
    """Busca empresas por textp"""
    return _post("/app/type/company", {"query": query})

if __name__ == "__main__":
    # Ejecuta el servidor por STDIO (ideal para desarrollo/local)
    # mcp.run()
    mcp.run(transport="http", host="127.0.0.1", port=3333)