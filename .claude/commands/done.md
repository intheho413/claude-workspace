작업 완료 후 GitHub에 저장하는 명령어입니다.

다음을 순서대로 실행하세요:

1. 프로젝트 디렉토리로 이동 후 변경된 파일을 확인
2. 모든 변경사항을 스테이징
3. 오늘 날짜와 시간을 포함한 커밋 메시지로 커밋
4. GitHub에 push

아래 bash 명령어를 실행해주세요:

```bash
cd "C:\Users\inho4\OneDrive\바탕 화면\claude\2.TheSC-MSO 사이트" && git add . && git commit -m "작업 저장 $(date '+%Y-%m-%d %H:%M')" && git push && echo "✅ GitHub 업로드 완료"
```

완료되면 결과를 사용자에게 알려주세요.
