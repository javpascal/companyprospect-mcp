"""
CompanyProspect Query Parser Module
===================================
Parses natural language queries into structured JSON for company searches.
"""

import json
from typing import Dict, Any, List, Callable
from openai import OpenAI


# =============================================================================
# SYSTEM PROMPT
# =============================================================================

SYSTEM_PROMPT = """You are a query parser for a B2B company database. Extract structured information from user queries.

## REGION EXPANSION (use these mappings)
- EMEA → gb, de, fr, es, it, nl, be, se, no, dk, fi, ch, at, ie, pt, pl, ae, sa, za, eg, il
- APAC → cn, jp, kr, in, au, sg, hk, tw, nz, th, id, my, ph, vn
- DACH → de, at, ch
- Nordics → se, no, dk, fi
- LATAM → br, mx, ar, cl, co, pe, ec
- Europe/EU → de, fr, es, it, nl, be, se, no, dk, fi, ch, at, ie, pt, pl, gb
- Use ISO 2-letter country codes (lowercase)

## COMPANY SIZE MAPPING
- "startup" → [1, 20]
- "SMB" or "small" → [10, 200]
- "mid-market" or "mid-sized" → [50, 200]
- "enterprise" → [1000, -1]
- "over/more than X employees" → [X, -1]
- "under/less than X employees" → [1, X]
- If not mentioned → [-1, -1]
- -1 means "no limit"

## TITLE EXPANSION
- "decision maker" → ["ceo", "cfo", "cto", "coo", "owner", "founder", "partner", "director"]
- "sales" → ["ae", "account executive", "sdr", "business development", "sales manager"]
- "marketing" → ["cmo", "marketing manager", "growth", "demand generation"]
- "tech" → ["cto", "vp engineering", "software engineer", "developer"]

## OUTPUT FORMAT (JSON only, no markdown)
{
  "industry_summary": "<1-2 sentence description of the industry/sector, NO company names or filters>",
  "competitor_names": ["<company name 1>", "<company name 2>"],
  "suggested_companies": ["<relevant company 1>", "<relevant company 2>"],
  "filt_lead_type": ["company"] or ["employee"] or ["company", "employee"],
  "filt_comp_cc2_list": ["xx", "yy"],
  "filt_comp_hc": [min, max],
  "filt_emp_title": ["title1", "title2"],
  "filt_emp_cc2_list": ["xx", "yy"]
}

## RULES
1. industry_summary: Describe ONLY the industry/sector. Remove specific company names, locations, sizes.
2. competitor_names: Extract explicit company mentions from the query. BE SPECIFIC to avoid ambiguity:
   - "Apollo" in sales context → "Apollo.io" (not Apollo-Optik, Apollo Hospitals, etc.)
   - "Square" in payments → "Square payments" or "Block Inc"
   - Include domain (.io, .com) or industry qualifier when the name is common
3. suggested_companies: Think of 3-5 well-known companies that fit the industry description. Use specific names.
4. filt_lead_type: Default to ["company"] unless employees/people are mentioned
5. filt_comp_cc2_list: Expand regions, use lowercase ISO codes
6. filt_comp_hc: Use [min, max] format, -1 for no limit
7. filt_emp_title: Expand titles if generic terms used
8. filt_emp_cc2_list: Only if employee locations differ from company locations
9. Omit fields that are not mentioned or not applicable (except industry_summary which is required)"""


# =============================================================================
# VALIDATION PROMPT - To select correct company from lookup results
# =============================================================================

VALIDATION_PROMPT = """You are validating company search results. Given the original query context and search results, select the correct company.

Original query: {query}
Industry context: {industry}
Search term: "{search_term}"

Search results (comp_id, name, headcount, country, industry):
{candidates}

Select the comp_id that best matches the intended company based on context.
If none match, return null.

Output JSON only: {{"comp_id": <id or null>, "confidence": "high"|"medium"|"low"}}"""


# =============================================================================
# QUERY PARSER
# =============================================================================

def parse_query(
    query: str,
    openai_api_key: str,
    lookup_many_fn: Callable[[List[str]], List[Dict[str, Any]]] = None,
    model: str = "gpt-4o-mini"
) -> Dict[str, Any]:
    """
    Parse a natural language query into structured JSON.
    
    Args:
        query: User's natural language query
        openai_api_key: OpenAI API key
        lookup_many_fn: Function to lookup company IDs (optional)
        model: OpenAI model to use
    
    Returns:
        Structured JSON with parsed query components
    """
    client = OpenAI(api_key=openai_api_key)
    
    # 1. Call LLM to parse the query
    response = client.chat.completions.create(
        model=model,
        messages=[
            {"role": "system", "content": SYSTEM_PROMPT},
            {"role": "user", "content": f"Parse this query:\n\n{query}"}
        ],
        temperature=0.1,
        response_format={"type": "json_object"}
    )
    
    # 2. Parse LLM response
    try:
        parsed = json.loads(response.choices[0].message.content)
    except json.JSONDecodeError:
        return {"error": "Failed to parse LLM response", "raw": response.choices[0].message.content}
    
    # 3. Resolve competitor IDs if lookup function provided
    result = {
        "industry_summary": parsed.get("industry_summary", ""),
        "competitor_parsed_list": [],
        "competitor_suggested_list": [],
    }
    
    # Add filter fields if present
    for field in ["filt_lead_type", "filt_comp_cc2_list", "filt_comp_hc", 
                  "filt_emp_title", "filt_emp_cc2_list"]:
        if field in parsed:
            result[field] = parsed[field]
    
    # 4. Lookup competitor IDs
    if lookup_many_fn:
        # Lookup parsed competitor names
        competitor_names = parsed.get("competitor_names", [])
        if competitor_names:
            lookup_results = lookup_many_fn(competitor_names)
            result["competitor_parsed_list"] = _extract_comp_ids(lookup_results)
        
        # Lookup suggested companies
        suggested_names = parsed.get("suggested_companies", [])
        if suggested_names:
            lookup_results = lookup_many_fn(suggested_names)
            result["competitor_suggested_list"] = _extract_comp_ids(lookup_results)
    else:
        # Return names if no lookup function
        result["competitor_names"] = parsed.get("competitor_names", [])
        result["suggested_companies"] = parsed.get("suggested_companies", [])
    
    return result


def _extract_comp_ids(lookup_results: List[Dict[str, Any]]) -> List[int]:
    """Extract comp_ids from lookup_many results."""
    comp_ids = []
    for item in lookup_results:
        result = item.get('result', {})
        rows = result.get('rows', [])
        if rows:
            # First column is typically comp_id
            comp_ids.append(rows[0][0])
    return comp_ids

