# 게임 데이터와 FPS 상세 보기

## 저장과 사용
기존 `data/pc.db`에 다음 테이블을 추가했습니다. 기존 부품·가격 테이블은 유지합니다.

- `game_observations`: 기본 FPS 실측 407건, 그래픽 모드 실측 7건, 조건 미확인 보류 자료 152건. 종류를 `kind`로 구분합니다.
- `game_snapshot`: 출처·수집 시각·NVIDIA 공식 기능 지원 기록.
- `game_predictions`: 실제로 계산한 구성별 모드 예측. CPU/GPU·게임·해상도·기본 옵션 FPS·병목 정보·모델/근거 버전을 키에 포함합니다. 실측 테이블과 별개입니다.
- `data/game_benchmarks.json`: 이동·검토 가능한 원본 스냅샷 및 DB 읽기 실패 시 대체 자료.
- `data/game_icons.json`, `assets/game-icons/`: 공식 게임 이미지의 출처·확인 시각과 로컬 이미지.

예측기는 DB의 검증된 기본 FPS 행을 읽습니다. 보류 자료는 예측에 쓰지 않습니다. DB 기록 실패는 정상 FPS 응답을 막지 않습니다. 데이터 갱신 후 서버를 재시작하면 메모리 캐시가 갱신됩니다.

## 확대 범위
게임 34종 → 41종. 새 게임: 도타 2, F1 24, 더 라스트 오브 어스 파트 I, 마블 스파이더맨 2, 라쳇 앤 클랭크: 리프트 어파트, 스페이스 마린 2, 클레르 옵스퀴르: 33 원정대.
이 중 원정대 33은 The Game Awards 2025 GOTY 수상작입니다.
기본 FPS 실측이 있는 게임은 28종입니다. 나머지는 기존 모델 추정을 유지하며 실측으로 표시하지 않습니다.

## 수집 기준
- Back2Gaming RTX 5070 리뷰: 기사에 연결된 CSV, Ryzen 7 9800X3D, 1080p/1440p/4K, 게임별 프리셋을 검증한 기본 렌더링 246건. 제조사 OC 중복은 기준 모델을 우선하여 제거합니다.
- ClockupCore 젠레스 존 제로: 해상도·CPU·GPU·High/render scale 1.0·전투 장면이 명시된 111건.
- 기존 GamersNexus/GeekaWhat 자료: 기본 FPS 48건 및 RT/DLSS/FG 5건.
- The FPS Review: RTX 5070 FE 기본 클럭 + 9800X3D, 1440p. 앨런 웨이크 2 High 기본 73.6 / DLSS Quality 108.2, 원정대 33 Epic 기본 47.6 / DLSS Quality 74 FPS. 기본·업스케일링을 별도 행에 저장합니다.
- 이미지 차트의 값은 사람이 검토한 차트 해시와 연결합니다. 차트가 바뀌면 자동으로 추측하지 않고 재검토 대상으로 오류를 기록합니다.
- Cyberpunk의 이 리뷰 본문과 차트 숫자가 일치하지 않아 새 측정값으로 가져오지 않았습니다.
- 원신·엘든 링의 기존 게임 자체 60 FPS 제한을 유지합니다. 조건이 빠진 그래프, 불분명한 GPU 변형/오타는 실측 근거로 사용하지 않습니다.

## DLSS·프레임 생성
양쪽 FPS 영역에 React 18 disclosure를 추가했습니다. 기본은 닫힘이며, 상세 DOM은 열 때만 생성됩니다.
DLSS/FG/MFG는 NVIDIA 공식 게임 지원표와 RTX 세대별 지원을 함께 확인합니다. NVIDIA App override가 필요한 옵션에는 안내를 붙입니다.
대응하는 DLSS 실측이 있으면 이를 우선하며, 구성 차이는 기존 기본 FPS 비율로 보정합니다. 그 밖의 DLSS Quality/FSR Quality 및 FG 2×/MFG 4×는 렌더링 부하·CPU 제한·FG 오버헤드를 반영한 **모델 추정**입니다. 모든 게임·GPU의 실측이 있다는 뜻이 아닙니다.
생성 프레임 포함 표시 FPS와 실제 렌더링 FPS를 구분합니다. 조작 반응 속도 개선과 동일하지 않습니다. 기존 원문의 DLSS 품질/FG 배율이 없으면 해당 조건 미공개를 표시합니다.
NVIDIA 최신 기능 중 6× 예측은 구현하지 않았으며, 확인 가능한 2×/4×만 제공합니다.

