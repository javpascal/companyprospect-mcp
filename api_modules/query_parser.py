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

## CRITICAL: LANGUAGE RULES
- industry_summary: ALWAYS write in ENGLISH (used for semantic embeddings)
- competitor_names: Include BOTH original name AND English translation if applicable
  Example: "Mercadona" → ["Mercadona", "Mercadona supermarkets"]
  Example: "Deutsche Bank" → ["Deutsche Bank", "German Bank"]
  If name is already English or universal, just use one: "Stripe" → ["Stripe"]
- suggested_companies: Same as competitor_names - include both original and English if applicable

The user query can be in any language. Industry descriptions must be in English. Company names should include both original and English variants to maximize search matches.

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

## TITLE EXPANSION (BE EXPANSIVE - include many relevant titles)
ALWAYS convert C-level acronyms to full names:
- "ceo" → "Chief Executive Officer"
- "coo" → "Chief Operating Officer"
- "cfo" → "Chief Financial Officer"
- "cto" → "Chief Technology Officer"
- "cmo" → "Chief Marketing Officer"
- "cio" → "Chief Information Officer"
- "chro" → "Chief Human Resources Officer"
- "cpo" → "Chief Product Officer"
- "cro" → "Chief Revenue Officer"
- "vp" → "Vice President"

IMPORTANT: When user mentions a CATEGORY of titles (like "marketing titles" or "senior roles in X"), 
be VERY expansive and include ALL relevant titles at different seniority levels.

Category expansion examples:
- "marketing titles" or "marketing roles" → ["Chief Marketing Officer", "VP Marketing", "Head of Marketing", "Marketing Director", "Senior Marketing Manager", "Marketing Manager", "Growth Manager", "Demand Generation Manager", "Brand Manager", "Content Marketing Manager", "Digital Marketing Manager", "Performance Marketing Manager"]
- "sales titles" → ["Chief Revenue Officer", "VP Sales", "Head of Sales", "Sales Director", "Senior Account Executive", "Account Executive", "Sales Development Representative", "Business Development Manager", "Sales Manager", "Enterprise Account Executive", "Inside Sales Representative"]
- "operations titles" → ["Chief Operating Officer", "VP Operations", "Head of Operations", "Operations Director", "Senior Operations Manager", "Operations Manager", "Operations Coordinator", "Business Operations Manager"]
- "senior titles in X" → Include: Chief X Officer, VP of X, Head of X, Director of X, Senior X Manager
- "decision maker" → ["Chief Executive Officer", "Chief Financial Officer", "Chief Operating Officer", "Chief Marketing Officer", "Chief Revenue Officer", "VP", "Director", "Head of", "Owner", "Founder", "Partner", "General Manager", "Managing Director"]
- "tech titles" → ["Chief Technology Officer", "VP Engineering", "Head of Engineering", "Engineering Director", "Senior Software Engineer", "Software Engineer", "Tech Lead", "Principal Engineer", "Staff Engineer", "Developer", "Full Stack Developer", "Backend Engineer", "Frontend Engineer"]

When multiple categories are mentioned, expand EACH category fully.

## OUTPUT FORMAT (JSON only, no markdown)
{
  "industry_summary": "<1-2 sentence description of the industry/sector, NO company names or filters>",
  "competitor_names": ["<company name 1>", "<company name 2>"],
  "suggested_companies": ["<relevant company 1>", "<relevant company 2>"],
  "explicit_comp_names_curr": ["<company where user wants CURRENT employees>"],
  "explicit_comp_names_past": ["<company where user wants FORMER employees>"],
  "explicit_comp_names_any": ["<company where user wants employees (any time)>"],
  "profile_industry_experience": "<industry description for filtering past work experience>",
  "headline_skills_explicit": ["<functional skill NOT inferable from title or industry>"],
  "headline_skills_explicit_expanded": ["<expanded related skills>"],
  "filt_lead_type": ["company"] or ["employee"] or ["company", "employee"],
  "filt_comp_loc_cc2": ["xx", "yy"],
  "filt_comp_loc_city": ["city variant 1", "city variant 2"],
  "filt_comp_loc_region": ["region variant 1", "region variant 2"],
  "filt_comp_hc": [min, max],
  "filt_emp_title": ["title1", "title2"],
  "filt_emp_cc2_list": ["xx", "yy"]
}

