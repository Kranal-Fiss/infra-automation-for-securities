

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
- OSPF: Backbone Triangle 구간(ceos1-ceos2-ceos3) 및 각 Loopback 도달성 확보를 위한 내부 라우팅 01_config_underlay.yml에서
  모든 인터페이스를 Area0로 구성하여 네트워크 전체의 IP 도달성 확보.
- BGP: overlay 구간,Loopback 을 기반으로 한 iBGP 피어링 및 경로 확장, 
  03_config_bgp_ecmp.yml에서 ceos1, 2, 3 간 풀-메시(Full-mesh)를 형성하여 유연한 경로 광고 체계를 구축 
- IGMP: 호스트와 라우터 간 멀티캐스트 그룹 멤버십 관리 프로토콜
- PIM: unicast route 경로를 따라 multicast 경로 구성
- PIM-SM: 유니캐스트 경로를 기반으로 트리를 구성하며, RP(Rendezvous Point)를 통해 요청이 있는 지점에만 데이터를 복제/전달
- VARP: Arista 특화 고가용성 다중화 기능 - 여러대의 라우터가 동일한 VIP와 MAC을 공유하는 방식
  02_config_ha_gateway.yml을 통해 Cloud 영역의 ceos1, ceos2를 하나의 가상 게이트웨이(172.16.1.254)로 묶어 무중단 환경을 제공
- ECMP: 목적지까지의 metric이 동일한 다중경로로 분산전송 
  Backbone 구간의 삼각형 토폴로지에서 중복 경로를 활용해 트래픽 부하 분산을 구현

Orchestration: Containerlab (v0.72.0+)

Automation: Ansible (v2.19.5+)

Monitoring: Zabbix (SNMPv3, API Integration), Grafana

Notification: Slack API (Incoming Webhooks)

Infrastructure: AWS EC2 (Ubuntu 24.04 LTS) 또는 WSL2

Testing Tools: ubuntu Linux, socat (Multicast Testing), tcpdump, iperf3, mtr

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
│       ├── 00_generate_configs.yml     # Day 0: Bootstrap 설정 생성
│       ├── 00-1_config_ntp.yml         # 기초: 시간 동기화
│       ├── 00-2_config_snmp.yml        # 기초: SNMPv3 보안 설정
│       ├── 01_config_underlay.yml      # 인프라: OSPF 및 IP 구축
│       ├── 02_config_ha_gateway.yml    # 가용성: VARP Active-Active 설정
│       ├── 03_config_bgp_ecmp.yml      # 확장: iBGP 및 ECMP 부하분산
│       ├── 04_get_zabbix_token.yml     # [Update] 모니터링 연동을 위한 토큰 관리
│       └── 05_register_monitoring.yml  # 운영: Zabbix API 등록 및 Slack 연동
│       └── 08_final_fix_all.yml        # multicast 및 PIM 등 설정 
├── docker/
│   ├── ceos-lab/             # Data Plane: Containerlab 토폴로지 설계도
│   └── monitoring/           # Management Plane: Zabbix, Grafana (Docker Compose)
└── README.md

