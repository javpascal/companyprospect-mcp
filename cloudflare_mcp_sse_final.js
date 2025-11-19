// Cloudflare Worker MCP with SSE support for Claude
export default {
  async fetch(request, env, ctx) {
    const url = new URL(request.url);

    // CORS headers
    const corsHeaders = {
      'Access-Control-Allow-Origin': '*',
      'Access-Control-Allow-Methods': 'GET, POST, OPTIONS',
      'Access-Control-Allow-Headers': 'Content-Type, Authorization',
    };

    // Handle CORS preflight
    if (request.method === 'OPTIONS') {
      return new Response(null, { headers: corsHeaders });
    }

    // Handle health check
    if (url.pathname === '/health' && request.method === 'GET') {
      return new Response(JSON.stringify({ status: 'ok', service: 'nummary-mcp' }), {
        headers: { ...corsHeaders, 'Content-Type': 'application/json' }
      });
    }

    // Handle MCP SSE endpoint
    if (url.pathname === '/mcp' && request.method === 'GET') {
      // Create SSE response
      const encoder = new TextEncoder();
      const stream = new ReadableStream({
        async start(controller) {
          // Send endpoint event
          const endpoint = `${url.origin}/mcp`;
          const event = `event: endpoint\ndata: ${endpoint}\n\n`;
          controller.enqueue(encoder.encode(event));

          // Keep connection alive
          const keepAlive = setInterval(() => {
            try {
              controller.enqueue(encoder.encode(':keepalive\n\n'));
            } catch (e) {
              clearInterval(keepAlive);
            }
          }, 30000);

          // Clean up on abort
          request.signal.addEventListener('abort', () => {
            clearInterval(keepAlive);
            controller.close();
          });
        }
      });

      return new Response(stream, {
        headers: {
          ...corsHeaders,
          'Content-Type': 'text/event-stream',
          'Cache-Control': 'no-cache',
          'Connection': 'keep-alive',
        }
      });
    }

    // Handle MCP POST requests
    if (url.pathname === '/mcp' && request.method === 'POST') {
      return handleMCPRequest(request, env, corsHeaders);
    }

    // 404 for other paths
    return new Response(JSON.stringify({ error: 'Not found' }), {
      status: 404,
      headers: { ...corsHeaders, 'Content-Type': 'application/json' }
    });
  },
};

