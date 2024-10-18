import asyncio
import websockets
import json
import logging
from api_helper import NorenApiPy
import requests
import time

logging.basicConfig(level=logging.DEBUG)

# Flag to tell us if the websocket is open
socket_opened = False

# Initialize the API object
api = NorenApiPy()

# Event handlers
def event_handler_order_update(message):
    print("order event: " + str(message))

def event_handler_quote_update(message):
    print(f"quote event: {time.strftime('%d-%m-%Y %H:%M:%S')} {message}")
    logging.info(f"Quote update received: {message}")
    asyncio.run_coroutine_threadsafe(quote_queue.put(message), loop)

async def get_credentials_and_security_ids():
    try:
        response = await asyncio.get_event_loop().run_in_executor(
            None,
            lambda: requests.get('http://localhost:3000/flattrade-websocket-data')
        )
        response.raise_for_status()
        data = response.json()
        usersession = data.get('usersession', '')
        userid = data.get('userid', '')
        defaultCallSecurityId = data.get('defaultCallSecurityId', '')
        defaultPutSecurityId = data.get('defaultPutSecurityId', '')
        
        if usersession and userid and defaultCallSecurityId and defaultPutSecurityId:
            logging.info("Valid data retrieved successfully")
            return usersession, userid, defaultCallSecurityId, defaultPutSecurityId
        else:
            logging.info("Waiting for valid data...")
            return None, None, None, None
    except requests.exceptions.RequestException as e:
        logging.error(f"Failed to retrieve data: {e}")
        return None, None, None, None

async def wait_for_data():
    while True:
        usersession, userid, defaultCallSecurityId, defaultPutSecurityId = await get_credentials_and_security_ids()
        if usersession and userid and defaultCallSecurityId and defaultPutSecurityId:
            return usersession, userid, defaultCallSecurityId, defaultPutSecurityId
        await asyncio.sleep(5)  # Wait for 5 seconds before trying again

async def setup_api_connection(usersession, userid, defaultCallSecurityId, defaultPutSecurityId):
    global api
    # Set up the session
    ret = api.set_session(userid=userid, password='', usertoken=usersession)

    if ret is not None:
        # Start the websocket
        ret = api.start_websocket(
            order_update_callback=event_handler_order_update,
            subscribe_callback=event_handler_quote_update,
            socket_open_callback=open_callback  # No parameters needed
        )
        print(ret)
    else:
        raise Exception("Failed to set up API session")
    
    
def open_callback():
    global socket_opened
    socket_opened = True
    print('app is connected')
    
    # Optionally, you can log or perform other actions here
    # without subscribing to hardcoded symbols

    
quote_queue = asyncio.Queue()

async def websocket_server(websocket, path):
    try:
        # Create a task to continuously send quote updates to the client
        send_task = asyncio.create_task(send_quote_updates(websocket))
        
        async for message in websocket:
            await handle_websocket_message(websocket, message)
    except websockets.exceptions.ConnectionClosed:
        print("Connection closed")
    finally:
        # Cancel the send task when the connection is closed
        send_task.cancel()

async def send_quote_updates(websocket):
    while True:
        try:
            quote = await quote_queue.get()
            await websocket.send(json.dumps(quote))
        except Exception as e:
            logging.error(f"Error sending quote update: {e}")
            # If there's an error, wait a bit before trying again
            await asyncio.sleep(1)

async def handle_websocket_message(websocket, message):
    data = json.loads(message)
    if 'action' in data:
        if data['action'] == 'unsubscribe':
            for symbol in data['symbols']:
                api.unsubscribe([symbol])
                print(f"Unsubscribed from {symbol}")
                logging.info(f"Unsubscribed from {symbol}")
        elif data['action'] == 'subscribe':
            for symbol in data['symbols']:
                api.subscribe([symbol])
                print(f"Subscribed to {symbol}")
                logging.info(f"Subscribed to {symbol}")
            
            # Add a small delay after subscribing
            await asyncio.sleep(0.1)
            
            # Check for any pending quote updates
            while not quote_queue.empty():
                quote = await quote_queue.get()
                await websocket.send(json.dumps(quote))
    else:
        # Handle the existing credential update logic
        global usersession, userid, defaultCallSecurityId, defaultPutSecurityId
        usersession = data.get('usersession', '')
        userid = data.get('userid', '')
        defaultCallSecurityId = data.get('defaultCallSecurityId', '')
        defaultPutSecurityId = data.get('defaultPutSecurityId', '')
        print(f"Updated credentials and security IDs: {usersession[:5]}..., {userid}, {defaultCallSecurityId}, {defaultPutSecurityId}")

async def main():
    global loop
    loop = asyncio.get_running_loop()

    try:
        # Wait for valid credentials and security IDs
        logging.info("Waiting for valid data...")
        usersession, userid, defaultCallSecurityId, defaultPutSecurityId = await wait_for_data()
        logging.info(f"Using usersession: {usersession[:5]}..., userid: {userid}, defaultCallSecurityId: {defaultCallSecurityId}, defaultPutSecurityId: {defaultPutSecurityId}")

        # Set up API connection
        await setup_api_connection(usersession, userid, defaultCallSecurityId, defaultPutSecurityId)

        # Set up WebSocket server
        server = await websockets.serve(websocket_server, "localhost", 8765)
        await server.wait_closed()

    except Exception as e:
        logging.error(f"An error occurred: {e}")

if __name__ == "__main__":
    asyncio.run(main())