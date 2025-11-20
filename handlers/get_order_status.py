import json
import os
import boto3
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
                'body': json.dumps({
                    'error': 'Pedido no encontrado'
                })
            }
        
        pedido = response['Item']
        
        resultado = {
            'order_id': order_id,
            'status': pedido.get('status', 'created'),
            'customer_id': pedido.get('customer_id'),
            'items': clean_decimals(pedido.get('items', [])),
            'total': float(pedido.get('total', 0)),
            'created_at': pedido.get('created_at'),
            'updated_at': pedido.get('updated_at'),
            'progress': calcular_progreso(pedido.get('status', 'created'))
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
            'body': json.dumps({
                'error': 'Error interno del servidor',
                'details': str(e)
            })
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

def clean_decimals(obj):
    if isinstance(obj, list):
        return [clean_decimals(i) for i in obj]
    if isinstance(obj, dict):
        return {k: clean_decimals(v) for k, v in obj.items()}
    if isinstance(obj, Decimal):
        return int(obj) if obj % 1 == 0 else float(obj)
    return obj