async function handleMCPRequest(request, env, corsHeaders) {
  try {
    const body = await request.json();
    const method = body.method;
    const params = body.params || {};
    const requestId = body.id;

    console.log(`Handling MCP request: ${method}`);

    // Handle initialize
    if (method === 'initialize') {
      return new Response(JSON.stringify({
        jsonrpc: '2.0',
        id: requestId,
        result: {
          protocolVersion: '2024-11-05',
          capabilities: {
            tools: {},
            prompts: {}
          },
          serverInfo: {
            name: 'nummary-mcp',
            version: '1.0.0'
          }
        }
      }), {
        headers: { ...corsHeaders, 'Content-Type': 'application/json' }
      });
    }

    // Handle notifications/initialized
    if (method === 'notifications/initialized') {
      return new Response(JSON.stringify({
        jsonrpc: '2.0',
        id: requestId,
        result: {}
      }), {
        headers: { ...corsHeaders, 'Content-Type': 'application/json' }
      });
    }

    // Handle tools/list
    if (method === 'tools/list') {
      return new Response(JSON.stringify({
        jsonrpc: '2.0',
        id: requestId,
        result: {
          tools: [
            {
              name: 'company_typeahead',
              description: 'Busca empresas que coincidan con el query proporcionado',
              inputSchema: {
                type: 'object',
                properties: {
                  query: {
                    type: 'string',
                    description: 'Término de búsqueda para encontrar empresas'
                  }
                },
                required: ['query']
              }
            },
            {
              name: 'find_competitors',
              description: 'Busca competidores basándose en una lista de empresas y palabras clave',
              inputSchema: {
                type: 'object',
                properties: {
                  context: {
                    type: 'array',
                    description: 'Lista de empresas y palabras clave para buscar competidores',
                    items: {
                      type: 'object',
                      properties: {
                        type: {
                          type: 'string',
                          enum: ['company', 'keyword'],
                          description: 'Tipo de entidad (company o keyword)'
                        },
                        id: {
                          type: 'integer',
                          description: 'ID de la empresa (solo para type=company)'
                        },
                        text: {
                          type: 'string',
                          description: 'Nombre de la empresa o palabra clave'
                        }
                      },
                      required: ['type', 'text']
                    }
                  }
                },
                required: ['context']
              }
            }
          ]
        }
      }), {
        headers: { ...corsHeaders, 'Content-Type': 'application/json' }
      });
    }

    // Handle prompts/list
    if (method === 'prompts/list') {
      return new Response(JSON.stringify({
        jsonrpc: '2.0',
        id: requestId,
        result: {
          prompts: []
        }
      }), {
        headers: { ...corsHeaders, 'Content-Type': 'application/json' }
      });
    }

    // Handle tools/call
    if (method === 'tools/call') {
      const toolName = params.name;
      const args = params.arguments || {};

      console.log(`Calling tool: ${toolName} with args:`, args);

      if (toolName === 'company_typeahead') {
        const query = args.query;
        const result = await callNummaryAPI(query);

        return new Response(JSON.stringify({
          jsonrpc: '2.0',
          id: requestId,
          result: {
            content: [
              {
                type: 'text',
                text: JSON.stringify(result, null, 2)
              }
            ]
          }
        }), {
          headers: { ...corsHeaders, 'Content-Type': 'application/json' }
        });
      }

      if (toolName === 'find_competitors') {
        const context = args.context;
        const result = await callNummaryNaturalSearchAPI(context);

        return new Response(JSON.stringify({
          jsonrpc: '2.0',
          id: requestId,
          result: {
            content: [
              {
                type: 'text',
                text: JSON.stringify(result, null, 2)
              }
            ]
          }
        }), {
          headers: { ...corsHeaders, 'Content-Type': 'application/json' }
        });
      }

      // Tool not found
      return new Response(JSON.stringify({
        jsonrpc: '2.0',
        id: requestId,
        error: {
          code: -32601,
          message: `Tool '${toolName}' not found`
        }
      }), {
        status: 400,
        headers: { ...corsHeaders, 'Content-Type': 'application/json' }
      });
    }

    // Method not found
    return new Response(JSON.stringify({
      jsonrpc: '2.0',
      id: requestId,
      error: {
        code: -32601,
        message: `Method '${method}' not found`
      }
    }), {
      status: 400,
      headers: { ...corsHeaders, 'Content-Type': 'application/json' }
    });

  } catch (error) {
    console.error('Error handling MCP request:', error);
    return new Response(JSON.stringify({
      jsonrpc: '2.0',
      id: body?.id,
      error: {
        code: -32603,
        message: `Internal error: ${error.message}`
      }
    }), {
      status: 500,
      headers: { ...corsHeaders, 'Content-Type': 'application/json' }
    });
  }
}

async function callNummaryAPI(query) {
  try {
    const response = await fetch('https://api.nummary.co/app/type/company', {
      method: 'POST',
      headers: {
        'X-Api-Key': 'nm_92051a269374f2c79569b3e07231dbd5',
        'X-User-Id': 'bba3be65-fe5e-4ff9-9951-24a0cb2c912c',
        'Accept': 'application/json',
        'Content-Type': 'application/json',
      },
      body: JSON.stringify({ query: query.trim() })
    });

    if (!response.ok) {
      throw new Error(`Nummary API error: ${response.status}`);
    }

    return await response.json();

  } catch (error) {
    console.error('Error calling Nummary API:', error);
    return {
      error: 'API call failed',
      message: error.message
    };
  }
}

async function callNummaryNaturalSearchAPI(context) {
  try {
    const response = await fetch('https://api.nummary.co/app/naturalsearch', {
      method: 'POST',
      headers: {
        'X-Api-Key': 'nm_92051a269374f2c79569b3e07231dbd5',
        'X-User-Id': 'bba3be65-fe5e-4ff9-9951-24a0cb2c912c',
        'Accept': 'application/json',
        'Content-Type': 'application/json',
      },
      body: JSON.stringify({ context: context })
    });

    if (!response.ok) {
      throw new Error(`Nummary Natural Search API error: ${response.status}`);
    }

    return await response.json();

  } catch (error) {
    console.error('Error calling Nummary Natural Search API:', error);
    return {
      error: 'API call failed',
      message: error.message
    };
  }
}

