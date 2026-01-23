#!/usr/bin/env python3
import os
import subprocess
import sys
import shutil
import time
from pathlib import Path

# ==========================================
# Script Name: init_lab.py (Idempotent Version)
# Description: 환경 독립적 실행 및 멱등성 확보를 위한 자동화 스크립트
# ==========================================

# 1. 로케일 강제 고정 (Ansible 및 시스템 정합성 확보)
os.environ["LANG"] = "en_US.UTF-8"
os.environ["LC_ALL"] = "en_US.UTF-8"

# --- [변수 설정] ---
HOME = str(Path.home())
PROJECT_ROOT = os.path.dirname(os.path.abspath(__file__)) # 현재 실행 경로 기준

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
    """자식 프로세스에 환경변수(env)를 명시적으로 상속하는 헬퍼 함수"""
    if use_sudo:
        cmd = ["sudo"] + cmd
    try:
        # env=os.environ.copy()를 통해 부모의 로케일 설정을 자식에게 전파
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
    """Step 5.15: clab 네트워크 존재 여부 및 서브넷 확인 후 자동 생성 (멱등성 핵심)"""
    print("Step 5.15: Docker 네트워크(clab) 점검 중...")
    check_net = run_command(["docker", "network", "inspect", "clab"], check=False, capture_output=True)
    
    if check_net.returncode != 0:
        print(" -> 'clab' 네트워크가 없습니다. 서브넷 172.20.20