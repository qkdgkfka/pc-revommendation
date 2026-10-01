"""Reviewed rendering observations independent of the user's live snapshots."""
import json
from pathlib import Path
from unittest.mock import patch


def install_rendering_fixture(test):
    data = json.loads((Path(__file__).parent / 'fixtures/rendering.json').read_text())
    calibration = {key: data[key] for key in ('fg_calibration', 'upscale_calibration', 'fsr_support')}
    targets = ['rendering_calibration.calibration_data', 'graphics_estimates.calibration_data']
    if hasattr(__import__(test.__module__), 'calibration_data'):
        targets.append(test.__module__ + '.calibration_data')
    for target in targets:
        patcher = patch(target, return_value=calibration)
        patcher.start()
        test.addCleanup(patcher.stop)
