"""
CompanyProspect Reports Module
==============================
Report generation logic for ClickHouse queries to S3.
"""

import json
import csv
import io
from datetime import datetime
from typing import Dict, Any

import boto3
import requests


# =============================================================================
# CONFIGURATION
# =============================================================================

S3_BUCKET = 'companyprospect'
S3_PREFIX = 'reports'

# ClickHouse endpoint for reports
CLICKHOUSE_REPORT_ENDPOINT = '79ac8578-cd5c-4aea-895a-e0caa6337ce5'


# =============================================================================
# REPORT GENERATION
# =============================================================================

def generate_report(
    report_id: str,
    query_variables: Dict[str, Any],
    clickhouse_key_id: str,
    clickhouse_key_secret: str,
    file_format: str = 'json',
    clickhouse_endpoint: str = None
) -> Dict[str, Any]:
    """
    Generate a report from ClickHouse and upload to S3.
    
    Args:
        report_id: Unique identifier for the report
        query_variables: Variables to pass to the ClickHouse query
        clickhouse_key_id: ClickHouse API key ID
        clickhouse_key_secret: ClickHouse API key secret
        file_format: Output format ('json' or 'csv')
        clickhouse_endpoint: ClickHouse Cloud endpoint UUID (optional, uses default)
    
    Returns:
        Dict with 'url' (presigned S3 URL), 'report_id', 'rows_count', etc.
    """
    # Use default endpoint if not provided
    endpoint = clickhouse_endpoint or CLICKHOUSE_REPORT_ENDPOINT
    
    # Default filter_hc if not provided
    if 'filter_hc' not in query_variables:
        query_variables['filter_hc'] = 0
    
    # 1. Query ClickHouse - always use POST with version 2 for queryVariables
    response = requests.post(
        f'https://queries.clickhouse.cloud/run/{endpoint}',
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
    
    # 2. Parse response - handle both JSON and JSONEachRow formats
    response_text = response.text.strip()
    
    if response_text.startswith('{') and '"meta"' in response_text[:100]:
        # JSON/JSONCompact format: {"meta": [...], "data": [[...]]}
        result = response.json()
        columns = [col['name'] for col in result.get('meta', [])]
        rows = result.get('data', [])
    else:
        # JSONEachRow format: one JSON object per line
        lines = [line for line in response_text.split('\n') if line.strip()]
        if lines:
            first_row = json.loads(lines[0])
            columns = list(first_row.keys())
            rows = [list(json.loads(line).values()) for line in lines]
        else:
            columns = []
            rows = []
    
    # 3. Format data
    timestamp = datetime.utcnow().strftime('%Y%m%d_%H%M%S')
    
    if file_format == 'csv':
        output = io.StringIO()
        writer = csv.writer(output)
        writer.writerow(columns)
        writer.writerows(rows)
        content = output.getvalue()
        file_ext = 'csv'
    else:  # json
        content = json.dumps({'columns': columns, 'rows': rows}, ensure_ascii=False)
        file_ext = 'json'
    
    # 4. Upload to S3
    s3_key = f'{S3_PREFIX}/{report_id}/{timestamp}.{file_ext}'
    s3_client = boto3.client('s3')
    s3_client.put_object(Body=content, Bucket=S3_BUCKET, Key=s3_key)
    
    # 5. Generate presigned URL (7 days expiration)
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

