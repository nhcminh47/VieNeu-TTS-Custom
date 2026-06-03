from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path


@dataclass(frozen=True)
class StorageUsage:
    output_dir: Path
    file_count: int
    total_bytes: int
    max_files: int
    max_bytes: int


class OutputStorage:
    def __init__(self, output_dir: Path, max_files: int = 0, max_bytes: int = 0):
        self.output_dir = output_dir
        self.max_files = max_files
        self.max_bytes = max_bytes
        self.output_dir.mkdir(parents=True, exist_ok=True)

    def path_for(self, job_id: str, format_name: str = "wav") -> Path:
        return self.output_dir / f"{job_id}.{format_name}"

    def audio_files(self) -> list[Path]:
        return [path for path in self.output_dir.glob("*.wav") if path.is_file()]

    def usage(self) -> StorageUsage:
        files = self.audio_files()
        return StorageUsage(
            output_dir=self.output_dir,
            file_count=len(files),
            total_bytes=sum(path.stat().st_size for path in files),
            max_files=self.max_files,
            max_bytes=self.max_bytes,
        )

    def prune(self, protected: set[Path] | None = None) -> list[Path]:
        protected_resolved = {path.resolve() for path in protected or set()}
        files = sorted(self.audio_files(), key=lambda path: path.stat().st_mtime)
        deleted: list[Path] = []

        def over_limit(paths: list[Path]) -> bool:
            if self.max_files and len(paths) > self.max_files:
                return True
            if self.max_bytes and sum(path.stat().st_size for path in paths) > self.max_bytes:
                return True
            return False

        while files and over_limit(files):
            candidate = files.pop(0)
            if candidate.resolve() in protected_resolved:
                files.append(candidate)
                if all(path.resolve() in protected_resolved for path in files):
                    break
                continue
            try:
                candidate.unlink()
                deleted.append(candidate)
            except FileNotFoundError:
                deleted.append(candidate)

        return deleted
