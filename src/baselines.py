#!/usr/bin/env python3

from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Dict


REPO_ROOT = Path(__file__).resolve().parents[1]
PUBLIC_GOOGLE_BASELINE_PATH = REPO_ROOT / 'data' / 'public_google_baseline.json'


def load_public_google_baseline_artifact() -> Dict[str, Any]:
    return json.loads(PUBLIC_GOOGLE_BASELINE_PATH.read_text())


def load_public_google_baseline_lines() -> Dict[str, Any]:
    return dict(load_public_google_baseline_artifact()['lines'])


def load_public_google_baseline_projection() -> Dict[str, Any]:
    artifact = load_public_google_baseline_artifact()
    return {
        'source': artifact['source'],
        'window_size': int(artifact['window_size']),
        'retained_window_additions': int(artifact['retained_window_additions']),
        **load_public_google_baseline_lines(),
    }


PUBLIC_GOOGLE_BASELINE_LINES = load_public_google_baseline_lines()
PUBLIC_GOOGLE_BASELINE_PROJECTION = load_public_google_baseline_projection()

