# infra-automation-for-securities
Infra Automation for Securities (Arista cEOS Lab)
본 프로젝트는 증권사 네트워크 환경을 모델링하여 Arista cEOS 기반의 인프라를 구축하고, Ansible 및 Zabbix/Grafana를 연동하여 운영 자동화와 가시성을 확보하는 NetDevOps 실무 환경을 구현합니다.

Tech Stack

Network OS: Arista cEOS (v4.35.1F) - Custom Baked Image

Orchestration: Containerlab (v0.72.0+)

Automation: Ansible (Configuration Management)

Monitoring: Zabbix (SNMP), Grafana (Visualization)

Infrastructure: AWS EC2 (t3.medium, Ubuntu 24.04 LTS)

Languages: Python (Custom scripts for API & gNMI)

Project Structure
관리 효율성과 확장성을 고려하여 다음과 같이 디렉토리 구조를 최적화하였습니다.

Branch
.
├── ansible/                # 네트워크 설정 자동화 (IaC)
│   ├── inventory.ini       # cEOS 장비 IP 및 그룹 정의
│   ├── roles/              # 인터페이스, OSPF, 멀티캐스트 설정 Role
│   └── site.yml            # 메인 플레이북
├── docker/
│   ├── ceos-lab/           # 데이터 평면 (Data Plane)
│   │   └── ceos.clab.yml   # Containerlab 토폴로지 설계도 (삼각형 구조)
│   └── monitoring/         # 관리 평면 (Management Plane)
│       ├── docker-compose.yml # Zabbix, Grafana, DB 스택
│       └── zabbix-agent/      # 커스텀 모니터링 설정
├── images/                 # Golden Image 저장소
│   └── cEOS64-4.35.1F-loadable.tar.gz  # 추출된 로드 가능 이미지
├── python/                 # 자동화 및 연동 스크립트
│   ├── zabbix_api.py       # Zabbix 호스트 자동 등록 스크립트
│   └── telemetry_parser.py  # gNMI 데이터 처리용
├── certs/                  # 보안 관리 (TLS/SSL)
│   └── gen_certs.sh        # gNMI/HTTPS 통신용 인증서 생성 스크립트
├── .github/workflows/      # CI/CD 파이프라인
└── README.md               # 프로젝트 가이드 

주요 수정 및 운영 포인트
1. docker/ 디렉토리 이원화
ceos-lab/: 이제 docker-compose를 버리고 **ceos.clab.yml**을 사용합니다. 스위치 간의 L2/L3 연결성을 담당합니다.

monitoring/: Zabbix나 Grafana는 여전히 **docker-compose**가 관리하기에 최적입니다. 이들은 고정된 서비스이기 때문입니다.

2. images/ 폴더의 위상 강화
기존에는 import용 날것의 파일을 두었으나, 이제는 --change 설정이 모두 구워진 **loadable.tar.gz**를 관리합니다.

EC2에서 WSL2로, 혹은 팀원에게 환경을 공유할 때 이 파일 하나만 전달하면 끝납니다.

3. 모니터링 연동의 핵심 (Network Bridge)
Containerlab이 생성하는 관리용 브리지(기본값: clab)에 모니터링 컨테이너들이 조인해야 합니다.

monitoring/docker-compose.yml에 아래 설정을 추가하여 포팅할 예정입니다.

networks:
  default:
    external: true
    name: clab  # clab 네트워크에 모니터링 툴을 직접 연결

향후 브랜치 운용 전략
main: 위 구조를 유지하며, EC2와 WSL2에서 공통으로 쓰이는 코드를 관리합니다.

dev-ec2: docker/monitoring/의 ports 설정에 퍼블릭 IP 접근용 포트 포워딩을 포함합니다.

dev-local-wsl: ceos.clab.yml에서 로컬 경로 환경 변수를 최적화합니다.

실행방법
sudo clab deploy -t ceos.clab.yml