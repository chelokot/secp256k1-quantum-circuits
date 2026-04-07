#!/usr/bin/env python3
"""Canonical modeled resource projection for the primary secp256k1 artifact.

The primary improvement over earlier revisions is that the whole-circuit totals
are no longer stored as standalone constants.  Instead, they are derived from:

- the checked-in leaf netlist,
- the checked-in retained-window scaffold,
- the checked-in lookup contract,
- a versioned backend model bundle.

The exact boundary still ends at the kickmix ISA.  Below that boundary the file
emits backend projections, not theorem-proved primitive-gate totals.
"""

from __future__ import annotations

from pathlib import Path
from typing import Any, Dict

from common import artifact_projection_path, dump_json
from derived_resources import PUBLIC_GOOGLE_BASELINE, build_derived_resource_family


def build_resource_projection(repo_root: Path) -> Dict[str, Any]:
    return build_derived_resource_family(repo_root)


def compute_improvement_vs_google(repo_root: Path) -> Dict[str, Dict[str, float]]:
    projection = build_resource_projection(repo_root)
    return projection['improvement_vs_google']


def write_resource_projection(repo_root: Path) -> Dict[str, Any]:
    projection = build_resource_projection(repo_root)
    dump_json(artifact_projection_path(repo_root / 'artifacts', 'resource_projection.json'), projection)
    return projection


__all__ = [
    'PUBLIC_GOOGLE_BASELINE',
    'build_resource_projection',
    'compute_improvement_vs_google',
    'write_resource_projection',
]
