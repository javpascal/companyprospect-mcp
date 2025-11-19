#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Ejemplo de uso del MCP de Nummary expandido.
Este archivo muestra como usar las diferentes herramientas disponibles.
"""

import asyncio
from agents import Agent, Runner

# Configuración del MCP
ABS_PATH = "/Users/jpastrana/Desktop/agent/mcp_server.py"
ENV = {
    "API_URL": "https://api.nummary.co",
    "API_KEY": "nm_92051a269374f2c79569b3e07231dbd5",
    "API_USER": "bba3be65-fe5e-4ff9-9951-24a0cb2c912c",
}

def make_stdio_params():
    """
    Crea MCPServerStdioParams probando distintos nombres de campo
    (según la versión del SDK): command / executable / cmd / path + argv.
    """
    from agents.mcp import MCPServerStdio, MCPServerStdioParams
    
    candidates = [
        {"command": "python", "args": [ABS_PATH], "env": ENV},
        {"executable": "python", "args": [ABS_PATH], "env": ENV},
        {"cmd": "python", "args": [ABS_PATH], "env": ENV},
        {"path": "python", "argv": [ABS_PATH], "env": ENV},
    ]
    last_err = None
    for c in candidates:
        try:
            return MCPServerStdioParams(**c)
        except TypeError as e:
            last_err = e
            continue
    raise RuntimeError(f"No pude construir MCPServerStdioParams con {candidates}. Último error: {last_err}")

def test_company_typeahead():
    """Prueba la función de búsqueda de empresas."""
    print("=== Probando company_typeahead ===")
    
    stdio_params = make_stdio_params()
    mcp_server = MCPServerStdio(params=stdio_params, name="nummary-mcp")
    
    agent = Agent(
        name="Analista Nummary",
        instructions="Usa company_typeahead para buscar empresas.",
        tools=[mcp_server],
        model="gpt-4o-mini",
    )
    
    res = Runner.run_sync(agent, "Busca empresas que contengan 'apple' usando company_typeahead")
    print(f"Resultado: {res.final_output}")
    print()


def run_comprehensive_analysis():
    """Ejecuta un análisis completo usando múltiples herramientas."""
    print("=== Análisis Completo ===")
    
    stdio_params = make_stdio_params()
    mcp_server = MCPServerStdio(params=stdio_params, name="nummary-mcp")
    
    agent = Agent(
        name="Analista Nummary Completo",
        instructions="""
        Eres un analista financiero experto. Usa las herramientas disponibles para:
        1. Mapear una empresa
        """,
        tools=[mcp_server],
        model="gpt-4o-mini",
    )
    
    res = Runner.run_sync(agent, """
    Realiza un análisis completo de empresas tecnológicas:
    1. Busca empresas que contengan 'graphext'
    """)
    print(f"Análisis completo: {res.final_output}")
    print()

if __name__ == "__main__":
    print("🚀 Iniciando pruebas del MCP de Nummary expandido...\n")
    
    try:
        # Ejecutar pruebas individuales
        test_company_typeahead()
        
        # Ejecutar análisis completo
        run_comprehensive_analysis()
        
        print("✅ Todas las pruebas completadas exitosamente!")
        
    except Exception as e:
        print(f"❌ Error durante las pruebas: {e}")
        import traceback
        traceback.print_exc()
