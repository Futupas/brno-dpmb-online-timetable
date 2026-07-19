import websocket

WS_URL = 'wss://gis.brno.cz/geoevent/ws/services/stream_kordis_26/StreamServer/subscribe'
# WS_URL = 'wss://gis.brno.cz/geoevent/ws/services/stream_kordis_26/StreamServer/subscribe?outSR=4326'

def on_message(ws, message):
    print(f'MESSAGE: {message}')

def on_error(ws, error):
    print(f'ERROR: {error}')

def on_close(ws, status, msg):
    print(f'CLOSED: {status} - {msg}')

def on_open(ws):
    print('OPENED')

if __name__ == '__main__':
    ws = websocket.WebSocketApp(
        WS_URL,
        on_open=on_open,
        on_message=on_message,
        on_error=on_error,
        on_close=on_close
    )
    ws.run_forever()
