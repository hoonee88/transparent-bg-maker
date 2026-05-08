# GitHub로 배포하기

GitHub Pages만으로는 이 앱을 배포할 수 없습니다. 이 앱은 Python 서버와 AI 모델 추론이 필요해서, GitHub는 저장소/CI/CD/컨테이너 이미지 배포에 쓰고 실제 실행은 컨테이너 서버에서 해야 합니다.

## 1. GitHub 저장소 만들기

GitHub에서 새 repository를 만든 뒤 이 폴더에서 실행합니다.

```bash
git init
git add .
git commit -m "Initial deployable background remover"
git branch -M main
git remote add origin https://github.com/YOUR_NAME/YOUR_REPO.git
git push -u origin main
```

## 2. 가장 쉬운 배포: Render/Railway/Fly에서 GitHub repo 연결

서버 플랫폼에서 새 Web Service를 만들고 GitHub repository를 연결합니다.

권장 설정:

- Runtime: Docker
- Dockerfile: `Dockerfile`
- Port: `8080`
- RAM: 최소 8GB, 권장 16GB

환경 변수:

```bash
PORT=8080
MAX_UPLOAD_MB=12
MAX_IMAGE_MEGAPIXELS=12
INFERENCE_CONCURRENCY=1
```

Dockerfile은 프런트엔드를 빌드하고 모델을 미리 다운로드한 뒤 FastAPI 서버를 실행합니다.

## 3. GitHub Container Registry 사용

`.github/workflows/docker-publish.yml`가 `main` 브랜치 push마다 Docker 이미지를 GHCR에 올립니다.

이미지 주소:

```bash
ghcr.io/YOUR_NAME/YOUR_REPO:latest
```

서버에서 실행:

```bash
docker pull ghcr.io/YOUR_NAME/YOUR_REPO:latest
docker run -d --name transparent-bg-maker -p 8080:8080 ghcr.io/YOUR_NAME/YOUR_REPO:latest
```

## 4. 비용/성능 주의

프로 모드는 `bria-rmbg + birefnet-general-lite`를 사용해서 메모리를 많이 씁니다. 무료 호스팅 인스턴스에서는 죽거나 타임아웃이 날 수 있습니다. 공개 서비스는 동시 추론을 1개로 유지하고, 트래픽이 늘면 worker를 수평 확장하는 쪽이 안전합니다.

## 5. 운영 전에 추가하면 좋은 것

- 요청 횟수 제한
- 간단한 이용약관/개인정보 안내
- 파일 자동 삭제 정책 안내
- Cloudflare 같은 앞단 캐시/방화벽
- 큰 이미지 자동 리사이즈
