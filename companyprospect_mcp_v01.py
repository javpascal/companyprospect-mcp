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
    .add_local_python_source("api_modules")
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

@app.function(
    image=python_image,
    timeout=600,  # 10 minutes for long-running reports
    min_containers=1,
    secrets=[
        Secret.from_name("secrets_clickhouse_api"),
        Secret.from_name("my-aws-secret"),
        Secret.from_name("secrets_openai"),  # Needs: openai_key
    ],
    region='us-east',
)
@asgi_app(custom_domains=["api.companyprospect.com"])
def fastapi_app():
    """Main FastAPI application with all endpoints."""
    from api_modules import reports, query_parser, lookups, lookalikes
    
    # Initialize services
    embedder = GPUEmbedder()
    CLICKHOUSE_KEY_ID = os.environ.get('key_id', 'NOT_FOUND')
    CLICKHOUSE_KEY_SECRET = os.environ.get('key_secret', 'NOT_FOUND')
    OPENAI_API_KEY = os.environ.get('openai_key', 'NOT_FOUND')

    # -------------------------------------------------------------------------
    # HELPER FUNCTIONS
    # -------------------------------------------------------------------------

    # -------------------------------------------------------------------------
    # HELPER WRAPPERS (use api_modules with credentials)
    # -------------------------------------------------------------------------
    
    async def lookup(query: str, limit: int = 10, size_weight: float = 0.1) -> Dict[str, Any]:
        """Wrapper for lookups.lookup with credentials."""
        return await lookups.lookup(query, CLICKHOUSE_KEY_ID, CLICKHOUSE_KEY_SECRET, limit, size_weight)
    
    async def lookup_many(queries: List[str], limit: int = 10, size_weight: float = 0.1) -> List[Dict[str, Any]]:
        """Wrapper for lookups.lookup_many with credentials."""
        return await lookups.lookup_many(queries, CLICKHOUSE_KEY_ID, CLICKHOUSE_KEY_SECRET, limit, size_weight)
    
    async def lookalike_from_ids(
        company_ids: List[int],
        filter_hc: Optional[int] = None,
        filter_cc2: Optional[List[str]] = None,
        size_weight: float = 0.20,
        limit: int = 100
    ) -> Dict[str, Any]:
        """Wrapper for lookalikes.lookalike_from_ids with credentials."""
        return await lookalikes.lookalike_from_ids(
            company_ids, CLICKHOUSE_KEY_ID, CLICKHOUSE_KEY_SECRET,
            filter_hc, filter_cc2, size_weight, limit
        )
    
    async def lookalike_from_term(query: str, size_weight: float = 0.20, limit: int = 100) -> Dict[str, Any]:
        """Wrapper for lookalikes.lookalike_from_term with credentials."""
        return await lookalikes.lookalike_from_term(
            query, CLICKHOUSE_KEY_ID, CLICKHOUSE_KEY_SECRET,
            embedder.embed_inputs.remote, size_weight, limit
        )

    # -------------------------------------------------------------------------
    # ENDPOINTS: Health / Wake-up
    # -------------------------------------------------------------------------

    @web_app.get("/ping")
    async def api_ping():
        """
        Health check / wake-up endpoint.
        
        Call this first to ensure the server is active before making other API calls.
        The server may be sleeping to save costs and needs ~10-30 seconds to wake up.
        
        Returns: {"status": "ok", "message": "Server is active"}
        """
        return JSONResponse(content={"status": "ok", "message": "Server is active"})

    # -------------------------------------------------------------------------
    # ENDPOINTS: Lookup
    # -------------------------------------------------------------------------

    @web_app.get("/v01/lookup")
    async def api_lookup(query: str, limit: int = 10, size_weight: float = 0.1):
        """
        Single query lookup - find companies by name.
        
        Query params:
            query: Search term (company name)
            limit: Maximum results (default 10, max 100)
            size_weight: Bias toward larger companies (0.0-0.3, default 0.1)
        
        Returns columns: comp_id, comp_slug, comp_name, comp_web, dist
        """
        return JSONResponse(content=await lookup(query, limit, size_weight))


    @web_app.post("/v01/lookup_many")
    async def api_lookup_many(payload: Dict[str, Any]):
        """
        Batch lookup for multiple queries - find companies by name.
        Results are deduplicated by comp_id across all queries.
        
        Request body: 
        {
            "queries": ["query1", "query2", ...],
            "limit": 10,           // optional, default 10, max 100
            "size_weight": 0.1     // optional, default 0.1
        }
        
        Returns columns: comp_id, comp_slug, comp_name, comp_web, dist
        """
        queries = payload.get('queries', [])
        limit = payload.get('limit', 10)
        size_weight = payload.get('size_weight', 0.1)
        return JSONResponse(content=await lookup_many(queries, limit, size_weight))

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
        Generate lookalikes for a single term using semantic search.
        
        Request body:
        {
            "query": "term",                   // required: search term
            "size_weight": 0.20,               // optional: size weight (default 0.20, ranges 0.0 - 0.3)
            "limit": 100                       // optional: max results (default 100, max 1000)
        }
        
        Returns columns: comp_id, comp_slug, comp_name, comp_web, dist
        
        size_weight controls the bias toward larger companies in the results:
          - 0.0       = pure similarity search (no size bias)
          - 0.0 - 0.1 = light size bias
          - 0.1 - 0.2 = pronounced size bias
          - 0.2 - 0.3 = heavy size bias
        """
        query = payload.get('query', '')
        size_weight = payload.get('size_weight', 0.20)
        limit = payload.get('limit', 100)
        result = await lookalike_from_term(query, size_weight, limit)
        return JSONResponse(content=result)


    @web_app.post("/v01/lookalike_from_ids")
    async def api_lookalike_from_ids(payload: Dict[str, Any]):
        """
        Generate lookalikes for a list of comp_id with optional filters.
        
        Request body:
        {
            "company_ids": [10667, 12345],      // required: list of comp_ids
            "filter_hc": 10,                     // optional: minimum headcount
            "filter_cc2": ["es", "fr", "de"],    // optional: country codes
            "size_weight": 0.15,                 // optional: size weight (default 0.15, ranges 0.0 - 0.3)
            "limit": 100                         // optional: max results (default 100, max 1000)
        }
        
        Returns columns: comp_id, comp_slug, comp_name, comp_web, dist
        
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
        limit = payload.get('limit', 100)

        result = await lookalike_from_ids(company_ids, filter_hc, filter_cc2, size_weight, limit)
        return JSONResponse(content=result)

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
        
        # Call the report generator from reports module
        result = reports.generate_report(
            report_id=report_id,
            query_variables=query_variables,
            clickhouse_key_id=CLICKHOUSE_KEY_ID,
            clickhouse_key_secret=CLICKHOUSE_KEY_SECRET,
            file_format=file_format,
            clickhouse_endpoint=clickhouse_endpoint
        )
        
        return JSONResponse(content=result)

    # -------------------------------------------------------------------------
    # ENDPOINTS: Query Parser
    # -------------------------------------------------------------------------

    @web_app.post("/v01/parse_query")
    async def api_parse_query(payload: Dict[str, Any]):
        """
        Parse a natural language query into structured JSON for company searches.
        
        Request body:
        {
            "query": "startups en online payments en españa con >10 empleados"
        }
        
        Returns:
        {
            "industry_summary": "Online payment fintech service providers",
            "competitor_parsed_list": [10145, 9033],           // Explicit mentions resolved to IDs
            "competitor_suggested_list": [10667, 4006],        // LLM-suggested companies
            "industry_lookalikes_list": [12345, 67890, ...],   // Semantic search on industry_summary
            "filt_lead_type": ["company"],
            "filt_comp_cc2_list": ["es"],
            "filt_comp_hc": [10, -1]
        }
        """
        query = payload.get('query', '')
        
        if not query:
            return JSONResponse(
                content={'error': 'query is required'},
                status_code=400
            )
        
        # Call the query parser without lookup (returns names instead of IDs)
        result = query_parser.parse_query(
            query=query,
            openai_api_key=OPENAI_API_KEY,
            lookup_many_fn=None  # We'll do lookups async below
        )
        
        # Check for errors
        if 'error' in result:
            return JSONResponse(content=result)
        
        # Resolve competitor names to IDs using async lookup_many with validation
        competitor_names = result.pop('competitor_names', [])
        suggested_names = result.pop('suggested_companies', [])
        industry_context = result.get('industry_summary', '')
        
        result['competitor_parsed_list'] = []
        result['competitor_suggested_list'] = []
        
        # Helper to validate and select best match from multiple candidates
        def validate_company(search_term: str, rows: list, columns: list) -> int | None:
            if not rows:
                return None
            if len(rows) == 1:
                return int(rows[0][0])
            
            # Multiple candidates - use LLM to pick the right one
            from openai import OpenAI
            client = OpenAI(api_key=OPENAI_API_KEY)
            
            # Format candidates for LLM
            candidates_str = "\n".join([
                f"- {row[0]}: {row[1] if len(row) > 1 else 'N/A'} | {row[2] if len(row) > 2 else 'N/A'} employees | {row[3] if len(row) > 3 else 'N/A'}"
                for row in rows[:10]  # Limit to top 10
            ])
            
            validation_prompt = f"""Select the correct company from these search results.

Original query: {query}
Industry: {industry_context}
Search term: "{search_term}"

Candidates (id: name | employees | country):
{candidates_str}

Return JSON: {{"comp_id": <best matching id or null>}}"""
            
            try:
                response = client.chat.completions.create(
                    model="gpt-4o-mini",
                    messages=[{"role": "user", "content": validation_prompt}],
                    temperature=0,
                    response_format={"type": "json_object"}
                )
                validation = json.loads(response.choices[0].message.content)
                comp_id = validation.get('comp_id')
                return int(comp_id) if comp_id else None
            except:
                return int(rows[0][0])  # Fallback to first
        
        if competitor_names:
            lookup_results = await lookup_many(competitor_names)
            for item in lookup_results:
                res = item.get('result', {})
                rows = res.get('rows', [])
                columns = res.get('columns', [])
                comp_id = validate_company(item.get('query', ''), rows, columns)
                if comp_id:
                    result['competitor_parsed_list'].append(comp_id)
        
        if suggested_names:
            lookup_results = await lookup_many(suggested_names)
            for item in lookup_results:
                res = item.get('result', {})
                rows = res.get('rows', [])
                columns = res.get('columns', [])
                comp_id = validate_company(item.get('query', ''), rows, columns)
                if comp_id:
                    result['competitor_suggested_list'].append(comp_id)
        
        # Get industry lookalikes using semantic search on industry_summary
        result['industry_lookalikes_list'] = []
        if industry_context:
            lookalike_result = await lookalike_from_term(industry_context, size_weight=0.15, limit=20)
            rows = lookalike_result.get('rows', [])
            if rows:
                result['industry_lookalikes_list'] = [int(row[0]) for row in rows]
        
        return JSONResponse(content=result)

    # -------------------------------------------------------------------------


    return web_app
    