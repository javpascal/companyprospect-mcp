"""
CompanyProspect Lookalikes Module
=================================
Functions for finding similar companies using embeddings.

Returns: comp_id, comp_slug, comp_name, comp_web, dist
"""

import asyncio
import httpx
from typing import Dict, Any, List, Optional, Callable


# =============================================================================
# CLICKHOUSE ENDPOINTS
# =============================================================================

LOOKALIKE_FROM_IDS_ENDPOINT = '140e404a-0b69-47e6-9432-6633bdd89ce5'
LOOKALIKE_FROM_TERM_ENDPOINT = '66327799-c11f-4777-8cac-09e4e359fbff'


# =============================================================================
# LOOKALIKE FUNCTIONS
# =============================================================================

async def lookalike_from_ids(
    company_ids: List[int],
    clickhouse_key_id: str,
    clickhouse_key_secret: str,
    filter_hc: Optional[int] = None,
    filter_cc2: Optional[List[str]] = None,
    size_weight: float = 0.20,
    limit: int = 100
) -> Dict[str, Any]:
    """
    Query ClickHouse for lookalike companies for a list of comp_ids.
    
    Args:
        company_ids: List of company IDs to find lookalikes for
        clickhouse_key_id: ClickHouse API key ID
        clickhouse_key_secret: ClickHouse API key secret
        filter_hc: Minimum headcount filter (optional)
        filter_cc2: Country code filter list (optional)
        size_weight: Bias toward larger companies (0.0 - 0.3, default 0.20)
            - 0.0       = pure similarity search (no size bias)
            - 0.0 - 0.1 = light size bias
            - 0.1 - 0.2 = pronounced size bias
            - 0.2 - 0.3 = heavy size bias
        limit: Maximum number of results to return (default 100, max 1000)
    
    Returns:
        Dict with 'columns' and 'rows' (limited to `limit` rows)
    """
    if not company_ids:
        return {'columns': [], 'rows': []}
    
    # Build query variables with optional filters
    query_variables = {
        'company_ids': company_ids,
        'max_log_hc': 6.0,
        'size_weight': size_weight,
        'filter_hc': filter_hc if filter_hc is not None else 0,
        'filter_cc2': filter_cc2 if filter_cc2 else [],
        'limit': min(limit, 1000),
    }
    
    async with httpx.AsyncClient(timeout=120.0) as client:
        response = await client.post(
            f'https://queries.clickhouse.cloud/run/{LOOKALIKE_FROM_IDS_ENDPOINT}',
            params={'format': 'JSONCompact'},
            headers={
                'Content-Type': 'application/json',
                'x-clickhouse-endpoint-version': '2',
            },
            auth=(clickhouse_key_id, clickhouse_key_secret),
            json={'queryVariables': query_variables}
        )
        
    if response.status_code == 200:
        result = response.json()
        rows = result.get('data', [])
        capped_limit = min(limit, 1000)  # Cap at 1000
        return {
            'columns': [col['name'] for col in result.get('meta', [])],
            'rows': rows[:capped_limit]
        }
    
    return {
        'company_ids': company_ids,
        'error': f'Status {response.status_code}',
        'detail': response.text[:500] if response.text else 'No response body',
        'query_variables': query_variables
    }


async def lookalike_from_term(
    query: str,
    clickhouse_key_id: str,
    clickhouse_key_secret: str,
    embed_fn: Callable[[List[str]], List],
    size_weight: float = 0.20,
    limit: int = 100
) -> Dict[str, Any]:
    """
    Query ClickHouse for lookalike companies for a single term.
    
    Args:
        query: Search term to find similar companies
        clickhouse_key_id: ClickHouse API key ID
        clickhouse_key_secret: ClickHouse API key secret
        embed_fn: Function to generate embeddings (takes list of strings, returns list of embeddings)
        size_weight: Bias toward larger companies (0.0 - 0.3, default 0.20)
            - 0.0       = pure similarity search (no size bias)
            - 0.0 - 0.1 = light size bias
            - 0.1 - 0.2 = pronounced size bias
            - 0.2 - 0.3 = heavy size bias
        limit: Maximum number of results to return (default 100, max 1000)
    
    Returns:
        Dict with 'columns' and 'rows' (limited to `limit` rows)
    """
    if not query:
        return {'columns': [], 'rows': []}

    # Get embedding with timeout - run in thread pool to avoid blocking async loop
    loop = asyncio.get_event_loop()
    try:
        query_emb = await asyncio.wait_for(
            loop.run_in_executor(None, lambda: embed_fn([query])[0].tolist()),
            timeout=120.0  # 2 minute timeout for embedding (cold start can be slow)
        )
    except asyncio.TimeoutError:
        return {
            'query': query,
            'error': 'Embedding timeout',
            'detail': 'Embedding generation timed out after 120 seconds'
        }
    except Exception as e:
        return {
            'query': query,
            'error': 'Embedding failed',
            'detail': str(e)[:500]
        }
    
    async with httpx.AsyncClient(timeout=90.0) as client:
        response = await client.post(
            f'https://queries.clickhouse.cloud/run/{LOOKALIKE_FROM_TERM_ENDPOINT}',
            params={'format': 'JSONCompact'},
            headers={
                'Content-Type': 'application/json',
                'x-clickhouse-endpoint-version': '2',
            },
            auth=(clickhouse_key_id, clickhouse_key_secret),
            json={
                'queryVariables': {
                    'query': query_emb,
                    'max_log_hc': 6.0,
                    'size_weight': size_weight,
                    'limit': min(limit, 1000),
                }
            }
        )
        
    if response.status_code == 200:
        result = response.json()
        rows = result.get('data', [])
        capped_limit = min(limit, 1000)  # Cap at 1000
        return {
            'columns': [col['name'] for col in result.get('meta', [])],
            'rows': rows[:capped_limit]
        }
    
    return {
        'query': query,
        'error': f'Status {response.status_code}',
        'detail': response.text[:500] if response.text else 'No response body'
    }

