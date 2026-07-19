import requests
from google.transit import gtfs_realtime_pb2

# Target URL
URL = 'https://kordis-jmk.cz/gtfs/gtfsReal.dat'

def fetch_and_print():
    try:
        # Fetch raw binary data
        response = requests.get(URL, timeout=10)
        
        # Initialize GTFS Realtime message object
        feed = gtfs_realtime_pb2.FeedMessage()
        
        # Decode the binary Protobuf data
        feed.ParseFromString(response.content)
        
        # Print the decoded human-readable structure
        print(feed)
        
    except Exception as e:
        print(f'Error: {e}')

if __name__ == '__main__':
    fetch_and_print()
