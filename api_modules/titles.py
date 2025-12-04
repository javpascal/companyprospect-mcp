"""
CompanyProspect Titles Module
=============================
Functions for looking up job titles using semantic search.

Returns: title_id, title_name, supertitle_id, function_id, function_name, dist
"""

import asyncio
import httpx
from typing import Dict, Any, List, Callable


# =============================================================================
# CLICKHOUSE ENDPOINTS
# =============================================================================

TITLE_LOOKUP_ENDPOINT = '06bb0080-938c-4a3d-bf52-dc59bfd85675'


# =============================================================================
# TITLE FUNCTIONS
# =============================================================================

async def lookup_title(
    query: str,
    clickhouse_key_id: str,
    clickhouse_key_secret: str,
    embed_fn: Callable[[List[str]], List],
    limit: int = 10
) -> Dict[str, Any]:
    """
    Query ClickHouse for similar job titles using semantic search.
    
    Args:
        query: Search term for job title (e.g., 'founder', 'data scientist', 'sales manager')
        clickhouse_key_id: ClickHouse API key ID
        clickhouse_key_secret: ClickHouse API key secret
        embed_fn: Function to generate embeddings (takes list of strings, returns list of embeddings)
        limit: Maximum number of results to return (default 10, max 100)
    
    Returns:
        Dict with 'columns' [title_id, title_name, supertitle_id, function_id, function_name, dist] and 'rows'
    """
    if not query:
        return {'columns': [], 'rows': []}

    # Get embedding as list for queryVariables
    query_emb = embed_fn([query])[0].tolist()
    
    async with httpx.AsyncClient() as client:
        response = await client.post(
            f'https://queries.clickhouse.cloud/run/{TITLE_LOOKUP_ENDPOINT}',
            params={'format': 'JSONCompact'},
            headers={
                'Content-Type': 'application/json',
                'x-clickhouse-endpoint-version': '2',
            },
            auth=(clickhouse_key_id, clickhouse_key_secret),
            json={
                'queryVariables': {
                    'query': query_emb,
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


async def lookup_title_many(
    queries: List[str],
    clickhouse_key_id: str,
    clickhouse_key_secret: str,
    embed_fn: Callable[[List[str]], List],
    limit: int = 10,
    dedupe: bool = False
) -> List[Dict[str, Any]]:
    """
    Run multiple title lookups concurrently.
    
    Args:
        queries: List of search terms for job titles
        clickhouse_key_id: ClickHouse API key ID
        clickhouse_key_secret: ClickHouse API key secret
        embed_fn: Function to generate embeddings (takes list of strings, returns list of embeddings)
        limit: Maximum number of results per query (default 10, max 100)
        dedupe: Remove duplicate title IDs across results (default True)
    
    Returns:
        List of dicts with 'query' and 'result' for each input.
        Each result has 'columns' [title_id, title_name, supertitle_id, function_id, function_name, dist] and 'rows'.
        Results are deduplicated by title_id across all queries.
    """
    if not queries:
        return []
    
    tasks = [
        lookup_title(q, clickhouse_key_id, clickhouse_key_secret, embed_fn, limit)
        for q in queries
    ]
    results = await asyncio.gather(*tasks)
    
    # Deduplicate by title_id (first column) across all results
    if dedupe:
        seen_ids = set()
        deduped_results = []
        for q, r in zip(queries, results):
            if 'rows' in r:
                unique_rows = []
                for row in r['rows']:
                    title_id = row[0] if row else None
                    if title_id and title_id not in seen_ids:
                        seen_ids.add(title_id)
                        unique_rows.append(row)
                deduped_results.append({
                    'query': q,
                    'result': {**r, 'rows': unique_rows}
                })
            else:
                deduped_results.append({'query': q, 'result': r})
        return deduped_results
    
    return [{'query': q, 'result': r} for q, r in zip(queries, results)]

