# 파워 추천 기준

2026-10-12 적용. 구현: `power_requirements.py`.

## 필수 조건

- 자동 견적은 **80 PLUS Gold / Platinum / Titanium**만 선택한다. 인증 불명,
  Standard, Bronze, Silver는 예산과 관계없이 제외한다.
- 상품명·상세 사양의 `80 PLUS` 인증을 확인한다. 단순 Gold 상품명/색상이나
  Cybenetics Gold를 80 PLUS Gold로 취급하지 않는다. 서로 다른 등급이 표시되면
  보수적으로 낮은 등급을 따른다. 기본 카탈로그에는 인증 등급을 명시한다.
- 판매 상품을 용량별로 압축하기 **전에** 인증을 필터링한다. 저렴한 Bronze 두
  제품 때문에 같은 용량의 Gold 제품이 추천 후보에서 사라지지 않는다.
- 조건을 만족하는 제품이 없으면 해당 조합을 제외한다. 낮은 등급이나 부족한
  출력으로 대체하지 않는다. 수동 부품 검색은 기존 상품을 계속 제공한다.

## 용량 계산

`50W 단위 올림(max(GPU별 권장 시스템 파워, (CPU 최대 전력 + GPU 보드 전력 + 100W) / 0.8))`

100W는 보드·메모리·저장장치·팬 등 주변 부품을 위한 설계 여유다. 0.8은 정격
DC 출력의 20%를 남기기 위한 정책이며, 인증 효율이나 실측 소비전력을 뜻하지
않는다. PSU 자체 효율을 적용해 정격 출력을 낮추지 않는다.

CPU는 검증한 Intel 최대 터보 전력과 명시적인 `max_power_watt`,
`max_turbo_power`, `ppt` 중 큰 값을 사용한다. 알려진 최대 전력이 없으면 AMD는
TDP × 1.4, 그 외는 TDP × 2.1 및 보수적인 155W/253W 하한을 적용한다. 이 대체값은
제조사 스펙이 아닌 추천 정책이다. 기본 설정의 일반 데스크톱을 대상으로 하며
무제한 전력 해제나 오버클럭을 보장하지 않는다.

GPU는 카탈로그 소비전력, 상품별 명시적인 보드 전력, 상세 사양의 소비전력 중
큰 값을 사용한다. GPU 제조사 권장 시스템 용량 및 상품별 더 높은 권장 용량을
하한으로 적용한다. 판매처 상품 ID가 달라도 `performance_ref_id`를 통해 원래
CPU/GPU 기준을 유지한다.

인증 등급은 효율 분류다. 보호회로, 커넥터 수, 케이블 호환성, 과도 부하 대응을
개별적으로 검증했다는 의미는 아니다. 현재 변경은 인증 및 출력 적합성에 한정한다.

## 근거

- [NVIDIA 공식 GPU 비교표](https://www.nvidia.com/en-us/geforce/graphics-cards/compare/):
  RTX 30/40/50 시리즈의 Required System Power. 5060 Ti 600W,
  5070 650W, 5070 Ti 750W, 5080 850W, 5090 1000W 등.
- [ASUS CPU/GPU별 권장 파워 표](https://dlcdnets.asus.com/pub/ASUS/Accessory/Power_Supply/Manual/RECOMMENDED_PSU_TABLE.pdf):
  Radeon 기본 하한 참고. RX 6600/6650 XT 550W, 6750 XT 650W, 7600 550W,
  7900 XT 750W, 7900 XTX 850W, 9070 650W, 9070 XT 750W.
  7900 GRE는 표의 Ryzen 7 / i7 기준 750W를 보수적 하한으로 사용한다.
- [AMD 공식 GPU 사양](https://www.amd.com/es/products/specifications/graphics.html):
  RX 7700 XT 및 7800 XT는 AMD의 700W 하한을 유지한다.
- [Intel 터보 전력 설명](https://www.intel.com/content/www/us/en/support/articles/000055611/processors.html):
  기본 TDP만으로 최대 소비전력을 판단하지 않는다.
- [Intel K 시리즈 공식 표](https://www.intel.com/content/www/us/en/gaming/overclocking-intel-processors.html):
  i9-14900K / i7-14700K 253W, i5-14600K/KF 181W.
- [Intel i7 사양 안내](https://www.intel.com/content/www/us/en/support/articles/000006778/processors.html):
  i7-13700K 253W.
- [Intel 12세대 표](https://cdrdv2-public.intel.com/754040/CPM-21-02_12thGen_QuickRefGuide_P2_v2.pdf):
  i7-12700KF 190W.
- [Intel i5-12400F](https://www.intel.la/content/www/xl/es/products/sku/134587/intel-core-i512400f-processor-18m-cache-up-to-4-40-ghz/specifications.html): 117W.
- [Intel i5-14400F 비교표](https://www.intel.com/content/www/us/en/products/compare.html?productIds=236853%2C236777%2C236786%2C236854): 148W.
- [Intel Core Ultra Series 2](https://www.intel.com/content/www/us/en/products/docs/processors/core-ultra/core-ultra-desktop-processors-series-2-brief.html):
  265K 250W, 245K 159W.

예: Ryzen 5 7600 + RTX 5070 → 최소 650W, i9-14900K + RTX 5080 → 최소
900W, i9-14900K + RTX 5090 → 최소 1200W. 실제 추천은 이 용량 이상인 Gold 이상
판매 상품 중에서 고르므로 카탈로그 구성에 따라 한 단계 큰 제품이 선택될 수 있다.
