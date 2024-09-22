from googleapiclient.discovery import build

KEYWORD = "플레이리스트|playlist|플리"

def get_search_channel(youtube):
    response = youtube.search().list(
        part = 'snippet',
        maxResults = 30,
        q = KEYWORD,
        type = "channel",
        order = 'relevance'
    ).execute()

    return [item['id']['channelId'] for item in response['items'] if item['id']['kind'] == 'youtube#channel']