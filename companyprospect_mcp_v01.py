"""
CompanyProspect MCP API v01
===========================
API endpoints for company lookup and embeddings.
"""

# =============================================================================
# IMPORTS
# =============================================================================

# Standard library
import os
import re
import json
import time
import asyncio
import base64
from typing import List, Dict, Optional, Any
from collections import Counter

# Third party
import numpy as np
import httpx
import torch
from huggingface_hub import snapshot_download
from sentence_transformers import SentenceTransformer
from starlette.responses import JSONResponse
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

# Modal
import modal
from modal import Image, App, asgi_app, Secret


# =============================================================================
# CONFIGURATION
# =============================================================================

MODEL_MPNET = {
    'repo_id': 'sentence-transformers/all-mpnet-base-v2',
    'embedding_dim': 768,
    'context_size': 512,
}

MODEL_DIR = "/cache"
VOL_CACHE = modal.Volume.from_name("hf-hub-cache", create_if_missing=True)

CORS_ORIGINS = [
    "http://localhost:3000",
    "https://localhost:3000",
    "http://127.0.0.1:3000",
    "https://127.0.0.1:3000",
    "http://companyprospect.com",
    "https://companyprospect.com",
    "http://app.companyprospect.com",
    "https://app.companyprospect.com",
]


# =============================================================================
# MODAL IMAGE
# =============================================================================

python_image = (
    Image.debian_slim(python_version="3.10")
    .run_commands(
        "apt-get update",
        "apt-get install -y software-properties-common",
        "apt-add-repository non-free",
        "apt-add-repository contrib",
    )
    .pip_install(
        "boto3",
        "pyarrow",
        "fastparquet",
        "numpy",
        "pymongo[srv]",
        "motor[srv]",
        "clickhouse-connect",
        "openai",
        "typesense",
        "scikit-learn",
        "scipy==1.12",
        "huggingface-hub==0.27.1",
        "transformers[torch]",
        "sentencepiece",
        "sentence-transformers",
        "einops",
        "xformers",
        "accelerate",
        "cloudflare",
        "svgwrite",
        "httpx",
        "requests",
    )
    .env({"HF_HUB_CACHE": MODEL_DIR})
    .add_local_python_source("_remote_module_non_scriptable")
)


# =============================================================================
# MODAL APP & FASTAPI SETUP
# =============================================================================

app = App(name="companyprospect_mcp_v01")
web_app = FastAPI(title="CompanyProspect API", version="0.1.0")

web_app.add_middleware(
    CORSMiddleware,
    allow_origins=CORS_ORIGINS,
    allow_methods=["*"],
    allow_headers=["*"],
    allow_credentials=True,
)



# =============================================================================
# MODAL CLASSES
# =============================================================================

@app.cls(
    image=python_image,
    timeout=60,
    volumes={MODEL_DIR: VOL_CACHE},
    enable_memory_snapshot=True,
    min_containers=1,
    scaledown_window=300,
)
class GPUEmbedder:
    """Sentence transformer embedder with memory snapshot for fast cold starts."""
    
    @modal.enter(snap=True)
    def initialize(self):
        """Load model from cache (runs once, then snapshot is used)."""
        self.cache_path = snapshot_download(
            repo_id=MODEL_MPNET['repo_id'],
            cache_dir=MODEL_DIR,
            local_files_only=True
        )
        self.device = "cuda" if torch.cuda.is_available() else "cpu"
        self.model = SentenceTransformer(
            model_name_or_path=self.cache_path,
            trust_remote_code=True,
            cache_folder=MODEL_DIR,
            device=self.device
        )
        self.model.max_seq_length = MODEL_MPNET['context_size']
        self.model.eval()

    @modal.method()
    def embed_inputs(self, input_list: List[str]) -> np.ndarray:
        """Generate embeddings for a list of text inputs."""
        embeddings = self.model.encode(
            input_list,
            convert_to_tensor=True,
            normalize_embeddings=True,
            show_progress_bar=False
        )
        return embeddings.cpu().numpy().astype(np.float32)



# =============================================================================
# API FUNCTION
# =============================================================================

# =============================================================================
# REPORT GENERATOR (Long-running task)
# =============================================================================

S3_BUCKET = 'companyprospect'
S3_PREFIX = 'reports'

# TODO: Replace with actual ClickHouse endpoint UUID once created
CLICKHOUSE_REPORT_ENDPOINT = 'xxxxxxxx-xxxx-xxxx-xxxx-xxxxxxxxxxxx'

