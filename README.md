---

# Infra Automation for Securities (Arista cEOS Lab)

본 프로젝트는 증권사 네트워크 환경을 모델링하여 Arista cEOS 기반의 인프라를 구축하고, Ansible 및 Zabbix/Grafana를 연동하여 운영 자동화와 가시성을 확보하는 **NetDevOps 실무 환경**을 구현합니다.

## 1. Network Topology

본 실습 환경은 가용성과 확장성을 고려하여 3대의 Arista cEOS를 삼각형(Triangle) 구조로 배치하였으며, 별도의 Management Plane을 통해 모니터링 시스템과 연결됩니다.

```text
===========================================================================
[ Management Plane ] - Out-of-Band (OOB) Monitoring
===========================================================================
            
            +-----------------------------+
            |      Zabbix / Grafana       | (Monitoring Stack)
            +--------------+--------------+
                           |
                [ clab bridge (MGMT) ]  <-- Subnet: 172.20.20.0/24
                           |
          +----------------+----------------+----------------+
          |                |                |                |
    (Ma0: .11)       (Ma0: .12)       (Ma0: .13)             |
     [ceos1]          [ceos2]          [ceos3]               |
                                                             |
===========================================================================
[ Data Plane ] - Service Traffic & Redundancy
===========================================================================

              +-------------------------------+
              |      External Network (EXT)    |
              +-------/---------------\-------+
                     /                 \
             (Path A)                   (Path B)
            +-------/-------+          +-------\-------+
            |      ceos1     +----------+      ceos2   |
            |    (Spine 1)   |  (eth1)  |    (Spine 2) |
            +---+-------+---+          +---+-------+---+
                |                                  |
         (eth2) |                                  | (eth2)
                |                                  |
                |                                  |
                |         +------------+           |
                +---------+    ceos3   +-----------+
                  (eth1)  |   (Leaf)   |  (eth2)
                          +------------+



## 2. Tech Stack

* **Network OS**: Arista cEOS (v4.35.1F)
* **Orchestration**: Containerlab (v0.72.0+)
* **Automation**: Ansible (v12.3.0 / Core 2.19.5)
* **Monitoring**: Zabbix (SNMPv3), Grafana (Visualization)
* **Infrastructure**: AWS EC2 (Ubuntu 24.04 LTS) or WSL2
* **Languages**: Python 3.10+ (Custom venv)

---
```
![Topology](docker/ceos-lab/topology.clab.drawio.svg)

## 3. Project Structure

```text
.
├── setup_env.sh              # [Step 0] 시스템 의존성 및 환경 구축 스크립트
├── requirements.txt          # Python 라이브러리 명세
├── init_lab.py               # [Step 1] 토폴로지 배포 및 초기 설정 자동화
├── ansible/                  # 네트워크 설정 자동화 (IaC)
│   ├── inventory/
│   │   ├── inventory.yml     # cEOS 장비 및 그룹 정의
│   │   └── group_vars/
│   │       └── all.yml       # Zabbix Token, SNMPv3 유저 등 공통 변수
│   └── playbooks/            # 기능별 플레이북
├── docker/
│   ├── ceos-lab/             # Data Plane: Containerlab 토폴로지 설계도
│   └── monitoring/           # Management Plane: Zabbix, Grafana (Docker Compose)
├── venv/                     # Python 가상환경
└── README.md                 # 프로젝트 가이드

```

---

## 4. Getting Started

### Step 0. 환경 세팅 및 의존성 설치

```bash
chmod +x setup_env.sh
./setup_env.sh

```

### Step 1. 가상환경 활성화 및 랩 배포

```bash
source venv/bin/activate
./init_lab.py

```

### Step 2. 모니터링 스택 구동

```bash
docker compose -f ./docker/monitoring/docker-compose.yml up -d

```

### Step 3. Zabbix 호스트 등록 프로세스 (필수)

새로운 환경에서 Zabbix 서버가 구동된 후, 장비 설정을 넣기 전 모니터링 시스템에 먼저 등록해야 합니다.

1. **Zabbix API 토큰 발급**: `http://127.0.0.1:8081` 접속 후 API Token 신규 발급
2. **변수 업데이트**: `ansible/inventory/group_vars/all.yml` 내 `zabbix_token` 값 수정
3. **호스트 등록 실행**:

```bash
ansible-playbook -i ansible/inventory/inventory.yml ansible/playbooks/register_zabbix.yml

```

### Step 4. 인프라 설정 및 환경 구성 체크

Zabbix 등록이 완료된 상태에서 기본 플레이북을 실행하여 실제 데이터 수집 여부를 확인합니다.

```bash
ansible-playbook -i ansible/inventory/inventory.yml ansible/playbooks/config_NTP.yml
ansible-playbook -i ansible/inventory/inventory.yml ansible/playbooks/config_snmp.yml

```

*정상 동작 확인을 통해 전체 환경 구성의 적절성 여부를 최종 체크합니다.*

---

## 5. Architecture Points

### 1) 관리 및 데이터 평면 분리

Containerlab(L2/L3 인프라)과 Docker Compose(모니터링 서비스)를 분리하여 운영 효율을 높였습니다.

### 2) 선(先) 등록 후(後) 설정 프로세스

Zabbix에 호스트를 먼저 등록한 뒤 네트워크 설정을 주입함으로써, 설정 변경에 따른 모니터링 지표 변화를 즉시 검증할 수 있는 워크플로우를 구축했습니다.

### 3) IaC 기반 보안 강화

모든 장비는 SNMPv3(authPriv)를 통해 보안이 강화된 상태로 모니터링됩니다.

---
