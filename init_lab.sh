#!/bin/bash

# ==========================================
# Script Name: init_lab.sh
# Description: SSH 키 준비, NTP 설정, Lab 배포 및 Ansible Inventory 자동 생성
# ==========================================

# --- [변수 설정] ---
# 토폴로지 파일 경로 (기존 경로 유지)
TOPO_FILE="docker/ceos-lab/topology.clab.yml"

# Ansible 인벤토리 경로 (논의한 경로 반영)
INVENTORY_DIR="ansible/inventory"
INVENTORY_FILE="${INVENTORY_DIR}/inventory.ini"

# SSH 키 경로 (기존 경로 유지)
KEY_PATH="$HOME/.ssh/ansible_id_rsa"


# ==========================================
# 1. SSH 키 준비
# ==========================================
echo "🔑 SSH 키 점검 중..."
if [ ! -f "$KEY_PATH" ]; then
    echo "   -> SSH 키가 없어 새로 생성합니다: $KEY_PATH"
    ssh-keygen -t rsa -b 4096 -f "$KEY_PATH" -N "" -q 
else
    echo "   -> 기존 SSH 키를 사용합니다."
fi


# ==========================================
# 2. Chrony (NTP) 설정
# ==========================================
echo "🕰️  NTP 서버(Chrony) 점검 중..."
if ! command -v chronyd &> /dev/null; then
    echo "   -> Chrony 설치 중..."
    sudo apt-get update && sudo apt-get install -y chrony
fi
# 서비스 재시작
sudo service chrony restart


# ==========================================
# 3. Lab 배포
# ==========================================
echo "🚀 Containerlab 배포 시작..."

if [ ! -f "$TOPO_FILE" ]; then
    echo "❌ 오류: 토폴로지 파일을 찾을 수 없습니다: $TOPO_FILE"
    exit 1
fi

# jq 설치 확인 (인벤토리 생성에 필수)
if ! command -v jq &> /dev/null; then
    echo "⚠️  'jq'가 설치되어 있지 않습니다. 설치를 진행합니다..."
    sudo apt-get update && sudo apt-get install -y jq
fi

# 배포 실행
sudo containerlab deploy -t "$TOPO_FILE" --reconfigure

if [ $? -ne 0 ]; then
    echo "❌ Containerlab 배포 실패."
    exit 1
fi


# =================================================================
# [Next Securities] 인프라 자동화 환경 최적화 설정
# =================================================================

# 1. 로케일 에러 방지 (Ansible 실행 필수 설정)
export LANG=C.UTF-8
export LC_ALL=C.UTF-8

# 2. 프로젝트 가상환경(venv) 자동 활성화
PROJECT_ROOT="$HOME/infra-automation-for-securities"
VENV_PATH="$PROJECT_ROOT/venv/bin/activate"

if [ -f "$VENV_PATH" ]; then
    source "$VENV_PATH"
    echo "✅ Python 가상환경 활성화 완료"
else
    echo "⚠️  경고: 가상환경($VENV_PATH)을 찾을 수 없습니다."
fi

# 3. Ansible 실행 환경 점검
echo "🔍 Ansible 인벤토리 및 장비 연결 확인..."
# -i 옵션 없이도 실행되도록 ansible.cfg와 연동 확인
ansible-inventory --graph --vars

# 4. (선택) Arista 컨테이너가 뜰 때까지 대기 후 핑 테스트
# clab 배포 직후 바로 실행하면 실패할 수 있으므로 잠시 대기 기능을 넣을 수 있습니다.
# ansible arista -m ping


# ==========================================
# 5. 완료 메시지
# ==========================================
echo "---------------------------------------------------"
echo "🎉 모든 준비가 완료되었습니다."
echo ""
echo "📂 생성된 인벤토리:"
cat "$INVENTORY_FILE"
echo ""
echo "---------------------------------------------------"
echo "👉 다음 명령어로 통신 테스트를 해보세요:"
echo "   ansible arista -i $INVENTORY_FILE -m ping"
echo "---------------------------------------------------"