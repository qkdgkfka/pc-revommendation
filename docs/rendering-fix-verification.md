# DLSS·FSR·프레임 생성 수정 검증

2026-10-01

## 원인과 수정

운영 JSON과 SQLite 스냅샷에는 `fg_calibration`, `upscale_calibration`,
`fsr_support`가 없었습니다. RTX 5070의 사이버펑크·스타필드에는 DLSS/FG 값이
표시되지 않았고, AMD에는 기능 미확인 안내가 표시되었습니다.
게임 벤치마크 크롤러가 기존 보정 필드를 보존하지 않는 경로도 확인했습니다.

- 실제 원문 차트에서 FG 전후 22쌍과 네이티브/Quality 9쌍을 확인하고,
  `data/rendering_calibration.json`에 별도 저장했습니다. 테스트용 파일을 운영에 복사하지 않았습니다.
- 게임·해상도·GPU 순서로 업스케일링 자료를 선택합니다. 같은 리뷰의 GPU·CPU·해상도·프리셋이
  일치하는 네이티브/Quality 자료도 자동으로 연결합니다.
- FG 2×와 MFG 4×의 측정 처리 비용을 각각 사용합니다. MFG가 없는 게임은 같은 게임의
  FG 자료를 우선하며, MFG 비교에는 동일 GPU 세대의 측정 집단을 유지합니다.
- FSR 버전을 보존하고, FSR 1/2/3과 ML 프레임 생성 자료가 섞이지 않게 했습니다.
  AMD의 ML/Redstone 지원 정보만으로 FSR 3 성능을 만들어내지 않습니다.
- 그래픽 상세에 출처, 다른 게임의 보정 여부, RT 부하의 포함 여부를 표시합니다.
  기능 미지원/미확인과 측정 자료 부족을 구분합니다.
- 보정 파일 교체 시 FPS·추천 캐시를 무효화하고, 크롤러는 기존 보정 필드를 보존합니다.

## 원문 자료

모든 자료에는 원문 URL, 차트/페이지 SHA-256, 측정 조건과 수집 시각을 저장했습니다.

