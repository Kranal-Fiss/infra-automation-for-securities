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


# ==========================================
# 4. Ansible Inventory 자동 생성 (New!)
# ==========================================
echo "📝 Ansible Inventory 자동 생성 중: $INVENTORY_FILE"

# 디렉토리 생성
if [ ! -d "$INVENTORY_DIR" ]; then
    mkdir -p "$INVENTORY_DIR"
fi

# (1) [arista] 그룹 헤더 작성
echo "[arista]" > "$INVENTORY_FILE"

# (2) clab inspect 결과를 파싱하여 IP 정보 입력
# 설명: 컨테이너 이름과 IPv4 주소를 추출하여 '이름 ansible_host=IP' 형식으로 저장
sudo containerlab inspect -t "$TOPO_FILE" --format json | \
jq -r '.containers[] | "\(.name) ansible_host=\(.ipv4_address)"' >> "$INVENTORY_FILE"

# (3) [arista:vars] 공통 변수 추가
# 주의: ssh_private_key_file은 위에서 설정한 KEY_PATH를 참조합니다.
cat <<EOF >> "$INVENTORY_FILE"

[arista:vars]
# OS 및 연결 설정
ansible_network_os=arista.eos.eos
ansible_connection=network_cli
ansible_user=admin

# 인증 방식: 위에서 생성/확인한 SSH 키 사용
ansible_ssh_private_key_file=$KEY_PATH

# Enable 모드 설정
ansible_become=yes
ansible_become_method=enable

# 랩 환경 특성상 호스트 키 검증 무시 (필수)
ansible_ssh_common_args='-o StrictHostKeyChecking=no'
EOF


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