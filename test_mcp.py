import requests
import os

MODAL_DIRECT = 'https://nummary-analytics--companyprospect-mcp-v01-fastapi-app.modal.run'
CUSTOM_DOMAIN = 'https://api.companyprospect.com'

# Get API key from environment or prompt
API_KEY = os.environ.get('CP_API_KEY', 'nm_abcde')
if not API_KEY:
    API_KEY = input("Enter API Key (nm_...): ").strip()

print(f"Using API Key: {API_KEY[:10]}***")

# Test with Custom Domain + API Key
print("\n=== Testing Custom Domain with X-Api-Key header ===")
print("\n/v01/lookalike_from_ids (POST):")
r = requests.post(
    f'{CUSTOM_DOMAIN}/v01/lookalike_from_ids',
    headers={'X-Api-Key': API_KEY},
    json={'company_ids': [10667], 'filter_hc': 10, 'filter_cc2': ['es']}
)
print("Status:", r.status_code)
print("Text:", r.text[:500] if r.text else "EMPTY")
