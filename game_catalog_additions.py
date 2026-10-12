"""Additional popular/benchmark games, with explicitly unmeasured workload priors.

Selection sources are not FPS evidence. No entry here creates a benchmark row,
native RT result, graphics-feature support claim, or measured 1% Low.
"""

SELECTION_SOURCES = {
    'steam': 'https://store.steampowered.com/charts/mostplayed',
    'gpu_review': 'https://www.techspot.com/review/2947-nvidia-geforce-rtx-5080/',
    'kcd_review': 'https://www.techspot.com/review/2952-kingdom-come-deliverance-2-benchmark/',
    'intel_suite': 'https://download.intel.com/newsroom/2024/client-computing/Intel-Core-Ultra-Series-2-Media-Deck.pdf',
    'riot': 'https://www.leagueoflegends.com/en-sg/how-to-play/',
}

# Store IDs also drive the existing artwork collector; aliases refer to the
# exact PC edition (GTA V Legacy is deliberately distinct from Enhanced).
_GAMES = [
    ('rust', '러스트', 'Rust', 'openworld', 'openworld', 252490, 'steam', ['러스트', 'rust']),
    ('palworld', '팰월드', 'Palworld', 'openworld', 'openworld', 1623730, 'steam', ['팔월드']),
    ('helldivers2', '헬다이버즈 2', 'HELLDIVERS 2', 'fps', 'fps', 553850, 'steam', ['헬다이버2', '헬다이버즈2']),
    ('diablo4', '디아블로 IV', 'Diablo IV', 'rpg', 'game', 2344520, 'steam', ['디아블로4', '디아4', 'Diablo 4']),
    ('path_of_exile2', '패스 오브 엑자일 2', 'Path of Exile 2', 'rpg', 'game', 2694490, 'steam', ['POE2', 'POE 2', '패오엑2']),
    ('monster_hunter_wilds', '몬스터 헌터 와일즈', 'Monster Hunter Wilds', 'rpg', 'openworld', 2246340, 'steam', ['몬헌 와일즈', '몬헌와일즈']),
    ('valheim', '발헤임', 'Valheim', 'openworld', 'openworld', 892970, 'steam', []),
    ('warframe', '워프레임', 'Warframe', 'fps', 'fps', 230410, 'steam', []),
    ('gta5_legacy', 'GTA V 레거시', 'Grand Theft Auto V Legacy', 'openworld', 'openworld', 271590, 'steam', ['GTA V', 'GTA5', 'GTA 5 Legacy']),
    ('total_war_warhammer3', '토탈 워: 워해머 III', 'Total War: WARHAMMER III', 'sim', 'game', 1142710, 'steam', ['토탈워 워해머3', '워해머3', 'Total War Warhammer 3']),
    ('civilization6', '시드 마이어의 문명 VI', "Sid Meier's Civilization VI", 'sim', 'game', 289070, 'steam', ['문명6', '문명 6', 'Civ6', 'Civilization 6']),
    ('destiny2', '데스티니 가디언즈', 'Destiny 2', 'fps', 'fps', 1085660, 'steam', ['데스티니2', '데스티니 2']),
    ('stalker2', '스토커 2: 하트 오브 초르노빌', 'S.T.A.L.K.E.R. 2: Heart of Chornobyl', 'openworld', 'openworld', 1643320, 'gpu_review', ['스토커2', 'STALKER 2', 'Stalker2']),
    ('delta_force', '델타 포스', 'Delta Force', 'fps', 'fps', 2507950, 'gpu_review', ['델타포스']),
    ('jedi_survivor', '스타워즈 제다이: 서바이버', 'STAR WARS Jedi: Survivor', 'aaa', 'aaa', 1774580, 'gpu_review', ['제다이 서바이버', 'Jedi Survivor']),
    ('plague_tale_requiem', '플래그 테일: 레퀴엠', 'A Plague Tale: Requiem', 'aaa', 'aaa', 1182900, 'gpu_review', ['플래그테일 레퀴엠', 'Plague Tale Requiem']),
    ('dragon_age_veilguard', '드래곤 에이지: 베일가드', 'Dragon Age: The Veilguard', 'rpg', 'aaa', 1845910, 'gpu_review', ['드래곤에이지 베일가드', 'Dragon Age Veilguard']),
    ('war_thunder', '워 썬더', 'War Thunder', 'sim', 'fps', 236390, 'gpu_review', ['워썬더']),
    ('spider_man_remastered', '마블 스파이더맨 리마스터', "Marvel's Spider-Man Remastered", 'openworld', 'openworld', 1817070, 'gpu_review', ['스파이더맨 리마스터', 'Spider-Man Remastered']),
    ('kingdom_come_deliverance2', '킹덤 컴: 딜리버런스 II', 'Kingdom Come: Deliverance II', 'rpg', 'openworld', 1771300, 'kcd_review', ['킹덤컴2', '킹덤 컴 2', 'KCD2', 'Kingdom Come Deliverance 2']),
    ('league_of_legends', '리그 오브 레전드', 'League of Legends', 'moba', 'fps', None, 'riot', ['롤', 'LoL', '리그오브레전드']),
    ('forza_horizon5', '포르자 호라이즌 5', 'Forza Horizon 5', 'sim', 'game', 1551360, 'intel_suite', ['포르자5', '포르자 호라이즌5', 'FH5']),
    ('shadow_of_tomb_raider', '섀도 오브 더 툼 레이더', 'Shadow of the Tomb Raider', 'aaa', 'aaa', 750920, 'intel_suite', ['섀도 오브 툼레이더', '쉐도우 오브 툼레이더', 'SOTTR']),
    ('control', '컨트롤', 'Control Ultimate Edition', 'aaa', 'aaa', 870780, 'intel_suite', ['Control']),
]