```
## 4. Getting Started

### Step 1. 환경 세팅 및 의존성 설치
Bash
chmod +x setup_env.sh && ./setup_env.sh
source venv/bin/activate
./init_lab.py

#### 정상 구동 검증 containerlab topology 구성 확인
sudo clab graph -t ./docker/ceos-lab/topology.clab.yml 

### Step 2. 인프라 설정
# [1] 기초 시스템 설정: 시간 동기화 및 모니터링 보안 채널(SNMPv3) 확보
ansible-playbook -i ansible/inventory/inventory.yml ansible/playbooks/00-1_config_ntp.yml 
ansible-playbook -i ansible/inventory/inventory.yml ansible/playbooks/00-2_config_snmp.yml

# [2] 네트워크 뼈대 구축: OSPF 언더레이를 통한 루프백 도달성 확보
ansible-playbook -i ansible/inventory/inventory.yml ansible/playbooks/01_config_underlay.yml

# [3] 고가용성 및 라우팅 확장: VARP 게이트웨이 및 iBGP ECMP 설정
ansible-playbook -i ansible/inventory/inventory.yml ansible/playbooks/02_config_ha_gateway.yml
ansible-playbook -i ansible/inventory/inventory.yml ansible/playbooks/03_config_bgp_ecmp.yml

### Step 3. 서비스 활성화 및 모니터링 통

# [4] 운영 통합: Zabbix API 연동 및 장애 알림(slack) 자동화
ansible-playbook -i ansible/inventory/inventory.yml ansible/playbooks/04_get_zabbix_token.yml
docker compose -f ./docker/monitoring/docker-compose.yml up -d
ansible-playbook -i ansible/inventory/inventory.yml ansible/playbooks/05_register_monitoring.yml

# [5] 서비스 주입: 금융 데이터 전송을 위한 Multicast(PIM-SM) 활성화
ansible-playbook -i ansible/inventory/inventory.yml ansible/playbooks/08_final_fix_all.yml

### Step 4. 호스트 라우팅 설정 (Data Plane 활성화)
컨테이너 호스트들이 관리망이 아닌 Arista Fabric을 타도록 라우팅을 추가합니다.

# cloud-host -> internal-host 경로 추가

docker exec clab-ceos-triangle-cloud-host ip route add 192.168.10.0/24 via 172.16.1.254

# internal-host -> cloud-host 경로 추가
docker exec clab-ceos-triangle-internal-host ip route add 172.16.1.0/24 via 192.168.10.1

## 5. 핵심 설계 및 검증 포인트 (Architecture Points)
1) VARP 기반 고가용성 (L3 Redundancy)
Arista VARP를 활용하여 모든 게이트웨이 라우터가 동일한 가상 IP와 MAC을 공유하는 Active-Active 구조를 구현했습니다. 이를 통해 특정 장비 장애 시 별도의 프로토콜 수렴 시간 없이 즉각적인 장애 조치(Failover)가 가능함을 입증했습니다.

2) 멀티캐스트 배달 최적화
PIM-SM 아키텍처에서 소스 등록 및 SPT(Shortest Path Tree) 전환 과정을 검증했습니다. socat을 이용해 실제 멀티캐스트 패킷을 송수신하며 데이터 평면의 정합성을 확인했습니다.

3) OSPF ECMP를 통한 트래픽 부하 분산
동일 비용 다중 경로(ECMP) 설정을 통해 업링크 트래픽을 분산 처리함으로써 네트워크 자원 활용도를 극대화하고 전용 회선의 혼잡을 방지하는 구조를 설계했습니다.

4) AWS 하이브리드 확장성 (Future Vision)
본 프로젝트에서 검증된 논리는 On-premise와 Cloud 간의 일관된 IaC 운영 모델을 제시하고 있습니다. AWS Transit Gateway(TGW)의 Anycast 게이트웨이 및 Direct Connect(DX) ECMP 설계로 확장 가능합니다. 
온프레미스 멀티캐스트 소스를 TGW Multicast Domain과 연동하여 하이브리드 클라우드 전 구간에 실시간 데이터를 배달하는 차세대 금융 망 설계안을 포함하고 있습니다.

## 6. Verification Commands (검증 가이드)
설정 후 정상 동작 여부를 확인하기 위한 주요 커맨드입니다.

1) L3 인터페이스 활성화 확인
   - `show ip interface brief` (Et1~3가 up/up 인지 확인)
   
   ceos1# show ip interface brief
Interface          IP Address            Status       Protocol
----------------- --------------------- ------------ --------------
Loopback0          1.1.1.1/32            up           up
Ethernet1          10.1.12.1/30          up           up
Ethernet2          10.1.13.1/30          up           up
Ethernet3          172.16.1.1/24         up           up
   
2) OSPF 및 BGP 인접 관계 확인
   - `show ip ospf neighbor`
   - `show ip bgp summary`
   백본 구간에서 동일 비용 다중 경로가 생성되어 트래픽 부하 분산이 가능한지 확인합니다
   
   ceos1# show ip route ospf
 O        2.2.2.2/32 [110/20]
           via 10.1.12.2, Ethernet1
           via 172.16.1.2, Ethernet3  <-- ECMP 경로 확보
		   
   
3) VARP 가상 게이트웨이 동작 확인
   - `show ip virtual-router` (Virtual IP address가 보여야 함)
   ceos1과 ceos2가 동일한 가상 IP(172.16.1.254)를 공유하며 Active 상태로 동작하는지 확인합니다.
   
   ceos1# show ip virtual-router
Interface    Virtual IP Address    Protocol    State
----------- -------------------- ---------- -----------
Et3          172.16.1.254          U           active

4) 멀티캐스트 트리 확인: show ip mroute (SPT 생성 확인)
PIM-SM 프로토콜이 정상 가동되어 RP(3.3.3.3)를 중심으로 멀티캐스트 배달 경로가 생성되었는지 확인합니다.
ceos3# show ip mroute
239.1.1.1
  0.0.0.0, 0:00:14, RP 3.3.3.3, flags: W
    Incoming interface: Ethernet1 (via OSPF 1.1.1.1)
    Outgoing interface list:
      Ethernet3  <-- 수신자(Receiver) 접점 활성화
	  

5) BGP 오버레이 세션 확인
루프백 IP 주소를 기반으로 iBGP 피어링이 Established 상태인지 확인합니다.
ceos1#sh ip bgp summary
BGP summary information for VRF default
Router identifier 1.1.1.1, local AS number 65100
Neighbor Status Codes: m - Under maintenance
  Description              Neighbor V AS           MsgRcvd   MsgSent  InQ OutQ  Up/Down State   PfxRcd PfxAcc PfxAdv
  PEER_TO_CEOS1            1.1.1.1  4 65100             78        78    0    0 01:28:01 Active
  PEER_TO_CEOS2            2.2.2.2  4 65100             32        32    0    0 00:24:33 Estab   0      0      0
  PEER_TO_CEOS3            3.3.3.3  4 65100             32        32    0    0 00:24:33 Estab   0      0      0


6) SNMPv3 보안 통신 검증
SNMPv3(Auth/Priv)를 통해 모니터링 서버(Zabbix)와 안전하게 데이터를 주고받는지 검증합니다.
# 제어 노드(WSL/EC2)에서 실행
snmpwalk -v3 -l authPriv -u admin -a SHA -A [AUTH_PW] -x AES -X [PRIV_PW] 172.20.20.11 .1.3.6.1.2.1.1.5.0

~/infra-automation-for-securities main infra-automation-for-securities                                         13:38:18
❯ snmpwalk -v3 -l authPriv -u admin -a SHA -A 'admin123' -x AES -X 'admin123' 172.20.20.11 .1.3.6.1.2.1.1.5.0
iso.3.6.1.2.1.1.5.0 = STRING: "ceos1"

##7. 기술적 성과 및 분석 (Troubleshooting & Analysis)
핵심 요약: PIM-SM 제어 평면(Control-Plane)의 완전 자동화 구현 및 가상화 인프라 내 데이터 평면(Data-Plane) 병목 구간 식별

IaC 기반 제어 평면 검증 성공: Ansible 플레이북(01~08)을 통해 OSPF, iBGP, VARP 및 PIM-SM의 전 과정을 자동화하였으며, 각 라우터에서 멀티캐스트 라우팅 테이블(mroute) 및 트리 엔트리가 정상적으로 형성됨을 확인했습니다.

데이터 평면 전송 병목 현상 포착: 제어 평면의 정상 동작에도 불구하고 최종 UDP 패킷 전송이 불가능했던 지점을 가상 인터페이스(veth)와 리눅스 브리지 구간으로 특정했습니다.

인프라적 제약 사항 확인:

L2 Snooping 이슈: Containerlab 기반 리눅스 브리지의 mcast_snooping 활성화 시, 가상 라우터의 IGMP 제어 메시지가 상위로 투명하게 전달되지 않는 현상을 확인했습니다.

가상화 환경의 한계: 실제 하드웨어 ASIC이 없는 컨테이너 커널 환경에서 가상 인터페이스 간 멀티캐스트 패킷 복제(Replication) 시 발생하는 비결정적 드랍 가능성을 식별했습니다.

##8. 향후 과제 (Future Work)
EBGP 기반 하이브리드 클라우드 아키텍처 확장:

현재의 내부 AS(65100) 구성을 넘어, Edge 라우터(ceos1, 2)와 AWS Transit Gateway(TGW) 간의 EBGP 피어링을 통한 표준 하이브리드 경로 연동 구현.

가상 데이터 평면(Data-Plane) 고도화:

리눅스 기본 브리지의 제약을 극복하기 위해 OVS(Open vSwitch) 환경을 도입하여 멀티캐스트 포워딩 정합성을 재검증하고, 인프라 추상화 수준을 높이는 테스트 진행.
