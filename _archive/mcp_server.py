import os, requests
from fastmcp import FastMCP
from typing import Optional, Dict, Any, List
import logging
from config import API_CONFIG, MCP_CONFIG, LOGGING_CONFIG, get_api_headers, VALIDATION_CONFIG

# Configurar logging
logging.basicConfig(
    level=getattr(logging, LOGGING_CONFIG["level"]),
    format=LOGGING_CONFIG["format"],
    datefmt=LOGGING_CONFIG["datefmt"]
)
logger = logging.getLogger(__name__)

mcp = FastMCP("nummary-mcp")

def _make_request(method: str, path: str, data: Optional[Dict] = None, timeout: Optional[int] = None) -> Dict[str, Any]:
    """
    Realiza una petición HTTP a la API de Nummary con manejo de errores mejorado.
    """
    try:
        url = f"{API_CONFIG['url'].rstrip('/')}/{path.lstrip('/')}"
        headers = get_api_headers()
        timeout = timeout or MCP_CONFIG["timeout"]
        
        logger.info(f"Making {method} request to {url}")
        
        if method.upper() == "GET":
            response = requests.get(url, headers=headers, timeout=timeout)
        elif method.upper() == "POST":
            response = requests.post(url, json=data or {}, headers=headers, timeout=timeout)
        elif method.upper() == "PUT":
            response = requests.put(url, json=data or {}, headers=headers, timeout=timeout)
        elif method.upper() == "DELETE":
            response = requests.delete(url, headers=headers, timeout=timeout)
        else:
            raise ValueError(f"Unsupported HTTP method: {method}")
        
        response.raise_for_status()
        return response.json()
        
    except requests.exceptions.Timeout:
        logger.error(f"Timeout error for {method} {path}")
        return {"error": "Request timeout", "message": "La petición tardó demasiado tiempo"}
    except requests.exceptions.ConnectionError:
        logger.error(f"Connection error for {method} {path}")
        return {"error": "Connection error", "message": "No se pudo conectar con la API"}
    except requests.exceptions.HTTPError as e:
        logger.error(f"HTTP error for {method} {path}: {e}")
        return {"error": "HTTP error", "message": f"Error HTTP {e.response.status_code}: {e.response.text}"}
    except Exception as e:
        logger.error(f"Unexpected error for {method} {path}: {e}")
        return {"error": "Unexpected error", "message": str(e)}

@mcp.tool
def company_typeahead(query: str) -> Dict[str, Any]:
    """
    Busca empresas que coincidan con el query proporcionado.
    
    Args:
        query: Término de búsqueda para encontrar empresas
        
    Returns:
        Diccionario con los resultados de la búsqueda de empresas
    """
    if not query or not query.strip():
        return {"error": "Invalid input", "message": "El query no puede estar vacío"}
    
    return _make_request("POST", "/app/type/company", {"query": query.strip()})
if __name__ == "__main__":
    # STDIO mode (lo lanzará MCPServerStdio)
    mcp.run()