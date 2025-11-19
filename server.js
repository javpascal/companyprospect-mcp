import express from 'express';
import { McpServer } from '@modelcontextprotocol/sdk/server/mcp.js';
import { SSEServerTransport } from '@modelcontextprotocol/sdk/server/sse.js';
import { z } from 'zod';
import cors from 'cors';

const app = express();
app.use(cors());

const server = new McpServer({
    name: 'nummary-mcp',
    version: '1.0.0',
});

// Helper function to call Nummary API
async function callNummaryAPI(endpoint, body) {
    try {
        const response = await fetch(`https://api.nummary.co${endpoint}`, {
            method: 'POST',
            headers: {
                'X-Api-Key': 'nm_92051a269374f2c79569b3e07231dbd5',
                'X-User-Id': 'bba3be65-fe5e-4ff9-9951-24a0cb2c912c',
                'Accept': 'application/json',
                'Content-Type': 'application/json',
            },
            body: JSON.stringify(body)
        });

        if (!response.ok) {
            throw new Error(`Nummary API error: ${response.status}`);
        }

        return await response.json();
    } catch (error) {
        console.error(`Error calling Nummary API (${endpoint}):`, error);
        throw error;
    }
}

// Tool: company_typeahead
server.tool(
    'company_typeahead',
    'Busca empresas que coincidan con el query proporcionado',
    {
        query: z.string().describe('Término de búsqueda para encontrar empresas'),
    },
    async ({ query }) => {
        const result = await callNummaryAPI('/app/type/company', { query: query.trim() });
        return {
            content: [{ type: 'text', text: JSON.stringify(result, null, 2) }],
        };
    }
);

// Tool: find_competitors
server.tool(
    'find_competitors',
    'Busca competidores basándose en una lista de empresas y palabras clave',
    {
        context: z.array(
            z.object({
                type: z.enum(['company', 'keyword']).describe('Tipo de entidad (company o keyword)'),
                id: z.number().optional().describe('ID de la empresa (solo para type=company)'),
                text: z.string().describe('Nombre de la empresa o palabra clave'),
            })
        ).describe('Lista de empresas y palabras clave para buscar competidores'),
    },
    async ({ context }) => {
        const result = await callNummaryAPI('/app/naturalsearch', { context });
        return {
            content: [{ type: 'text', text: JSON.stringify(result, null, 2) }],
        };
    }
);

let transport;

app.get('/sse', async (req, res) => {
    console.log('New SSE connection');
    transport = new SSEServerTransport('/messages', res);
    await server.connect(transport);
});

app.post('/messages', async (req, res) => {
    console.log('New message');
    if (transport) {
        await transport.handlePostMessage(req, res);
    } else {
        res.status(400).json({ error: 'No active SSE connection' });
    }
});

const PORT = process.env.PORT || 3000;

if (process.env.NODE_ENV !== 'production') {
    app.listen(PORT, () => {
        console.log(`Server is running on port ${PORT}`);
    });
}

export default app;
