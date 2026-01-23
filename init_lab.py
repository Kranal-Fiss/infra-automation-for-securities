#!/usr/bin/env python3
import os
import subprocess
import sys
import shutil
import time
from pathlib import Path

# ==========================================
# Script Name: init_lab.py
# Description: 권한 복구, 브릿지 생성, SSH 키 준비, Docker 네트워크 자동화,
#              Grafana 연동, Lab 배포 및 호스트 라우팅 통합 스크립트
# ==========================================

# 1. 로케일 강제 고정 (Ansible 및 시스템 정합성 확보)
os.environ["LANG"] = "en_US.UTF-8"
os.environ["LC_ALL"] = "en_US.UTF-8"

# --- [변수 설정] ---
HOME = str(Path.home())
PROJECT_ROOT = os.path.dirname(os.path.abspath(__file__)) 

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

# venv 및 실행 파일 경로
VENV_BIN = os.path.join(PROJECT_ROOT, "venv/bin")
ANSIBLE_PLAYBOOK = os.path.join(VENV_BIN, "ansible-playbook") if os.path.exists(os.path.join(VENV_BIN, "ansible-playbook")) else "ansible-playbook"
ANSIBLE_BIN = os.path.join(VENV_BIN, "ansible") if os.path.exists(os.path.join(VENV_BIN, "ansible")) else "ansible"

def run_command(cmd, use_sudo=False, check=True, capture_output=False):
    """자식 프로세스에 환경변수를 상속하는 헬퍼 함수"""
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

def ensure_docker_network():
    """Docker 네트워크(clab) 유무 확인 및 서브넷 고정 생성 (멱등성 핵심)"""
    print("Step 5.15: Docker 네트워크(clab) 점검 중...")
    check_net = run_command(["docker", "network", "inspect", "clab"], check=False, capture_output=True)
    
    if check_net.returncode != 0:
        print(" -> 'clab' 네트워크가 없습니다. 서브넷 172.20.20.0/24로 생성합니다.")
        run_command(["docker", "network", "create", "--subnet=172.20.20.0/24", "clab"], use_sudo=True)
    else:
        print(" -> 'clab' 네트워크가 이미 존재합니다.")

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
    """호스트들이 Arista Fabric을 타도록 정적 라우팅 설정"""
    print("Step 6.1: 데이터 평면 활성화를 위한 호스트 라우팅 설정 중...")
    run_command(["docker", "exec", "clab-ceos-triangle-cloud-host", "ip", "route", "add", "192.168.10.0/24", "via", "172.16.1.254"], check=False)
    run_command(["docker", "exec", "clab-ceos-triangle-internal-host", "ip", "route", "add", "172.16.1.0/24", "via", "192.168.10.1"], check=False)
    print(" -> 호스트 라우팅 설정 완료.")

def main():
    print("Step 0: 데이터 및 설정 디렉토리 권한 복구 중...")
    for path in [os.path.join(PROJECT_ROOT, "zbx_env"), os.path.join(PROJECT_ROOT, "docker/ceos-lab/configs"), MONITORING_DIR]:
        if os.path.exists(path):
            run_command(["chmod", "-R", "777", path], use_sudo=True)

    print("Step 1: 브릿지 네트워크 점검 및 IGMP Snooping 설정 중...")
    for br in ["br-cloud", "br-internal"]:
        if subprocess.run(["ip", "link", "show", br], capture_output=True).returncode != 0:
            run_command(["ip", "link", "add", br, "type", "bridge"], use_sudo=True)
        run_command(["ip", "link", "set", "dev", br, "type", "bridge", "mcast_snooping", "1"], use_sudo=True)
        run_command(["ip", "link", "set", "dev", br, "type", "bridge", "mcast_querier", "1"], use_sudo=True)
        run_command(["ip", "link", "set", br, "up"], use_sudo=True)

    if not os.path.exists(KEY_PATH):
        run_command(["ssh-keygen", "-t", "rsa", "-b", "4096", "-f", KEY_PATH, "-N", "", "-q"])

    try:
        run_command(["service", "chrony", "restart"], use_sudo=True)
    except:
        print(" [Warning] Chrony service not found. Skipping...")

    print("Step 5: Ansible을 이용한 Startup Config 생성 중...")
    run_command([ANSIBLE_PLAYBOOK, "-i", INVENTORY_FILE, PLAYBOOK_FILE])

    ensure_docker_network()

    setup_grafana_provisioning()
    print("Step 5.2: 모니터링 스택(Zabbix/Grafana) 실행 중...")
    run_command(["docker", "compose", "-f", DOCKER_COMPOSE_FILE, "up", "-d"], use_sudo=True)

    print("Step 6: Containerlab 배포 시작...")
    run_command(["containerlab", "deploy", "-t", TOPO_FILE, "--reconfigure"], use_sudo=True)

    setup_host_routing()

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