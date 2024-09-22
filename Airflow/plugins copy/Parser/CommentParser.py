import re
from Model.Playlist import Playlist

from tqdm import tqdm
from googleapiclient.errors import HttpError

def remove_emoticons(text):
    # 이모티콘을 감지하기 위한 정규 표현식
    emoticon_pattern = re.compile(
        r'[\U0001F600-\U0001F64F'  
        r'\U0001F300-\U0001F5FF'  
        r'\U0001F680-\U0001F6FF'  
        r'\U0001F900-\U0001F9FF'  
        r'\U0001FA00-\U0001FA6F'  
        r'\U0001FA70-\U0001FAFF'   
        r']', re.UNICODE)
    
    return emoticon_pattern.sub('', text)

def parse_reply(comment):
    informations = []
    split_comments = comment.split("\n")

    for line in split_comments:
        line = remove_emoticons(line)
        line = line.replace(u'\xa0', u' ')
        line = line.strip()

        #타임스탬프 형식으로 시작하는 라인만 남기기
        time_line_format = r'^\[\d{1,2}:\d{2}(:\d{2})?\]\s+|^\d{1,2}:\d{2}(:\d{2})?\s+'
        if not re.match(time_line_format, line):
            continue

        line = re.sub(time_line_format, '', line)
        line = re.sub(r'\r', '', line)
        line_splits = list(map(lambda x: x.strip(), line.split("-")))
        if line and len(line_splits) == 2:
            join_values = ' - '.join(line_splits)
            informations.append(join_values)
    return informations

def parse_video(youtube, items):
    playlist_list = []
    video_ids = [item['id']['videoId'] for item in items if item['id']['kind'] == "youtube#video"]

    video_response = youtube.videos().list(
        part='snippet,statistics',
        id=','.join(video_ids)
    ).execute()

    for item in video_response['items']:
        title = item['snippet']['title']
        video_id = item['id']
        comment_count = int(item['statistics'].get('commentCount', 0))

        playlist = Playlist(title = title, video_id = video_id)

        if comment_count == 0:
            print(f"댓글이 없는 동영상입니다: {title}")
            continue
        
        try:
            replies = youtube.commentThreads().list(
                part = 'snippet,replies',
                videoId = video_id,
                maxResults = 1
            ).execute()
            
            reply_items = replies['items']

            if len(reply_items) < 1: continue
            comment = reply_items[0]['snippet']['topLevelComment']['snippet']['textOriginal']
            informations = parse_reply(comment)

            if len(comment) < 1 or len(informations) < 1: continue
            
            playlist.convert_informations(informations)
            playlist_list.append(playlist.to_json())
        except HttpError as e:
            if 'commentsDisabled' in str(e):
                print(f"댓글이 비활성화된 동영상입니다: {title}")
            else:
                print(f"동영상 {title}에 대한 댓글을 가져오는 중 오류 발생: {e}")

    return playlist_list

def get_comment_playlist(youtube, channel_id):
    next_page_token = None
    
    response = youtube.search().list(
        part = 'snippet',
        channelId = channel_id,
        maxResults = 10,
        pageToken = next_page_token,
        type = "video",
        order = 'date'
    ).execute()

    items = response['items']
    playlist_list = parse_video(youtube, items)
    return playlist_list
