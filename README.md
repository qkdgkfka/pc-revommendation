# 🖥️ PC 견적 도우미 (PC Config Server)

![Python](https://img.shields.io/badge/Python-3.8+-blue.svg)
![Vanilla JS](https://img.shields.io/badge/JavaScript-Vanilla-yellow.svg)

**PC 견적 도우미**는 사용자 예산과 목적(게이밍, 작업 등)에 맞춰 최적의 PC 부품 조합을 추천해 주는 오프라인/온라인 하이브리드 추천 서비스입니다. 다나와 및 컴퓨존의 실시간 가격과 벤치마크 데이터를 기반으로 성능 및 호환성을 자동으로 검증합니다.

---

## 🚀 시작하기

별도의 의존성 없이 Python 표준 라이브러리만으로도 기본 서버를 실행할 수 있습니다.

```sh
python3 server_fixed.py --port 4000
```

실행 후 브라우저에서 `http://127.0.0.1:4000`에 접속하여 서비스를 이용하세요.

---

## ✨ 주요 기능

### 1. 실시간 부품 검색 및 가격 연동
- **다나와·컴퓨존 연동**: 공개된 상품 목록에서 제품 옵션별 가격, 상세 페이지, 대표 이미지를 실시간으로 조회합니다.
- **캐시 및 최적화**: 조회한 상품은 `data/product_catalog.json` 및 `data/market_cache.json`에 보관되며, 24시간 이내의 데이터를 우선 사용해 API 호출 병목을 줄입니다. 24시간 초과 시 이전 가격임을 명시합니다.
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
```

> [!NOTE]
> `crawl_game_benchmarks.py`는 원문 조건과 FPS 문구를 검증해 갱신하며, 페이지 구조가 변경된 경우 기존 데이터를 보존합니다. 출처, 원문 조건, 수집 시각은 스냅샷과 추천 근거에 남습니다.

---

## 🧪 테스트 (회귀 검사)

가격, FPS 검증, 호환성 로직의 안정성을 확인하기 위한 단위 테스트를 제공합니다.

```sh
python3 -m unittest discover -s tests -v
node --test tests/test_builder_ui.js
```

> [!IMPORTANT]  
> 성능 기준 모델이 명확하지 않은 상품은 정확도를 위해 이웃 모델의 벤치마크를 임의로 끌어와 사용하지 않도록 설계되었습니다. 가격과 FPS의 검증 범위는 철저히 분리되어 동작합니다.

## 코드 구조와 유지보수

실행 진입점은 `server_fixed.py` 하나입니다. Python 표준 라이브러리의
`ThreadingHTTPServer`가 API와 정적 파일을 함께 제공하며, 별도의 프론트엔드 빌드는 없습니다.
`requirements.txt`의 BeautifulSoup은 HTML 파싱을 보완합니다.

| 파일 | 역할 |
| --- | --- |
| `server_fixed.py` | HTTP 라우팅, 판매처 연동, 추천 및 가격/FPS 처리 |
| `server_catalogs.py` | 기준 부품, 게임, 성능 카탈로그 |
| `product_metadata.py` | 제품명, 제조사, 정확한 모델 식별, RAM/SSD 등 규격 해석 |
| `retailer_parsing.py` | 서버와 오프라인 크롤러가 공유하는 다나와 목록/가격 추출 |
| `market_catalog.py` | 저장 상품, 가격 유효기간, 파일 변경 시 갱신되는 검증 캐시 |
| `product_images.py` | 외부 이미지 검증과 제한된 이미지 프록시/캐시 |
| `component_compatibility.py` | CPU·메인보드·RAM 호환성 |
| `game_benchmarks.py`, `graphics_estimates.py` | 게임 실측 자료 및 그래픽 옵션 추정 |
| `app.js`, `app_utils.js`, `app_data.js` | 화면 상태/이벤트, 부품 선택/렌더링, 오프라인 기본 데이터 |
| `product_images.js` | 추천과 직접 선택에서 공유하는 이미지·미리보기·오류 대체 표시 |
| `gpu_selector.js`, `vendor/react/` | GPU 모델 선택에만 사용하는 React 컴포넌트와 런타임 |
| `tests/` | Python 회귀 검사 및 Node 기반 프론트엔드 로직 검사 |

제품의 `image_url`은 이미지 주소이며 구매 주소와 별개입니다. 기존 API 호환성을 위해
구매 주소의 `url`/`source_url` 별칭과 RAM의 DDR 세대를 뜻하는 `type`을 유지합니다.
부품 종류는 `component_type`/`part_type`으로 전달되며, 프론트엔드 경계에서 정규화됩니다.

`product_import.py`와 서버의 가져오기 헬퍼는 보존되어 있지만, 현재 페이지에는
제품 가져오기 UI나 `/api/import/*` 라우트가 없습니다. 저장된 가져오기 상품을 읽는
카탈로그 경로는 유지됩니다.

`train_model.py`는 신경망 학습 대신 보정 JSON을 생성하는 독립 도구입니다.
`artifacts/`의 과거 모델 파일은 현재 서버가 로드하지 않지만, 출처 확인 전까지 보존합니다.
`data/`의 기준 데이터와 `vendor/react/`는 배포에 포함해야 합니다.
`.gjc/`, `node_modules/`, 로그, Python 캐시, 실행 중 생성되는 시장 캐시는 Git 추적 대상이 아닙니다.
