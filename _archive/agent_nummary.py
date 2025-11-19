
API_URL = 'https://api.nummary.co'
API_KEY = 'nm_92051a269374f2c79569b3e07231dbd5'
API_USER = 'bba3be65-fe5e-4ff9-9951-24a0cb2c912c'
# agent_nummary.py
import os
from agents import Agent, Runner

# Imports compatibles según versión
try:
    from agents.mcp import MCPServerStdio, MCPServerStdioParams
except ImportError:
    from agents.mcp.server import MCPServerStdio, MCPServerStdioParams  # fallback


ABS_PATH = "/Users/jpastrana/Desktop/mcp_server.py"  # <- pon la ruta absoluta a mcp_server.py
ENV = {
    "API_URL":  "https://api.nummary.co",
    "API_KEY":  API_KEY,
    "API_USER": API_USER,
}

def make_stdio_params():
    """
    Crea MCPServerStdioParams probando distintos nombres de campo
    (según la versión del SDK): command / executable / cmd / path + argv.
    """
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

if __name__ == "__main__":
    stdio_params = make_stdio_params()

    mcp_server = MCPServerStdio(
        params=stdio_params,
        name="nummary-mcp",
        # tunables opcionales (si existen en tu build):
        # client_session_timeout_seconds=15,
        # max_retry_attempts=1,
    )

    agent = Agent(
        name="Analista Nummary",
        instructions="Usa company_typeahead cuando te lo pida.",
        tools=[mcp_server],
        model="gpt-5.1-mini",
    )

    res = Runner.run_sync(agent, "Usa company_typeahead('factorial') y dame 5 nombres.")
    print(res.final_output)