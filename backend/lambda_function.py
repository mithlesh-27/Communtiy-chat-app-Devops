import json
import boto3
import uuid
from datetime import datetime
from decimal import Decimal

# Initialize the DynamoDB resource
dynamodb = boto3.resource('dynamodb')
table = dynamodb.Table('CommunityChats')

def lambda_handler(event, context):
    method = event['httpMethod']
    path = event['resource']

    try:
        if method == 'POST' and path == '/createThread':
            return create_thread(event)
        elif method == 'POST' and path == '/addReply':
            return add_reply(event)
        elif method == 'PUT' and path == '/updateThread':
            return update_thread(event)
        elif method == 'DELETE' and path == '/deleteThread':
            return delete_thread(event)
        elif method == 'DELETE' and path == '/deleteReply':
            return delete_reply(event)
        elif method == 'GET' and path == '/listThreads':
            return list_threads()
        elif method == 'GET' and path == '/getChatMessages':
            return get_chat_messages(event)
        else:
            return {
                'statusCode': 404,
                'headers': cors_headers(),
                'body': json.dumps({'message': 'Endpoint not found'})
            }
    except Exception as e:
        print(f"Error in processing request: {str(e)}")
        return {
            'statusCode': 500,
            'headers': cors_headers(),
            'body': json.dumps({'error': 'Internal server error'})
        }

def cors_headers():
    return {
        'Access-Control-Allow-Origin': '*',
        'Access-Control-Allow-Methods': 'GET, POST, PUT, DELETE',
        'Access-Control-Allow-Headers': 'Content-Type',
    }

def decimal_to_float(data):
    if isinstance(data, list):
        return [decimal_to_float(item) for item in data]
    elif isinstance(data, dict):
        return {key: decimal_to_float(value) for key, value in data.items()}
    elif isinstance(data, Decimal):
        return float(data)
    return data

def thread_exists(thread_id):
    try:
        response = table.get_item(Key={'threadId': thread_id})
        return 'Item' in response
    except Exception as e:
        print(f"Error checking thread existence: {str(e)}")
        return False

def create_thread(event):
    data = json.loads(event['body'])
    if not all(key in data for key in ['userId', 'title', 'content']):
        return {
            'statusCode': 400,
            'headers': cors_headers(),
            'body': json.dumps({'error': 'Missing required fields: userId, title, and content are required.'})
        }

    thread_id = int(datetime.now().timestamp())
    user_id = data['userId']
    title = data['title']
    content = data['content']

    item = {
        'threadId': thread_id,
        'userId': user_id,
        'title': title,
        'content': content,
        'createdAt': datetime.now().isoformat(),
        'messages': []  # Initialize messages as an empty list
    }

    try:
        table.put_item(Item=item)
    except Exception as e:
        print(f"Failed to create thread: {str(e)}")
        return {
            'statusCode': 500,
            'headers': cors_headers(),
            'body': json.dumps({'error': 'Failed to create thread'})
        }

    return {
        'statusCode': 201,
        'headers': cors_headers(),
        'body': json.dumps({'message': 'Thread created', 'threadId': thread_id})
    }

def add_reply(event):
    data = json.loads(event['body'])
    if not all(key in data for key in ['threadId', 'userId', 'content']):
        return {
            'statusCode': 400,
            'headers': cors_headers(),
            'body': json.dumps({'error': 'Missing required fields: threadId, userId, and content are required.'})
        }

    thread_id = int(data['threadId'])
    user_id = data['userId']
    content = data['content']
    message_id = str(uuid.uuid4())  # Generate a unique message ID

    if not thread_exists(thread_id):
        return {
            'statusCode': 404,
            'headers': cors_headers(),
            'body': json.dumps({'error': 'Thread not found.'})
        }

    try:
        table.update_item(
            Key={'threadId': thread_id},
            UpdateExpression='SET #messages = list_append(if_not_exists(#messages, :empty_list), :message)',
            ExpressionAttributeNames={'#messages': 'messages'},
            ExpressionAttributeValues={
                ':message': [{
                    'messageId': message_id,
                    'userId': user_id,
                    'content': content,
                    'createdAt': datetime.now().isoformat(),
                }],
                ':empty_list': []
            }
        )
    except Exception as e:
        print(f"Failed to add message: {str(e)}")
        return {
            'statusCode': 500,
            'headers': cors_headers(),
            'body': json.dumps({'error': 'Failed to add message'})
        }

    return {
        'statusCode': 200,
        'headers': cors_headers(),
        'body': json.dumps({'message': 'Message added', 'messageId': message_id})
    }

