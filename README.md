# 🖥️ PC 견적 도우미 (PC Config Server)

![Python](https://img.shields.io/badge/Python-3.9+-blue.svg)
![React](https://img.shields.io/badge/React-18.3.1-blue.svg)
![Vite](https://img.shields.io/badge/Build-Vite-purple.svg)

**PC 견적 도우미**는 사용자 예산과 목적(게이밍, 작업 등)에 맞춰 최적의 PC 부품 조합을 추천해 주는 오프라인/온라인 하이브리드 추천 서비스입니다. 다나와 및 컴퓨존의 실시간 가격과 벤치마크 데이터를 기반으로 성능 및 호환성을 자동으로 검증합니다.

---

## 🚀 시작하기

운영 화면은 Vite로 빌드하고 Python 서버에서 제공합니다. Node.js 22.12 이상과 Python 3.9 이상이 필요합니다.

```sh
npm ci
npm run build
python3 server_fixed.py --port 4000
```

브라우저에서 `http://127.0.0.1:4000`에 접속하세요. 빌드 결과가 없어도 API는 동작하며 웹 접속에는 빌드 안내가 표시됩니다. 다른 정적 파일 폴더는 `--static-dir`로 지정할 수 있습니다.

개발할 때는 두 터미널을 사용합니다.

```sh
# 터미널 1: Python API
python3 server_fixed.py --port 4000

# 터미널 2: Vite 화면과 자동 새로고침
npm run dev
```

개발 화면 `http://localhost:5173`의 `/api`와 `/health` 요청은 Python 서버로 전달됩니다. React는 18.3.1을 유지하며 버전은 npm 잠금 파일로 고정합니다.

---

## ✨ 주요 기능

### 1. 실시간 부품 검색 및 가격 연동
- **다나와·컴퓨존 연동**: 공개된 상품 목록에서 제품 옵션별 가격, 상세 페이지, 대표 이미지를 실시간으로 조회합니다.
- **캐시 및 최적화**: 동일 조건의 동시 조회를 공유하고, 제품 목록은 판매처 조회 완료 후 표시합니다. 저장된 확인가는 출처·시각을 유지하며 24시간이 지나면 이전 가격임을 명시합니다.
- **UX 편의성**: 목록, 구성품, 추천 결과 등에서 부품에 마우스를 올리면 제품 썸네일 이미지를 즉시 확인할 수 있습니다.

### 2. 스마트 PC 추천 시스템
- **목적 맞춤형 추천**: 선택한 게임, 해상도, 목표 FPS 또는 작업 용도를 분석해 최적의 조합을 제안합니다. (Steam 하드웨어 설문의 데스크톱 GPU 사용 비율을 보조 점수로 사용합니다)
- **철저한 호환성 검증**: CPU 소켓, 세대, 메인보드 칩셋, RAM 규격 호환성을 자동으로 검사합니다.
- **합리적 예산 분배**: 예산 내 구성이 불가능할 경우 예산을 살짝 초과하더라도 **가장 합리적인 최소 호환 구성**을 찾아 제시하며, LOW → MID → HIGH의 가격·성능 역전을 막아줍니다.
- **가성비(프레임당 가격) 분석**: `본체 부품 합계 ÷ 선택한 게임·해상도의 높음 옵션 예상 평균 FPS`를 계산하여 1프레임당 가격을 보여줍니다.

### 3. FPS 예측 및 벤치마크
- **실측 기반 데이터**: GamersNexus, GeekaWhat 등 신뢰할 수 있는 리뷰에서 크롤링한 실측 데이터를(`data/game_benchmarks.json`) 우선 사용합니다.
- **보정 추정치 제공**: 실측 데이터가 없는 게임이나 해상도의 경우 내장 모델을 통해 FPS를 추정하고 보정치를 표시합니다.
- **최신 기술 적용 (RT / DLSS / FSR)**: 레이 트레이싱과 업스케일링, 프레임 생성 기술을 적용했을 때의 시나리오를 비교하여 보여줍니다.

---

## 🔄 데이터 갱신 방법

크롤러를 통해 최신 부품 가격, 벤치마크, 하드웨어 통계를 갱신할 수 있습니다. 스크립트 실행을 위해 추가 의존성이 필요할 수 있습니다.

```sh
# 1. 필요 패키지 설치
python3 -m pip install -r requirements.txt

# 2. 다나와/컴퓨존 상품 카탈로그 갱신
python3 scripts/refresh_product_catalog.py --pages 5 --source all

# 3. Steam 하드웨어 통계 갱신
python3 steam_hardware.py

# 4. GPU 계층 표 및 벤치마크 갱신 (Tom's Hardware)
python3 crawl_data.py crawl

# 5. 게임별 FPS 벤치마크 갱신
python3 crawl_game_benchmarks.py

# 6. DLSS·FSR·FG 보정 자료 갱신 (네이티브 DB와 별도 저장)
python3 scripts/refresh_rendering_calibration.py
```

> [!NOTE]
> `crawl_game_benchmarks.py`는 원문 조건과 FPS 문구를 검증해 갱신하며, 페이지 구조가 변경된 경우 기존 데이터를 보존합니다. 출처, 원문 조건, 수집 시각은 스냅샷과 추천 근거에 남습니다.

---

## 🧪 테스트 (회귀 검사)

가격, FPS 검증, 호환성 로직의 안정성을 확인하기 위한 단위 테스트를 제공합니다.

```sh
python3 scripts/run_python_tests.py
npm test
npm run build
```

운영 서버를 실행한 뒤 Chrome 화면 검증은 `FRONTEND_URL=http://127.0.0.1:4000 npm run test:browser`로 실행합니다. 성능 비교와 검증 조건은 [리팩토링 검증 보고서](docs/refactor-verification.md)를 참고하세요.

> [!IMPORTANT]  
> 성능 기준 모델이 명확하지 않은 상품은 정확도를 위해 이웃 모델의 벤치마크를 임의로 끌어와 사용하지 않도록 설계되었습니다. 가격과 FPS의 검증 범위는 철저히 분리되어 동작합니다.

## 코드 구조와 유지보수

실행 진입점은 `server_fixed.py`입니다. Python 표준 라이브러리의 `ThreadingHTTPServer`가 기존 API와 `dist/`의 빌드 파일을 제공합니다. BeautifulSoup은 판매처 HTML 파싱을 보완합니다.

- `pcbuilder/`: HTTP 응답, 판매처 조회, SQLite 스냅샷, 가격 처리, 추천 후보 계산, FPS 계산을 각각 분리합니다. 기존 스크립트에서 사용하는 서버 헬퍼는 진입점에서 재노출합니다.
- `src/`: React 화면·컴포넌트, 상태 저장소, 요청 처리, 제품 규격·필터·성능 계산을 모듈로 관리합니다. 부품 선택은 상태 저장소에 보관하며 숨겨진 HTML 선택 요소에 의존하지 않습니다.
- `product_metadata.py`, `product_filters.py`, `component_compatibility.py`: 정확한 모델/사양 해석과 필터, 부품 호환성을 처리합니다.
- `product_parsing.py`, `retailer_parsing.py`, `market_catalog.py`, `market_search.py`, `product_images.py`: 공통 파싱, 저장된 확인가, 안정적인 검색 커서와 페이지네이션, 제한된 이미지 프록시를 담당합니다.
- `game_benchmarks.py`, `graphics_estimates.py`, `rendering_calibration.py`: 실측 자료와 명시적인 보정 추정치를 구분합니다.
- `tests/`: Python 회귀 검사, ES 모듈 기반 Node 검사, 화면 동작 검증을 제공합니다. Python 테스트 실행 도구는 DB와 시장 카탈로그를 임시 폴더에 복사하여 사용합니다.

화면은 직접 사양 선택으로 시작합니다. 다른 화면과 그래픽 상세는 필요할 때 로드하고, 화면 전환 후에도 입력과 선택 부품을 유지합니다. 새로운 검색 조건에는 완료된 판매처 조회 결과를 표시하며, 취소된 요청이나 이전 응답이 최신 상태를 덮어쓰지 않도록 처리합니다.

정적 빌드 자산은 해시 파일명과 gzip 압축을 사용합니다. HTML은 재검증하며, 가격·추천 응답은 브라우저에 저장하지 않습니다. 서버 내부의 짧은 조회 캐시와 기존 24시간 가격 유효기간은 별도로 적용하고 확인 시각과 오래된 가격 표시를 유지합니다.

제품의 `image_url`은 이미지 주소이며 구매 주소와 별개입니다. 기존 API 호환성을 위해
구매 주소의 `url`/`source_url` 별칭과 RAM의 DDR 세대를 뜻하는 `type`을 유지합니다.
부품 종류는 `component_type`/`part_type`으로 전달되며, 프론트엔드 경계에서 정규화됩니다.

현재 페이지에는 제품 가져오기 UI나 `/api/import/*` 라우트가 없습니다. 기존에 저장한 가져오기 상품을 읽는 카탈로그 경로는 유지됩니다.

`train_model.py`는 신경망 학습 대신 보정 JSON을 생성하는 독립 도구입니다.
`artifacts/`의 과거 모델 파일은 현재 서버가 로드하지 않지만, 출처 확인 전까지 보존합니다.
운영에는 `data/`의 기준 데이터와 `dist/` 빌드 파일이 필요합니다. 서체와 게임 아이콘은 빌드에 포함됩니다.
`.gjc/`, `node_modules/`, 로그, Python 캐시, 실행 중 생성되는 시장 캐시는 Git 추적 대상이 아닙니다.

직접 선택의 상세 조건은 같은 항목 내 OR, 항목 간 AND로 적용됩니다. 검색어 없이
필터를 선택하면 판매처 조건을 유지하면서 저장된 전체 카탈로그도 함께 검색합니다.

직접 선택에서는 CPU와 메인보드의 소켓을 정규화해 비교합니다. 소켓이 다르면
내 부품 구성 상단에 제품명과 소켓을 표시하고, 정보가 없으면 확인 필요로 안내합니다.
CPU를 변경해도 선택한 메인보드를 유지하며 다른 소켓의 제품도 계속 검색할 수 있습니다.
SSD 속도는 판매처에 기재된 순차 읽기·쓰기 MB/s이며, 누락된 사양은 `미확인`으로
분류합니다. M.2 폼팩터와 SATA/NVMe 인터페이스, 80 PLUS와 다른 인증은 구분합니다.


HTTP의 FPS 계산은 예측 결과를 DB에 쓰지 않습니다. 저장이 필요하면 `python3 scripts/precompute_game_predictions.py`를 별도로 실행하세요. 현재 실측·보정 자료에 없는 그래픽 옵션은 임의 수치로 생성하지 않습니다. 테스트의 검증된 보정 자료는 운영 데이터와 별도로 `tests/fixtures/`에 보관합니다.

DLSS·FSR·FG 계산은 `data/rendering_calibration.json`의 원문 전후 측정값을 사용합니다.
각 배율의 처리 비용과 CPU 제한을 반영하고, 실측과 다른 게임·구성의 예측은 상세 화면에 표시합니다.
보정 방식과 자료의 한계는 [계산 기준](docs/rendering-calibration.md),
이번 수정의 결과는 [DLSS·FSR·FG 검증 보고서](docs/rendering-fix-verification.md)를 참고하세요.
운영 서버에서 실제 FPS API를 연결한 화면 검증은
`FRONTEND_URL=http://127.0.0.1:4000 node tests/rendering.browser.mjs`로 실행합니다.
