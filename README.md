# Flujo Completo de Operación

> Caso de Uso: Soporte busca logs de un trabajador

Usuario de soporte abre el portal: http://support-portal:8080
Ingresa el RUT real: 12.345.678-9

El portal:
1. Llama a /search del tokenizer service
2. Recibe el token: TOK_RUT_a1b2c3d4e5f6...
3. Busca en New Relic usando ese token
4. Recibe logs donde aparece ese token
5. Resultado: El equipo de soporte puede ver todos los logs relacionados sin que New Relic almacene el RUT real

```
Conceptual:

Apps (Splunk) → OpenTelemetry Collector → New Relic
                    ↓
              Token Vault Service
              (Azure Key Vault / HashiCorp Vault)
                    ↑
              Support Portal/API
              (Para búsquedas)
```
