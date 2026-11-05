# 수업 번역기

영어 수업을 실시간으로 한국어로 번역하는 웹앱이에요. 아이폰 Safari에서 씁니다.

- 사이트 주소: https://jade17164-tech.github.io/phishing_break/
- 코드 위치: GitHub `jade17164-tech/phishing_break` 저장소의 `gh-pages` 브랜치

## 파일
| 파일 | 내용 |
|---|---|
| `index.html` | 앱 전체 (화면, 음성 인식, 번역, 수업 기록, 단어장, 요약, 백업) |
| `worker.js` | DeepL 중계 서버 코드 (Cloudflare Worker에 붙여넣는 코드) |
| `.nojekyll` | GitHub Pages 설정용 빈 파일 |

## 기능
1. 수업별 기록 (이름 바꾸기, 주차 추천, 삭제)
2. 영어 단어를 누르면 뜻 보기, 단어장
3. 수업 요약 (핵심 단어, 중요한 문장, Claude 요약용 복사)
4. 잘린 문장 합치기, 옛 기록 다시 번역
5. 번역 엔진: 구글(기본, 무료) 또는 DeepL(Cloudflare Worker 연결)
6. 기록 백업 파일 저장 / 불러오기

## 수정한 뒤 사이트에 올리기
```
git add index.html worker.js
git commit -m "변경 내용"
git push origin gh-pages
```
1~2분 뒤 사이트에 반영돼요.

## 기록(데이터) 관련 주의
- 수업 기록은 휴대폰 Safari 안(localStorage `lt.v2`)에 저장돼요. 코드를 바꿀 때 이 저장 이름과 형식을 바꾸면 기록이 안 보이게 되니, 필드는 추가만 하고 이름을 바꾸거나 지우지 마세요.
- 사이트 주소가 `jade17164-tech.github.io` 안에 있는 한, 저장소를 옮겨도 기록은 그대로 보여요.
- DeepL 키는 코드에 넣지 말고 Cloudflare Worker의 비밀 변수 `DEEPL_KEY`에만 넣으세요.
