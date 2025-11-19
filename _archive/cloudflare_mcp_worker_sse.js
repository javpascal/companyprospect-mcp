// Cloudflare Worker for MCP with SSE support
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
    if (url.pathname === '/health') {
      return new Response(JSON.stringify({ status: 'ok', service: 'nummary-mcp' }), {
        headers: { ...corsHeaders, 'Content-Type': 'application/json' }
      });
    }

    // Handle SSE endpoint for MCP
    if (url.pathname === '/mcp' && request.method === 'GET') {
      // SSE headers
      const headers = new Headers({
        ...corsHeaders,
        'Content-Type': 'text/event-stream',
        'Cache-Control': 'no-cache',
        'Connection': 'keep-alive',
      });

      // Create a readable stream for SSE
      const stream = new ReadableStream({
        async start(controller) {
          const encoder = new TextEncoder();
          
          // Helper to send SSE message
          const sendMessage = (data) => {
            controller.enqueue(encoder.encode(`data: ${JSON.stringify(data)}\n\n`));
          };

          // Send initial connection event
          sendMessage({ type: 'connection', status: 'connected' });

          // Wait for incoming messages from client
          // In SSE, client sends requests via POST to a different endpoint
          // For now, we'll just keep the connection open
          
          // Keep connection alive with periodic heartbeat
          const heartbeatInterval = setInterval(() => {
            try {
              controller.enqueue(encoder.encode(':heartbeat\n\n'));
            } catch (e) {
              clearInterval(heartbeatInterval);
            }
          }, 30000);

          // Handle connection close
          request.signal.addEventListener('abort', () => {
            clearInterval(heartbeatInterval);
            controller.close();
          });
        }
      });

      return new Response(stream, { headers });
    }

    // Handle MCP RPC requests
    if (url.pathname === '/mcp/rpc' && request.method === 'POST') {
      return handleMCPRequest(request, env, corsHeaders);
    }

    // Handle standard MCP POST (backward compatibility)
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
    console.log('Request body:', JSON.stringify(body));

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
