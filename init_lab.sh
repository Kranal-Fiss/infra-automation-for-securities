#!/bin/bash

# ==========================================
# Script Name: init_lab.sh
# Description: SSH 키 준비, NTP 설정, Ansible Config 생성 및 Lab 배포
# ==========================================

# --- [변수 설정] ---
# 프로젝트 루트 (가상환경 및 경로 기준점)
PROJECT_ROOT="$HOME/infra-automation-for-securities"

# 토폴로지 파일 경로
TOPO_FILE="${PROJECT_ROOT}/docker/ceos-lab/topology.clab.yml"

# Ansible 관련 경로 (YAML 형식 반영)
INVENTORY_DIR="${PROJECT_ROOT}/ansible/inventory"
INVENTORY_FILE="${INVENTORY_DIR}/inventory.yml"
PLAYBOOK_FILE="${PROJECT_ROOT}/ansible/playbooks/generate_configs.yml"

# SSH 키 경로
KEY_PATH="$HOME/.ssh/ansible_id_rsa"


# ==========================================
# 1. SSH 키 준비
# ==========================================
echo "🔑 Step 1: SSH 키 점검 중..."
if [ ! -f "$KEY_PATH" ]; then
    echo "   -> SSH 키가 없어 새로 생성합니다: $KEY_PATH"
    ssh-keygen -t rsa -b 4096 -f "$KEY_PATH" -N "" -q 
else
    echo "   -> 기존 SSH 키를 사용합니다."
fi


# ==========================================
# 2. Chrony (NTP) 설정
# ==========================================
echo "🕰️  Step 2: NTP 서버(Chrony) 점검 중..."
if ! command -v chronyd &> /dev/null; then
    echo "   -> Chrony 설치 중..."
    sudo apt-get update && sudo apt-get install -y chrony
fi
sudo service chrony restart


# ==========================================
# 3. 가상환경 및 로케일 설정
# ==========================================
echo "⚙️  Step 3: 실행 환경 설정 중..."
export LANG=C.UTF-8
export LC_ALL=C.UTF-8

VENV_PATH="$PROJECT_ROOT/venv/bin/activate"
if [ -f "$VENV_PATH" ]; then
    source "$VENV_PATH"
    echo "   -> Python 가상환경 활성화 완료"
else
    echo "⚠️  경고: 가상환경을 찾을 수 없습니다. 시스템 파이썬을 사용합니다."
fi


# ==========================================
# 4. Startup Config (.cfg) 생성 (Ansible)
# ==========================================
echo "📝 Step 4: Ansible을 이용한 Startup Config 생성 중..."
if [ ! -f "$PLAYBOOK_FILE" ]; then
    echo "❌ 오류: 플레이북 파일을 찾을 수 없습니다: $PLAYBOOK_FILE"
    exit 1
fi

# 인벤토리에 지정된 템플릿을 사용하여 configs/ 폴더에 .cfg 생성
ansible-playbook -i "$INVENTORY_FILE" "$PLAYBOOK_FILE"

if [ $? -ne 0 ]; then
    echo "❌ 오류: Startup Config 생성 실패."
    exit 1
fi
echo "   -> Config 생성 완료 (docker/ceos-lab/configs/)"


# ==========================================
# 5. Lab 배포 (Containerlab)
# ==========================================
echo "🚀 Step 5: Containerlab 배포 시작..."

if [ ! -f "$TOPO_FILE" ]; then
    echo "❌ 오류: 토폴로지 파일을 찾을 수 없습니다: $TOPO_FILE"
    exit 1
fi

# 배포 실행 (생성된 .cfg 파일들을 물고 올라감)
sudo containerlab deploy -t "$TOPO_FILE" --reconfigure

if [ $? -ne 0 ]; then
    echo "❌ Containerlab 배포 실패."
    exit 1
fi


# ==========================================
# 6. 완료 및 연결 확인
# ==========================================
echo "---------------------------------------------------"
echo "🎉 모든 준비가 완료되었습니다."
echo ""
echo "🔍 장비 연결(Ping) 테스트 중..."
# 장비가 완전히 부팅될 때까지 잠시 대기 (cEOS 부팅 시간 고려)
sleep 5
ansible arista -i "$INVENTORY_FILE" -m ping

echo "---------------------------------------------------"
echo "👉 프로젝트 정보:"
echo "   - 인벤토리: $INVENTORY_FILE"
echo "   - 토폴로지: $TOPO_FILE"
echo "---------------------------------------------------"