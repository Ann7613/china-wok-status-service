import json
import os
import boto3
from datetime import datetime
from decimal import Decimal

dynamodb = boto3.resource('dynamodb')
table = dynamodb.Table(os.environ['ORDERS_TABLE'])

def lambda_handler(event, context):

    print(f"Request: {json.dumps(event)}")
    
    try:
        order_id = event['pathParameters']['order_id']
        
        response = table.get_item(Key={'order_id': order_id})
        
        if 'Item' not in response:
            return {
                'statusCode': 404,
                'headers': {
                    'Access-Control-Allow-Origin': '*',
                    'Content-Type': 'application/json'
                },
                'body': json.dumps({'error': 'Pedido no encontrado'})
            }
        
        pedido = response['Item']
        
        history_original = pedido.get('history', [])
        event_history = pedido.get('event_history', [])
        
        timeline = construir_timeline(history_original, event_history)
        estadisticas = calcular_estadisticas(timeline, pedido)
        
        resultado = {
            'order_id': order_id,
            'customer_id': pedido.get('customer_id'),
            'status': pedido.get('status'),
            'items': clean_decimals(pedido.get('items', [])),
            'total': float(pedido.get('total', 0)),
            'created_at': pedido.get('created_at'),
            'updated_at': pedido.get('updated_at'),
            'timeline': timeline,
            'statistics': estadisticas
        }
        
        return {
            'statusCode': 200,
            'headers': {
                'Access-Control-Allow-Origin': '*',
                'Content-Type': 'application/json'
            },
            'body': json.dumps(resultado)
        }
        
    except Exception as e:
        print(f"Error: {str(e)}")
        return {
            'statusCode': 500,
            'headers': {
                'Access-Control-Allow-Origin': '*',
                'Content-Type': 'application/json'
            },
            'body': json.dumps({'error': str(e)})
        }

def construir_timeline(history_original, event_history):

    timeline = []
    
    for entry in history_original:
        timeline.append({
            'timestamp': entry.get('at'),
            'action': entry.get('action'),
            'by': entry.get('by'),
            'reason': entry.get('reason', ''),
            'source': 'order_service'
        })
    
    for entry in event_history:
        timeline.append({
            'timestamp': entry.get('timestamp'),
            'event': entry.get('event'),
            'details': {k: v for k, v in entry.items() if k not in ['timestamp', 'event']},
            'source': 'status_service'
        })
    
    timeline.sort(key=lambda x: x.get('timestamp', ''))
    
    return timeline

def calcular_estadisticas(timeline, pedido):

    if not timeline:
        return {}
    
    try:
        created_at = pedido.get('created_at')
        updated_at = pedido.get('updated_at')
        
        if created_at and updated_at:
            inicio = datetime.fromisoformat(created_at.replace('Z', '+00:00'))
            fin = datetime.fromisoformat(updated_at.replace('Z', '+00:00'))
            tiempo_total = (fin - inicio).total_seconds() / 60
        else:
            tiempo_total = 0
        
        cambios_estado = len([e for e in timeline if 'status_changed' in e.get('action', '')])
        
        return {
            'tiempo_total_minutos': round(tiempo_total, 2),
            'eventos_totales': len(timeline),
            'cambios_estado': cambios_estado,
            'estado_actual': pedido.get('status')
        }
    except Exception as e:
        print(f"Error calculando estadísticas: {str(e)}")
        return {'error': 'No se pudieron calcular estadísticas'}

def clean_decimals(obj):
    if isinstance(obj, list):
        return [clean_decimals(i) for i in obj]
    if isinstance(obj, dict):
        return {k: clean_decimals(v) for k, v in obj.items()}
    if isinstance(obj, Decimal):
        return int(obj) if obj % 1 == 0 else float(obj)
    return obj