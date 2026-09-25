# 검증 상품 수집 및 저장

프로젝트 폴더에서 실행:

```powershell
python scripts/refresh_product_catalog.py --pages 12 --source all --models
```

- 다나와·컴퓨존 CPU/GPU/메인보드/RAM/SSD/파워 페이지와 CPU/GPU 모델별 검색.
- 실제 양수 판매가, 정확한 SKU 및 정상 이미지 응답을 검증한 상품만 SQL 저장.
- 실패한 조회는 이전 저장 자료를 지우거나 확인 시각을 갱신하지 않음.
- 추가 페이지부터 수집: `--start-page 7 --pages 12`.
- 다른 부품군 지정: `--types cpu,gpu,mb,ram,storage,psu,hdd,case`.
- 수집은 수동 실행이며 자동 예약 작업은 설정하지 않음.

## 저장 위치

- `data/pc.db` / `retail_products`: 판매처별 SKU, 상품명, 가격, 상품/사진 URL, 확인 시각, 사양 JSON.
- `data/pc.db` / `retail_price_history`: SKU별 관측 가격 이력.
- `data/product_images/`: URL 해시로 중복 제거한 실제 사진 파일.
- `data/retail_crawl_report.json`: 최근 실행의 수집·검증·누적 저장 수.

기존 components/prices/benchmarks 테이블과 계산식은 유지한다.
저장 상품은 catalog API와 상품 검색의 페이지에 합쳐지며, 판매처·검색어 조건을 따른다.
가격 확인 후 24시간이 지나면 이전 확인가로 표시하고 자동 추천 후보에서 제외한다.
이미지 캐시는 6시간 후 재검증한다. 파일이 없어지거나 이미지 확인에 실패하면 추천하지 않는다.
추천 계산은 알려진 성능·호환성 자료가 있는 검증 상품을 대상으로 한다.
따라서 전체 저장 SKU 수와 한 번의 추천에서 평가하는 대표 후보 수는 다르다.
