# 로딩·계산 최적화 검증 (2026-10-11)

기존 작업 내용을 유지한 상태에서 중복 분석·렌더링과 다운로드 대기 순서를 개선했다. 가격 유효기간, 상품 필터, 추천 구성, FPS 계산식과 API 응답 구조는 유지했다.

## 변경 사항

- `product_filters.py`: 제조사 정규식을 미리 컴파일하고 반복하는 패턴을 제한된 캐시에 보관한다. 필터가 없는 케이스·소프트웨어는 전체 상품 사양 분석을 생략한다.
- `game_benchmarks.py`: 평균 FPS와 1% Low에서 사용하는 두 인덱스를 함께 보관한다. 두 계산이 서로의 캐시를 지워 재생성하던 비용을 없앴다.
- `pcbuilder/fps.py`: 게임명·별칭 조회 인덱스를 재사용한다. 이름·별칭 변경과 순서 변경은 캐시 키에 반영하며, 기존 첫 일치 우선순위를 유지한다.
- `GamePicker.jsx`: 닫힌 게임 목록의 선택 버튼과 이미지를 생성하지 않는다. 초기 AAA 목록의 버튼 41개와 이미지 41개가 필요할 때 생성된다.
- `RecommendationResults.jsx`: 견적 요청이 시작되면 결과 카드 모듈을 미리 받아 API 대기 시간과 겹친다. 선행 다운로드 실패도 처리한다.
- `SearchableSelect.jsx`, `FpsCalculatorScreen.jsx`: 검색 결과와 CPU 목록을 메모하여 방향키 이동이나 결과 갱신 때 같은 필터링을 반복하지 않는다.

## 측정 결과

로컬 Python 3.9.6 환경에서 변경 직전 코드와 변경 후 코드를 별도 프로세스로 번갈아 실행했다. 각 버전 5회 중앙값이며, 전체 페이지 로딩 시간이나 외부 판매처의 실제 응답 시간은 아니다.

| 측정 대상 | 변경 전 | 변경 후 | 감소 |
| --- | ---: | ---: | ---: |
| 초기 compact 카탈로그 준비 | 755.6 ms | 651.6 ms | 13.8% |
| 고정 상품 입력의 첫 추천 계산 | 111.4 ms | 63.6 ms | 42.9% |
| 반복 FPS 응답 처리 | 1.549 ms | 0.728 ms | 53.0% |

카탈로그는 기존 로컬 데이터를 사용했고 판매처에 접속하지 않았다. 추천 비교는 임시 DB와 고정 상품 목록을 사용한 `scripts/benchmark_requests.py` 시나리오를 기준으로 했다. FPS 비교는 같은 부품·게임·해상도 입력으로 수행했다. [개별 측정값](benchmarks/2026-10-11-loading.json)을 함께 보관한다.

카탈로그 10회 응답의 SHA-256이 동일했다. 저장 상품 6,015개의 정규화 사양, 추천의 부품·총액·FPS, FPS 응답 전체를 변경 전후 비교해 동일함을 확인했다. 판매처 응답 및 네트워크 상황에 따른 체감 시간은 달라질 수 있다.

## 검증

- Python 회귀 테스트 347개 통과. 테스트는 변경 가능한 DB·카탈로그를 임시 폴더에 복사하여 실행했다.
- JavaScript 테스트 74개, 운영 빌드, 수정한 프론트엔드 파일의 Prettier 검사 통과.
- 운영 빌드의 데스크톱·모바일 브라우저 검사 통과: 9개 상품 분류, 검색·정렬·필터·페이지 이동, 추천·취소·실패 후 재시도, 화면 전환 후 입력 유지.
- 닫힌 게임 목록 미생성, 키보드 이동·Escape·포커스 복귀, API 응답 대기 중 결과 모듈 요청을 추가 검증했다.
- 실제 FPS API와 화면의 평균 FPS·1% Low 일치, 검색·키보드 선택, 재시도, 모바일 가로 넘침 없음 확인.
- HTTP gzip, 정적 파일 캐시, 폰트, 카탈로그·FPS 응답 검증 통과. 이 검사는 브라우저 검증 뒤에 실행했으므로 이미 준비된 서버 캐시를 사용한다.

재검증 명령:

```sh
python3 scripts/run_python_tests.py
npm test
npm run build
python3 scripts/benchmark_catalog.py --iterations 12
python3 scripts/benchmark_requests.py
```

별도 터미널에서 `python3 server_fixed.py --port 4000`으로 서버를 시작한 뒤:

```sh
FRONTEND_URL=http://127.0.0.1:4000 npm run test:browser
FRONTEND_URL=http://127.0.0.1:4000 node tests/fps-calculator.browser.mjs
python3 scripts/verify_http.py --url http://127.0.0.1:4000
```
