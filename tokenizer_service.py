from flask import Flask, request, jsonify
from azure.data.tables import TableServiceClient
from azure.identity import DefaultAzureCredential
import hashlib
import secrets
import re

app = Flask(__name__)

# Conexión a Azure Table Storage
credential = DefaultAzureCredential()
table_service = TableServiceClient(
    endpoint="https://tokenstore.table.core.windows.net",
    credential=credential
)
token_table = table_service.get_table_client("tokens")

# Patrones de datos sensibles
PATTERNS = {
    'rut': r'\b\d{1,2}\.?\d{3}\.?\d{3}-[0-9kK]\b',
    'email': r'\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,}\b',
    'phone': r'\+?56\s?9\s?\d{4}\s?\d{4}',
    'license': r'\b[A-Z]{2}-\d{6,8}\b'
}

def generate_token(original_value, data_type):
    """Genera o recupera un token para un valor"""
    # Crear un hash del valor original como clave
    value_hash = hashlib.sha256(original_value.encode()).hexdigest()
    
    try:
        # Intentar recuperar token existente
        entity = token_table.get_entity(
            partition_key=data_type,
            row_key=value_hash
        )
        return entity['token']
    except:
        # Crear nuevo token
        token = f"TOK_{data_type.upper()}_{secrets.token_hex(16)}"
        
        # Guardar bidireccional
        token_table.create_entity({
            'PartitionKey': data_type,
            'RowKey': value_hash,
            'token': token,
            'original_value': original_value  # Encriptado en producción
        })
        
        # Índice inverso para búsquedas
        token_table.create_entity({
            'PartitionKey': 'reverse_lookup',
            'RowKey': token,
            'original_value': original_value,
            'data_type': data_type
        })
        
        return token

def tokenize_log(log_body):
    """Tokeniza todos los datos sensibles en un log"""
    tokenized = log_body
    tokens_used = {}
    
    for data_type, pattern in PATTERNS.items():
        matches = re.finditer(pattern, log_body)
        for match in matches:
            original = match.group(0)
            token = generate_token(original, data_type)
            tokenized = tokenized.replace(original, token)
            tokens_used[data_type] = tokens_used.get(data_type, 0) + 1
    
    return tokenized, tokens_used

@app.route('/tokenize', methods=['POST'])
def tokenize():
    """Endpoint para tokenizar logs"""
    data = request.json
    log_body = data.get('log_body', '')
    
    tokenized_body, tokens_used = tokenize_log(log_body)
    
    return jsonify({
        'original_body': log_body,
        'tokenized_body': tokenized_body,
        'tokens_used': tokens_used
    })

@app.route('/detokenize', methods=['POST'])
def detokenize():
    """Endpoint para recuperar valor original (solo para soporte autorizado)"""
    data = request.json
    token = data.get('token')
    
    try:
        entity = token_table.get_entity(
            partition_key='reverse_lookup',
            row_key=token
        )
        return jsonify({
            'token': token,
            'original_value': entity['original_value'],
            'data_type': entity['data_type']
        })
    except:
        return jsonify({'error': 'Token not found'}), 404

@app.route('/search', methods=['POST'])
def search_by_value():
    """Búsqueda: dado un valor real, encontrar su token"""
    data = request.json
    original_value = data.get('value')
    data_type = data.get('type', 'rut')  # tipo por defecto
    
    value_hash = hashlib.sha256(original_value.encode()).hexdigest()
    
    try:
        entity = token_table.get_entity(
            partition_key=data_type,
            row_key=value_hash
        )
        return jsonify({
            'original_value': original_value,
            'token': entity['token'],
            'data_type': data_type
        })
    except:
        return jsonify({'error': 'Value not found'}), 404

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000)