@app.function(
    image=python_image,
    timeout=600,  # 10 minutes max
    secrets=[
        Secret.from_name("secrets_clickhouse_api"),
        Secret.from_name("my-aws-secret"),
    ],
    region='us-east',
)
def generate_report(
    report_id: str,
    query_variables: Dict[str, Any],
    file_format: str = 'json',
    clickhouse_endpoint: str = None
) -> Dict[str, Any]:
    """
    Generate a report from ClickHouse and upload to S3.
    
    Args:
        report_id: Unique identifier for the report
        query_variables: Variables to pass to the query
        file_format: Output format ('json' or 'csv')
        clickhouse_endpoint: ClickHouse Cloud endpoint UUID (optional, uses default)
    
    Returns:
        Dict with 'url' (presigned S3 URL) and 'report_id'
    """
    import boto3
    import requests
    from datetime import datetime
    
    clickhouse_key_id = os.environ.get('key_id', 'NOT_FOUND')
    clickhouse_key_secret = os.environ.get('key_secret', 'NOT_FOUND')
    
    # Use default endpoint if not provided
    endpoint = clickhouse_endpoint or CLICKHOUSE_REPORT_ENDPOINT
    
    # 1. Query ClickHouse (or use mock data if placeholder endpoint)
    if endpoint == 'xxxxxxxx-xxxx-xxxx-xxxx-xxxxxxxxxxxx':
        # TODO: Remove mock data once real endpoint is configured
        columns = ['comp_id', 'name', 'domain', 'headcount', 'country']
        rows = [
            [1, 'Mock Company A', 'mock-a.com', 100, 'US'],
            [2, 'Mock Company B', 'mock-b.com', 250, 'ES'],
            [3, 'Mock Company C', 'mock-c.com', 50, 'FR'],
        ]
    else:
        response = requests.post(
            f'https://queries.clickhouse.cloud/run/{endpoint}',
            params={'format': 'JSONCompact'},
            headers={
                'Content-Type': 'application/json',
                'x-clickhouse-endpoint-version': '2',
            },
            auth=(clickhouse_key_id, clickhouse_key_secret),
            json={'queryVariables': query_variables},
            timeout=540  # 9 minutes
        )
        
        if response.status_code != 200:
            return {
                'error': f'ClickHouse error: {response.status_code}',
                'detail': response.text[:500] if response.text else 'No response body',
                'report_id': report_id
            }
        
        result = response.json()
        columns = [col['name'] for col in result.get('meta', [])]
        rows = result.get('data', [])
    
    # 2. Format data
    timestamp = datetime.utcnow().strftime('%Y%m%d_%H%M%S')
    
    if file_format == 'csv':
        import csv
        import io
        output = io.StringIO()
        writer = csv.writer(output)
        writer.writerow(columns)
        writer.writerows(rows)
        content = output.getvalue()
        file_ext = 'csv'
    else:  # json
        content = json.dumps({'columns': columns, 'rows': rows}, ensure_ascii=False)
        file_ext = 'json'
    
    # 3. Upload to S3: numerau-scraping/companyprospect/reports/{report_id}/{timestamp}.{ext}
    s3_key = f'{S3_PREFIX}/{report_id}/{timestamp}.{file_ext}'
    s3_client = boto3.client('s3')
    s3_client.put_object(Body=content, Bucket=S3_BUCKET, Key=s3_key)
    
    # 4. Generate presigned URL (7 days expiration)
    presigned_url = s3_client.generate_presigned_url(
        'get_object',
        Params={'Bucket': S3_BUCKET, 'Key': s3_key},
        ExpiresIn=7 * 24 * 60 * 60  # 7 days in seconds
    )
    
    return {
        'report_id': report_id,
        'url': presigned_url,
        'rows_count': len(rows),
        'file_format': file_format,
        'expires_in_days': 7
    }


# =============================================================================
# API FUNCTION
# =============================================================================

