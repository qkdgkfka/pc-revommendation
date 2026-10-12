"""Keep the offline frontend game choices in sync with the server catalog."""
import json
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from server_catalogs import GAME_OPTIONS

REQUIRED_FIELDS = ('id', 'label', 'group', 'category', 'genre')
OPTIONAL_FIELDS = ('aliases', 'english_title', 'steam_app_id', 'image_url')


def frontend_game_options(games):
    """Preserve search/art metadata without requiring it on legacy choices."""
    return [{**{key: row[key] for key in REQUIRED_FIELDS},
             **{key: row[key] for key in OPTIONAL_FIELDS if row.get(key) is not None}}
            for row in games]


if __name__ == '__main__':
    rows = frontend_game_options(GAME_OPTIONS)
    target = ROOT / 'src/domain/gameOptions.json'
    target.write_text(json.dumps(rows, ensure_ascii=False, indent=2) + '\n', encoding='utf-8')
    print(f'Synchronized {len(rows)} game choices.')
