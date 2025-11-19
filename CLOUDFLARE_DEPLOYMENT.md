# 🚀 Deployment en Cloudflare para OpenAI Agent Builder

## ✅ Respuesta a tu Pregunta

**SÍ**, puedes hacer el deployment en Cloudflare y usarlo en OpenAI Agent Builder, pero con algunas consideraciones:

### 🔄 Flujo de Integración:
1. **Deploy en Cloudflare Workers** → API REST
2. **Configurar en OpenAI Agent Builder** → Como función externa
3. **Usar en conversaciones** → OpenAI llama a tu API

## 🛠️ Opciones de Deployment en Cloudflare

### Opción 1: Cloudflare Workers (Recomendado)

**Ventajas:**
- ✅ Serverless, sin servidor que mantener
- ✅ Global CDN, latencia baja
- ✅ Escalabilidad automática
- ✅ Gratis hasta 100,000 requests/día
- ✅ Fácil integración con OpenAI

**Desventajas:**
- ❌ Limitado a 10ms CPU time por request
- ❌ No puede mantener conexiones persistentes
- ❌ Limitado a JavaScript/TypeScript

### Opción 2: Cloudflare Pages con Functions

**Ventajas:**
- ✅ Soporte para Python con Pyodide
- ✅ Más flexibilidad
- ✅ Mejor para lógica compleja

**Desventajas:**
- ❌ Más complejo de configurar
- ❌ Limitaciones de Pyodide

## 🚀 Deployment en Cloudflare Workers

### Paso 1: Instalar Wrangler

```bash
npm install -g wrangler
```

### Paso 2: Login en Cloudflare

```bash
wrangler login
```

### Paso 3: Configurar Variables de Entorno

```bash
# En Cloudflare Dashboard o con wrangler
wrangler secret put NUMMMARY_API_KEY
wrangler secret put NUMMMARY_API_USER
```

### Paso 4: Deploy

```bash
# Deploy a staging
npm run deploy:staging

# Deploy a production
npm run deploy:production
```

### Paso 5: Probar el Deployment

```bash
# Test local
npm run dev

# Test en staging
curl https://nummary-mcp-staging.workers.dev/health

# Test de la función
curl -X POST https://nummary-mcp-staging.workers.dev/company_typeahead \
  -H "Content-Type: application/json" \
  -d '{"query": "apple"}'
```

## 🔧 Integración con OpenAI Agent Builder

### Método 1: OpenAI Function Calling

```python
import openai
from openai import OpenAI

client = OpenAI(api_key="tu_openai_api_key")

# Definir función que llama a tu Cloudflare Worker
def company_typeahead(query):
    import requests
    response = requests.post(
        "https://nummary-mcp.workers.dev/company_typeahead",
        json={"query": query}
    )
    return response.json()

# Configurar para OpenAI
functions = [
    {
        "name": "company_typeahead",
        "description": "Busca empresas que coincidan con el query proporcionado",
        "parameters": {
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

# Usar en conversación
response = client.chat.completions.create(
    model="gpt-4o-mini",
    messages=[
        {"role": "user", "content": "Busca empresas que contengan 'apple'"}
    ],
    functions=functions,
    function_call="auto"
)
```

### Método 2: OpenAI Assistant con Function Calling

1. **Crear Assistant en OpenAI Studio**
2. **Agregar función externa:**
   ```json
   {
     "name": "company_typeahead",
     "description": "Busca empresas que coincidan con el query proporcionado",
     "parameters": {
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
   ```
3. **Configurar webhook o usar OpenAI Functions**

### Método 3: OpenAI Actions (Recomendado para Agent Builder)

