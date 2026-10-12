import test from 'node:test';
import assert from 'node:assert/strict';
import { execFileSync } from 'node:child_process';
import { GAME_OPTIONS } from '../src/domain/options.js';

test('offline and live game choices stay identical with at least 200 games and searchable metadata', () => {
  const live = JSON.parse(execFileSync('python3', ['-c',
    'import json; from server_catalogs import GAME_OPTIONS; print(json.dumps(GAME_OPTIONS))'],
    { cwd: new URL('..', import.meta.url), encoding: 'utf8' }));
  assert.ok(GAME_OPTIONS.length >= 200);
  const choices = rows => rows.map(({ id, label, group, category, genre, aliases, english_title, steam_app_id, image_url }) =>
    ({ id, label, group, category, genre, aliases, english_title, steam_app_id: steam_app_id ?? undefined, image_url }));
  assert.deepEqual(choices(GAME_OPTIONS), choices(live));
  assert.equal(new Set(GAME_OPTIONS.map(row => row.id)).size, GAME_OPTIONS.length);
});
