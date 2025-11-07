from flask import Flask, render_template, request, jsonify
import requests
from azure.identity import DefaultAzureCredential
from azure.data.tables import TableServiceClient

app = Flask(__name__)

TOKENIZER_URL = "http://localhost:5000"
NEWRELIC_API = "https://api.newrelic.com/graphql"
NEWRELIC_API_KEY = "YOUR_USER_API_KEY"

@app.route('/')
def index():
    return render_template('search.html')

@app.route('/search', methods=['POST'])
def search():
    """Búsqueda por dato sensible real"""
    data = request.json
    search_value = data.get('value')  # ej: "12.345.678-9"
    search_type = data.get('type', 'rut')
    
    # 1. Obtener el token para ese valor
    token_response = requests.post(
        f"{TOKENIZER_URL}/search",
        json={'value': search_value, 'type': search_type}
    )
    
    if not token_response.ok:
        return jsonify({'error': 'Value not found in token database'}), 404
    
    token_data = token_response.json()
    token = token_data['token']
    
    # 2. Buscar en New Relic usando el token
    nrql_query = f"""
    {{
      actor {{
        account(id: YOUR_ACCOUNT_ID) {{
          nrql(query: "SELECT * FROM Log WHERE message LIKE '%{token}%' SINCE 7 DAYS AGO LIMIT 100") {{
            results
          }}
        }}
      }}
    }}
    """
    
    nr_response = requests.post(
        NEWRELIC_API,
        headers={
            'Content-Type': 'application/json',
            'API-Key': NEWRELIC_API_KEY
        },
        json={'query': nrql_query}
    )
    
    logs = nr_response.json()
    
    return jsonify({
        'search_value': search_value,
        'token': token,
        'logs_found': len(logs.get('data', {}).get('actor', {}).get('account', {}).get('nrql', {}).get('results', [])),
        'logs': logs
    })

@app.route('/detokenize/<token>', methods=['GET'])
def detokenize(token):
    """Ver valor original de un token (para debugging)"""
    response = requests.post(
        f"{TOKENIZER_URL}/detokenize",
        json={'token': token}
    )
    
    if response.ok:
        return jsonify(response.json())
    return jsonify({'error': 'Token not found'}), 404

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=8080)