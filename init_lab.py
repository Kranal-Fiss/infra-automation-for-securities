#!/usr/bin/env python3
import os
import subprocess
import sys
import shutil
import time
from pathlib import Path

# ==========================================
# Script Name: init_lab.py
# Description: 권한 복구, 브릿지 생성, SSH 키 준비, NTP 설정, 
#              Grafana 자동연동 설정, 모니터링 스택 및 Lab 배포, 호스트 라우팅 자동화
# ==========================================

# --- [변수 설정] ---
HOME = str(Path.home())
PROJECT_ROOT = os.path.join(HOME, "infra-automation-for-securities")

# 경로 설정
TOPO_FILE = os.path.join(PROJECT_ROOT, "docker/ceos-lab/topology.clab.yml")
INVENTORY_DIR = os.path.join(PROJECT_ROOT, "ansible/inventory")
INVENTORY_FILE = os.path.join(INVENTORY_DIR, "inventory.yml")
PLAYBOOK_FILE = os.path.join(PROJECT_ROOT, "ansible/playbooks/00_generate_configs.yml")
KEY_PATH = os.path.join(HOME, ".ssh/ansible_id_rsa")

# 모니터링 관련 경로 추가
MONITORING_DIR = os.path.join(PROJECT_ROOT, "docker/monitoring")
GRAFANA_PROV_DIR = os.path.join(MONITORING_DIR, "grafana_env/provisioning")
DOCKER_COMPOSE_FILE = os.path.join(MONITORING_DIR, "docker-compose.yml")

# 로케일 설정
os.environ["LANG"] = "en_US.UTF-8"
os.environ["LC_ALL"] = "en_US.UTF-8"

# venv 및 실행 파일 경로
VENV_BIN = os.path.join(PROJECT_ROOT, "venv/bin")
ANSIBLE_PLAYBOOK = os.path.join(VENV_BIN, "ansible-playbook") if os.path.exists(os.path.join(VENV_BIN, "ansible-playbook")) else "ansible-playbook"
ANSIBLE_BIN = os.path.join(VENV_BIN, "ansible") if os.path.exists(os.path.join(VENV_BIN, "ansible")) else "ansible"

def run_command(cmd, use_sudo=False, check=True, capture_output=False):
    """쉘 명령어를 실행하는 헬퍼 함수"""
    if use_sudo:
        cmd = ["sudo"] + cmd
    try:
        result = subprocess.run(
            cmd, 
            check=check, 
            text=True, 
            capture_output=capture_output,
            env=os.environ.copy()
        )
        return result
    except subprocess.CalledProcessError as e:
        if check:
            print(f"[Error] Command failed: {' '.join(cmd)}")
            if e.stderr:
                print(f"[Details] {e.stderr}")
            sys.exit(1)
        return e

def setup_grafana_provisioning():
    """Grafana Zabbix 자동 연동 YAML 생성"""
    print("Step 5.1: Grafana Provisioning 설정 생성 중...")
    
    os.makedirs(os.path.join(GRAFANA_PROV_DIR, "datasources"), exist_ok=True)
    os.makedirs(os.path.join(GRAFANA_PROV_DIR, "plugins"), exist_ok=True)

    ds_content = """apiVersion: 1
datasources:
  - name: Zabbix
    type: alexanderzobnin-zabbix-datasource
    access: proxy
    url: http://zabbix-web:8080/api_jsonrpc.php
    editable: true
    jsonData:
      username: Admin
      password: zabbix
"""
    with open(os.path.join(GRAFANA_PROV_DIR, "datasources/zabbix.yaml"), "w") as f:
        f.write(ds_content)

    pl_content = """apiVersion: 1
apps:
  - type: alexanderzobnin-zabbix-app
    disabled: false
"""
    with open(os.path.join(GRAFANA_PROV_DIR, "plugins/zabbix.yaml"), "w") as f:
        f.write(pl_content)
    print(" -> Grafana 자동 연동 설정 파일 생성 완료.")

