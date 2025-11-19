# -*- coding: utf-8 -*-
"""
Configuracion centralizada para el MCP de Nummary.
"""

import os

# Configuracion de la API de Nummary
API_CONFIG = {
    "url": "https://api.nummary.co",
    "key": "nm_92051a269374f2c79569b3e07231dbd5",
    "user": "bba3be65-fe5e-4ff9-9951-24a0cb2c912c",
}

# Configuracion del MCP
MCP_CONFIG = {
    "name": "nummary-mcp",
    "timeout": 20,
    "max_retries": 3,
    "log_level": "INFO",
}

# Configuracion de validacion
VALIDATION_CONFIG = {
    "max_companies_compare": 10,
    "min_companies_compare": 2,
    "max_search_limit": 100,
    "min_search_limit": 1,
    "max_news_limit": 50,
    "min_news_limit": 1,
}

# Configuracion de logging
LOGGING_CONFIG = {
    "level": MCP_CONFIG["log_level"],
    "format": "%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    "datefmt": "%Y-%m-%d %H:%M:%S",
}

def get_api_headers():
    """
    Retorna los headers necesarios para las peticiones a la API de Nummary.
    """
    return {
        "X-Api-Key": API_CONFIG["key"],
        "X-User-Id": API_CONFIG["user"],
        "Accept": "application/json",
        "Content-Type": "application/json"
    }

def get_mcp_env():
    """
    Retorna las variables de entorno para el MCP.
    """
    return {
        "API_URL": API_CONFIG["url"],
        "API_KEY": API_CONFIG["key"],
        "API_USER": API_CONFIG["user"],
        "MCP_TIMEOUT": str(MCP_CONFIG["timeout"]),
        "MCP_MAX_RETRIES": str(MCP_CONFIG["max_retries"]),
        "MCP_LOG_LEVEL": MCP_CONFIG["log_level"],
    }

def validate_config():
    """
    Valida que la configuracion sea correcta.
    """
    required_fields = ["url", "key", "user"]
    
    for field in required_fields:
        if not API_CONFIG[field]:
            print("Error: " + field + " no esta configurado")
            return False
    
    if not API_CONFIG["url"].startswith("http"):
        print("Error: API_URL debe ser una URL valida")
        return False
    
    if len(API_CONFIG["key"]) < 10:
        print("Error: API_KEY parece ser invalido")
        return False
    
    print("Configuracion valida")
    return True

if __name__ == "__main__":
    print("Configuracion del MCP de Nummary")
    print("=" * 40)
    
    print("API URL: " + API_CONFIG['url'])
    print("API Key: " + API_CONFIG['key'][:10] + "...")
    print("API User: " + API_CONFIG['user'])
    print("Timeout: " + str(MCP_CONFIG['timeout']) + "s")
    print("Log Level: " + MCP_CONFIG['log_level'])
    
    print("\n" + "=" * 40)
    validate_config()