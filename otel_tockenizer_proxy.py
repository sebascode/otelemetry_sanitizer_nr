"""
Proxy que recibe logs del Collector y los tokeniza
"""
from flask import Flask, request, jsonify
import requests
import json

app = Flask(__name__)
TOKENIZER_URL = "http://localhost:5000/tokenize"

@app.route('/logs', methods=['POST'])
def process_logs():
    """Recibe logs OTLP y los tokeniza"""
    otlp_data = request.json
    
    # Procesar cada log
    for resource_log in otlp_data.get('resourceLogs', []):
        for scope_log in resource_log.get('scopeLogs', []):
            for log_record in scope_log.get('logRecords', []):
                # Tokenizar el body
                original_body = log_record.get('body', {}).get('stringValue', '')
                
                if original_body:
                    response = requests.post(
                        TOKENIZER_URL,
                        json={'log_body': original_body},
                        timeout=5
                    )
                    
                    if response.ok:
                        result = response.json()
                        log_record['body']['stringValue'] = result['tokenized_body']
                        
                        # Agregar metadata de tokens usados
                        if 'attributes' not in log_record:
                            log_record['attributes'] = []
                        
                        log_record['attributes'].append({
                            'key': 'tokens_used',
                            'value': {'stringValue': json.dumps(result['tokens_used'])}
                        })
    
    return jsonify(otlp_data)

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=4319)