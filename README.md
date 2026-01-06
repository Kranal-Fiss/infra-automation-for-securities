# infra-automation-for-securities
Infra Automation for Securities (Arista cEOS Lab)
본 프로젝트는 증권사 네트워크 환경을 모델링하여 Arista cEOS 기반의 인프라를 구축하고, Ansible 및 Zabbix/Grafana를 연동하여 운영 자동화와 가시성을 확보하는 NetDevOps 실무 환경을 구현합니다.

Tech Stack
Network OS: Arista cEOS (v4.35.1F)

Automation: Ansible (Configuration Management)

Monitoring: Zabbix (SNMP), Grafana (Visualization)

Infrastructure: Docker & Docker-Compose (Containerized Lab)

Languages: Python (Custom scripts for API & gNMI)

Security: TLS/h2 (Secure Management Plane)

Project Structure
관리 효율성과 확장성을 고려하여 다음과 같이 디렉토리 구조를 최적화하였습니다.

Branch
.
├── ansible/             # 인벤토리 정의 및 설정 자동화를 위한 Playbook 및 Role
├── python/              # Zabbix API 연동 및 데이터 수집용 커스텀 스크립트
├── docker/              # cEOS 컨테이너 환경 설정 및 리소스 관리
├── certs/               # 관리 평면 보안 강화를 위한 TLS/SSL 인증서
├── .github/workflows/   # CI/CD 자동화 파이프라인 (GitHub Actions)
└── README.md
Key Features
1. Infrastructure as Code (IaC)
Ansible을 활용하여 멀티캐스트 설정 및 인터페이스 구성을 자동화하였습니다.

수동 설정 시 발생할 수 있는 휴먼 에러를 방지하고, 다수의 장비에 동일한 정책을 신속하게 배포할 수 있도록 설계되었습니다.

2. Scalable Monitoring Pipeline
SNMP-Zabbix-Grafana 통합 라인을 구축하여 장비의 실시간 상태 정보를 가시화하였습니다.

증권 인프라 운영의 핵심 지표들을 대시보드화하여 신속한 장애 탐지 및 대응 능력을 확보했습니다.

3. Secure Management Plane (h2/TLS)
관리용 트래픽 보안을 위해 HTTP/2 over TLS(h2)를 적용하였습니다.

자체 서명 인증서(Self-signed Certificate) 인프라를 구축하여 gNMI(Telemetry) 통신의 보안성을 강화하고 데이터 무결성을 보장합니다.

Future Roadmap
Streaming Telemetry 도입: SNMP의 한계를 극복하기 위해 gNMI 기반의 실시간 상태 전송 시스템 고도화 예정.

CI/CD 파이프라인 통합: 코드 Push 시 Virtual Lab 환경에서 설정을 자동 검증하는 프로세스 완성.

Multicast 트래픽 모니터링: 시세 데이터 전송 안정성 확보를 위한 멀티캐스트 트래픽 정밀 분석 기능 추가.

How to Start
인증서 생성: certs/gen_certs.sh 실행 (TLS 환경 구성)

환경 실행: docker-compose up -d

설정 배포: ansible-playbook -i ansible/inventory.ini ansible/site.yml
