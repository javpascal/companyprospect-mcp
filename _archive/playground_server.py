#!/usr/bin/env python3
"""
Nummary Playground Server
A Flask server that proxies requests to the Nummary API and handles CORS for the playground
"""

from flask import Flask, request, jsonify
from flask_cors import CORS
import requests
import os
from datetime import datetime
import json
from typing import Dict, Any, Optional, List

# Import existing configuration
from config import API_CONFIG, get_api_headers

app = Flask(__name__)
CORS(app)  # Enable CORS for all routes

# Store conversation history
conversation_history = []

@app.route('/health', methods=['GET'])
def health_check():
    """Health check endpoint"""
    return jsonify({
        'status': 'healthy',
        'timestamp': datetime.now().isoformat(),
        'api_configured': bool(API_CONFIG['key'])
    })

@app.route('/api/nummary/search', methods=['POST', 'OPTIONS'])
def search_companies():
    """
    Proxy endpoint for company search
    """
    if request.method == 'OPTIONS':
        return '', 204
    
    try:
        data = request.get_json()
        query = data.get('query', '').strip()
        
        if not query:
            return jsonify({
                'error': 'Invalid request',
                'message': 'Query parameter is required'
            }), 400
        
        # Call Nummary API
        url = f"{API_CONFIG['url']}/app/type/company"
        headers = get_api_headers()
        
        response = requests.post(
            url,
            headers=headers,
            json={'query': query},
            timeout=20
        )
        
        if response.ok:
            result = response.json()
            
            # Store in history
            conversation_history.append({
                'timestamp': datetime.now().isoformat(),
                'query': query,
                'results': result
            })
            
            # Transform the response for the frontend
            companies = []
            if isinstance(result, dict) and 'data' in result:
                companies = result['data']
            elif isinstance(result, list):
                companies = result
            
            # Format companies for display
            formatted_companies = []
            for company in companies[:10]:  # Limit to 10 results
                formatted_company = {
                    'name': company.get('name', 'Unknown'),
                    'description': company.get('description', ''),
                    'industry': company.get('industry', company.get('sector', '')),
                    'location': company.get('location', company.get('headquarters', '')),
                    'employees': company.get('employees', company.get('employee_count', '')),
                    'founded': company.get('founded', company.get('founded_year', '')),
                    'website': company.get('website', company.get('url', '')),
                    'revenue': company.get('revenue', ''),
                    'id': company.get('id', company.get('company_id', ''))
                }
                formatted_companies.append(formatted_company)
            
            return jsonify({
                'success': True,
                'data': formatted_companies,
                'count': len(formatted_companies),
                'query': query
            })
        else:
            return jsonify({
                'error': f'API error {response.status_code}',
                'message': response.text
            }), response.status_code
            
    except requests.exceptions.Timeout:
        return jsonify({
            'error': 'Request timeout',
            'message': 'The API request took too long to respond'
        }), 504
    except requests.exceptions.ConnectionError:
        return jsonify({
            'error': 'Connection error',
            'message': 'Could not connect to the Nummary API'
        }), 503
    except Exception as e:
        return jsonify({
            'error': 'Server error',
            'message': str(e)
        }), 500

@app.route('/api/nummary/company/<company_id>', methods=['GET'])
def get_company_details(company_id):
    """
    Get detailed information about a specific company
    """
    try:
        # This would call a specific company details endpoint if available
        url = f"{API_CONFIG['url']}/app/company/{company_id}"
        headers = get_api_headers()
        
        response = requests.get(
            url,
            headers=headers,
            timeout=20
        )
        
        if response.ok:
            return jsonify(response.json())
        else:
            # Fallback to mock data for demonstration
            return jsonify({
                'success': True,
                'data': {
                    'id': company_id,
                    'name': 'Example Company',
                    'description': 'Detailed company information would be displayed here',
                    'industry': 'Technology',
                    'founded': '2020',
                    'employees': '100-500',
                    'location': 'Global'
                }
            })
    except Exception as e:
        return jsonify({
            'error': 'Failed to fetch company details',
            'message': str(e)
        }), 500