@app.function(
    image=python_image,
    min_containers=1,
    secrets=[Secret.from_name("secrets_clickhouse_api")],
    region='us-east',
)
@asgi_app(custom_domains=["api.companyprospect.com"])
def fastapi_app():
    """Main FastAPI application with all endpoints."""
    
    # Initialize services
    embedder = GPUEmbedder()
    CLICKHOUSE_KEY_ID = os.environ.get('key_id', 'NOT_FOUND')
    CLICKHOUSE_KEY_SECRET = os.environ.get('key_secret', 'NOT_FOUND')

    # -------------------------------------------------------------------------
    # HELPER FUNCTIONS
    # -------------------------------------------------------------------------

    async def lookup(query: str) -> Dict[str, Any]:
        """Query ClickHouse for a single lookup."""
        if not query:
            return {'columns': [], 'rows': []}

        async with httpx.AsyncClient() as client:
            response = await client.get(
                'https://queries.clickhouse.cloud/run/679eff13-08ef-48ef-9e6d-e1dd15a9d151',
                params={'format': 'JSONCompact', 'param_query': query},
                headers={'Content-Type': 'application/json'},
                auth=(CLICKHOUSE_KEY_ID, CLICKHOUSE_KEY_SECRET)
            )
            
        if response.status_code == 200:
            result = response.json()
            return {
                'columns': [col['name'] for col in result.get('meta', [])],
                'rows': result.get('data', [])
            }
        return {'query': query, 'error': f'Status {response.status_code}'}


    async def lookup_many(query: List[str]) -> List[Dict[str, Any]]:
        """Run multiple lookups concurrently."""
        if not query:
            return []
        tasks = [lookup(q) for q in query]
        results = await asyncio.gather(*tasks)
        return [{'query': q, 'result': r} for q, r in zip(query, results)]


    async def lookalike_from_ids(
        company_ids: List[int],
        filter_hc: Optional[int] = None,
        filter_cc2: Optional[List[str]] = None,
        size_weight: float = 0.20
    ) -> Dict[str, Any]:
        """
        Query ClickHouse for lookalike companies for a list of comp_id with optional filters.
        
        Args:
            company_ids: List of company IDs to find lookalikes for
            filter_hc: Minimum headcount filter (optional)
            filter_cc2: Country code filter list (optional)
            size_weight: Bias toward larger companies (0.0 - 0.3, default 0.20)
                - 0.0       = pure similarity search (no size bias)
                - 0.0 - 0.1 = light size bias
                - 0.1 - 0.2 = pronounced size bias
                - 0.2 - 0.3 = heavy size bias
        """
        if not company_ids:
            return {'columns': [], 'rows': []}
        
        # Build query variables with optional filters
        query_variables = {
            'company_ids': company_ids,
            'max_log_hc': 6.0,
            'size_weight': size_weight,
        }
        
        # Add headcount filter (default to 0 if not provided)
        query_variables['filter_hc'] = filter_hc if filter_hc is not None else 0
        
        # Add country filter (default to empty array if not provided)
        query_variables['filter_cc2'] = filter_cc2 if filter_cc2 else []
        
        async with httpx.AsyncClient() as client:
            response = await client.post(
                'https://queries.clickhouse.cloud/run/140e404a-0b69-47e6-9432-6633bdd89ce5',
                params={'format': 'JSONCompact'},
                headers={
                    'Content-Type': 'application/json',
                    'x-clickhouse-endpoint-version': '2',
                },
                auth=(CLICKHOUSE_KEY_ID, CLICKHOUSE_KEY_SECRET),
                json={'queryVariables': query_variables}
            )
            
        if response.status_code == 200:
            result = response.json()
            return {
                'columns': [col['name'] for col in result.get('meta', [])],
                'rows': result.get('data', [])
            }
        # Debug: return full error details
        return {
            'company_ids': company_ids,
            'error': f'Status {response.status_code}',
            'detail': response.text[:500] if response.text else 'No response body',
            'query_variables': query_variables
        }




    async def lookalike_from_term(query: str, size_weight: float = 0.20) -> Dict[str, Any]:
        """
        Query ClickHouse for lookalike companies for a single term.
        
        Args:
            query: Search term to find similar companies
            size_weight: Bias toward larger companies (0.0 - 0.3, default 0.20)
                - 0.0       = pure similarity search (no size bias)
                - 0.0 - 0.1 = light size bias
                - 0.1 - 0.2 = pronounced size bias
                - 0.2 - 0.3 = heavy size bias
        """
        if not query:
            return {'columns': [], 'rows': []}

        # Get embedding as list for queryVariables
        query_emb = embedder.embed_inputs.remote([query])[0].tolist()
        
        async with httpx.AsyncClient() as client:
            response = await client.post(
                'https://queries.clickhouse.cloud/run/66327799-c11f-4777-8cac-09e4e359fbff',
                params={'format': 'JSONCompact'},
                headers={
                    'Content-Type': 'application/json',
                    'x-clickhouse-endpoint-version': '2',
                },
                auth=(CLICKHOUSE_KEY_ID, CLICKHOUSE_KEY_SECRET),
                json={
                    'queryVariables': {
                        'query': query_emb,
                        'max_log_hc': 6.0,
                        'size_weight': size_weight,
                    }
                }
            )
            
        if response.status_code == 200:
            result = response.json()
            return {
                'columns': [col['name'] for col in result.get('meta', [])],
                'rows': result.get('data', [])
            }
        return {'query': query, 'error': f'Status {response.status_code}'}

        # Debug: print full error response
        # print(f"ClickHouse Error {response.status_code}: {response.text}")
        # return {'query': query, 'error': f'Status {response.status_code}', 'detail': response.text}
        

    # -------------------------------------------------------------------------
    # ENDPOINTS: Lookup
    # -------------------------------------------------------------------------

    @web_app.get("/v01/lookup")
    async def api_lookup(query: str):
        """Single query lookup."""
        return JSONResponse(content=await lookup(query))


    @web_app.post("/v01/lookup_many")
    async def api_lookup_many(payload: Dict[str, List[str]]):
        """
        Batch lookup for multiple queries.
        
        Request body: {"queries": ["query1", "query2", ...]}
        """
        return JSONResponse(content=await lookup_many(payload['queries']))

    # -------------------------------------------------------------------------
    # ENDPOINTS: Embeddings
    # -------------------------------------------------------------------------

    @web_app.get("/v01/embed_many")
    async def api_embed_many(query: str):
        """
        Generate embeddings for comma-separated inputs.
        
        Query param: query="text1, text2, text3"
        """
        input_list = [s.strip() for s in query.split(',')]
        embeddings = embedder.embed_inputs.remote(input_list)
        return JSONResponse(content=embeddings.tolist())


    # -------------------------------------------------------------------------
    # ENDPOINTS: Lookalikes
    # -------------------------------------------------------------------------

    @web_app.post("/v01/lookalike_from_term")
    async def api_lookalike_from_term(payload: Dict[str, Any]):
        """
        Generate lookalikes for a single term.
        
        Request body:
        {
            "query": "term",                   // required: search term
            "size_weight": 0.20                // optional: size weight (default 0.20, ranges 0.0 - 0.3)
        }
        
        size_weight controls the bias toward larger companies in the results:
          - 0.0       = pure similarity search (no size bias)
          - 0.0 - 0.1 = light size bias
          - 0.1 - 0.2 = pronounced size bias
          - 0.2 - 0.3 = heavy size bias
        """
        query = payload.get('query', '')
        size_weight = payload.get('size_weight', 0.20)
        lookalikes = await lookalike_from_term(query, size_weight)
        return JSONResponse(content=lookalikes)



    @web_app.post("/v01/lookalike_from_ids")
    async def api_lookalike_from_ids(payload: Dict[str, Any]):
        """
        Generate lookalikes for a list of comp_id with optional filters.
        
        Request body:
        {
            "company_ids": [10667, 12345],      // required: list of comp_ids
            "filter_hc": 10,                     // optional: minimum headcount
            "filter_cc2": ["es", "fr", "de"]     // optional: country codes
            "size_weight": 0.15,                 // optional: size weight (default 0.15, ranges 0.0 - 0.3)
        }
        
        size_weight controls the bias toward larger companies in the results:
          - 0.0       = pure similarity search (no size bias)
          - 0.0 - 0.1 = light size bias
          - 0.1 - 0.2 = pronounced size bias
          - 0.2 - 0.3 = heavy size bias
        """
        company_ids = payload.get('company_ids', [])
        filter_hc = payload.get('filter_hc')
        filter_cc2 = payload.get('filter_cc2')
        size_weight = payload.get('size_weight', 0.15)

        lookalikes = await lookalike_from_ids(company_ids, filter_hc, filter_cc2, size_weight)
        return JSONResponse(content=lookalikes)

    # -------------------------------------------------------------------------
    # ENDPOINTS: Reports
    # -------------------------------------------------------------------------

    @web_app.post("/v01/generate_report")
    async def api_generate_report(payload: Dict[str, Any]):
        """
        Generate a report from ClickHouse query and upload to S3.
        Returns a presigned URL valid for 7 days.
        
        Files are saved to: s3://companyprospect/reports/{report_id}/
        
        Request body:
        {
            "report_id": "my-report-123",           // required: unique report identifier
            "query_variables": {                    // required: variables for the query
                "filter_hc": 10,
                "filter_cc2": ["es", "fr"],
                ...
            },
            "file_format": "json",                  // optional: 'json' (default) or 'csv'
            "clickhouse_endpoint": "uuid-here"      // optional: override default ClickHouse endpoint
        }
        
        Returns:
        {
            "report_id": "my-report-123",
            "url": "https://s3.amazonaws.com/...",  // presigned URL (expires in 7 days)
            "rows_count": 1234,
            "file_format": "json",
            "expires_in_days": 7
        }
        
        Note: This endpoint may take several minutes to complete for large queries.
        """
        report_id = payload.get('report_id')
        query_variables = payload.get('query_variables', {})
        file_format = payload.get('file_format', 'json')
        clickhouse_endpoint = payload.get('clickhouse_endpoint')  # optional override
        
        if not report_id:
            return JSONResponse(
                content={'error': 'report_id is required'},
                status_code=400
            )
        
        # Call the long-running report generator
        result = generate_report.remote(
            report_id=report_id,
            query_variables=query_variables,
            file_format=file_format,
            clickhouse_endpoint=clickhouse_endpoint
        )
        
        return JSONResponse(content=result)

    # -------------------------------------------------------------------------


    return web_app
    