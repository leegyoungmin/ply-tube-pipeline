from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from dotenv import load_dotenv
from src.database import database, engine
from src.routes import router
from src.tables import metadata

app = FastAPI()

# 허용할 출처 목록
origins = [
    "http://localhost",
    "http://localhost:3000",  # React 개발 환경에서 자주 사용하는 포트
    "http://3.38.28.112:3000",  # 실제 배포 환경 도메인
]

# CORS 설정
app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,  # 허용할 출처
    allow_credentials=True,  # 쿠키 등의 자격 증명 허용 여부
    allow_methods=["*"],  # 허용할 HTTP 메서드
    allow_headers=["*"],  # 허용할 HTTP 헤더
)

app.include_router(router)
@app.get("/")
async def root():
    return {"message": "Hello FastAPI"}

# 애플리케이션이 시작될 때 데이터베이스 연결
@app.on_event("startup")
async def startup():
    await database.connect()
    metadata.create_all(engine)

# 애플리케이션이 종료될 때 데이터베이스 연결 해제
@app.on_event("shutdown")
async def shutdown():
    await database.disconnect()

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)