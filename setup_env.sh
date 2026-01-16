#!/bin/bash

# Script Name: setup_env.sh
# Description: Next증권 타이니 프로젝트 통합 환경 구축 스크립트

# 색상 정의
GREEN='\033[0;32m'
CYAN='\033[0;36m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
NC='\033[0m'

echo -e "${CYAN}====================================================${NC}"
echo -e "${CYAN}   Next증권 타이니 프로젝트: 통합 환경 구축 스크립트   ${NC}"
echo -e "${CYAN}====================================================${NC}"

# 1. 시스템 패키지 업데이트 및 필수 도구 설치
echo -e "${GREEN}[1/6] 시스템 패키지 및 종속성 설치 중...${NC}"
sudo apt-get update
sudo apt-get install -y curl gnupg2 software-properties-common python3-venv python3-pip git chrony iproute2 snmp
# --- [기존 시스템 패키지 설치 섹션에 추가] ---

echo -e "${GREEN}[1/6] 시스템 패키지 및 종속성 설치 중...${NC}"
sudo apt-get update
sudo apt-get install -y curl gnupg2 software-properties-common python3-venv python3-pip git chrony iproute2 snmp locales

echo -e "${GREEN}[1/6] 언어 팩(Locales) 구성 및 영구 설정 중...${NC}"
# 시스템에 영문 UTF-8 로케일 생성 및 기존 불필요 항목 제거
sudo locale-gen --purge en_US.UTF-8

# 시스템 전체 기본 언어 설정을 en_US.UTF-8로 고정
sudo update-locale LANG=en_US.UTF-8 LC_ALL=en_US.UTF-8

# 현재 실행 중인 스크립트 세션에 즉시 적용
export LANG=en_US.UTF-8
export LC_ALL=en_US.UTF-8

# .bashrc에 로케일 설정을 추가하여 향후 모든 로그인 세션에 적용 (중복 추가 방지)
if ! grep -q "en_US.UTF-8" ~/.bashrc; then
    echo -e "\n# 로케일 설정 자동 추가 (Next증권 프로젝트)" >> ~/.bashrc
    echo 'export LANG=en_US.UTF-8' >> ~/.bashrc
    echo 'export LC_ALL=en_US.UTF-8' >> ~/.bashrc
    echo " -> .bashrc에 환경 변수 주입 완료."
fi

# 2. Docker 및 Docker Compose 설치
echo -e "${GREEN}[2/6] Docker 엔진 및 Compose 플러그인 확인...${NC}"
if ! command -v docker &> /dev/null; then
    echo " -> Docker 설치를 시작합니다..."
    curl -fsSL https://get.docker.com -o get-docker.sh
    sudo sh get-docker.sh
    sudo usermod -aG docker $USER
    sudo apt-get install -y docker-compose-plugin
else
    echo -e " -> Docker가 이미 존재합니다. Compose 플러그인 최신화 중..."
    sudo apt-get install -y docker-compose-plugin
fi

# 3. Containerlab 설치
echo -e "${GREEN}[3/6] Containerlab 설치 확인...${NC}"
if ! command -v containerlab &> /dev/null; then
    echo " -> Containerlab 저장소 등록 및 설치 중..."
    echo "deb [trusted=yes] https://apt.fury.io/netdevops/ /" | sudo tee /etc/apt/sources.list.d/netdevops.list
    sudo apt-get update && sudo apt-get install -y containerlab
else
    echo -e " -> Containerlab이 이미 설치되어 있습니다."
fi

# 4. Python 가상환경 및 라이브러리 설치
echo -e "${GREEN}[4/6] Python 가상환경(venv) 구축 및 라이브러리 설치...${NC}"
if [ ! -d "./venv" ]; then
    python3 -m venv venv
    echo " -> venv 생성 완료."
fi

source venv/bin/activate
pip install --upgrade pip
if [ -f "./requirements.txt" ]; then
    pip install -r requirements.txt
    echo -e " -> requirements.txt 설치 완료."
else
    echo -e "${RED}[!] requirements.txt 파일이 없어 기본 패키지만 설치합니다.${NC}"
    pip install ansible paramiko scp pyzabbix
fi

# Ansible Arista 컬렉션 설치
echo -e "${GREEN}Ansible Arista EOS 컬렉션 설치 중...${NC}"
ansible-galaxy collection install arista.eos

# 5. Zabbix & Grafana 환경 준비
echo -e "${GREEN}[5/6] 모니터링 데이터 디렉토리 설정 중...${NC}"
PROJECT_ROOT=$(pwd)
mkdir -p "$PROJECT_ROOT/zbx_env/var/lib/postgresql/data"
mkdir -p "$PROJECT_ROOT/zbx_env/usr/lib/zabbix/externalscripts"
mkdir -p "$PROJECT_ROOT/zbx_env/var/lib/grafana"

# 권한 문제 사전 해결
sudo chmod -R 777 "$PROJECT_ROOT/zbx_env"
echo -e " -> Zabbix/Grafana 볼륨 디렉토리 권한 설정 완료 (777)."

# 6. 인프라 상태 최종 확인
echo -e "${GREEN}[6/6] 필수 구성 요소 확인...${NC}"
CEOS_IMAGE=$(docker images -q ceosimage:latest 2> /dev/null)
if [ -z "$CEOS_IMAGE" ]; then
    echo -e "${YELLOW}[!] 주의: 'ceosimage:latest'를 찾을 수 없습니다.${NC}"
    echo "     장비 배포 전 Arista 이미지를 수동으로 로드해 주세요."
else
    echo -e " -> cEOS 이미지 확인됨."
fi

echo -e "\n${CYAN}====================================================${NC}"
echo -e "${GREEN}환경 설정이 성공적으로 완료되었습니다.${NC}"
echo -e "${YELLOW}※ Docker 권한 적용을 위해 로그아웃 후 다시 로그인해 주세요.${NC}"
echo -e "1. docker compose up -d (모니터링 시작)"
echo -e "2. ./init_lab.py (네트워크 배포)"
echo -e "${CYAN}====================================================${NC}"