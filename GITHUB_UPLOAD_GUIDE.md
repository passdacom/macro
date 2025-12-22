# GitHub 업로드 가이드

## ✅ 완료된 작업
- `.gitignore` 파일 생성 (임시 파일 및 빌드 파일 제외)
- v3.0 변경사항 커밋 완료
  - 커밋 메시지: "v3.0 Release: Added recording confirmation, partial playback, and multiple bug fixes"
  - 변경된 파일: 5개 (404 insertions, 124 deletions)

## 📝 다음 단계

### 1. GitHub에서 새 저장소 만들기
1. https://github.com/new 접속
2. Repository name 입력 (예: `macro-editor` 또는 `advanced-macro-editor`)
3. Public 또는 Private 선택
4. **"Add a README file" 체크 해제** (이미 로컬에 코드가 있음)
5. "Create repository" 클릭

### 2. 저장소 URL 복사
생성 후 나타나는 URL을 복사하세요:
- HTTPS: `https://github.com/사용자명/저장소명.git`
- SSH: `git@github.com:사용자명/저장소명.git`

### 3. 저장소 URL을 알려주세요
저장소 URL을 알려주시면 자동으로 푸시해드리겠습니다!

## 🚀 수동으로 푸시하려면
```bash
cd c:/cli/macro2
git remote add origin https://github.com/사용자명/저장소명.git
git push -u origin master
```

## 📦 포함될 파일들
- `main.py` - 메인 실행 파일
- `app_gui.py` - GUI 및 메인 로직
- `event_recorder.py` - 이벤트 녹화
- `event_player.py` - 이벤트 재생
- `event_grouper.py` - 이벤트 그룹화
- `event_utils.py` - 유틸리티 함수
- `action_editor.py` - 액션 편집기
- `hotkey_manager.py` - 핫키 관리
- `key_mapper_gui.py` - 키 매핑 GUI
- 기타 설정 파일들

## ⚠️ 제외될 파일들 (.gitignore)
- 빌드 파일 (build/, dist/)
- 임시 파일 (_temp_*.py)
- 로그 파일 (macro_log.txt)
- 백업 파일 (*.tar.gz)
