---

[Project] Arista cEOS 기반 네트워크 자동화 및 통합 모니터링 스택 구축
본 프로젝트는 금융권 네트워크 엔지니어에게 요구되는 인프라 가시성 확보와 운영 자동화 역량을 증명하기 위한 'Tiny Project'입니다. Arista cEOS 가상 환경 배포부터 SNMP v3 기반 감시, 그리고 Zabbix API를 이용한 슬랙(Slack) 장애 전파 자동화까지의 전 과정을 IaC로 구현했습니다.

## 주요 특징 (Key Highlights)

One-Step Deployment: init_lab.py 실행만으로 네트워크 토폴로지 구성, Ansible 기반 장비 설정 생성, 모니터링 스택 배포가 완벽하게 수행됩니다.

Unified Alerting System: 장애 발생 시 단순 알림을 넘어, 운영자가 즉시 실행할 수 있는 **조치 가이드(Troubleshooting Guide)**가 포함된 슬랙 메시지를 자동 전송합니다.

API-Driven Configuration: Zabbix UI 조작 없이 Ansible과 Zabbix API(V5 iteration)를 통해 Media Type, User Media, Action을 100% 코드로 관리합니다.

Infrastructure as Code (IaC):

Ansible: 장비 설정, SNMP v3 등록 및 Zabbix 알림 체계 구축을 자동화했습니다.

Grafana Provisioning: YAML 설정을 통해 데이터 소스 연동을 자동화했습니다.

Advanced Monitoring Logic: ICMP Jitter 계산(Standard Deviation 활용) 및 인터페이스 상태(err-disabled) 감시를 통해 정밀한 원장망 가용성을 측정합니다.

## 1. Network Topology

본 실습 환경은 가용성과 확장성을 고려하여 3대의 Arista cEOS를 삼각형(Triangle) 구조로 배치하였으며, 별도의 Management Plane을 통해 모니터링 시스템과 연결됩니다.

![Topology](docker/ceos-lab/topology.clab.drawio.svg)
```
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
            |      ceos1    +----------+      ceos2    |
            |    (Spine 1)  |  (eth1)  |    (Spine 2)  |
            +---+-------+---+          +---+-------+---+
                |                                  |
         (eth2) |                                  | (eth2)
                |                                  |
                |                                  |
                |         +------------+           |
                +---------+    ceos3   +-----------+
                  (eth1)  |   (Leaf)   |  (eth2)
                          +------------+
```




## 2. Tech Stack

* **Network OS**: Arista cEOS (v4.35.1F)
* **Orchestration**: Containerlab (v0.72.0+)
* **Automation**: Ansible (v12.3.0 / Core 2.19.5)
* **Monitoring**: Zabbix (SNMPv3, API Integration), Grafana (Visualization)
* **Notification: Slack API (Incoming Webhooks)
* **Infrastructure**: AWS EC2 (Ubuntu 24.04 LTS) or WSL2
* **Languages**: Python 3.10+ (Custom venv)


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
│   └── playbooks/
│       ├── config_NTP.yml, config_NTP.yml, register_zabbix.yml # 네트워크장비 기본세팅 및 zabbix 등록 
│       └── setup_zabbix_jitter_monitoring.yml                  # err-disabled 감시 및 jitter 임계값 이상에 대한 slack 알림 구현
├── docker/
│   ├── ceos-lab/             # Data Plane: Containerlab 토폴로지 설계도
│   └── monitoring/           # Management Plane: Zabbix, Grafana (Docker Compose)
├── venv/                     # Python 가상환경
└── README.md                 # 프로젝트 가이드

```

---

## 4. Getting Started

### Step 0. 환경 세팅 및 의존성 설치


chmod +x setup_env.sh
./setup_env.sh



### Step 1. 가상환경 활성화 및 랩 배포


source venv/bin/activate
./init_lab.py



### Step 2. 모니터링 스택 구동


docker compose -f ./docker/monitoring/docker-compose.yml up -d



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