| 원문 | 계산에 사용하는 범위 |
| --- | --- |
| [ComputerBase DLSS 3 / FSR 3 비교](https://www.computerbase.de/artikel/grafikkarten/amd-fsr-nvidia-dlss-frame-generation-vergleich.86978/) | 4K에서 Quality 전후 평균 FPS와 FG 전후 평균 FPS. NVIDIA와 AMD 분리 |
| [ComputerBase RTX 5090 DLSS 4](https://www.computerbase.de/artikel/grafikkarten/nvidia-geforce-rtx-5090-test.91081/seite-8) | RTX 5090/4090, RT + SR/RR, FG 2×·MFG 3×/4×의 상대 처리 비용. 차트에 품질 모드가 명시되지 않아 Quality 절대 FPS로 사용하지 않음 |
| [ComputerBase RTX 5060 DLSS 4](https://www.computerbase.de/artikel/grafikkarten/nvidia-geforce-rtx-5060-test.92811/seite-6) | Doom 1080p Quality·필수 RT·낮은 텍스처의 FG/MFG 처리 비용 |
| [The FPS Review RTX 5070](https://www.thefpsreview.com/2025/11/17/overclocking-nvidia-geforce-rtx-5070/3/) | RTX 5070 기본 클럭, 9800X3D, 1440p에서 Alan Wake 2/Expedition 33의 네이티브/Quality 평균 FPS |
| [AMD 게임 지원 목록](https://www.amd.com/en/products/graphics/technologies/fidelityfx/supported-games.html) | FSR 지원 버전과 ML 지원을 분리한 게임별 목록 |

## 실제 API와 화면 결과

CPU Ryzen 7 9800X3D, RAM DDR5 32GB 6000, 1440p에서 확인했습니다.
상품 목록과 이미지·가격 조회는 테스트 자료로 격리하고, 아래 FPS 값은 실행 중인 Python API를 사용했습니다.
추천 기준과 기본 FPS 계산 정책은 변경하지 않았습니다.

| GPU / 게임 | 기본 FPS | Quality | FG 2× | MFG 4× |
| --- | ---: | ---: | ---: | ---: |
| RTX 5070 / Expedition 33 | 47.6 실측 | DLSS 74.0 실측 | 131.8 예상 | 237.1 예상 |
| RTX 5070 / Starfield | 97.4 예상 | DLSS 131.8 예상 | 180.8 예상 | 지원 미확인으로 생략 |
| RX 7800 XT / Starfield | 92.7 예상 | FSR 3 123.4 예상 | 220.2 예상 | 생략 |

RTX 3060에서는 DLSS SR만 표시하며 NVIDIA FG/MFG는 만들지 않습니다.
FSR 1 게임에 FSR 3 SR 자료만 있는 경우에는 수치를 만들지 않고 자료 부족을 안내합니다.
FG 출력 FPS와 실제 렌더링 FPS는 분리되며, 기본 FPS와 프레임당 가격에는 생성 프레임을 넣지 않습니다.

## 검증과 한계

- 운영 보정 파일의 **FG 22쌍, SR 9쌍 모두** 해당 원문 입력 조건의 평균 FPS를 재현했습니다.
- FG 2×/4× 18개 관측의 게임 단위 제외 검증에서 평균 절대 백분율 오차는
  비교 기준인 `0.9 × 배율` 계산 15.286%, 측정 처리 비용 계산 6.748%였습니다.
  이는 소규모 자료 내부 검증이며 모든 구성의 실제 정확도 보장은 아닙니다.
- Python 전체 테스트 **213개**, Node 테스트 **45개** 통과, Vite 운영 빌드 성공.
- 운영 빌드의 일반 화면 회귀와 실제 FPS API 화면 검증 통과.
  1440×1000 데스크톱과 390×844 모바일에서 콘솔/페이지 오류 및 가로 넘침 없음.
- 코드 리뷰에서 지적된 FSR 버전 누락을 실패 테스트로 재현한 뒤 수정했습니다.

다른 GPU·CPU·해상도·장면의 값에는 보정이 필요합니다. RT/RR 부하에서 측정한 FG 비용을
RT가 꺼진 구성에 적용한 경우에도 추정으로 표시합니다. 예상 범위는 휴리스틱이며
통계적 신뢰구간이 아닙니다. 게임 패치, 드라이버, VRAM 부족과 프레임 제한으로 오차가 커질 수 있습니다.

원래 DB와 벤치마크 JSON은 최종 SHA-256이 작업 시작 시와 일치합니다.
중간 브라우저 검증에서 가격 조회가 추가한 두 건은 복원했고, 최종 검증은 임시 DB 복사본으로 실행했습니다.

| 파일 | 보존 SHA-256 |
| --- | --- |
| `data/pc.db` | `e7ade6218743038d2376de228c33c371fbbe0a08ef78e715afe4ccc48efd7865` |
| `data/game_benchmarks.json` | `5872673b7189401613b2f1c4a691d1f8754444b78cfa8c42bb80a5fb50b6e2cf` |

## 재현 명령

```sh
python3 scripts/run_python_tests.py
npm test
npm run build
python3 server_fixed.py --port 4000
FRONTEND_URL=http://127.0.0.1:4000 npm run test:browser
FRONTEND_URL=http://127.0.0.1:4000 node tests/rendering.browser.mjs
```

Python 회귀 테스트는 DB 복사본을 사용합니다. FPS 화면 검증은 판매처/가격 조회를 격리하고
실제 FPS API를 사용합니다. 일반 웹 사용의 가격 조회는 기존 동작대로 DB에 확인가를 저장할 수 있습니다.
자료 갱신은 `python3 scripts/refresh_rendering_calibration.py`로 실행하며 네이티브 DB를 덮어쓰지 않습니다.
