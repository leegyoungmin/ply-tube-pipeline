FROM apache/airflow:2.10.1

# root 권한으로 작업을 진행하기 위해 USER root로 설정
USER root

# sudo를 설치
RUN apt-get update && apt-get install -y sudo

# airflow 사용자에게 sudo 권한 부여
RUN usermod -aG sudo airflow

# 필요한 패키지 설치를 sudo로 실행
RUN sudo apt-get update && sudo apt-get install -y git
RUN git config --global user.email "dlrudals8899@gmail.com"
RUN git config --global user.name "leegyoungmin"

COPY .ssh /opt/airflow/.ssh
RUN eval "$(ssh-agent -s)" && \
ssh-add .ssh/id_rsa_github_gm

# airflow 사용자로 다시 변경
USER airflow

# requirements.txt 설치
ADD requirements.txt .
RUN pip install -r requirements.txt

# AWS 및 환경 파일 복사
COPY .aws /opt/airflow/.aws
COPY .env /opt/airflow/.env
