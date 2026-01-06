#!/bin/bash

# 디렉토리 이동
cd $(dirname $0)

echo "Generating TLS Certificates for Arista cEOS..."

# 1. Root CA 생성 (가상 인증 기관)
openssl genrsa -out rootCA.key 2048
openssl req -x509 -new -nodes -key rootCA.key -sha256 -days 3650 -out rootCA.pem \
    -subj "/C=KR/ST=Seoul/O=MyLabCA"

# 2. Server Key 생성
openssl genrsa -out server.key 2048

# 3. CSR(인증서 서명 요청) 생성
# CN은 나중에 접속할 대표 IP나 도메인을 적습니다.
openssl req -new -key server.key -out server.csr \
    -subj "/C=KR/ST=Seoul/O=AristaLab/CN=ceos-lab"

# 4. CA의 키로 서버 인증서 서명
openssl x509 -req -in server.csr -CA rootCA.pem -CAkey rootCA.key -CAcreateserial \
    -out server.crt -days 365 -sha256

echo "Certificates generated successfully in ./certs directory."