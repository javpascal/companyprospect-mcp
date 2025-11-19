# MCP de Nummary en Cloudflare

## Descripción
Servidor MCP (Model Context Protocol) desplegado en Cloudflare Workers que proporciona acceso a las APIs de Nummary.

## URL de Producción
```
https://nummary-mcp.nummary-analytics.workers.dev/mcp
```

## Endpoints Disponibles

### Health Check
```bash
GET https://nummary-mcp.nummary-analytics.workers.dev/health
```

### MCP Protocol
```bash
POST https://nummary-mcp.nummary-analytics.workers.dev/mcp
```

## Herramientas Disponibles

### company_typeahead
Busca empresas que coincidan con el query proporcionado.

**Parámetros:**
- `query` (string): Término de búsqueda para encontrar empresas

**Ejemplo sin autenticación:**
```bash
curl -X POST https://nummary-mcp.nummary-analytics.workers.dev/mcp \
  -H "Content-Type: application/json" \
  -d '{
    "jsonrpc": "2.0",
    "id": 1,
    "method": "tools/call",
    "params": {
      "name": "company_typeahead",
      "arguments": {
        "query": "factorial"
      }
    }
  }'
```

**Ejemplo con Bearer token:**
```bash
curl -X POST https://nummary-mcp.nummary-analytics.workers.dev/mcp \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer nummary-mcp-token-2024" \
  -d '{
    "jsonrpc": "2.0",
    "id": 1,
    "method": "tools/call",
    "params": {
      "name": "company_typeahead",
      "arguments": {
        "query": "factorial"
      }
    }
  }'
```

## Métodos MCP Soportados

- `initialize`: Inicializa la conexión MCP
- `tools/list`: Lista las herramientas disponibles
- `tools/call`: Ejecuta una herramienta

## Autenticación

El servidor MCP soporta autenticación opcional con Bearer token:
- **Sin autenticación**: El servidor acepta peticiones sin token (backward compatible)
- **Con autenticación**: Si se proporciona un token, debe ser válido
- **Token válido**: `Bearer nummary-mcp-token-2024`

## Configuración en OpenAI Agent Builder

### Opción 1: Sin autenticación
1. Ve a OpenAI Agent Builder / ChatGPT Developer Mode
2. Crea un nuevo conector MCP
3. Ingresa la URL: `https://nummary-mcp.nummary-analytics.workers.dev/mcp`
4. Authentication: "No authentication"

### Opción 2: Con Bearer token
1. Ve a OpenAI Agent Builder / ChatGPT Developer Mode
2. Crea un nuevo conector MCP
3. Ingresa la URL: `https://nummary-mcp.nummary-analytics.workers.dev/mcp`
4. Authentication: "Bearer"
5. Token: `nummary-mcp-token-2024`

## Desarrollo Local

### Requisitos
- Node.js 18+
- Wrangler CLI

### Instalación
```bash
npm install -g wrangler
```

### Deployment
```bash
npx wrangler deploy
```

### Logs
```bash
npx wrangler tail
```

## Estructura del Proyecto

```
/agent/
├── cloudflare_mcp_worker.js  # Worker principal de Cloudflare
├── wrangler.toml             # Configuración de Wrangler
├── package.json              # Dependencias del proyecto
└── README.md                 # Este archivo
```

## Notas

- El MCP está configurado para aceptar peticiones de cualquier origen (CORS habilitado)
- Las credenciales de la API de Nummary están incluidas en el worker
- El protocolo MCP utiliza JSON-RPC 2.0