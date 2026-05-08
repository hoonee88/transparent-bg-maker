# Transparent Background Maker 배포

이 프로젝트는 하나의 FastAPI 서버가 웹 UI와 `/api`를 같이 제공합니다.

## 로컬 프로덕션 실행

```bash
npm install
npm run build
python -m venv .venv
. .venv/bin/activate
pip install -r requirements.txt
python scripts/prefetch_models.py
uvicorn backend:app --host 0.0.0.0 --port 8080
```

접속: `http://localhost:8080`

## Docker 배포

```bash
docker build -t transparent-bg-maker .
docker run --rm -p 8080:8080 transparent-bg-maker
```

접속: `http://localhost:8080`

기본 Docker 빌드는 모델을 이미지 안에 미리 다운로드합니다. 이미지가 크고 빌드가 오래 걸리면:

```bash
docker build --build-arg PREFETCH_MODELS=0 -t transparent-bg-maker .
```

이 경우 첫 요청 때 모델을 다운로드합니다.

## 서버 권장 사양

- 최소: RAM 8GB, 동시 추론 1개
- 권장: RAM 16GB 이상
- CPU만으로도 가능하지만 프로 모드는 느립니다.

## 환경 변수

- `PORT`: 서버 포트, 기본 `8080`
- `MAX_UPLOAD_MB`: 업로드 파일 제한, 기본 `12`
- `MAX_IMAGE_MEGAPIXELS`: 이미지 픽셀 제한, 기본 `12`
- `INFERENCE_CONCURRENCY`: 동시 추론 개수, 기본 `1`
- `PUBLIC_ORIGINS`: 별도 프런트 도메인을 쓸 때 CORS 허용 origin CSV
- `U2NET_HOME`: 모델 저장 위치, Docker 기본 `/app/models`

## 개인정보

현재 구현은 업로드 이미지를 디스크에 저장하지 않고 메모리에서 처리한 뒤 PNG만 반환합니다. 공개 서비스로 운영할 때는 이용약관, 개인정보 안내, 요청 제한, 로그 정책을 추가하는 것이 좋습니다.

GitHub를 사용한 배포 흐름은 [README_GITHUB_DEPLOY.md](./README_GITHUB_DEPLOY.md)를 참고하세요.
