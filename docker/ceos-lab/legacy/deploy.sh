#!/bin/bash

echo "🚀 Starting cEOS Lab Containers..."
docker-compose up -d

# 컨테이너가 생성될 때까지 잠시 대기
sleep 3

for i in 1 2 3
do
    echo "🛠️ Patching ceos$i..."
    # 커널 모듈 체크 속이기
    docker exec ceos$i ln -sf /bin/true /sbin/modprobe
    
    # 멈춘 서비스 재시작하여 부팅 진행
    docker exec ceos$i systemctl restart EosStage2
    echo "✅ ceos$i Patch Applied."
done

echo "✨ All patches applied! Wait about 1-2 minutes for full boot."
echo "Check status with: docker exec -it ceos1 Cli"