def update_thread(event):
    data = json.loads(event['body'])
    if not all(key in data for key in ['threadId', 'title', 'content']):
        return {
            'statusCode': 400,
            'headers': cors_headers(),
            'body': json.dumps({'error': 'Missing required fields: threadId, title, and content are required.'})
        }

    thread_id = int(data['threadId'])
    title = data['title']
    content = data['content']

    if not thread_exists(thread_id):
        return {
            'statusCode': 404,
            'headers': cors_headers(),
            'body': json.dumps({'error': 'Thread not found.'})
        }

    try:
        table.update_item(
            Key={'threadId': thread_id},
            UpdateExpression='SET title = :title, content = :content',
            ExpressionAttributeValues={
                ':title': title,
                ':content': content
            }
        )
    except Exception as e:
        print(f"Failed to update thread: {str(e)}")
        return {
            'statusCode': 500,
            'headers': cors_headers(),
            'body': json.dumps({'error': 'Failed to update thread'})
        }

    return {
        'statusCode': 200,
        'headers': cors_headers(),
        'body': json.dumps({'message': 'Thread updated successfully'})
    }

def delete_thread(event):
    thread_id = int(event['queryStringParameters']['threadId'])

    if not thread_exists(thread_id):
        return {
            'statusCode': 404,
            'headers': cors_headers(),
            'body': json.dumps({'error': 'Thread not found.'})
        }

    try:
        table.delete_item(Key={'threadId': thread_id})
    except Exception as e:
        print(f"Failed to delete thread: {str(e)}")
        return {
            'statusCode': 500,
            'headers': cors_headers(),
            'body': json.dumps({'error': 'Failed to delete thread'})
        }

    return {
        'statusCode': 200,
        'headers': cors_headers(),
        'body': json.dumps({'message': 'Thread deleted successfully'})
    }

def delete_reply(event):
    thread_id = int(event['queryStringParameters']['threadId'])
    reply_id = event['queryStringParameters']['replyId']

    if not thread_exists(thread_id):
        return {
            'statusCode': 404,
            'headers': cors_headers(),
            'body': json.dumps({'error': 'Thread not found.'})
        }

    try:
        response = table.get_item(Key={'threadId': thread_id})
        if 'Item' not in response or 'messages' not in response['Item']:
            return {
                'statusCode': 404,
                'headers': cors_headers(),
                'body': json.dumps({'error': 'No messages found for this thread.'})
            }

        messages = response['Item']['messages']
        updated_messages = [msg for msg in messages if msg['messageId'] != reply_id]

        table.update_item(
            Key={'threadId': thread_id},
            UpdateExpression='SET #messages = :messages',
            ExpressionAttributeNames={'#messages': 'messages'},
            ExpressionAttributeValues={':messages': updated_messages}
        )
    except Exception as e:
        print(f"Failed to delete reply: {str(e)}")
        return {
            'statusCode': 500,
            'headers': cors_headers(),
            'body': json.dumps({'error': 'Failed to delete reply'})
        }

    return {
        'statusCode': 200,
        'headers': cors_headers(),
        'body': json.dumps({'message': 'Reply deleted successfully'})
    }

def list_threads():
    try:
        response = table.scan()
        threads = response.get('Items', [])
        threads = decimal_to_float(threads)
        return {
            'statusCode': 200,
            'headers': cors_headers(),
            'body': json.dumps(threads)
        }
    except Exception as e:
        print(f"Failed to retrieve threads: {str(e)}")
        return {
            'statusCode': 500,
            'headers': cors_headers(),
            'body': json.dumps({'error': 'Failed to retrieve threads'})
        }

def get_chat_messages(event):
    thread_id = int(event['queryStringParameters']['threadId'])
    message_id = event['queryStringParameters'].get('messageId', None)

    if not thread_exists(thread_id):
        return {
            'statusCode': 404,
            'headers': cors_headers(),
            'body': json.dumps({'error': 'Thread not found.'})
        }

    try:
        response = table.get_item(Key={'threadId': thread_id})
        if 'Item' not in response or 'messages' not in response['Item']:
            return {
                'statusCode': 404,
                'headers': cors_headers(),
                'body': json.dumps({'error': 'No messages found for this thread.'})
            }

        messages = response['Item']['messages']
        messages = decimal_to_float(messages)

        if message_id is not None:
            message = next((msg for msg in messages if msg['messageId'] == message_id), None)

            if message is None:
                return {
                    'statusCode': 404,
                    'headers': cors_headers(),
                    'body': json.dumps({'error': 'Message not found.'})
                }

            return {
                'statusCode': 200,
                'headers': cors_headers(),
                'body': json.dumps(message)
            }
        
        return {
            'statusCode': 200,
            'headers': cors_headers(),
            'body': json.dumps(messages)
        }
    except Exception as e:
        print(f"Failed to retrieve messages: {str(e)}")
        return {
            'statusCode': 500,
            'headers': cors_headers(),
            'body': json.dumps({'error': 'Failed to retrieve messages'})
        }
