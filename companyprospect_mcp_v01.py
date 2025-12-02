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


    async def lookalike_from_ids(query: str) -> Dict[str, Any]:
        """Query ClickHouse for lookalike companies for a list of comp_id"""
        if not query:
            return {'columns': [], 'rows': []}

        query_list = [int(s.strip()) for s in query.split(',') if s.strip().isdigit()]
        if not query_list:
            return {'columns': [], 'rows': []}
        
        async with httpx.AsyncClient() as client:
            response = await client.post(
                'https://queries.clickhouse.cloud/run/140e404a-0b69-47e6-9432-6633bdd89ce5',
                params={'format': 'JSONCompact'},
                headers={
                    'Content-Type': 'application/json',
                    'x-clickhouse-endpoint-version': '2',
                },
                auth=(CLICKHOUSE_KEY_ID, CLICKHOUSE_KEY_SECRET),
                json={'queryVariables': {'query': query_list}}
            )
            
        if response.status_code == 200:
            result = response.json()
            return {
                'columns': [col['name'] for col in result.get('meta', [])],
                'rows': result.get('data', [])
            }
        return {'query': query, 'error': f'Status {response.status_code}'}




    async def lookalike_from_term(query: str) -> Dict[str, Any]:
        """Query ClickHouse for lookalike companies for a single term"""
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
                json={'queryVariables': {'query': query_emb}}
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

    @web_app.get("/v01/lookalike_from_term")
    async def api_lookalike_from_term(query: str):
        """
        Generate lookalikes for a single term.
        
        Query param: query="term"
        """
        lookalikes = await lookalike_from_term(query)
        return JSONResponse(content=lookalikes)


    @web_app.get("/v01/lookalike_from_ids")
    async def api_lookalike_from_ids(query: str):
        """
        Generate lookalikes for a list of comp_id.
        
        Query param: query=["comp_id1", "comp_id2", "comp_id3"]
        """
        lookalikes = await lookalike_from_ids(query)
        return JSONResponse(content=lookalikes)

    # -------------------------------------------------------------------------


    return web_app
    