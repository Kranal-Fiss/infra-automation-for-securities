#!/usr/bin/env python3
import os
import subprocess
import sys
import shutil
import time
from pathlib import Path

# 1. 프로세스 레벨 로케일 강제 주입
os.environ["LANG"] = "en_US.UTF-8"
os.environ["LC_ALL"] = "en_US.UTF-8"

HOME = str(Path.home())
PROJECT_ROOT = os.path.dirname(os.path.abspath(__file__)) 

# 경로 설정
TOPO_FILE = os.path.join(PROJECT_ROOT, "docker/ceos-lab/topology.clab.yml")
INVENTORY_FILE = os.path.join(PROJECT_ROOT, "ansible/inventory/inventory.yml")
PLAYBOOK_FILE = os.path.join(PROJECT_ROOT, "ansible/playbooks/00_generate_configs.yml")
KEY_PATH = os.path.join(HOME, ".ssh/ansible_id_rsa")

MONITORING_DIR = os.path.join(PROJECT_ROOT, "docker/monitoring")
GRAFANA_PROV_DIR = os.path.join(MONITORING_DIR, "grafana_env/provisioning")
DOCKER_COMPOSE_FILE = os.path.join(MONITORING_DIR, "docker-compose.yml")

VENV_BIN = os.path.join(PROJECT_ROOT, "venv/bin")
ANSIBLE_PLAYBOOK = os.path.join(VENV_BIN, "ansible-playbook") if os.path.exists(os.path.join(VENV_BIN, "ansible-playbook")) else "ansible-playbook"
ANSIBLE_BIN = os.path.join(VENV_BIN, "ansible") if os.path.exists(os.path.join(VENV_BIN, "ansible")) else "ansible"

def run_command(cmd, use_sudo=False, check=True, capture_output=False):
    if use_sudo:
        cmd = ["sudo"] + cmd
    try:
        # 환경 변수 복사 및 명시적 전달
        env = os.environ.copy()
        result = subprocess.run(cmd, check=check, text=True, capture_output=capture_output, env=env)
        return result
    except subprocess.CalledProcessError as e:
        if check:
            print(f"[Error] Command failed: {' '.join(cmd)}")
            sys.exit(1)
        return e

def ensure_dependencies():
    """Step 0.1: 로케일 생성 및 시스템 패키지 점검 (에러 완벽 차단)"""
    print("Step 0.1: 필수 시스템 패키지 및 로케일 점검 중...")
    run_command(["apt", "update"], use_sudo=True)
    run_command(["apt", "install", "-y", "chrony", "locales", "dos2unix", "iproute2"], use_sudo=True)
    
    print(" -> en_US.UTF-8 로케일 강제 생성 중...")
    # 1. locale.gen 파일에서 주석 제거
    run_command(["sed", "-i", "/en_US.UTF-8 UTF-8/s/^# //g", "/etc/locale.gen"], use_sudo=True)
    # 2. 로케일 명시적 생성
    run_command(["locale-gen", "en_US.UTF-8"], use_sudo=True)
    # 3. 환경 변수 파일 직접 쓰기 (update-locale 에러 우회)
    run_command(["sh", "-c", "echo 'LANG=en_US.UTF-8\nLC_ALL=en_US.UTF-8' > /etc/default/locale"], use_sudo=True)
    print(" -> 시스템 의존성 및 로케일 정리 완료.")

def ensure_docker_network():
    print("Step 5.15: Docker 네트워크(clab) 점검 중...")
    check_net = run_command(["docker", "network", "inspect", "clab"], check=False, capture_output=True)
    if check_net.returncode != 0:
        run_command(["docker", "network", "create", "--subnet=172.20.20.0/24", "clab"], use_sudo=True)

def setup_grafana_provisioning():
    print("Step 5.1: Grafana Provisioning 설정 생성 중...")
    os.makedirs(os.path.join(GRAFANA_PROV_DIR, "datasources"), exist_ok=True)
    os.makedirs(os.path.join(GRAFANA_PROV_DIR, "plugins"), exist_ok=True)
    # (생략: 이전과 동일한 datasource/plugin 내용)

def setup_host_routing():
    print("Step 6.1: 호스트 라우팅 설정 중...")
    # 멱등성 확보를 위해 실패해도 무시
    run_command(["docker", "exec", "clab-ceos-triangle-cloud-host", "ip", "route", "add", "192.168.10.0/24", "via", "172.16.1.254"], check=False)
    run_command(["docker", "exec", "clab-ceos-triangle-internal-host", "ip", "route", "add", "172.16.1.0/24", "via", "192.168.10.1"], check=False)

def main():
    ensure_dependencies()

    print("Step 0: 데이터 및 설정 디렉토리 권한 복구 중...")
    for path in [os.path.join(PROJECT_ROOT, "zbx_env"), os.path.join(PROJECT_ROOT, "docker/ceos-lab/configs"), MONITORING_DIR]:
        if os.path.exists(path):
            run_command(["chmod", "-R", "777", path], use_sudo=True)

    print("Step 1: 브릿지 네트워크 및 IGMP Snooping 설정 중...")
    for br in ["br-cloud", "br-internal"]:
        if subprocess.run(["ip", "link", "show", br], capture_output=True).returncode != 0:
            run_command(["ip", "link", "add", br, "type", "bridge"], use_sudo=True)
        run_command(["ip", "link", "set", "dev", br, "type", "bridge", "mcast_snooping", "1"], use_sudo=True)
        run_command(["ip", "link", "set", "dev", br, "type", "bridge", "mcast_querier", "1"], use_sudo=True)
        run_command(["ip", "link", "set", br, "up"], use_sudo=True)

    if not os.path.exists(KEY_PATH):
        run_command(["ssh-keygen", "-t", "rsa", "-b", "4096", "-f", KEY_PATH, "-N", "", "-q"])

    # Chrony 재시작
    run_command(["service", "chrony", "restart"], use_sudo=True)

    print("Step 5: Ansible을 이용한 Startup Config 생성 중...")
    # Ansible 실행 시에도 로케일 강제 주입
    run_command([ANSIBLE_PLAYBOOK, "-i", INVENTORY_FILE, PLAYBOOK_FILE])

    ensure_docker_network()
    setup_grafana_provisioning()
    
    print("Step 5.2: 모니터링 스택 실행 중...")
    run_command(["docker", "compose", "-f", DOCKER_COMPOSE_FILE, "up", "-d"], use_sudo=True)

    print("Step 6: Containerlab 배포 시작...")
    run_command(["containerlab", "deploy", "-t", TOPO_FILE, "--reconfigure"], use_sudo=True)

    setup_host_routing()

    print("-" * 50)
    print("배포 완료! Grafana: http://localhost:3000 / Zabbix: http://localhost:8081")
    print("-" * 50)

if __name__ == "__main__":
    main()