언어: [English](README.md) | [한국어](README.ko.md)

[![Release](https://img.shields.io/github/v/release/hamonikr/codai)](https://github.com/hamonikr/codai/releases)
[![License](https://img.shields.io/badge/License-Apache%202.0-blue.svg)](LICENSE)
[![Linux](https://img.shields.io/badge/Linux-FCC624?style=flat&logo=linux&logoColor=black)](https://github.com/hamonikr/codai)
[![macOS](https://img.shields.io/badge/macOS-000000?style=flat&logo=apple&logoColor=white)](https://github.com/hamonikr/codai)
[![Windows](https://img.shields.io/badge/Windows-0078D6?style=flat&logo=windows&logoColor=white)](https://github.com/hamonikr/codai)
[![ARM](https://img.shields.io/badge/ARM-02569B?style=flat&logo=arm&logoColor=white)](https://github.com/hamonikr/codai)

로컬 환경에서 강력한 AI 기능을 가장 쉽게 사용할 수 있는 방법입니다. Rust로 개발되어 최고의 성능과 안정성을 제공하며, 복잡한 설정 없이 터미널에서 바로 다양한 AI 모델의 기능을 활용할 수 있습니다.

## 🌟 주요 기능

- **🚀 강력한 AI 통합**
  - 다양한 AI 제공업체 지원 (OpenAI, Anthropic, Google, Groq, Ollama)
  - 스마트한 컨텍스트 처리와 토큰 최적화
  - 실시간 비용 모니터링 및 분석

- **💻 개발자 중심 도구**
  - 컨텍스트 인식 기반의 지능형 코드 생성
  - 자동화된 코드 리뷰 및 분석
  - 직접 코드 실행 기능
  - 다중 언어 지원
  - AI 제공업체별 비용 추적 기능

- **⚡ 성능 및 안정성**
  - Rust 기반으로 최고의 속도와 안정성 제공
  - 효율적인 메모리 관리
  - 최적화된 토큰 사용
  - 자동 컨텍스트 요약

- **🔧 간편한 설정 및 사용**
  - 한 번의 명령어로 설치
  - 초기 설정 없이 바로 시작
  - 직관적인 CLI 인터페이스
  - 크로스 플랫폼 지원

## 🔬 핵심 기술

- **🛠️ Rust 기반 개발**
  - 고성능, 메모리 안전한 시스템 프로그래밍
  - 제로 비용 추상화
  - 스레드 안전성과 동시성 처리
  - 크로스 플랫폼 호환성

- **🧠 AI 통합**
  - 다중 모델 지원 (GPT-4, Claude-3, Gemini, Mixtral)
  - 효율적인 토큰 관리와 컨텍스트 처리
  - 실시간 처리를 통한 스트리밍 응답
  - 맞춤형 프롬프트 엔지니어링 및 최적화

- **🤖 에이전틱 시스템 패턴**
  - 자율적 작업 계획 및 실행
  - 컨텍스트 기반 의사결정
  - 자가 개선형 프롬프트 최적화
  - 동적 도구 선택 및 활용
  - 적응형 오류 처리 및 복구

- **⚡ 성능 최적화**
  - Tokio를 활용한 비동기 작업
  - 효율적인 메모리 관리
  - 스마트 캐싱 시스템
  - 병렬 처리 기능

## codai를 선택해야 하는 이유

- **간편한 설치**: 한 번의 명령어로 설치, 초기 설정 없이 바로 시작
- **다양한 AI 제공업체**: 주요 AI 모델과의 즉시 사용 가능한 통합
  - OpenAI (GPT-4, GPT-3.5)
  - Anthropic (Claude-3)
  - Google (Gemini)
  - Groq (Mixtral)
  - Ollama (로컬 모델)

- **개발자 중심 기능**
  - 컨텍스트 인식 기반의 즉각적인 코드 생성
  - 자동화된 코드 리뷰 및 분석
  - 직접 코드 실행 지원
  - 다중 언어 호환성
  - AI 제공업체별 비용 추적 및 사용량 분석

- **스마트한 리소스 관리**
  - AI 제공업체별 최적화된 컨텍스트 처리
  - 효율적인 토큰 사용
  - 동적 대화 관리
  - 자동 컨텍스트 요약
  - 실시간 토큰 사용량 및 비용 모니터링

## 🚀 빠른 시작

### 한 줄 설치
```bash
# Linux/macOS
curl -sSL https://raw.githubusercontent.com/hamonikr/codai/main/install.sh | bash
```

### 기본 사용법
```bash
# AI로 코드 생성
codai code "뉴스 헤드라인을 위한 웹 스크래퍼 만들기" -r

# 즉각적인 프로그래밍 도움말
codai chat "Rust의 async/await 설명해줘"

# 파일에서 복잡한 작업 실행
echo "1. REST API 서버 생성
2. 사용자 인증 추가
3. 게시물 CRUD 작업 구현
4. API 문서화" > task.txt && codai task < task.txt
```

## 📦 설치 방법

### 패키지 매니저
```bash
# Homebrew (macOS/Linux)
brew install codai

# Cargo (Rust 패키지 매니저)
cargo install codai

# Windows (PowerShell)
winget install codai
```

### 수동 설치
1. [릴리즈 페이지](https://github.com/hamonikr/codai/releases)에서 사용 중인 플랫폼에 맞는 최신 버전을 다운로드
2. 압축 파일 해제
3. 실행 파일을 시스템 PATH에 추가

## ⚙️ 설정

`~/.config/codai/config.toml` (Linux/macOS) 또는 `%APPDATA%\codai\config.toml` (Windows)에 설정 파일을 생성하세요:

```toml
[api]
openai_api_key = "your-openai-key"
anthropic_api_key = "your-anthropic-key"
google_api_key = "your-google-key"
groq_api_key = "your-groq-key"

[defaults]
model = "gpt-4"
temperature = 0.7
max_tokens = 2000

[advanced]
context_window = 8000
cache_dir = "~/.cache/codai"
```

## 🤝 기여하기

여러분의 기여를 환영합니다! 다음과 같은 방법으로 참여하실 수 있습니다:

1. 저장소를 포크하세요
2. 기능 브랜치를 생성하세요: `git checkout -b feature/amazing-feature`
3. 변경사항을 커밋하세요: `git commit -m '멋진 기능 추가'`
4. 브랜치에 푸시하세요: `git push origin feature/amazing-feature`
5. Pull Request를 생성하세요

### 개발 환경 설정

```bash
# 저장소 클론
git clone https://github.com/hamonikr/codai.git
cd codai

# 개발 의존성 설치
cargo install --path .

# 테스트 실행
cargo test

# 릴리즈 모드로 빌드
cargo build --release
```

## 📚 기술 문서

- [기술 아키텍처](docs/architecture.ko.md) - 시스템 설계 및 컴포넌트 상세 설명
- [기능 상세](docs/features.ko.md) - 각 기능에 대한 심층 설명
- [핵심 기술](docs/core-technologies.ko.md) - 핵심 기술에 대한 기술적 심층 분석

## 📄 라이선스

이 프로젝트는 듀얼 라이선스로 제공됩니다:

### 커뮤니티 라이선스 (Apache License 2.0)
- 개인 사용자, 비영리 단체, 오픈소스 프로젝트에 무료로 제공
- 자세한 내용은 [LICENSE.community](LICENSE.community) 참조

### 상용 라이선스
- 기업 및 영리 목적의 사용시 필요
- 추가 기능, 기술 지원, 커스터마이징 옵션 포함
- 자세한 약관은 [LICENSE.commercial](LICENSE.commercial) 참조
- 연락처 정보:
  - 이메일: sales@invesume.com
  - 전화: +82-2-2039-3977
  - 주소: 서울특별시 서초구 사임당로8길 17, 201호 (06640)

상용 라이선스 문의는 [연락처 페이지](https://invesume.com/contactus.html)를 방문해 주세요.

