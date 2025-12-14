"""
CompanyProspect Lookups Module
==============================
Functions for looking up companies by name/query.

Returns: comp_id, comp_slug, comp_name, comp_web, dist
"""

import asyncio
import httpx
from typing import Dict, Any, List


# =============================================================================
# CLICKHOUSE ENDPOINTS
# =============================================================================

LOOKUP_ENDPOINT = '679eff13-08ef-48ef-9e6d-e1dd15a9d151'


# =============================================================================
# LOOKUP FUNCTIONS
# =============================================================================

async def lookup(
    query: str,
    clickhouse_key_id: str,
    clickhouse_key_secret: str,
    limit: int = 10,
    size_weight: float = 0.1
) -> Dict[str, Any]:
    """
    Query ClickHouse for a single lookup.
    
    Args:
        query: Search term (company name)
        clickhouse_key_id: ClickHouse API key ID
        clickhouse_key_secret: ClickHouse API key secret
        limit: Maximum number of results to return (default 10, max 100)
        size_weight: Bias toward larger companies (0.0-0.3, default 0.1)
            - 0.0       = pure similarity search (no size bias)
            - 0.0 - 0.1 = light size bias
            - 0.1 - 0.2 = pronounced size bias
            - 0.2 - 0.3 = heavy size bias
    
    Returns:
        Dict with 'columns' [comp_id, comp_slug, comp_name, comp_web, dist] and 'rows'
    """
    if not query:
        return {'columns': [], 'rows': []}

    async with httpx.AsyncClient(timeout=60.0) as client:
        response = await client.post(
            f'https://queries.clickhouse.cloud/run/{LOOKUP_ENDPOINT}',
            params={'format': 'JSONCompact'},
            headers={
                'Content-Type': 'application/json',
                'x-clickhouse-endpoint-version': '2',
            },
            auth=(clickhouse_key_id, clickhouse_key_secret),
            json={
                'queryVariables': {
                    'query': query,
                    'max_log_hc': 6.0,
                    'size_weight': size_weight,
                    'limit': min(limit, 100),
                }
            }
        )
        
    if response.status_code == 200:
        result = response.json()
        rows = result.get('data', [])
        capped_limit = min(limit, 100)  # Cap at 100
        return {
            'columns': [col['name'] for col in result.get('meta', [])],
            'rows': rows[:capped_limit]
        }
    return {'query': query, 'error': f'Status {response.status_code}'}


async def lookup_many(
    queries: List[str],
    clickhouse_key_id: str,
    clickhouse_key_secret: str,
    limit: int = 10,
    size_weight: float = 0.1,
    dedupe: bool = True
) -> List[Dict[str, Any]]:
    """
    Run multiple lookups concurrently.
    
    Args:
        queries: List of search terms
        clickhouse_key_id: ClickHouse API key ID
        clickhouse_key_secret: ClickHouse API key secret
        limit: Maximum number of results per query (default 10, max 100)
        size_weight: Bias toward larger companies (0.0-0.3, default 0.1)
        dedupe: Remove duplicate company IDs across results (default True)
    
    Returns:
        List of dicts with 'query' and 'result' for each input.
        Each result has 'columns' [comp_id, comp_slug, comp_name, comp_web, dist] and 'rows'.
        Results are deduplicated by comp_id across all queries.
    """
    if not queries:
        return []
    
    tasks = [
        lookup(q, clickhouse_key_id, clickhouse_key_secret, limit, size_weight) 
        for q in queries
    ]
    results = await asyncio.gather(*tasks)
    
    # Deduplicate by comp_id (first column) across all results
    if dedupe:
        seen_ids = set()
        deduped_results = []
        for q, r in zip(queries, results):
            if 'rows' in r:
                unique_rows = []
                for row in r['rows']:
                    comp_id = row[0] if row else None
                    if comp_id and comp_id not in seen_ids:
                        seen_ids.add(comp_id)
                        unique_rows.append(row)
                deduped_results.append({
                    'query': q,
                    'result': {**r, 'rows': unique_rows}
                })
            else:
                deduped_results.append({'query': q, 'result': r})
        return deduped_results
    
    return [{'query': q, 'result': r} for q, r in zip(queries, results)]
