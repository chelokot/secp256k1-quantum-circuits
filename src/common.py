#!/usr/bin/env python3
"""Common arithmetic and hashing helpers for the secp256k1 audit repository.

The intent is clarity over cleverness.  Everything here is written in straight
Python with no third-party dependencies so that the verification path is easy to
inspect and rerun.
"""

from __future__ import annotations

import csv
import hashlib
import json
from pathlib import Path
from typing import Any, Dict, Iterable, Iterator, List, Optional, Tuple

SECP_P = 0xFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFEFFFFFC2F
SECP_N = 0xFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFEBAAEDCE6AF48A03BBFD25E8CD0364141
SECP_B = 7
SECP_B3 = 21
SECP_G = (
    55066263022277343669578718895168534326250603453777594175500187360389116729240,
    32670510020758816978083085130507043184471273380659243275938904335757337482424,
)

PointAffine = Optional[Tuple[int, int]]
PointProj = Tuple[int, int, int]


def sha256_bytes(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def sha256_path(path: Path) -> str:
    return sha256_bytes(path.read_bytes())


def load_json(path: Path) -> Any:
    return json.loads(path.read_text())


def dump_json(path: Path, obj: Any) -> None:
    path.write_text(json.dumps(obj, indent=2, sort_keys=False))


def affine_to_proj(point: PointAffine, p: int) -> PointProj:
    if point is None:
        return (0, 1, 0)
    x, y = point
    return (x % p, y % p, 1)


def proj_to_affine(point: PointProj, p: int) -> PointAffine:
    x, y, z = [v % p for v in point]
    if z == 0:
        return None
    zinv = pow(z, -1, p)
    return ((x * zinv) % p, (y * zinv) % p)


def neg_affine(point: PointAffine, p: int) -> PointAffine:
    if point is None:
        return None
    x, y = point
    return (x, (-y) % p)


def add_affine(pa: PointAffine, qa: PointAffine, p: int, b: int) -> PointAffine:
    """Affine group law for short Weierstrass curves with a = 0.

    The curve parameter `b` is carried for readability and symmetry with the rest
    of the code, even though the standard affine formulas here do not use it
    explicitly after the points have already been assumed to lie on the curve.
    """
    if pa is None:
        return qa
    if qa is None:
        return pa
    x1, y1 = pa
    x2, y2 = qa
    if x1 == x2:
        if (y1 + y2) % p == 0:
            return None
        lam = (3 * x1 * x1) * pow((2 * y1) % p, -1, p)
    else:
        lam = (y2 - y1) * pow((x2 - x1) % p, -1, p)
    lam %= p
    x3 = (lam * lam - x1 - x2) % p
    y3 = (lam * (x1 - x3) - y1) % p
    return (x3, y3)


def mul_affine(k: int, point: PointAffine, p: int, b: int, order: int | None = None) -> PointAffine:
    if order is not None:
        k %= order
    if point is None or k == 0:
        return None
    if k < 0:
        return mul_affine(-k, neg_affine(point, p), p, b, order=None)
    result = None
    addend = point
    while k:
        if k & 1:
            result = add_affine(result, addend, p, b)
        addend = add_affine(addend, addend, p, b)
        k >>= 1
    return result


def precompute_window_tables(base: PointAffine, p: int, b: int, width: int = 8, bits: int = 256) -> List[List[PointAffine]]:
    chunks = (bits + width - 1) // width
    base_pos: List[PointAffine] = [None] * chunks
    base_pos[0] = base
    for pos in range(1, chunks):
        q = base_pos[pos - 1]
        for _ in range(width):
            q = add_affine(q, q, p, b)
        base_pos[pos] = q
    tables: List[List[PointAffine]] = []
    for pos in range(chunks):
        arr: List[PointAffine] = [None] * (1 << width)
        arr[0] = None
        arr[1] = base_pos[pos]
        for digit in range(2, 1 << width):
            arr[digit] = add_affine(arr[digit - 1], base_pos[pos], p, b)
        tables.append(arr)
    return tables


def mul_fixed_window(k: int, tables: List[List[PointAffine]], p: int, b: int, width: int = 8, order: int | None = None) -> PointAffine:
    if order is not None:
        k %= order
    if k == 0:
        return None
    result = None
    mask = (1 << width) - 1
    pos = 0
    while k:
        digit = k & mask
        if digit:
            result = add_affine(result, tables[pos][digit], p, b)
        k >>= width
        pos += 1
    return result


def complete_projective_add_a0(pj: PointProj, qj: PointProj, p: int, b: int) -> PointProj:
    """Independent complete projective reference path for a = 0 curves.

    This mirrors the compact complete formulas used as the independent check in
    the optimized verifier.  It is not the same instruction schedule as the
    optimized leaf, which makes it useful as a cross-check.
    """
    x1, y1, z1 = [v % p for v in pj]
    x2, y2, z2 = [v % p for v in qj]
    b3 = (3 * b) % p
    t0 = (x1 * x2) % p
    t1 = (y1 * y2) % p
    t2 = (z1 * z2) % p
    t3 = (x1 + y1) % p
    t4 = (x2 + y2) % p
    t3 = (t3 * t4) % p
    t4 = (t0 + t1) % p
    t3 = (t3 - t4) % p
    t4 = (y1 + z1) % p
    x3 = (y2 + z2) % p
    t4 = (t4 * x3) % p
    x3 = (t1 + t2) % p
    t4 = (t4 - x3) % p
    x3 = (x1 + z1) % p
    y3 = (x2 + z2) % p
    x3 = (x3 * y3) % p
    y3 = (t0 + t2) % p
    y3 = (x3 - y3) % p
    x3 = (t0 + t0) % p
    t0 = (x3 + t0) % p
    t2 = (b3 * t2) % p
    z3 = (t1 + t2) % p
    t1 = (t1 - t2) % p
    y3 = (b3 * y3) % p
    x3 = (t4 * y3) % p
    t2 = (t3 * t1) % p
    x3 = (t2 - x3) % p
    y3 = (y3 * t0) % p
    t1 = (t1 * z3) % p
    y3 = (t1 + y3) % p
    t0 = (t0 * t3) % p
    z3 = (z3 * t4) % p
    z3 = (z3 + t0) % p
    return (x3, y3, z3)


def deterministic_scalars(seed: bytes, count: int, modulus: int) -> List[int]:
    """Deterministic nonzero scalar stream used by the optimized audit.

    The optimized package intentionally derives its audit cases from the netlist
    hash, so changing the machine-readable netlist changes the challenge set.
    """
    out: List[int] = []
    xof = hashlib.shake_256(seed).digest(count * 40)
    index = 0
    while len(out) < count:
        if index + 32 > len(xof):
            xof += hashlib.shake_256(seed + len(xof).to_bytes(4, 'big')).digest(count * 40)
        value = int.from_bytes(xof[index:index + 32], 'big') % modulus
        index += 32
        if value == 0:
            continue
        out.append(value)
    return out


def hex_or_inf(point: PointAffine) -> Tuple[str, str]:
    if point is None:
        return ('INF', 'INF')
    return (format(point[0], '064x'), format(point[1], '064x'))


def parse_hex_or_inf(text: str) -> Optional[int]:
    if text is None:
        return None
    value = text.strip()
    if value.upper() == 'INF':
        return None
    if value.startswith('0x') or value.startswith('0X'):
        return int(value, 16)
    return int(value, 16)


def parse_point_from_row(x_text: str, y_text: str) -> PointAffine:
    x = parse_hex_or_inf(x_text)
    y = parse_hex_or_inf(y_text)
    if x is None or y is None:
        return None
    return (x, y)


def iter_csv_dicts(path: Path) -> Iterator[Dict[str, str]]:
    with path.open(newline='') as handle:
        yield from csv.DictReader(handle)


def relative_file_manifest(root: Path) -> Dict[str, Dict[str, Any]]:
    manifest: Dict[str, Dict[str, Any]] = {}
    for path in sorted(root.rglob('*')):
        if not path.is_file():
            continue
        rel = path.relative_to(root).as_posix()
        if rel.startswith('.git/'):
            continue
        if '/__pycache__/' in f'/{rel}/' or rel.endswith('.pyc'):
            continue
        if rel == 'MANIFEST.sha256' or rel.endswith('.zip'):
            continue
        if rel == 'results/repo_verification_summary.json':
            continue
        manifest[rel] = {
            'sha256': sha256_path(path),
            'bytes': path.stat().st_size,
        }
    return manifest
