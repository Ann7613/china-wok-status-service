import json
import os
import boto3
from boto3.dynamodb.conditions import Key
from datetime import datetime
from decimal import Decimal
from collections import Counter

dynamodb = boto3.resource('dynamodb')
table = dynamodb.Table(os.environ['ORDERS_TABLE'])

def lambda_handler(event, context):

    print(f"Request: {json.dumps(event)}")
    
    try:
        params = event.get('queryStringParameters', {}) or {}
        status_filter = params.get('status')
        
        if status_filter:
            response = table.query(
                IndexName='OrdersByStatus',
                KeyConditionExpression=Key('status').eq(status_filter),
                ScanIndexForward=True  
            )
        else:
            response = table.scan()
        
        pedidos = response.get('Items', [])
        
        pedidos_formateados = [
            {
                'order_id': p.get('order_id'),
                'customer_id': p.get('customer_id'),
                'status': p.get('status'),
                'items': clean_decimals(p.get('items', [])),
                'total': float(p.get('total', 0)),
                'created_at': p.get('created_at'),
                'updated_at': p.get('updated_at'),
                'tiempo_espera_minutos': calcular_tiempo_espera(p.get('created_at')),
                'pasos_completados': contar_pasos(p.get('history', []))
            }
            for p in pedidos
        ]
        
        pedidos_formateados.sort(key=lambda x: x['created_at'] or '')
        
        estadisticas = generar_estadisticas_dashboard(pedidos_formateados)
        
        return {
            'statusCode': 200,
            'headers': {
                'Access-Control-Allow-Origin': '*',
                'Content-Type': 'application/json'
            },
            'body': json.dumps({
                'orders': pedidos_formateados,
                'statistics': estadisticas,
                'total': len(pedidos_formateados),
                'filter_applied': status_filter
            })
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

def calcular_tiempo_espera(created_at):

    if not created_at:
        return 0
    
    try:
        fecha_pedido = datetime.fromisoformat(created_at.replace('Z', '+00:00'))
        ahora = datetime.now(fecha_pedido.tzinfo)
        diferencia = (ahora - fecha_pedido).total_seconds() / 60
        return round(diferencia, 1)
    except:
        return 0

def contar_pasos(history):

    return len([h for h in history if 'status_changed' in h.get('action', '')])

def generar_estadisticas_dashboard(pedidos):

    if not pedidos:
        return {
            'total_pedidos': 0,
            'por_estado': {},
            'tiempo_espera_promedio': 0,
            'pedido_mas_antiguo': 0,
            'total_ventas': 0
        }
    
    estados = Counter(p['status'] for p in pedidos)
    
    tiempos_espera = [p['tiempo_espera_minutos'] for p in pedidos]
    tiempo_promedio = sum(tiempos_espera) / len(tiempos_espera) if tiempos_espera else 0
    pedido_mas_antiguo = max(tiempos_espera) if tiempos_espera else 0
    
    total_ventas = sum(p['total'] for p in pedidos)
    
    return {
        'total_pedidos': len(pedidos),
        'por_estado': dict(estados),
        'tiempo_espera_promedio': round(tiempo_promedio, 1),
        'pedido_mas_antiguo_minutos': round(pedido_mas_antiguo, 1),
        'total_ventas': round(total_ventas, 2),
        'estados_disponibles': ['created', 'preparing', 'ready', 'delivering', 'delivered', 'cancelled']
    }

def clean_decimals(obj):
    if isinstance(obj, list):
        return [clean_decimals(i) for i in obj]
    if isinstance(obj, dict):
        return {k: clean_decimals(v) for k, v in obj.items()}
    if isinstance(obj, Decimal):
        return int(obj) if obj % 1 == 0 else float(obj)
    return obj