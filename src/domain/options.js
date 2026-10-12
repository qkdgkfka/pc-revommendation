import gameOptions from "./gameOptions.json" with { type: "json" };

export const GAME_CATEGORIES = [
  { id: "fps", label: "FPS / 경쟁" },
  { id: "openworld", label: "오픈월드" },
  { id: "aaa", label: "AAA 게임" },
  { id: "game", label: "일반 게임" },
];

export const GAME_OPTIONS = gameOptions;

export const WORK_PROFILES = {
  video_1080p: {
    name: "FHD 영상 편집",
    group: "영상 편집",
    w: { gpu: 0.22, cpu: 0.42, ram: 0.22, storage: 0.14 },
    req: { gpu: 35, cpu: 45, ramGb: 16, storageTb: 1 },
  },
  video_4k: {
    name: "4K 영상 편집",
    group: "영상 편집",
    w: { gpu: 0.32, cpu: 0.34, ram: 0.24, storage: 0.1 },
    req: { gpu: 58, cpu: 64, ramGb: 32, storageTb: 2 },
  },
  video_8k: {
    name: "8K/RAW 영상 편집",
    group: "영상 편집",
    w: { gpu: 0.36, cpu: 0.34, ram: 0.24, storage: 0.06 },
    req: { gpu: 78, cpu: 82, ramGb: 64, storageTb: 2 },
  },
  motion_graphics: {
    name: "모션그래픽/After Effects",
    group: "영상 편집",
    w: { gpu: 0.28, cpu: 0.38, ram: 0.28, storage: 0.06 },
    req: { gpu: 55, cpu: 68, ramGb: 32, storageTb: 1 },
  },
  graphic_design: {
    name: "그래픽 디자인",
    group: "그래픽",
    w: { gpu: 0.24, cpu: 0.34, ram: 0.32, storage: 0.1 },
    req: { gpu: 35, cpu: 45, ramGb: 16, storageTb: 1 },
  },
  large_canvas_design: {
    name: "대형 캔버스/인쇄 디자인",
    group: "그래픽",
    w: { gpu: 0.24, cpu: 0.3, ram: 0.38, storage: 0.08 },
    req: { gpu: 42, cpu: 55, ramGb: 32, storageTb: 1 },
  },
  modeling_3d: {
    name: "3D 모델링/뷰포트",
    group: "3D 모델링",
    w: { gpu: 0.46, cpu: 0.28, ram: 0.18, storage: 0.08 },
    req: { gpu: 55, cpu: 55, ramGb: 32, storageTb: 1 },
  },
  rendering_3d: {
    name: "3D 렌더링/GPU 렌더",
    group: "3D 모델링",
    w: { gpu: 0.58, cpu: 0.22, ram: 0.16, storage: 0.04 },
    req: { gpu: 74, cpu: 62, ramGb: 32, storageTb: 1 },
  },
  cad_archviz: {
    name: "CAD/건축 시각화",
    group: "3D 모델링",
    w: { gpu: 0.38, cpu: 0.34, ram: 0.22, storage: 0.06 },
    req: { gpu: 55, cpu: 62, ramGb: 32, storageTb: 1 },
  },
  music_prod: {
    name: "음악 제작/DAW",
    group: "음악/개발",
    w: { gpu: 0.04, cpu: 0.58, ram: 0.32, storage: 0.06 },
    req: { gpu: 15, cpu: 60, ramGb: 32, storageTb: 1 },
  },
  coding: {
    name: "코딩/개발",
    group: "음악/개발",
    w: { gpu: 0.05, cpu: 0.52, ram: 0.34, storage: 0.09 },
    req: { gpu: 15, cpu: 55, ramGb: 32, storageTb: 1 },
  },
  ai_dev: {
    name: "AI 개발/로컬 추론",
    group: "AI/개발",
    w: { gpu: 0.62, cpu: 0.18, ram: 0.16, storage: 0.04 },
    req: { gpu: 72, cpu: 55, ramGb: 32, storageTb: 1 },
  },
};
