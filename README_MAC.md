# MacBook Local Run

맥북에서 로컬 서버로 실행하는 패키지입니다. 인터넷에 업로드하지 않고 Mac 안에서 배경 제거 서버를 켜서 사용합니다.

## 실행

1. 압축을 풀고 터미널을 엽니다.
2. 압축을 푼 폴더로 이동합니다.
3. 아래 명령을 실행합니다.

```bash
bash start-mac.command
```

처음 실행할 때는 Python 패키지 설치와 기본 모델 다운로드 때문에 시간이 걸립니다. 준비가 끝나면 브라우저가 자동으로 열립니다.

```text
http://127.0.0.1:7000
```

종료하려면 터미널에서 `Ctrl+C`를 누르면 됩니다.

## 더블클릭 실행

압축 해제 후 더블클릭으로 실행하고 싶으면 한 번만 권한을 부여합니다.

```bash
chmod +x start-mac.command download-pro-models.command
```

그 다음부터는 `start-mac.command`를 더블클릭해서 실행할 수 있습니다.

## 고품질 모델 미리 받기

프로/최고품질 모드를 자주 쓸 거라면 아래 명령으로 모델을 미리 받을 수 있습니다.

```bash
bash download-pro-models.command
```

## 필요 조건

- macOS
- Python 3.11 이상
- 첫 설치와 첫 모델 다운로드 때 인터넷 연결 필요

Python이 없다면 아래에서 macOS용 Python을 설치하세요.

```text
https://www.python.org/downloads/macos/
```
