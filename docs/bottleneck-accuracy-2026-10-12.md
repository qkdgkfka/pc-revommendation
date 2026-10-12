# CPU·GPU 병목 계산 개선과 검증

2026-10-12. 실측 구성 비교를 우선 적용하고, 비교 자료가 없는 조건에서는 낮은 신뢰도의 처리 상한 모델을 사용한다. 평균 FPS 하나만으로 CPU·GPU의 실제 실행 시간을 분리해 측정할 수는 없다. 따라서 이번 검증은 공개 실측 비교의 재현과 계산 오류 수정이며, 모든 PC의 실제 병목률에 대한 정확도 인증은 아니다.

## 자료와 적용 범위

| 참고 자료 | 반영한 내용 |
| --- | --- |
| [NVIDIA: Stuttering in Game Graphics, p.34](https://developer.nvidia.com/sites/default/files/akamai/gameworks/CN/Stuttering_Analysis_EN.pdf#page=34) | CPU·GPU가 겹쳐 실행되는 이상적인 처리 시간은 두 단계 중 긴 시간에 의해 결정된다. 동기화는 별도 비용이므로 근거 없이 고정 손실을 추가하지 않는다. |
| [NVIDIA: Graphics Pipeline Performance](https://developer.nvidia.com/gpugems/gpugems/part-v-performance-and-practicalities/chapter-28-graphics-pipeline-performance) | 특정 부품의 부하나 처리 능력을 바꾸고 결과 변화를 비교하는 진단 원칙을 적용했다. |
| [Intel GPA: CPU/GPU Bound Scenarios](https://www.intel.com/content/www/us/en/docs/gpa/cookbook/2022-4/identify-basic-gpu-cpu-bound-scenarios.html) | CPU 제한, GPU 제한, VSync 제한을 구분한다. 게임의 FPS 상한도 별도 제한으로 처리한다. |
| [Intel PresentMon 지표 정의](https://github.com/GameTechDev/PresentMon/blob/main/README-CaptureApplication.md) | CPU Busy/GPU Busy 같은 실행 시간과 FPS를 구분한다. 부품 비교 비율을 CPU 실행 시간 비중이나 사용률로 취급하지 않는다. |
| [Gupta 외: An Online Learning Methodology for Performance Modeling of Graphics Processors](https://arxiv.org/abs/2003.11740) · IEEE Transactions on Computers, 2018 | 워크로드별 측정과 프레임 시간의 중요성을 참고했다. 이 논문은 주파수 변화와 런타임 계측을 사용하는 GPU 모델이므로 그 알고리즘이나 보고된 오차를 현재 웹 계산기에 그대로 적용했다고 주장하지 않는다. |
| [TechSpot: CPU and GPU Scaling with Ryzen 7 5800X3D](https://www.techspot.com/review/3021-ryzen-5800x3d-cpu-gpu-scaling/) | 해상도·옵션별 비교와 GPU 제조사에 따른 CPU/드라이버 효과를 확인했다. GPU 교체 비교는 같은 제조사로 제한한다. 원문 차트 전체를 가져오지 않았으며, 비슷한 이름의 CPU를 동일 모델로 대체하지 않았다. |
| [ClockUpCore: Zenless Zone Zero CPU·GPU 실측](https://clockupcore.com/zenlesszonezero/) | 기존 스냅샷의 111개 행과 연결되는 전투 장면·High·렌더 스케일 1.0 표를 확인했다. 그중 6개 조건의 수치와 비교 기준을 별도 검증 fixture에 기록했다. |

위 자료의 진단 원칙을 응용한 앱 자체 구현이다. 아래 비율 공식이나 5%p 판정 여유가 논문·제조사의 공인 병목 계산식이라는 의미는 아니다.

## 계산 규칙

`bottleneck_estimation.py`가 계산과 자료 선택을 담당한다.

1. 실제 선택한 CPU·GPU·해상도·옵션의 관측값이 있어야 실측 비교를 사용한다. 출처, 날짜, 게임 버전, 장면, 옵션 이름, 메모리 조건, Native/RT/프레임 생성 조건을 맞춘다.
2. CPU 비교는 GPU를 고정하고, GPU 비교는 CPU와 GPU 제조사를 고정한다. 두 방향의 대체 구성 자료가 모두 있어야 `matched_hardware_comparison`으로 표시한다.
3. 비교 비율은 `100 × (1 − 현재 FPS / max(현재 FPS, 비교 대상 최고 FPS))`다. CPU 비교에는 해당 GPU의 CPU별 결과를, GPU 비교에는 해당 CPU의 GPU별 결과를 사용한다. 이는 최고 **테스트 구성과의 차이**이며 현재 FPS 대비 업그레이드 증가율, 사용률, 이론적 최대 성능 손실이 아니다.
4. 비교 관측값을 독립적인 CPU/GPU 처리 상한으로 표시하지 않는다. `cpu_reference_fps` / `gpu_reference_fps`로 구분하고 UI도 “비교 구성 FPS”로 표시한다. 메모리 정보가 없는 자료는 낮은 신뢰도로 남긴다.
5. 실측 비교가 불가능하면 기존 상한 추정값을 사용하되 `min(CPU 상한 FPS, GPU 상한 FPS)`로 단계 간 차이를 계산한다. 상한이 같은 경우 양쪽에 15.9% 손실을 만들어 CPU 병목으로 분류하던 오류를 제거했다. 이 경로의 상한 자체는 여전히 모델 추정이다.
6. 양쪽 비율 차이가 5%p 이하면 비교상 균형으로 분류한다. 이 값은 작은 차이에 대한 표시 기준이며 통계적 신뢰구간이 아니다. 비교 자료의 가장 빠른 CPU·GPU에서도 0%가 나올 수 있으므로, 더 빠른 미측정 하드웨어의 효과까지 부정하지 않는다.
7. 게임 상한에 도달한 경우 `frame_cap`으로 분류한다. 화면의 CPU/GPU 제한 비율은 0으로 두고 상한 적용 전 추정은 `uncapped`에 보관한다.

DLSS/FSR 추정에서도 병목 비율을 CPU Busy 시간의 비중으로 재사용하던 계산을 제거했다. 측정된 업스케일링 배율을 적용한 뒤 CPU 상한을 한 번 반영한다. 실측 비교 경로에는 독립 CPU 상한이 없으므로 같은 CPU에서 관측한 최고 GPU 결과까지 보수적으로 제한한다. 이 제한 역시 이론적 CPU 상한이 아니다.

## 실측 사례

RTX 5070, 젠레스 존 제로, 동일 전투 장면·High·렌더 스케일 1.0. 비교 범위는 앱 스냅샷에 존재하는 구성이다.

| CPU | 해상도 | 관측 FPS | CPU 비교 차이 | GPU 비교 차이 | 비교 결과 |
| --- | --- | ---: | ---: | ---: | --- |
| i5-14400F | FHD | 74 | 52.9% | 2.6% | CPU 영향 우세 |
| 9800X3D | FHD | 157 | 0.0% | 3.7% | 비교상 균형 |
| i5-14400F | QHD | 75 | 43.6% | 1.3% | CPU 영향 우세 |
| 9800X3D | QHD | 133 | 0.0% | 11.9% | GPU 영향 우세 |
| i5-14400F | 4K | 56 | 17.6% | 11.1% | CPU 영향 우세 |
| 9800X3D | 4K | 68 | 0.0% | 23.6% | GPU 영향 우세 |

기존 공식은 이 6개 조건을 모두 GPU 병목으로 분류했다. 특히 i5-14400F의 FHD 조건에서 기존 CPU 제한율은 6.8%였지만, 같은 GPU에서 CPU를 바꾼 관측값은 74 → 157 FPS였다. 새 계산은 이 테스트 구성 간 차이를 직접 반영한다. 구·신 비율의 정의가 다르므로 이를 일반적인 예측 오차 감소율로 환산하지 않는다.

## 검증 결과

- Python 회귀 검사 359개, JavaScript 검사 74개, 운영 빌드 통과.
- 원문에서 확인한 6개 사례의 평균 FPS·CPU/GPU 비교 비율·분류 재현.
- 동급 상한의 허위 손실, 게임 상한, 다른 장면·버전·메모리·렌더링 모드 혼합, GPU 제조사 차이, 잘못된 수치, 없는 GPU 해상도 지수 처리 등을 검사했다.
- 데스크톱 1440px / 모바일 390px에서 실제 API의 52.9% / 2.6% 표시, 비교 기준 라벨, 검색·재시도·탭 유지와 기존 추천 기능을 확인했다. 제거했던 1% Low 세부 출처 블록은 다시 표시하지 않는다.
- 기존 407개 FPS 관측의 조건별 홀드아웃은 404개를 예측했고 평균 FPS의 게임별 평균 MAPE 10.26%, 전체 MAPE 7.26%로 기존 값과 같다. 이것은 FPS 보간 평가이며 병목 비율의 홀드아웃 정확도가 아니다.

[검증 결과 JSON](benchmarks/2026-10-12-bottleneck.json), [원문 확인 fixture](../tests/fixtures/bottleneck_review_cases.json).

```sh
python3 scripts/validate_bottlenecks.py
python3 scripts/validate_fps_accuracy.py --mode condition
python3 scripts/run_python_tests.py
npm test
npm run build
# 로컬 서버 실행 후
FRONTEND_URL=http://127.0.0.1:4000 node tests/fps-calculator.browser.mjs
FRONTEND_URL=http://127.0.0.1:4000 npm run test:browser
```
