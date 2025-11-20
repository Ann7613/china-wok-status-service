import json
import os
import boto3
from boto3.dynamodb.conditions import Key
from decimal import Decimal

dynamodb = boto3.resource('dynamodb')
table = dynamodb.Table(os.environ['ORDERS_TABLE'])

def lambda_handler(event, context):

    print(f"Request: {json.dumps(event)}")
    
    try:
        customer_id = event['pathParameters']['customer_id']
        
        response = table.query(
            IndexName='OrdersByCustomer',
            KeyConditionExpression=Key('customer_id').eq(customer_id),
            ScanIndexForward=False  
        )
        
        pedidos = response.get('Items', [])
        
        pedidos_formateados = [
            {
                'order_id': p.get('order_id'),
                'status': p.get('status'),
                'items': clean_decimals(p.get('items', [])),
                'total': float(p.get('total', 0)),
                'created_at': p.get('created_at'),
                'updated_at': p.get('updated_at'),
                'progress': calcular_progreso(p.get('status', 'created')),
                'status_label': obtener_label_estado(p.get('status'))
            }
            for p in pedidos
        ]
        
        return {
            'statusCode': 200,
            'headers': {
                'Access-Control-Allow-Origin': '*',
                'Content-Type': 'application/json'
            },
            'body': json.dumps({
                'customer_id': customer_id,
                'orders': pedidos_formateados,
                'total_orders': len(pedidos_formateados)
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

def calcular_progreso(status):
    estados = {
        'created': 10,
        'preparing': 40,
        'ready': 70,
        'delivering': 90,
        'delivered': 100,
        'cancelled': 0
    }
    return estados.get(status, 0)

def obtener_label_estado(status):
    labels = {
        'created': 'Pedido Recibido',
        'preparing': 'En Preparación',
        'ready': 'Listo para Recoger',
        'delivering': 'En Camino',
        'delivered': 'Entregado',
        'cancelled': 'Cancelado'
    }
    return labels.get(status, status)

def clean_decimals(obj):
    if isinstance(obj, list):
        return [clean_decimals(i) for i in obj]
    if isinstance(obj, dict):
        return {k: clean_decimals(v) for k, v in obj.items()}
    if isinstance(obj, Decimal):
        return int(obj) if obj % 1 == 0 else float(obj)
    return obj