import requests
import os
import json

MODAL_DIRECT = 'https://nummary-analytics--companyprospect-mcp-v01-fastapi-app.modal.run'
CUSTOM_DOMAIN = 'https://api.companyprospect.com'

# Get API key from environment or prompt
API_KEY = os.environ.get('CP_API_KEY', 'nm_abcde')
if not API_KEY:
    API_KEY = input("Enter API Key (nm_...): ").strip()

# print(f"Using API Key: {API_KEY[:10]}***")

# # Test with Custom Domain + API Key
# print("\n=== Testing Custom Domain with X-Api-Key header ===")

# print("\n/v01/lookalike_from_ids (POST):")
# r = requests.post(
#     f'{CUSTOM_DOMAIN}/v01/lookalike_from_ids',
#     headers={'X-Api-Key': API_KEY},
#     json={'company_ids': [10667], 'filter_hc': 10, 'filter_cc2': ['es']}
# )
# print("Status:", r.status_code)
# print("Text:", r.text[:500] if r.text else "EMPTY")

# =============================================================================
# Test generate_report endpoint
# =============================================================================
print("\n" + "="*60)
print("=== Testing /v01/generate_report (POST) ===")
print("="*60)

r = requests.post(
    f'{CUSTOM_DOMAIN}/v01/generate_report',
    headers={'X-Api-Key': API_KEY, 'Content-Type': 'application/json'},
    json={
        'report_id': 'test-5000-csv',
        'query_variables': {'filter_hc': 0},  # filter_hc parameter
        'file_format': 'csv'
    },
    timeout=120  # 2 minutes timeout for long-running request
)

print("Status:", r.status_code)
try:
    result = r.json()
    print("Response:", json.dumps(result, indent=2))
    
    if 'url' in result:
        print("\n✅ Presigned URL generated successfully!")
        print(f"   URL: {result['url'][:80]}...")
        print(f"   Rows: {result.get('rows_count', 'N/A')}")
        print(f"   Expires in: {result.get('expires_in_days', 'N/A')} days")
except Exception as e:
    print("Error parsing response:", e)
    print("Raw text:", r.text[:500] if r.text else "EMPTY")


# =============================================================================
# Test parse_query endpoint
# =============================================================================
print("\n" + "="*60)
print("=== Testing /v01/parse_query (POST) ===")
print("="*60)

r = requests.post(
    f'{CUSTOM_DOMAIN}/v01/parse_query',
    headers={'X-Api-Key': API_KEY, 'Content-Type': 'application/json'},
    json={
        'query': 'competidores de zoominfo o apollo'
    },
    timeout=60
)

print("Status:", r.status_code)
try:
    result = r.json()
    print("Response:", json.dumps(result, indent=2))
    
    if 'industry_summary' in result:
        print("\n✅ Query parsed successfully!")
        print(f"   Industry: {result.get('industry_summary', 'N/A')}")
        print(f"   Competitors parsed: {result.get('competitor_parsed_list', [])}")
        print(f"   Competitors suggested: {result.get('competitor_suggested_list', [])}")
        print(f"   Filters: hc={result.get('filt_comp_hc')}, cc2={result.get('filt_comp_cc2_list')}")
except Exception as e:
    print("Error parsing response:", e)
    print("Raw text:", r.text[:500] if r.text else "EMPTY")