def setup_host_routing():
    """호스트들이 Arista Fabric(Data Plane)을 타도록 정적 라우팅 설정"""
    print("Step 6.1: 데이터 평면 활성화를 위한 호스트 라우팅 설정 중...")
    
    # 1. cloud-host -> internal-host (via VARP VIP)
    cmd_cloud = ["docker", "exec", "clab-ceos-triangle-cloud-host", "ip", "route", "add", "192.168.10.0/24", "via", "172.16.1.254"]
    run_command(cmd_cloud, check=False) # 이미 존재할 수 있으므로 check=False
    
    # 2. internal-host -> cloud-host (via ceos3)
    cmd_internal = ["docker", "exec", "clab-ceos-triangle-internal-host", "ip", "route", "add", "172.16.1.0/24", "via", "192.168.10.1"]
    run_command(cmd_internal, check=False)
    
    print(" -> 호스트 라우팅 설정 완료.")

def main():
    # 0. 권한 복구
    print("Step 0: 데이터 및 설정 디렉토리 권한 복구 중...")
    run_command(["ls", "-v"], use_sudo=True, check=False) # sudo 세션 확인용
    
    for path in [os.path.join(PROJECT_ROOT, "zbx_env"), os.path.join(PROJECT_ROOT, "docker/ceos-lab/configs"), MONITORING_DIR]:
        if os.path.exists(path):
            run_command(["chmod", "-R", "777", path], use_sudo=True)

    pg_pid_file = os.path.join(PROJECT_ROOT, "zbx_env/var/lib/postgresql/data/postmaster.pid")
    if os.path.exists(pg_pid_file):
        run_command(["rm", "-f", pg_pid_file], use_sudo=True)
    print(" -> 권한 정리 완료.")

    # 1. 브릿지 네트워크 준비
    print("Step 1: 브릿지 네트워크 점검 중...")
    for br in ["br-cloud", "br-internal"]:
        if subprocess.run(["ip", "link", "show", br], capture_output=True).returncode != 0:
            run_command(["ip", "link", "add", br, "type", "bridge"], use_sudo=True)
            run_command(["ip", "link", "set", br, "up"], use_sudo=True)

    # 2. SSH 키 준비
    if not os.path.exists(KEY_PATH):
        run_command(["ssh-keygen", "-t", "rsa", "-b", "4096", "-f", KEY_PATH, "-N", "", "-q"])

    # 3. NTP 설정
    run_command(["service", "chrony", "restart"], use_sudo=True)

    # 4. 가상환경 경로 설정
    if os.path.exists(VENV_BIN):
        os.environ["PATH"] = VENV_BIN + os.pathsep + os.environ["PATH"]

    # 5. Startup Config 생성
    print("Step 5: Ansible을 이용한 Startup Config 생성 중...")
    run_command([ANSIBLE_PLAYBOOK, "-i", INVENTORY_FILE, PLAYBOOK_FILE])

    # 5-1. 모니터링 스택 자동화
    setup_grafana_provisioning()
    print("Step 5.2: 모니터링 스택(Zabbix/Grafana) 실행 중...")
    run_command(["docker", "compose", "-f", DOCKER_COMPOSE_FILE, "up", "-d"], use_sudo=True)

    # 6. Lab 배포
    print("Step 6: Containerlab 배포 시작...")
    run_command(["containerlab", "deploy", "-t", TOPO_FILE, "--reconfigure"], use_sudo=True)

    # 6.1 호스트 라우팅 추가 (신규 단계)
    setup_host_routing()

    # 7. 완료 확인
    print("-" * 50)
    print("모든 시스템 배포가 완료되었습니다.")
    print("장비 안정화 대기 중 (15초)...")
    time.sleep(15)
    run_command([ANSIBLE_BIN, "arista", "-i", INVENTORY_FILE, "-m", "ping"], check=False)
    
    print(f" - Grafana 접속: http://localhost:3000 (Zabbix 자동연동 완료)")
    print(f" - Zabbix 접속: http://localhost:8081")
    print("-" * 50)

if __name__ == "__main__":
    main()