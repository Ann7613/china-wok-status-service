import json
import os
from datetime import datetime, timezone
import boto3
from decimal import Decimal

dynamodb = boto3.resource('dynamodb')
table = dynamodb.Table(os.environ['ORDERS_TABLE'])

def handle_order_event(event, context):

    print(f"Evento recibido: {json.dumps(event)}")
    
    try:
        detail = event['detail']
        event_type = event['detail-type']
        order_id = detail['order_id']
        
        now = datetime.now(timezone.utc).isoformat()
        
        if event_type == "OrderCreated":
            history_entry = {
                "event": "order_created",
                "timestamp": now,
                "customer_id": detail.get('customer_id'),
                "status": detail.get('status', 'created'),
                "total": detail.get('total'),
                "event_time": detail.get('event_time', now)
            }
            
        elif event_type == "OrderStatusUpdated":
            history_entry = {
                "event": "status_updated",
                "timestamp": now,
                "old_status": detail.get('old_status'),
                "new_status": detail.get('new_status'),
                "event_time": detail.get('event_time', now)
            }
            
        elif event_type == "OrderCancelled":
            history_entry = {
                "event": "order_cancelled",
                "timestamp": now,
                "reason": detail.get('reason', ''),
                "cancelled_by": detail.get('cancelled_by', 'system'),
                "event_time": detail.get('event_time', now)
            }
        else:
            print(f"Evento no reconocido: {event_type}")
            return {
                'statusCode': 200,
                'body': json.dumps({'message': 'Event type not processed'})
            }
        
        response = table.update_item(
            Key={'order_id': order_id},
            UpdateExpression="""
                SET event_history = list_append(
                    if_not_exists(event_history, :empty_list), 
                    :history_entry
                ),
                last_event_update = :timestamp
            """,
            ExpressionAttributeValues={
                ':history_entry': [history_entry],
                ':empty_list': [],
                ':timestamp': now
            },
            ReturnValues='UPDATED_NEW'
        )
        
        print(f"Pedido {order_id} actualizado con evento {event_type}")
        
        return {
            'statusCode': 200,
            'body': json.dumps({
                'message': 'Event processed successfully',
                'order_id': order_id,
                'event_type': event_type
            })
        }
        
    except KeyError as e:
        print(f"Campo faltante en el evento: {str(e)}")
        return {
            'statusCode': 400,
            'body': json.dumps({'error': f'Missing field: {str(e)}'})
        }
    except Exception as e:
        print(f"Error procesando evento: {str(e)}")
        return {
            'statusCode': 500,
            'body': json.dumps({'error': str(e)})
        }
