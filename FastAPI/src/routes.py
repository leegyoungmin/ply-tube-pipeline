import random
from sqlalchemy.sql import text
from .database import database
from .tables import music
import requests
from typing import List
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from src.Preprocessing import preprocess

router = APIRouter()

split_query_result = []  # 쪼갠 결과 저장 리스트
original_result = []  # 원래 데이터를 저장하는 리스트

class RecommandKeyword(BaseModel):
    keywords: List[str]

# 사용자가 선택한 값을 받을 데이터 모델
class Selection(BaseModel):
    select_value: List[str]  # 선택된 값은 리스트로 받음

class Prediction(BaseModel):
    keywords: List[str]
    predictions: List[str]

@router.get("/random-items/")
async def get_random_items():
    global split_query_result, original_result

    # 데이터베이스에서 랜덤으로 음악 데이터를 가져옴
    query = music.select().with_only_columns(music.c.music_info).order_by(text("RANDOM()")).limit(15)
    result = await database.fetch_all(query)
    
    original_result = [row['music_info'] for row in result]  # 원래 값을 저장
    split_query_result = []
    for row in result:
        music_info = row["music_info"]
        split_music_info = music_info.split(' - ')
        
        if len(split_music_info) < 2:
            continue

        split_query_result.extend(split_music_info)  # '-'로 쪼개서 확장
    
    random.shuffle(split_query_result)  # 리스트를 랜덤으로 섞음
    remove_duplicate_result = list(set(split_query_result))
    return RecommandKeyword(keywords=remove_duplicate_result)

@router.post("/submit-selection/")
async def submit_selection(selection: Selection):
    global split_query_result, original_result
    
    predictions = []  # 모든 추론 결과를 저장할 리스트
    
    # 선택된 각 값에 대해 추론 서버에 요청
    for selected_value in selection.select_value:
        original_value = None
        
        # 선택된 값이 원래 어느 문자열에서 왔는지 찾기
        for item in original_result:
            if selected_value in item:
                original_value = item  # 원래 문자열을 찾음
                break
        
        # 만약 값을 찾지 못하면 에러 반환
        if original_value is None:
            raise HTTPException(status_code=404, detail=f"Original value not found for {selected_value}")
        
        # 찾은 원래 값으로 추론 서버에 POST 요청
        response = requests.post("http://15.164.99.159:5001/predict", 
                                 json={"input_song": preprocess(original_value)},
                                 headers={"Content-Type": "application/json"}
                                 )
        print(response.json())
        if response.status_code == 200:
            # 추론 결과를 리스트에 추가
            prediction_data = response.json()
            if "predicted_songs" in prediction_data:
                predicted_songs = prediction_data["predicted_songs"]

                # 각 예측된 노래에 대해 music_id 조회
                for song in predicted_songs:
                    query = music.select().with_only_columns(music.c.feature_music_info, music.c.music_info) \
                        .where(music.c.feature_music_info == song)
                    result = await database.fetch_one(query)

                    if result:
                        predictions.append(result["music_info"])
                    else:
                        continue
        else:
            raise HTTPException(status_code=response.status_code, detail="Inference server error")
    remove_duplicated_music_list = list(set(predictions))
    return Prediction(keywords=selection.select_value, predictions=remove_duplicated_music_list)