GROUPS = {'fps': 'FPS / 경쟁형', 'aaa': 'AAA / GOTY', 'openworld': '오픈월드', 'game': '일반 게임'}
ADDITIONAL_GAMES = [dict(id=key, label=label, english_title=title, genre=genre, category=category,
                         group=GROUPS[category], steam_app_id=app_id, aliases=[title, *aliases],
                         selection_source=SELECTION_SOURCES[source])
                    for key, label, title, genre, category, app_id, source, aliases in _GAMES]


def _prior(scale, cpu_weight, cpu_cap, low1, ram_hungry=False):
    return dict(scale=dict(zip(('1080', '1440', '2160'), scale)), cpu_weight=cpu_weight,
                cpu_cap=dict(zip(('1080', '1440', '2160'), cpu_cap)), low1=low1,
                ram_hungry=ram_hungry, model_basis='unmeasured_workload_prior')


# Explicit heuristic priors: CPU-heavy simulations/multiplayer worlds differ
# from GPU-heavy single-player titles. They are not benchmark-derived numbers;
# the shared engine reports low confidence/±40% allowance without observations.
ADDITIONAL_FPS_PROFILES = {
    'rust': _prior((1.02, .94, .80), .52, (225, 205, 175), .66, True),
    'palworld': _prior((.86, .80, .68), .36, (205, 180, 150), .70, True),
    'helldivers2': _prior((.92, .85, .72), .46, (190, 170, 145), .72, True),
    'diablo4': _prior((1.46, 1.35, 1.14), .28, (300, 270, 225), .78, True),
    'path_of_exile2': _prior((.95, .88, .74), .46, (205, 185, 155), .66, True),
    'monster_hunter_wilds': _prior((.52, .48, .40), .50, (125, 115, 95), .65, True),
    'valheim': _prior((1.08, .99, .85), .50, (235, 210, 175), .68, True),
    'warframe': _prior((2.18, 2.02, 1.70), .26, (430, 385, 325), .82),
    'gta5_legacy': _prior((1.65, 1.49, 1.22), .42, (230, 210, 180), .76),
    'total_war_warhammer3': _prior((.90, .80, .66), .56, (155, 140, 118), .70, True),
    'civilization6': _prior((1.70, 1.56, 1.32), .58, (235, 210, 175), .74),
    'destiny2': _prior((1.72, 1.58, 1.30), .40, (285, 255, 210), .78),
    'stalker2': _prior((.52, .49, .43), .52, (145, 128, 108), .64, True),
    'delta_force': _prior((1.72, 1.59, 1.32), .44, (340, 300, 245), .76, True),
    'jedi_survivor': _prior((.80, .74, .64), .42, (170, 155, 130), .67, True),
    'plague_tale_requiem': _prior((.77, .72, .62), .24, (225, 200, 165), .74, True),
    'dragon_age_veilguard': _prior((.69, .63, .52), .30, (200, 175, 145), .73, True),
    'war_thunder': _prior((2.32, 2.18, 1.88), .36, (430, 380, 320), .82),
    'spider_man_remastered': _prior((1.18, 1.08, .91), .44, (250, 220, 185), .75, True),
    'kingdom_come_deliverance2': _prior((.84, .77, .63), .46, (210, 185, 150), .70, True),
    'league_of_legends': _prior((3.10, 2.86, 2.40), .62, (540, 480, 400), .80),
    'forza_horizon5': _prior((1.34, 1.22, 1.02), .28, (300, 265, 220), .82),
    'shadow_of_tomb_raider': _prior((1.49, 1.35, 1.12), .30, (320, 285, 235), .80),
    'control': _prior((1.08, 1.00, .86), .18, (280, 250, 210), .77),
}
