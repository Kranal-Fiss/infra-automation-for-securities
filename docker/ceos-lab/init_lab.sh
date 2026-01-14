#!/bin/bash

# ==========================================
# 1. SSH 키 준비
# ==========================================
KEY_PATH="$HOME/.ssh/ansible_id_rsa"

if [ ! -f "$KEY_PATH" ]; then
    echo "🔑 SSH 키가 없어서 새로 만듭니다..."
    ssh-keygen -t rsa -b 4096 -f "$KEY_PATH" -N "" -q 
    echo "✅ 키 생성 완료!"
else
    echo "♻️  기존 SSH 키를 사용합니다."
fi

# ==========================================
# 2. Chrony 설치 및 설정 (Host를 NTP 서버로)
# ==========================================
echo "🕰️  Host에 Chrony(NTP)를 설치하고 설정합니다..."

# Chrony 설치 (Debian/Ubuntu 계열)
if ! command -v chronyd &> /dev/null; then
    sudo apt-get update && sudo apt-get install -y chrony
    echo "✅ Chrony 설치 완료"
else
    echo "♻️  Chrony가 이미 설치되어 있습니다."
fi

# Chrony 설정 (랩 환경용: 모든 대역 allow all)
# 주의: /etc/chrony/chrony.conf 경로가 다를 경우(RHEL계열 등) 확인 필요
sudo bash -c 'cat <<EOF > /etc/chrony/chrony.conf
pool ntp.ubuntu.com        iburst maxsources 4
pool 0.ubuntu.pool.ntp.org iburst maxsources 1
pool 1.ubuntu.pool.ntp.org iburst maxsources 1
pool 2.ubuntu.pool.ntp.org iburst maxsources 2

# 모든 네트워크 대역에서의 NTP 요청 허용 (Lab 환경용)
allow all

# 인터넷이 끊겨도 로컬 시간을 신뢰하여 서버 역할 수행
local stratum 10

keyfile /etc/chrony/chrony.keys
driftfile /var/lib/chrony/chrony.drift
logdir /var/log/chrony
maxupdateskew 100.0
rtcsync
makestep 1 3
EOF'

sudo service chrony restart
echo "✅ Chrony(NTP Server) 설정 완료!"

# ==========================================
# 3. Containerlab 배포
# ==========================================
echo "🚀 랩 환경을 배포합니다..."
if [ -f "topology.ceos.yml" ]; then
    sudo containerlab deploy -t topology.ceos.yml
else
    echo "⚠️  topology.ceos.yml 파일이 없습니다. 배포 단계를 건너뜁니다."
fi

# ==========================================
# 4. Ansible 필수 파일 생성 (실행 준비)
# ==========================================
echo "📂 Ansible 프로젝트 구조 및 설정 파일을 생성합니다..."
mkdir -p inventory playbooks group_vars host_vars

# ansible.cfg 생성
cat <<EOF > ansible.cfg
[defaults]
inventory = ./inventory/hosts.ini
host_key_checking = False
deprecation_warnings = False
command_warnings = False
interpreter_python = auto_silent
stdout_callback = yaml
EOF

# inventory/hosts.ini 생성 (패스워드 admin123)
# Containerlab 배포 후 생성된 컨테이너 이름이나 IP를 확인하여 수정하기 쉽도록 템플릿 제공
if [ ! -f inventory/hosts.ini ]; then
    cat <<EOF > inventory/hosts.ini
[routers]
# 예시: clab-lab-ceos1 ansible_host=172.20.20.2
# 예시: clab-lab-ceos2 ansible_host=172.20.20.3

[all:vars]
ansible_user=admin
ansible_password=admin123
ansible_connection=network_cli
ansible_network_os=arista.eos.eos
ansible_port=22
EOF
    echo "✅ hosts.ini 생성 완료 (패스워드: admin123)"
fi

echo "---------------------------------------------------"
echo "🎉 랩 환경 초기화가 완료되었습니다."
echo ""
echo "👉 다음 단계:"
echo "1. 'inventory/hosts.ini' 파일을 열어 장비 IP를 맞춰주세요."
echo "2. 준비가 되면 아래 명령어로 NTP 설정을 적용하세요:"
echo "   ansible-playbook playbooks/ntp.yml"
echo "---------------------------------------------------"