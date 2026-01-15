#!/usr/bin/env python3
import os
import subprocess
import sys
import shutil
from pathlib import Path

# ==========================================
# Script Name: init_lab.py
# Description: 권한 복구, 브릿지 생성, SSH 키 준비, NTP 설정, Config 생성 및 Lab 배포
# ==========================================

# --- [변수 설정] ---
HOME = str(Path.home())
PROJECT_ROOT = os.path.join(HOME, "infra-automation-for-securities")

TOPO_FILE = os.path.join(PROJECT_ROOT, "docker/ceos-lab/topology.clab.yml")
INVENTORY_DIR = os.path.join(PROJECT_ROOT, "ansible/inventory")
INVENTORY_FILE = os.path.join(INVENTORY_DIR, "inventory.yml")
PLAYBOOK_FILE = os.path.join(PROJECT_ROOT, "ansible/playbooks/generate_configs.yml")
KEY_PATH = os.path.join(HOME, ".ssh/ansible_id_rsa")

# venv 내의 실행 파일 경로 설정
VENV_BIN = os.path.join(PROJECT_ROOT, "venv/bin")
# 가상환경의 ansible이 있으면 사용하고, 없으면 시스템 명령어를 사용함
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
        print(f"[Error] Command failed: {' '.join(cmd)}")
        if e.stderr:
            print(f"[Details] {e.stderr}")
        if check:
            sys.exit(1)
        return e

def main():
    # ==========================================
    # 0. sudo 권한 선점 및 데이터 디렉토리 권한 복구
    # ==========================================
    print("Step 0: 데이터 및 설정 디렉토리 권한 복구 중...")
    run_command(["-v"], use_sudo=True)

    zbx_env_path = os.path.join(PROJECT_ROOT, "zbx_env")
    if os.path.exists(zbx_env_path):
        run_command(["chmod", "-R", "777", zbx_env_path], use_sudo=True)

    pg_pid_file = os.path.join(zbx_env_path, "var/lib/postgresql/data/postmaster.pid")
    if os.path.exists(pg_pid_file):
        print(f" -> 구형 PostgreSQL 락 파일 제거 중: {pg_pid_file}")
        run_command(["rm", "-f", pg_pid_file], use_sudo=True)

    configs_path = os.path.join(PROJECT_ROOT, "docker/ceos-lab/configs")
    if os.path.exists(configs_path):
        run_command(["chmod", "-R", "777", configs_path], use_sudo=True)
    
    print(" -> 권한 정리 완료.")

    # ==========================================
    # 1. 브릿지 네트워크(Data Plane) 준비
    # ==========================================
    print("Step 1: 브릿지 네트워크 점검 중...")
    bridges = ["br-cloud", "br-internal"]
    for br in bridges:
        check_br = subprocess.run(["ip", "link", "show", br], capture_output=True)
        if check_br.returncode != 0:
            print(f" -> {br} 생성 중...")
            run_command(["ip", "link", "add", br, "type", "bridge"], use_sudo=True)
            run_command(["ip", "link", "set", br, "up"], use_sudo=True)
        else:
            print(f" -> {br}가 이미 존재합니다.")

    # ==========================================
    # 2. SSH 키 준비
    # ==========================================
    print("Step 2: SSH 키 점검 중...")
    if not os.path.exists(KEY_PATH):
        run_command(["ssh-keygen", "-t", "rsa", "-b", "4096", "-f", KEY_PATH, "-N", "", "-q"])
    else:
        print(" -> 기존 SSH 키를 사용합니다.")

    # ==========================================
    # 3. Chrony (NTP) 설정
    # ==========================================
    print("Step 3: NTP 서버(Chrony) 점검 중...")
    if not shutil.which("chronyd"):
        run_command(["apt-get", "update"], use_sudo=True)
        run_command(["apt-get", "install", "-y", "chrony"], use_sudo=True)
    run_command(["service", "chrony", "restart"], use_sudo=True)

    # ==========================================
    # 4. 실행 환경 설정 (Locale & venv 체크)
    # ==========================================
    print("Step 4: 실행 환경 설정 중...")
    os.environ["LANG"] = "C.UTF-8"
    os.environ["LC_ALL"] = "C.UTF-8"
    
    if os.path.exists(VENV_BIN):
        print(f" -> 가상환경 경로 확인됨: {VENV_BIN}")
        # PATH 환경변수의 맨 앞에 venv/bin을 추가하여 해당 환경의 바이너리가 우선 순위를 갖게 함
        os.environ["PATH"] = VENV_BIN + os.pathsep + os.environ["PATH"]
    else:
        print("Warning: 가상환경(venv)을 찾을 수 없습니다. 시스템 라이브러리를 사용합니다.")

    # ==========================================
    # 5. Startup Config (.cfg) 생성 (Ansible)
    # ==========================================
    print("Step 5: Ansible을 이용한 Startup Config 생성 중...")
    if not os.path.exists(PLAYBOOK_FILE):
        print(f"Error: 플레이북 파일을 찾을 수 없습니다: {PLAYBOOK_FILE}")
        sys.exit(1)

    # 지정된 ANSIBLE_PLAYBOOK 경로 사용
    run_command([ANSIBLE_PLAYBOOK, "-i", INVENTORY_FILE, PLAYBOOK_FILE])
    print(" -> Config 생성 완료.")

    # ==========================================
    # 6. Lab 배포 (Containerlab)
    # ==========================================
    print("Step 6: Containerlab 배포 시작...")
    if not os.path.exists(TOPO_FILE):
        print(f"Error: 토폴로지 파일을 찾을 수 없습니다: {TOPO_FILE}")
        sys.exit(1)

    run_command(["chmod", "-R", "755", configs_path], use_sudo=True)
    run_command(["containerlab", "deploy", "-t", TOPO_FILE, "--reconfigure"], use_sudo=True)

    # ==========================================
    # 7. 완료 및 연결 확인
    # ==========================================
    print("-" * 50)
    print("모든 준비가 완료되었습니다.")
    print("장비 연결(Ping) 테스트 중 (15초 대기)...")
    
    import time
    time.sleep(15)
    
    # 지정된 ANSIBLE_BIN 경로 사용
    run_command([ANSIBLE_BIN, "arista", "-i", INVENTORY_FILE, "-m", "ping"], check=False)

    print("-" * 50)
    print(f" - 인벤토리: {INVENTORY_FILE}")
    print(f" - 토폴로지: {TOPO_FILE}")
    print("-" * 50)

if __name__ == "__main__":
    main()