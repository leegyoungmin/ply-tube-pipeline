# 기본 모듈
import os
import pendulum
import json

# Airflow 관련 모듈
from airflow.decorators import dag, task, task_group
from airflow import XComArg

# Python Operator 모듈
from googleapiclient.discovery import build
from dotenv import load_dotenv

# SQL 관련 모듈
from sqlalchemy import create_engine, Column, String, Integer
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker

@dag(
    dag_id="dags_collect_playlist",
    schedule="@daily",
    start_date=pendulum.now(tz="Asia/Seoul"),
    catchup=False,
    tags=["collect_playlist"]
)
def collect_playlist():
    load_dotenv('/opt/airflow/.env', override = True)

    API_KEY = os.environ.get("API_KEY")
    YOUTUBE_API_SERVICE_NAME = 'youtube'
    YOUTUBE_API_SERVICE_VERSION = 'v3'

    # PostgreSQL 연결 정보
    DATABASE_URL = os.environ.get("DATABASE_URL")  # .env 파일에서 가져올 것

    Base = declarative_base()

    class Playlist_Model(Base):
        __tablename__ = 'playlist'
        play_id = Column(String(50), primary_key=True)
        title = Column(String(255), nullable=False)

    class Music_Model(Base):
        __tablename__ = 'music'
        music_id = Column(Integer, primary_key=True, autoincrement=True)
        play_id = Column(String(50), nullable=False)
        music_info = Column(String(255))
        feature_music_info = Column(String(255))

    
    # YouTube API 클라이언트 생성 (고정된 값으로 처리)
    youtube_client = build(YOUTUBE_API_SERVICE_NAME, YOUTUBE_API_SERVICE_VERSION, developerKey=API_KEY)

    def preprocess(item):
        item = item.lower()
        
        item_split = item.split('-')
        if len(item_split) == 2:
            item_split = list(map(lambda x: x.replace(' ',''), item_split))
            item = ' - '.join(item_split)
        return item
    
    @task(task_id="collect_playlist_channels")
    def collect_channel_ids():
        from Parser.ChannelParser import get_search_channel

        # YouTube API 클라이언트를 함수 내에서 사용
        channel_list = get_search_channel(youtube_client)
        print(f"Collected channels: {channel_list}")
        return channel_list  # 리스트 형태로 반환
    
    # 각 채널에 대한 비디오 수집 작업
    @task(task_id="collect_each_video_items")
    def collect_videos(channel_id: str):
        from Parser.CommentParser import get_comment_playlist

        # YouTube API 클라이언트를 여기서 사용
        comment_items = get_comment_playlist(youtube=youtube_client, channel_id=channel_id)
        print(f"{channel_id} : {len(comment_items)}")

        return comment_items
    
    @task(task_id = "dvc_pull_data")
    def dvc_pull_data(mounted_folder: str = "/opt/airflow/feature_store", data_filename: str = "playlist.json"):
        import subprocess

        dvc_repo_path = os.path.join(mounted_folder)
        
        if os.path.exists(dvc_repo_path + f"/{data_filename}"):
            command = f"cd {dvc_repo_path} && mv {data_filename} {data_filename}.backup && dvc pull"
        else:
            command = f"cd {dvc_repo_path} && dvc pull"

        subprocess.run(command, shell=True, check=True)
        print(f"DVC pull completed for {dvc_repo_path}")
     
    @task(task_id = "load_and_process_data")
    def load_and_process_data(mounted_folder: str = "/opt/airflow/feature_store", data_filename: str = "playlist.json"):
        data_file_path = os.path.join(mounted_folder, data_filename)

        # 파일 존재 여부 확인
        if not os.path.exists(data_file_path):
            return []

        # JSON 파일 읽기
        with open(data_file_path, 'r') as file:
            try:
                data = json.load(file)
            except json.JSONDecodeError:
                return []
                # JSON 내용이 비어 있는지 확인
        if not data:
            return []
        
        return data['playlists']
    
    @task(task_id="combine_video_data")
    def combine_video_data(video_data_list, existing_data):
        combined_data = []
        print(video_data_list)

        if isinstance(existing_data, list):
            combined_data = existing_data

        existing_video_ids = {item['video_id'] for item in combined_data}

        for video_data in video_data_list:
            for item in video_data:
                if item['video_id'] not in existing_video_ids:
                    combined_data.append(item)
                    existing_video_ids.add(item['video_id'])

        # JSON 형식으로 변환
        json_data = {
            'created_at': pendulum.now().format('YYYY.MM.DD HH:mm:ss'),
            'playlists': combined_data
        }

        return json_data

    @task(task_id = "save_combined_data_local")
    def save_combined_data_local(
        combined_data, 
        mounted_folder: str = "/opt/airflow/feature_store", 
        data_filename: str = "playlist.json"
    ):
        file_path = os.path.join(mounted_folder, data_filename)

        with open(file_path, 'w') as file:
            json.dump(combined_data, file, indent=4, ensure_ascii=False)
        
        print(f"Combined data saved to {file_path}")

    @task.bash(task_id = "upload_data_s3")
    def upload_data_s3():
        command = """
        cd /opt/airflow/feature_store && \
        git checkout dataset && \
        dvc add playlist.json && \
        dvc push && \
        eval "$(ssh-agent -s)" && \
        ssh-add /opt/airflow/.ssh/id_rsa_github_gm && \
        git config user.name "duri-wip" && \
        git config user.email "8s.eow.ooc@gmail.com" && \
        ssh-keyscan -t rsa github.com >> /opt/airflow/.ssh/known_hosts && \
        git add . && \
        git commit -m "Update playlist.json" && \
        GIT_SSH_COMMAND="ssh -o StrictHostKeyChecking=no" git push
        """
        return command

    @task_group(group_id = "split_and_save_postgres")
    def split_and_save_postgres(json_file):
        @task(task_id="save_postgres_playlist")
        def save_postgres(json_file):
            # SQLAlchemy 엔진 및 세션 설정
            engine = create_engine(DATABASE_URL)
            Session = sessionmaker(bind=engine)
            session = Session()

            saved_playlist = []

            for playlist in json_file['playlists']:
                playlist_title = playlist['title']
                video_id = playlist['video_id']

                is_existing_playlist = session.query(Playlist_Model).filter_by(play_id = video_id).first()

                if is_existing_playlist:
                    print(f"Skipped: video_id {video_id} already exists.")
                    continue

                try:
                    new_playlist = Playlist_Model(
                        play_id = video_id,
                        title = playlist_title
                    )
                    session.add(new_playlist)
                    saved_playlist.add(playlist)
                except Exception as e:
                    continue
            session.commit()
            session.close()
            return saved_playlist
        
        @task(task_id = "save_postgres_saved_playlist_music")
        def save_playlist_music(saved_playlist, json_file):
            engine = create_engine(DATABASE_URL)
            Session = sessionmaker(bind=engine)
            session = Session()

            for playlist in json_file['playlists']:
                if playlist['video_id'] in saved_playlist:
                    continue

                for music_info in playlist['items']:
                    feature_music_info = preprocess(item = music_info)
                    music = Music_Model(play_id = playlist['video_id'], music_info = music_info, feature_music_info = feature_music_info)
                    session.add(music)

                session.commit()
            session.close()

        saved_playlists = save_postgres(json_file)
        save_playlist_music(saved_playlist = saved_playlists, json_file = json_file)

    # 태스크 순서 설정
    collect_channel_id_task = collect_channel_ids()

    # 병렬로 각 채널의 비디오를 수집 (expand 사용)
    video_data_list = collect_videos.expand(channel_id=collect_channel_id_task)

    dvc_pull_task = dvc_pull_data()
    existing_data = load_and_process_data()
    combined_data = combine_video_data(video_data_list, existing_data)
    save_data_task = save_combined_data_local(combined_data)
    upload_data_s3_task = upload_data_s3()
    split_and_save_postgres_tasks = split_and_save_postgres(combined_data)

    dvc_pull_task >> existing_data
    collect_channel_id_task >> video_data_list
    [video_data_list, existing_data] >> combined_data >> [save_data_task, split_and_save_postgres_tasks] >> upload_data_s3_task

dag = collect_playlist()
