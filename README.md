# [Project] Arista cEOS 기반 고가용성 멀티캐스트 망 자동화 및 통합 모니터링 구축

본 프로젝트는 금융권 네트워크 인프라에서 필수적인 고가용성(HA) 확보, 실시간 멀티캐스트 데이터 배달, 그리고 운영 자동화 역량을 증명하기 위한 통합 네트워크 랩입니다. Arista cEOS 가상 환경을 기반으로 L3 게이트웨이 이중화(VARP)와 멀티캐스트(PIM-SM)를 구현하였으며, SNMP v3 기반의 Zabbix/Grafana 모니터링 및 Slack 장애 전파 시스템을 IaC로 통합 구축했습니다.

## 주요 특징 (Key Highlights)

* **High-Availability Gateway (VARP)**: Arista Virtual ARP를 통한 Active-Active 게이트웨이 구현으로 장애 발생 시 패킷 유실 없는 서비스 연속성을 보장합니다.
* **Multicast Data Pipeline**: PIM-SM(Sparse Mode) 및 IGMP 설정을 통해 금융 데이터 전송 환경을 재현하고 최단 경로 트리(SPT) 전환을 검증합니다.
* **Unified Automation (IaC)**: Ansible 역할을 활용하여 Underlay(OSPF), HA(VARP), Multicast(PIM) 및 모니터링 스택 등록까지 전 과정을 자동화했습니다.
* **API-Driven Monitoring**: Zabbix API를 이용해 장비 등록과 알림 체계를 코드로 관리하며, 장애 시 조치 가이드(Troubleshooting Guide)가 포함된 Slack 메시지를 전송합니다.
* **Hybrid Cloud Scalability**: 온프레미스에서 검증된 설계를 AWS Transit Gateway(TGW) 및 Direct Connect(DX) 환경으로 확장할 수 있는 아키텍처 모델을 제시합니다.

## 1. Network Topology

본 실습 환경은 가용성과 확장성을 고려하여 3대의 Arista cEOS를 삼각형(Triangle) 구조로 배치하였으며, 별도의 Management Plane을 통해 모니터링 시스템과 연결됩니다.

![Topology](docker/ceos-lab/topology.clab.drawio.svg)



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
[ Data Plane ] - High-Availability & Multicast Flow
===========================================================================
[ Cloud 영역 ]
      +------------------------------------------+
      |  [ cloud-host ] (172.16.1.10)            |
      +-------+----------------------------------+
              | (eth1)
      +-------+----------------------------------+
      |  [ br-cloud ] (L2 Bridge)                |
      +---+--------------------------+-----------+
          |                          |
   (Et3)  |                  (Et3)   |
  +-------+-------+          +-------+-------+
  |    ceos1      |          |    ceos2      |
  | (172.16.1.1)  |          | (172.16.1.2)  |
  +---------------+          +---------------+
          ^                          ^
          |        VARP VIP          |
          +------( 172.16.1.254 )----+
          
      [ Backbone 영역 (Triangle) ]
          / \                      / \
         /   \                    /   \
    (Et1)     (Et2)          (Et1)     (Et2)
      |         |              |         |
      +---------|--------------+         |
                |       (OSPF/PIM)       |
                |                        |
                |        (Et1)     (Et2) |
                +----------+---------+---+
                           |  ceos3  |
                           +----+----+
                                | (Et3)
      [ Internal 영역 ]         |
      +-------------------------+----------------+
      |  [ br-internal ] (L2 Bridge)             |
      +-------------------------+----------------+
                                | (eth1)
      +-------------------------+----------------+
      |  [ internal-host ] (192.168.10.10)       |
      +------------------------------------------+