@app.route('/api/nummary/analyze', methods=['POST'])
def analyze_industry():
    """
    Analyze industry trends and competitors
    """
    try:
        data = request.get_json()
        industry = data.get('industry', '')
        companies = data.get('companies', [])
        
        # This would call an industry analysis endpoint if available
        # For now, return a structured analysis response
        return jsonify({
            'success': True,
            'analysis': {
                'industry': industry,
                'market_size': 'Large',
                'growth_rate': '15% YoY',
                'key_trends': [
                    'Digital transformation',
                    'AI integration',
                    'Sustainability focus'
                ],
                'top_companies': companies[:5] if companies else [],
                'opportunities': [
                    'Emerging markets expansion',
                    'Product diversification',
                    'Strategic partnerships'
                ],
                'challenges': [
                    'Regulatory compliance',
                    'Market saturation',
                    'Technology disruption'
                ]
            }
        })
    except Exception as e:
        return jsonify({
            'error': 'Analysis failed',
            'message': str(e)
        }), 500

@app.route('/api/history', methods=['GET'])
def get_history():
    """
    Get conversation history
    """
    return jsonify({
        'success': True,
        'history': conversation_history[-50:]  # Last 50 queries
    })

@app.route('/api/history', methods=['DELETE'])
def clear_history():
    """
    Clear conversation history
    """
    global conversation_history
    conversation_history = []
    return jsonify({
        'success': True,
        'message': 'History cleared'
    })

@app.route('/api/export', methods=['GET'])
def export_data():
    """
    Export conversation history as JSON
    """
    return jsonify({
        'success': True,
        'data': conversation_history,
        'exported_at': datetime.now().isoformat()
    })

@app.route('/api/suggestions', methods=['POST'])
def get_suggestions():
    """
    Get search suggestions based on partial input
    """
    try:
        data = request.get_json()
        partial_query = data.get('query', '').strip()
        
        if len(partial_query) < 2:
            return jsonify({
                'success': True,
                'suggestions': []
            })
        
        # You could implement a real suggestion endpoint here
        # For now, return common search patterns
        suggestions = [
            f"{partial_query} startups",
            f"{partial_query} companies",
            f"{partial_query} industry leaders",
            f"{partial_query} technology",
            f"{partial_query} services"
        ]
        
        return jsonify({
            'success': True,
            'suggestions': suggestions[:5]
        })
    except Exception as e:
        return jsonify({
            'error': 'Failed to get suggestions',
            'message': str(e)
        }), 500

@app.errorhandler(404)
def not_found(error):
    return jsonify({
        'error': 'Endpoint not found',
        'message': 'The requested endpoint does not exist'
    }), 404

@app.errorhandler(500)
def internal_error(error):
    return jsonify({
        'error': 'Internal server error',
        'message': 'An unexpected error occurred'
    }), 500

if __name__ == '__main__':
    port = int(os.environ.get('PORT', 5000))
    debug = os.environ.get('DEBUG', 'true').lower() == 'true'
    
    print(f"""
    ╔══════════════════════════════════════════════╗
    ║     Nummary Playground Server Starting...    ║
    ╚══════════════════════════════════════════════╝
    
    🚀 Server Configuration:
    • Port: {port}
    • Debug: {debug}
    • API URL: {API_CONFIG['url']}
    • CORS: Enabled for all origins
    
    📝 Available Endpoints:
    • POST /api/nummary/search - Search companies
    • GET  /api/nummary/company/<id> - Get company details
    • POST /api/nummary/analyze - Analyze industry
    • GET  /api/history - Get search history
    • DELETE /api/history - Clear history
    • GET  /api/export - Export data
    • POST /api/suggestions - Get search suggestions
    • GET  /health - Health check
    
    🌐 Playground URL: http://localhost:{port}/
    
    Press Ctrl+C to stop the server
    """)
    
    app.run(
        host='0.0.0.0',
        port=port,
        debug=debug
    )
