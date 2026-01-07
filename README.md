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
본 프로젝트는 인프라 프로비저닝부터 설정 자동화까지 단계별로 구성되어 있습니다.

1. 인프라 프로비저닝 (Terraform)
AWS EC2(t3.medium, Ubuntu 20.04) 환경을 생성하고 필수 패키지(Docker, Ansible 등)를 자동 설치합니다.

Bash
cd terraform
terraform init
terraform apply -auto-approve

2. 네트워크 이미지 전송 (rsync)
로컬에 보유한 Arista cEOS 이미지를 생성된 EC2 서버로 전송합니다. 안정적인 전송과 이어받기를 위해 rsync를 사용합니다.

Bash
# EC2_IP는 테라폼 출력값(output) 참조
rsync -avzP -e "ssh -i your-key.pem" \
    docker/cEOS64-lab-4.35.1F.tar.xz \
    ubuntu@<EC2_IP>:/home/ubuntu/
	
3. 환경 초기화 및 컨테이너 실행
서버 접속 후 이미지를 로드하고, 통신 보안을 위한 인증서를 생성한 뒤 실습 환경을 실행합니다.

Bash
# 이미지 로드 (EC2 내부)
docker import /home/ubuntu/cEOS64-lab-4.35.1F.tar.xz ceosimage:latest

# 인증서 생성 및 랩 실행
bash certs/gen_certs.sh
docker-compose -f docker/docker-compose.yml up -d

4. 네트워크 설정 자동화 (Ansible)
실행된 cEOS 장비들에 인터페이스, OSPF, 멀티캐스트 설정을 일괄 배포합니다.

Bash
ansible-playbook -i ansible/inventory.ini ansible/site.yml