## RULES
1. industry_summary: Describe ONLY the industry/sector IN ENGLISH (for embeddings). Remove specific company names, locations, sizes.
2. competitor_names: Extract lookalike/similar company mentions (for finding similar companies). Include BOTH original AND English names when applicable.
3. suggested_companies: Think of 3-5 well-known companies that fit the industry description.
4. explicit_comp_names_curr: Companies where user wants CURRENT employees (default). "PMs at Meta" → ["Meta"]
   explicit_comp_names_past: Companies where user wants FORMER employees. "ex-Google engineers" or "previously at Google" → ["Google"]
   explicit_comp_names_any: Companies for any-time employees (current OR past). "people who have worked at Meta" → ["Meta"]
   Signals for PAST: "ex-", "former", "previously", "used to work", "alumni", "left"
   Signals for CURRENT: "at", "working at", "currently at" (default if ambiguous)
   Signals for ANY: "have worked at", "experience at", "background at"
5. profile_industry_experience: Industry of PAST COMPANIES where the person worked. Only when user mentions "past experience at [company]" or "previously at [company type]". IN ENGLISH.
   Example: "engineers with past experience at Stripe" → "Financial technology and digital payments companies"
   Example: "PMs who worked at consulting firms" → "Management consulting and professional services"
   NOT for: "PMs in machine learning" (this is a skill/domain, not past company industry)
6. headline_skills_explicit: FUNCTIONAL SKILLS that cannot be inferred from job title or industry. Only concrete, learnable skills.
   VALID skills (include these):
   - Programming/Tech: "python", "sql", "java", "machine learning", "data analysis"
   - Tools: "salesforce", "hubspot", "excel", "figma"
   - Languages: "spanish", "mandarin", "english"
   - Certifications: "CPA", "PMP", "AWS certified"
   
   NOT skills (do NOT include - these belong elsewhere):
   - Job specializations → go to filt_emp_title: "laboralista" in "abogado laboralista", "corporate" in "corporate lawyer"
   - Industry domains → go to profile_industry_experience: "fintech", "tech", "healthcare"
   - Seniority → go to filt_emp_title: "senior", "junior", "lead"
   
   Examples:
   - "abogado laboralista" → filt_emp_title: ["Labor Lawyer"], headline_skills_explicit: [] (nothing)
   - "analista con python" → filt_emp_title: ["Analyst"], headline_skills_explicit: ["python"]
   - "founder con experiencia en top tech" → filt_emp_title: ["Founder"], profile_industry_experience: "Top technology companies"
   - "PM fluent in spanish with SQL skills" → headline_skills_explicit: ["spanish", "SQL"]
   
7. headline_skills_explicit_expanded: Expand headline_skills_explicit with closely related skills.
   Example: ["python"] → ["python", "programming", "pandas", "numpy", "scripting"]
   Example: ["spanish"] → ["spanish", "español", "bilingual", "castellano"]
   Example: ["machine learning"] → ["machine learning", "ML", "deep learning", "neural networks"]
8. filt_lead_type: Default to ["company"] unless employees/people are mentioned
9. filt_comp_loc_cc2: ONLY if country is explicitly mentioned. Expand regions, use lowercase ISO codes. DO NOT invent countries.
10. filt_comp_loc_city: ONLY if city/locality is explicitly mentioned. Include ALL spelling variants for exact matching:
   - Local name + English name: "münchen" → ["munich", "münchen"]
   - Common abbreviations: "new york" → ["new york", "new york city", "nyc", "ny", "nueva york"]
   - "san francisco" → ["san francisco", "sf", "san fran"]
   - "london" → ["london", "londres"]
11. filt_comp_loc_region: ONLY if region/state/province is explicitly mentioned. Include variants:
   - "california" → ["california", "ca"]
   - "cataluña" → ["cataluña", "catalunya", "catalonia"]
   - "baviera" → ["baviera", "bavaria", "bayern"]
