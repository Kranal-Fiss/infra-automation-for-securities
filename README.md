안 책임님, 요청하신 **텍스트 기반 토폴로지 다이어그램**을 추가하고, 브랜치 전략을 **향후 추가 예정**으로 수정한 최종 README 버전입니다. 이모티콘은 모두 제거하고 전문적인 톤을 유지했습니다.

---

# Infra Automation for Securities (Arista cEOS Lab)

본 프로젝트는 증권사 네트워크 환경을 모델링하여 Arista cEOS 기반의 인프라를 구축하고, Ansible 및 Zabbix/Grafana를 연동하여 운영 자동화와 가시성을 확보하는 **NetDevOps 실무 환경**을 구현합니다.

## 1. Network Topology

본 실습 환경은 가용성과 확장성을 고려하여 3대의 Arista cEOS를 삼각형(Triangle) 구조로 배치하였으며, 별도의 Management Plane을 통해 모니터링 시스템과 연결됩니다.



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
             |     External Network (EXT)    |
             +-------/---------------\-------+
                    /                 \
            (Path A)                   (Path B)
           +-------/-------+          +-------\-------+
           |     ceos1     +----------+     ceos2     |
           |   (Spine 1)   |  (eth1)  |   (Spine 2)   |
           +---+-------+---+          +---+-------+---+
               |       |                  |       |
        (eth2) |       +------------------+       | (eth2)
               |             (eth3)               |
               |                                  |
               |         +------------+           |
               +---------+    ceos3   +-----------+
                 (eth1)  |   (Leaf)   |  (eth2)
                         +------------+

## 2. Tech Stack

* **Network OS**: Arista cEOS (v4.35.1F)
* **Orchestration**: Containerlab (v0.72.0+)
* **Automation**: Ansible (v12.3.0 / Core 2.19.5)
* **Monitoring**: Zabbix (SNMP), Grafana (Visualization)
* **Infrastructure**: AWS EC2 (Ubuntu 24.04 LTS) or WSL2
* **Languages**: Python 3.10+ (Custom venv)

---

## 3. Project Structure

관심사 분리(SoC) 원칙에 따라 관리 평면(Management)과 데이터 평면(Data)을 구분하여 최적화하였습니다.

```text
.
├── setup_env.sh              # [Step 0] 시스템 의존성 및 환경 구축 스크립트
├── requirements.txt          # Python 라이브러리 명세
├── init_lab.py               # [Step 1] 토폴로지 배포 및 초기 설정 자동화
├── ansible/                  # 네트워크 설정 자동화 (IaC)
│   ├── inventory/            # cEOS 장비 및 그룹 정의
│   └── playbooks/            # 인터페이스, OSPF, BGP 설정 플레이북
├── docker/
│   ├── ceos-lab/             # Data Plane: Containerlab 토폴로지 설계도
│   └── monitoring/           # Management Plane: Zabbix, Grafana (Docker Compose)
├── venv/                     # Python 가상환경 (Git 제외)
└── README.md                 # 프로젝트 가이드

```

---

## 4. Getting Started

### Step 0. 환경 세팅 및 의존성 설치

시스템 패키지(Docker, Containerlab 등)와 Python 라이브러리를 설치합니다.

```bash
chmod +x setup_env.sh
./setup_env.sh

```

### Step 1. 가상환경 활성화 및 랩 배포

Python 가상환경을 활성화한 후, cEOS 토폴로지를 배포하고 초기 구성을 주입합니다.

```bash
source venv/bin/activate
./init_lab.py

```

### Step 2. 모니터링 스택 구동

Zabbix와 Grafana를 컨테이너 방식으로 실행합니다.

```bash
docker compose -f ./docker/monitoring/docker-compose.yml up -d

```

---

## 5. Architecture Points

### 1) 관리 및 데이터 평면 분리

Containerlab은 가변적인 L2/L3 데이터 평면을 관리하며, Docker Compose는 고정된 서비스인 모니터링 스택을 담당하여 운영 효율을 높였습니다.

### 2) 네트워크 연동

Zabbix 컨테이너가 Containerlab으로 생성된 cEOS 장비들을 SNMP로 탐색할 수 있도록, `monitoring/docker-compose.yml`에서 외부 네트워크(`clab`)에 직접 조인하도록 구성되었습니다.

### 3) IaC 기반 형상 관리

모든 네트워크 설정은 Ansible Role 기반으로 템플릿화되어 있으며, `init_lab.py`를 통해 배포 시점에 동적으로 주입됩니다.

---

## 6. Branch Strategy (Planned)

현재 단일 메인 브랜치로 운영 중이며, 향후 환경별 최적화를 위해 아래와 같이 분리할 예정입니다.

* **main**: 표준 환경(WSL2/EC2 공통) 코드 관리
* **dev-ec2**: Public IP 접근 및 클라우드 최적화 설정 추가 예정
* **dev-local**: 로컬 개발 환경 최적화 버전 추가 예정

---

### 최종 점검 안내

1. **다이어그램 확인**: 위 ASCII 다이어그램의 `eth1`, `eth2` 등 포트 번호가 실제 `ceos.clab.yml` 설정과 일치하는지 확인해 주세요.
2. **경로 확인**: `docker-compose.yml` 실행 경로가 실제 프로젝트 폴더 구조와 일치하는지 다시 한 번 체크 부탁드립니다.
