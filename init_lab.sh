#!/bin/bash

# 1. SSH 키 경로 정의
KEY_PATH="$HOME/.ssh/ansible_id_rsa"

# 2. 키가 있는지 확인
if [ ! -f "$KEY_PATH" ]; then
    echo "🔑 SSH 키가 없어서 새로 만듭니다..."
    # -N "": 비밀번호 없음, -q: 조용히
    ssh-keygen -t rsa -b 4096 -f "$KEY_PATH" -N "" -q 
    echo "✅ 키 생성 완료!"
else
    echo "♻️  기존 SSH 키를 사용합니다."
fi

# 3. Containerlab 배포 (키가 준비된 상태에서 실행)
echo "🚀 랩 환경을 배포합니다..."
sudo containerlab deploy -t topology.ceos.yml