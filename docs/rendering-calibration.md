# FPS / DLSS / FSR calibration

## Native FPS
Exact game, GPU, CPU, resolution and preset observations retain their original FPS.
For GPUs missing from a game chart, interpolate log(FPS) between the two measured
GPU performance neighbors, within the same review, CPU, game version, preset and
resolution only. Never extrapolate that curve outside its measured bounds.
Existing CPU frame-time ceiling and memory-capacity adjustment still apply.

Held-out evaluation: remove all measurements of the target game + GPU, predict it
from the remainder. On 231 conditions where a same-review bracket exists, mean
absolute percentage error changed from 11.388% to 8.709%. This is an internal
cross-validation result, not a guarantee for unmeasured games or future patches.

## Super resolution
Prefer an exact, reviewed Quality observation. Otherwise select same-technology
paired native/Quality observations, prioritizing game and GPU, then resolution.
Let q = median(native_FPS / Quality_FPS), c = estimated CPU-limited fraction.
T_SR = (1000 / native_FPS) * [c + (1-c)*q].
F_SR = 1000 / T_SR, bounded by the estimated CPU ceiling (never below the native
measurement solely because the estimated ceiling is lower).

FSR has its own Quality samples and official AMD per-game support snapshot.
AMD renders FSR, NVIDIA renders DLSS. FSR 3 FG is not advertised as ML/Redstone FG.
No NVIDIA coefficients are reused as AMD measurements. Feature lists can change.

## FG / MFG
For a paired sample, k is its explicitly known frame-generation factor:
C_ms = 1000*k / observed_FG_FPS - 1000 / observed_FG_off_FPS.
This is effective processing/presentation overhead, not measured input latency.
Prediction = k*1000 / (1000/F_SR + C_ms).
Each factor uses its own measured overhead. 4x therefore does not share 2x's
render rate. Cross-resolution/hardware costs scale with output pixel count and
catalog GPU throughput; those scaling assumptions are estimates, not measured
optical-flow/tensor throughput. Cross-configuration predictions are capped at
the selected samples' median observed gain to avoid extrapolating towards k*x
at a very low base FPS. Stored fields retain both the scaled and effective costs.

22 FG pairs and 9 SR pairs are stored separately from native observations.
- ComputerBase RTX 5090: DLSS 4 SR+RR with RT, RTX 5090/4090, 4K.
- ComputerBase RTX 5060: Doom, DLSS 4 Quality, 1080p, lowest textures, mandatory RT.
- ComputerBase DLSS 3 / FSR 3 comparison: four games at 4K; only Quality average
  FPS for RX 7800 XT/FSR and RTX 4070/DLSS. Not latency or percentile charts.
- The FPS Review stock RTX 5070: Alan Wake 2 / Expedition 33 native and Quality.

RT/RR samples calibrate relative overhead; their absolute FPS is never presented
as an RT-off measurement. Rows with unspecified FG factor or quality are retained
in the source DB but no longer shown as comparable FG predictions.

Uncertainty ranges are heuristic allowances, not statistical confidence intervals.
VRAM overflow, scene/driver differences, newer FG implementations and frame caps
can invalidate extrapolation; no benchmark-verified accuracy is claimed there.

For FG leave-one-game-out validation (18 Quality 2x/4x observations), MAPE
fell from 15.286% with the old 0.9*k formula to 6.748%. These small-sample internal
results do not establish accuracy for every GPU, VRAM condition or newer FG version.

## Storage and refresh
`data/game_benchmarks.json` and SQLite `game_snapshot` metadata store paired
observations, hashes, URLs and collection times. `game_predictions` stores
calculated scenarios under `graphics-v3-native-curve` plus a calibration digest.
Run `scripts/refresh_rendering_calibration.py` to refresh reviewed FSR/DLSS3
pairs and AMD support. Previously reviewed DLSS4 pairs are retained.
Run `scripts/precompute_game_predictions.py` after refreshing and restart the
server to clear in-process data caches. Native FPS and price-per-frame use
native FPS; generated display FPS is never substituted into either calculation.
