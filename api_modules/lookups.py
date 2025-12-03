"""
CompanyProspect Lookups Module
==============================
Functions for looking up companies by name/query.
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
    limit: int = 10
) -> Dict[str, Any]:
    """
    Query ClickHouse for a single lookup.
    
    Args:
        query: Search term (company name)
        clickhouse_key_id: ClickHouse API key ID
        clickhouse_key_secret: ClickHouse API key secret
        limit: Maximum number of results to return (default 10, max 100)
    
    Returns:
        Dict with 'columns' and 'rows' (limited to `limit` rows)
    """
    if not query:
        return {'columns': [], 'rows': []}

    async with httpx.AsyncClient() as client:
        response = await client.get(
            f'https://queries.clickhouse.cloud/run/{LOOKUP_ENDPOINT}',
            params={'format': 'JSONCompact', 'param_query': query},
            headers={'Content-Type': 'application/json'},
            auth=(clickhouse_key_id, clickhouse_key_secret)
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
    dedupe: bool = True
) -> List[Dict[str, Any]]:
    """
    Run multiple lookups concurrently.
    
    Args:
        queries: List of search terms
        clickhouse_key_id: ClickHouse API key ID
        clickhouse_key_secret: ClickHouse API key secret
        limit: Maximum number of results per query (default 10, max 100)
        dedupe: Remove duplicate company IDs across results (default True)
    
    Returns:
        List of dicts with 'query' and 'result' for each input (deduplicated by comp_id)
    """
    if not queries:
        return []
    
    tasks = [
        lookup(q, clickhouse_key_id, clickhouse_key_secret, limit) 
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