12. filt_comp_hc: Use [min, max] format, -1 for no limit
13. filt_emp_title: Expand titles if generic terms used
14. filt_emp_cc2_list: Only if employee locations differ from company locations
15. Omit fields that are not mentioned or not applicable (except industry_summary which is required)
16. NEVER invent or assume data not present in the query."""


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
    lookup_title_many_fn: Callable[[List[str]], List[Dict[str, Any]]] = None,
    model: str = "gpt-4o-mini"
) -> Dict[str, Any]:
    """
    Parse a natural language query into structured JSON.
    
    Args:
        query: User's natural language query
        openai_api_key: OpenAI API key
        lookup_many_fn: Function to lookup company IDs (optional)
        lookup_title_many_fn: Function to lookup job title IDs (optional)
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
    
    # 3. Build result with parsed fields
    result = {
        "industry_summary": parsed.get("industry_summary", ""),
        "competitor_parsed_list": [],
        "competitor_suggested_list": [],
        "explicit_comp_id_list_curr": [],
        "explicit_comp_id_list_past": [],
        "explicit_comp_id_list_any": [],
    }
    
    # Add filter fields if present
    for field in ["filt_lead_type", "filt_comp_loc_cc2", "filt_comp_loc_city", 
                  "filt_comp_loc_region", "filt_comp_hc", "filt_emp_title", "filt_emp_cc2_list"]:
        if field in parsed:
            result[field] = parsed[field]
    
    # Add profile/headline fields if present
    if parsed.get("profile_industry_experience"):
        result["profile_industry_experience"] = parsed["profile_industry_experience"]
    if parsed.get("headline_skills_explicit"):
        result["headline_skills_explicit"] = parsed["headline_skills_explicit"]
    if parsed.get("headline_skills_explicit_expanded"):
        result["headline_skills_explicit_expanded"] = parsed["headline_skills_explicit_expanded"]
    
    # 4. Lookup company IDs
    if lookup_many_fn:
        # Lookup parsed competitor names (for lookalikes)
        competitor_names = parsed.get("competitor_names", [])
        if competitor_names:
            lookup_results = lookup_many_fn(competitor_names)
            result["competitor_parsed_list"] = _extract_comp_ids(lookup_results)
        
        # Lookup suggested companies (for lookalikes)
        suggested_names = parsed.get("suggested_companies", [])
        if suggested_names:
            lookup_results = lookup_many_fn(suggested_names)
            result["competitor_suggested_list"] = _extract_comp_ids(lookup_results)
        
        # Lookup explicit company names (where user wants employees)
        for suffix in ["curr", "past", "any"]:
            explicit_names = parsed.get(f"explicit_comp_names_{suffix}", [])
            if explicit_names:
                lookup_results = lookup_many_fn(explicit_names)
                result[f"explicit_comp_id_list_{suffix}"] = _extract_comp_ids(lookup_results)
    else:
        # Return names if no lookup function
        result["competitor_names"] = parsed.get("competitor_names", [])
        result["suggested_companies"] = parsed.get("suggested_companies", [])
        result["explicit_comp_names_curr"] = parsed.get("explicit_comp_names_curr", [])
        result["explicit_comp_names_past"] = parsed.get("explicit_comp_names_past", [])
        result["explicit_comp_names_any"] = parsed.get("explicit_comp_names_any", [])
    
    # 5. Lookup title IDs if searching for employees
    lead_type = result.get("filt_lead_type", [])
    emp_titles = result.get("filt_emp_title", [])
    
    if "employee" in lead_type and emp_titles and lookup_title_many_fn:
        title_lookup_results = lookup_title_many_fn(emp_titles)
        result["filt_emp_title_ids"] = _extract_title_ids(title_lookup_results)
    
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


def _extract_title_ids(lookup_results: List[Dict[str, Any]]) -> List[int]:
    """Extract title_ids from lookup_title_many results (top match per query)."""
    title_ids = []
    seen_ids = set()
    for item in lookup_results:
        result = item.get('result', {})
        rows = result.get('rows', [])
        if rows:
            # First column is title_id, take best match (first row)
            title_id = rows[0][0]
            if title_id not in seen_ids:
                seen_ids.add(title_id)
                title_ids.append(title_id)
    return title_ids

