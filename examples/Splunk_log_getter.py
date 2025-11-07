import requests
import splunklib.client as client

# Conectar a Splunk
service = client.connect(
    host='splunk-server',
    port=8089,
    username='admin',
    password='password'
)

# Query logs recientes
searchquery = "search index=* earliest=-5m"
job = service.jobs.create(searchquery)

# Reenviar a Collector
for result in job.results():
    requests.post(
        'http://otel-collector:8088/services/collector',
        json={
            'event': result['_raw'],
            'sourcetype': result['sourcetype']
        }
    )