```yaml
# openapi.yaml para OpenAI Actions
openapi: 3.0.0
info:
  title: Nummary MCP API
  version: 1.0.0
  description: API para búsqueda de empresas usando Nummary
servers:
  - url: https://nummary-mcp.workers.dev
paths:
  /company_typeahead:
    post:
      summary: Buscar empresas
      description: Busca empresas que coincidan con el query proporcionado
      requestBody:
        required: true
        content:
          application/json:
            schema:
              type: object
              properties:
                query:
                  type: string
                  description: Término de búsqueda para encontrar empresas
              required:
                - query
      responses:
        '200':
          description: Lista de empresas encontradas
          content:
            application/json:
              schema:
                type: object
                properties:
                  data:
                    type: array
                    items:
                      type: object
                      properties:
                        name:
                          type: string
                        web:
                          type: string
                        cc2:
                          type: string
                        nu_rank:
                          type: number
```

## 🔒 Configuración de Seguridad

### Variables de Entorno en Cloudflare

```bash
# Configurar secrets
wrangler secret put NUMMMARY_API_KEY
wrangler secret put NUMMMARY_API_USER

# Verificar configuración
wrangler secret list
```

### CORS y Rate Limiting

```javascript
// En cloudflare_worker.js
const corsHeaders = {
  'Access-Control-Allow-Origin': 'https://platform.openai.com',
  'Access-Control-Allow-Methods': 'GET, POST, OPTIONS',
  'Access-Control-Allow-Headers': 'Content-Type, Authorization',
};

// Rate limiting (opcional)
const rateLimit = {
  requests: 100,
  window: 60, // seconds
};
```

## 📊 Monitoreo y Logs

### Cloudflare Analytics

```bash
# Ver analytics
wrangler tail

# Ver logs en tiempo real
wrangler tail --format=pretty
```

### Health Check

```bash
# Endpoint de health check
curl https://nummary-mcp.workers.dev/health
```

## 🚀 Script de Deployment Automatizado

```bash
#!/bin/bash
# deploy_cloudflare.sh

echo "🚀 Deploying Nummary MCP to Cloudflare..."

# Verificar que wrangler esté instalado
if ! command -v wrangler &> /dev/null; then
    echo "❌ Wrangler no está instalado. Instalando..."
    npm install -g wrangler
fi

# Login si es necesario
wrangler whoami || wrangler login

# Deploy a staging
echo "📦 Deploying to staging..."
wrangler deploy --env staging

# Test staging
echo "🧪 Testing staging deployment..."
curl -X POST https://nummary-mcp-staging.workers.dev/company_typeahead \
  -H "Content-Type: application/json" \
  -d '{"query": "test"}' \
  --max-time 10

if [ $? -eq 0 ]; then
    echo "✅ Staging test passed. Deploying to production..."
    wrangler deploy --env production
    echo "🎉 Production deployment completed!"
else
    echo "❌ Staging test failed. Aborting production deployment."
    exit 1
fi
```

## 🔄 Flujo Completo de Integración

### 1. Deploy en Cloudflare
```bash
npm run deploy:production
```

### 2. Configurar en OpenAI Agent Builder
1. Crear nuevo Agent
2. Agregar función externa
3. Configurar endpoint: `https://nummary-mcp.workers.dev/company_typeahead`
4. Definir parámetros JSON

### 3. Usar en Conversaciones
```
Usuario: "Busca empresas que contengan 'apple'"
Agent: [Llama a tu función] → Cloudflare Worker → Nummary API
Agent: "Encontré estas empresas: Apple Inc. (US, ranking 4)..."
```

## 📝 Checklist de Deployment

- [ ] Instalar Wrangler
- [ ] Login en Cloudflare
- [ ] Configurar variables de entorno
- [ ] Deploy a staging
- [ ] Probar staging
- [ ] Deploy a production
- [ ] Configurar en OpenAI Agent Builder
- [ ] Probar integración completa

## 🎯 Ventajas de Cloudflare + OpenAI

1. **Global CDN**: Latencia baja desde cualquier lugar
2. **Serverless**: Sin servidor que mantener
3. **Escalabilidad**: Automática según demanda
4. **Costo**: Gratis hasta 100k requests/día
5. **Integración**: Fácil con OpenAI Function Calling
6. **Monitoreo**: Analytics integrados

---

**¡Sí, puedes usar Cloudflare + OpenAI Agent Builder perfectamente! 🚀**
