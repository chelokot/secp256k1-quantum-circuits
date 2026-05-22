#!/usr/bin/env python3

from __future__ import annotations

import hashlib
import json
import subprocess
from pathlib import Path
from typing import Any, Dict, Iterable, List


ARTIFACT_DIGEST_TREE_SCHEMA = 'compiler-project-artifact-digest-tree-v1'
DEFAULT_CHUNK_SIZE_BYTES = 1024 * 1024
DEFAULT_SIZE_THRESHOLD_BYTES = 1024 * 1024


def _sha256_bytes(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def _merkle_root(hashes: Iterable[str]) -> str:
    level = list(hashes)
    if not level:
        return _sha256_bytes(b'')
    while len(level) > 1:
        if len(level) % 2:
            level.append(level[-1])
        level = [
            _sha256_bytes((level[index] + level[index + 1]).encode())
            for index in range(0, len(level), 2)
        ]
    return level[0]


def _tracked_paths(repo_root: Path) -> List[str]:
    result = subprocess.run(
        ['git', 'ls-files'],
        cwd=repo_root,
        check=True,
        stdout=subprocess.PIPE,
        text=True,
    )
    return sorted(line for line in result.stdout.splitlines() if line)


def _chunk_file(repo_root: Path, relative_path: str, chunk_size_bytes: int) -> Dict[str, Any]:
    path = repo_root / relative_path
    chunks = []
    file_hash = hashlib.sha256()
    with path.open('rb') as handle:
        index = 0
        offset = 0
        while True:
            data = handle.read(chunk_size_bytes)
            if not data:
                break
            file_hash.update(data)
            chunks.append({
                'index': index,
                'offset': offset,
                'bytes': len(data),
                'sha256': _sha256_bytes(data),
            })
            index += 1
            offset += len(data)
    return {
        'path': relative_path,
        'bytes': path.stat().st_size,
        'sha256': file_hash.hexdigest(),
        'chunk_size_bytes': chunk_size_bytes,
        'chunk_count': len(chunks),
        'chunk_merkle_root_sha256': _merkle_root(chunk['sha256'] for chunk in chunks),
        'chunks': chunks,
    }


def build_artifact_digest_tree(
    *,
    repo_root: Path,
    size_threshold_bytes: int = DEFAULT_SIZE_THRESHOLD_BYTES,
    chunk_size_bytes: int = DEFAULT_CHUNK_SIZE_BYTES,
) -> Dict[str, Any]:
    files = [
        _chunk_file(repo_root, relative_path, chunk_size_bytes)
        for relative_path in _tracked_paths(repo_root)
        if (repo_root / relative_path).is_file()
        and (repo_root / relative_path).stat().st_size >= size_threshold_bytes
    ]
    files.sort(key=lambda row: (-int(row['bytes']), row['path']))
    repository_digest_input = json.dumps(
        [
            {
                'path': row['path'],
                'bytes': row['bytes'],
                'sha256': row['sha256'],
                'chunk_merkle_root_sha256': row['chunk_merkle_root_sha256'],
            }
            for row in files
        ],
        sort_keys=True,
        separators=(',', ':'),
    ).encode()
    checks = {
        'all_files_are_chunked': all(row['chunk_count'] >= 1 for row in files),
        'all_chunk_sizes_sum_to_file_size': all(
            sum(chunk['bytes'] for chunk in row['chunks']) == row['bytes']
            for row in files
        ),
        'large_artifact_set_is_non_empty': len(files) > 0,
    }
    return {
        'schema': ARTIFACT_DIGEST_TREE_SCHEMA,
        'scope': 'tracked repository files at or above the configured large-artifact threshold',
        'size_threshold_bytes': int(size_threshold_bytes),
        'chunk_size_bytes': int(chunk_size_bytes),
        'file_count': len(files),
        'repository_digest_sha256': _sha256_bytes(repository_digest_input),
        'files': files,
        'checks': checks,
        'pass': all(checks.values()),
    }


__all__ = [
    'ARTIFACT_DIGEST_TREE_SCHEMA',
    'DEFAULT_CHUNK_SIZE_BYTES',
    'DEFAULT_SIZE_THRESHOLD_BYTES',
    'build_artifact_digest_tree',
]