## 갱신
프로젝트 폴더에서:

```powershell
python scripts/refresh_game_icons.py
python scripts/refresh_game_data.py
python scripts/precompute_game_predictions.py
```

마지막 명령은 9800X3D / 32GB 기준 29 GPU × 41 게임 × 3 해상도 = 3,567개 구성을 계산·저장합니다. 다른 CPU/RAM 구성은 실제 요청 시 저장합니다. **계산 구성 수를 실측 데이터 수에 합산하지 않습니다.**
네트워크/파싱 실패 시 실패한 출처의 이전 데이터를 유지합니다. 실제 수집 결과는 `data/game_data_report.json`을 확인하세요.

## SQL 조회

```sql
SELECT kind, COUNT(*) FROM game_observations GROUP BY kind;
SELECT game, COUNT(*) FROM game_observations WHERE kind='measurements' GROUP BY game;
SELECT conditions, scenarios, calculated_at FROM game_predictions ORDER BY calculated_at DESC LIMIT 10;
```

## 주요 파일
수집: `scripts/refresh_game_data.py`, `scripts/reviewed_game_sources.py`, `scripts/refresh_game_icons.py`
저장: `game_database.py`, `scripts/precompute_game_predictions.py`
예측: `game_benchmarks.py`, `graphics_estimates.py`, `server_fixed.py`
UI: `graphics_details.js`, `game_picker.js`, `app.js`, `index.html`, `styles.css`, `server_catalogs.py`

## 근거 URL
- https://www.back2gaming.com/review/nvidia-geforce-rtx-5070-founders-edition/
- https://clockupcore.com/zenlesszonezero/
- https://www.thefpsreview.com/2025/11/17/overclocking-nvidia-geforce-rtx-5070/3/
- https://www.nvidia.com/en-us/geforce/news/nvidia-rtx-games-engines-apps/
- https://thegameawards.com/news/the-game-awards-breaks-viewership-record

## 검증 결과 (2026-09-25)
- Python 회귀 테스트 118개, JavaScript 테스트 9개 통과.
- 1440px 데스크톱 / 390px 모바일에서 실제 AI 추천 → 직접 사양 가져오기 → FPS/DLSS 결과 일치 확인.
- React 패널 기본 닫힘, 열 때만 상세 DOM 생성, 키보드 Enter, 게임 변경 후 패널 교체, 미지원 게임 안내 확인.
- 41개 게임 이미지 실제 디코딩, 이미지 요청 실패 시 대체 아이콘, 게임 메뉴 키보드/화면 잘림 확인.
- 정상 브라우저 흐름의 JS/콘솔 오류 0, HTTP 오류 0. 가로 넘침 없음.
- 추천 부품 응답에서 누락되던 performance_ref_id를 유지하여 직접 선택의 unknown gpu / HTTP 500 문제를 수정.
- DB 트랜잭션 실패 시 이전 실측 보존, 구성/버전별 예측 분리, 미지원 GPU FG 차단 테스트 통과.
- 기존 datetime.utcnow 사용의 폐기 예정 경고는 남아 있습니다.
- 상세 브라우저 결과: `artifacts/game-ui-verification.json`.

재실행 가능한 브라우저 점검: `node tests/browser_game_details.cjs` (Playwright 필요).
`QA_URL`, `QA_OUTPUT`, `CHROME_PATH` 환경변수로 서버·결과 폴더·Chrome 경로를 지정할 수 있습니다.