```

## 2. Tech Stack
Network OS: Arista cEOS (v4.35.1F)

Orchestration: Containerlab (v0.72.0+)

Automation: Ansible (v2.19.5+)

Monitoring: Zabbix (SNMPv3, API Integration), Grafana

Notification: Slack API (Incoming Webhooks)

Infrastructure: AWS EC2 (Ubuntu 24.04 LTS) 또는 WSL2

Testing Tools: Alpine Linux, socat (Multicast Testing), tcpdump

## 3. Project Structure

```text
.
├── setup_env.sh              # 시스템 의존성 및 환경 구축 스크립트
├── requirements.txt          # Python 라이브러리 명세
├── init_lab.py               # 토폴로지 배포 및 초기 설정 자동화 엔진
├── ansible/                  # 네트워크 설정 및 모니터링 자동화 (IaC)
│   ├── inventory/
│   │   ├── inventory.yml     # cEOS 장비 및 호스트 그룹 정의
│   │   └── group_vars/
│   │       └── all.yml       # Zabbix Token, SNMPv3 유저, VARP MAC 등 공통 변수
│   └── playbooks/
│       ├── config_underlay.yml     # OSPF 및 기본 IP 설정
│       ├── config_ha_gateway.yml   # VARP 기반 Active-Active GW 설정
│       ├── config_multicast.yml    # PIM-SM 및 IGMP 설정
│       ├── register_zabbix.yml     # Zabbix API 기반 호스트 등록
│       └── setup_monitoring.yml    # Jitter 감시 및 Slack 알림 체계 구축
├── docker/
│   ├── ceos-lab/             # Data Plane: Containerlab 토폴로지 설계도
│   └── monitoring/           # Management Plane: Zabbix, Grafana (Docker Compose)
└── README.md

```

---

## 4. Getting Started

### Step 1. 환경 세팅 및 의존성 설치
Bash
chmod +x setup_env.sh && ./setup_env.sh
source venv/bin/activate
./init_lab.py

### Step 2. 모니터링 스택 구동 및 호스트 등록
Zabbix 서버를 실행한 후, API 토큰을 발급받아 인벤토리에 업데이트한 뒤 등록 플레이북을 실행합니다.

Bash
docker compose -f ./docker/monitoring/docker-compose.yml up -d
ansible-playbook -i ansible/inventory/inventory.yml ansible/playbooks/register_zabbix.yml

### Step 3. 인프라 설정 및 가용성 검증
Bash
ansible-playbook -i ansible/inventory/inventory.yml ansible/playbooks/config_ha_gateway.yml
ansible-playbook -i ansible/inventory/inventory.yml ansible/playbooks/config_multi



*정상 동작 확인을 통해 전체 환경 구성의 적절성 여부를 최종 체크합니다.*

---

## 5. 핵심 설계 및 검증 포인트 (Architecture Points)
1) VARP 기반 고가용성 (L3 Redundancy)
Arista VARP를 활용하여 모든 게이트웨이 라우터가 동일한 가상 IP와 MAC을 공유하는 Active-Active 구조를 구현했습니다. 이를 통해 특정 장비 장애 시 별도의 프로토콜 수렴 시간 없이 즉각적인 장애 조치(Failover)가 가능함을 입증했습니다.

2) 멀티캐스트 배달 최적화
PIM-SM 아키텍처에서 소스 등록 및 SPT(Shortest Path Tree) 전환 과정을 검증했습니다. socat을 이용해 실제 멀티캐스트 패킷을 송수신하며 데이터 평면의 정합성을 확인했습니다.

3) OSPF ECMP를 통한 트래픽 부하 분산
동일 비용 다중 경로(ECMP) 설정을 통해 업링크 트래픽을 분산 처리함으로써 네트워크 자원 활용도를 극대화하고 전용 회선의 혼잡을 방지하는 구조를 설계했습니다.

4) AWS 하이브리드 확장성 (Future Vision)
본 프로젝트에서 검증된 논리는 AWS Transit Gateway(TGW)의 Anycast 게이트웨이 및 Direct Connect(DX) ECMP 설계로 확장 가능합니다. 온프레미스 멀티캐스트 소스를 TGW Multicast Domain과 연동하여 하이브리드 클라우드 전 구간에 실시간 데이터를 배달하는 차세대 금융 망 설계안을 포함하고 있습니다.

---
