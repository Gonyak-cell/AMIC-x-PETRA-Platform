#!/usr/bin/env python3
"""에러-수정 연결 알고리즘: 에러 발생과 git 커밋을 자동으로 연결한다.

3단계 히어리스틱:
1. 파일 경로 매칭 (HIGH 신뢰도)
2. 시간 근접 매칭 (MEDIUM 신뢰도)
3. 세션 맥락 추출 (보조)
"""
import re
import subprocess
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from difflib import SequenceMatcher
from enum import Enum
from pathlib import Path


class FixStatus(Enum):
    FIXED = "FIXED"
    LIKELY_FIXED = "LIKELY_FIXED"
    WORKAROUND = "WORKAROUND"
    UNRESOLVED = "UNRESOLVED"
    RECURRING = "RECURRING"


class RecurrenceRisk(Enum):
    LOW = "LOW"
    MEDIUM = "MEDIUM"
    HIGH = "HIGH"


@dataclass
class LinkedError:
    """에러와 수정 정보가 연결된 레코드."""

    error: dict
    cluster_count: int = 1
    fix_commits: list = field(default_factory=list)
    fix_status: FixStatus = FixStatus.UNRESOLVED
    fix_reason: str = ""
    work_context: str = ""
    fix_context: str = ""
    recurrence_risk: RecurrenceRisk = RecurrenceRisk.MEDIUM
    link_confidence: str = "none"


def sanitize_str(value: str) -> str:
    """Windows 한글 경로 등에서 발생하는 surrogate 문자 제거."""
    return value.encode("utf-8", errors="replace").decode("utf-8")


def normalize_path(path: str) -> str:
    """프로젝트 루트 기준 상대 경로로 정규화."""
    path = path.replace("\\", "/")
    # Docker 컨테이너 경로 제거
    if path.startswith("/app/"):
        path = path[5:]
    # Windows 절대 경로에서 프로젝트 부분 제거
    markers = ["AMIC x PETRA Platform/", "amic-platform/"]
    for marker in markers:
        idx = path.find(marker)
        if idx >= 0:
            path = path[idx + len(marker) :]
            break
    # 선행 슬래시 제거
    path = path.lstrip("/")
    return path


def extract_files_from_error(error: dict) -> set:
    """에러 스니펫과 명령어에서 파일 경로를 추출하고 정규화."""
    files = set()
    combined = error.get("error_snippet", "") + "\n" + error.get("command", "")

    # 패턴 1: Python traceback — File "/app/app/core/database.py", line 42
    for m in re.finditer(r'File ["\']([^"\']+\.py)["\']', combined):
        files.add(normalize_path(m.group(1)))

    # 패턴 2: Python import 에러 — from 'app.core.database'
    for m in re.finditer(r"from '([\w.]+)'", combined):
        module_path = m.group(1).replace(".", "/") + ".py"
        files.add(module_path)

    # 패턴 3: TypeScript/Node 경로
    for m in re.finditer(r"[(\s]([\w./\-]+\.(?:ts|tsx|js|jsx))[\s:)\]]", combined):
        files.add(normalize_path(m.group(1)))

    # 패턴 4: 일반 Unix 파일 경로
    for m in re.finditer(
        r"(?:^|[\s\"])((?:/[\w.\-]+)+\.(?:py|ts|tsx|js|json|yml|yaml|conf|sh))",
        combined,
    ):
        files.add(normalize_path(m.group(1)))

    # 패턴 5: Windows 경로
    for m in re.finditer(
        r"([A-Za-z]:\\[\w\\.\- ]+\.(?:py|ts|tsx|js|json|yml))", combined
    ):
        files.add(normalize_path(m.group(1)))

    return files


def normalize_snippet(snippet: str) -> str:
    """에러 스니펫 정규화 (비교용)."""
    text = snippet.lower()
    text = re.sub(r"[a-z]:\\[^\s:]+", "[PATH]", text)
    text = re.sub(r"/[\w./\-]+", "[PATH]", text)
    text = re.sub(r"\b\d+\b", "[N]", text)
    text = re.sub(r"\s+", " ", text).strip()
    return text


def cluster_errors(errors: list) -> list:
    """유사한 에러를 클러스터링. 각 클러스터는 [대표 에러, ...동일 에러들] 리스트."""
    clusters = []

    for entry in errors:
        snippet = entry.get("error_snippet", "")
        norm = normalize_snippet(snippet)
        category = entry.get("category", "other")

        matched = False
        for cluster in clusters:
            rep = cluster[0]
            rep_norm = normalize_snippet(rep.get("error_snippet", ""))
            if rep.get("category", "other") == category:
                similarity = SequenceMatcher(None, rep_norm, norm).ratio()
                if similarity > 0.6:
                    cluster.append(entry)
                    matched = True
                    break

        if not matched:
            clusters.append([entry])

    return clusters


class ErrorFixLinker:
    """에러와 수정 커밋을 연결하는 엔진."""

    def __init__(self, project_dir: str, target_date: str):
        self.project_dir = Path(project_dir)
        self.target_date = target_date  # "YYYY-MM-DD"

    def load_git_commits(self) -> list:
        """git log에서 대상 날짜의 커밋 정보를 추출."""
        cmd = [
            "git",
            "log",
            "--all",
            f"--since={self.target_date} 00:00:00",
            f"--until={self.target_date} 23:59:59",
            "--format=COMMIT_SEP%n%H%n%ai%n%s%n%b%nFILES_START",
            "--name-only",
        ]
        try:
            result = subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                cwd=self.project_dir,
                encoding="utf-8",
                errors="replace",
                timeout=30,
            )
            return self._parse_git_output(result.stdout)
        except (subprocess.TimeoutExpired, FileNotFoundError):
            return []

    def _parse_git_output(self, output: str) -> list:
        """git log 출력을 파싱."""
        commits = []
        blocks = output.split("COMMIT_SEP\n")

        for block in blocks:
            block = block.strip()
            if not block:
                continue
            lines = block.split("\n")
            if len(lines) < 3:
                continue

            hash_val = lines[0].strip()
            timestamp = lines[1].strip()
            subject = lines[2].strip()

            # body와 files 분리
            body_lines = []
            file_lines = []
            in_files = False
            for line in lines[3:]:
                if line.strip() == "FILES_START":
                    in_files = True
                    continue
                if in_files:
                    stripped = line.strip()
                    if stripped:
                        file_lines.append(stripped)
                else:
                    body_lines.append(line)

            body = "\n".join(body_lines).strip()

            # conventional commit 파싱
            commit_type = "other"
            scope = ""
            type_match = re.match(r"^(\w+)(?:\(([^)]+)\))?[!]?:\s*(.+)", subject)
            if type_match:
                commit_type = type_match.group(1).lower()
                scope = type_match.group(2) or ""

            commits.append(
                {
                    "hash": hash_val[:7],
                    "full_hash": hash_val,
                    "timestamp": timestamp,
                    "subject": subject,
                    "body": body,
                    "type": commit_type,
                    "scope": scope,
                    "files": [normalize_path(f) for f in file_lines],
                }
            )

        return commits

    def _get_commit_numstat(self, commit_hash: str) -> dict:
        """커밋의 추가/삭제 라인 수를 가져온다."""
        cmd = ["git", "diff", "--numstat", f"{commit_hash}~1", commit_hash]
        try:
            result = subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                cwd=self.project_dir,
                encoding="utf-8",
                errors="replace",
                timeout=10,
            )
            added = 0
            deleted = 0
            file_count = 0
            for line in result.stdout.strip().split("\n"):
                parts = line.split("\t")
                if len(parts) >= 3:
                    try:
                        a = int(parts[0]) if parts[0] != "-" else 0
                        d = int(parts[1]) if parts[1] != "-" else 0
                        added += a
                        deleted += d
                        file_count += 1
                    except ValueError:
                        pass
            return {"added": added, "deleted": deleted, "file_count": file_count}
        except (subprocess.TimeoutExpired, FileNotFoundError):
            return {"added": 0, "deleted": 0, "file_count": 0}

    def link_by_file(self, error: dict, commits: list) -> list:
        """1단계: 에러에서 언급된 파일과 커밋 변경 파일 교차 매칭."""
        error_files = extract_files_from_error(error)
        if not error_files:
            return []

        error_ts = error.get("ts", "")
        matches = []

        for commit in commits:
            # 에러 이후의 커밋만 (수정 커밋이므로)
            if commit["timestamp"][:19] < error_ts[:19]:
                continue
            commit_files_set = set(commit["files"])
            overlap = error_files & commit_files_set
            if overlap:
                confidence = "high" if commit["type"] == "fix" else "medium"
                matches.append(
                    {
                        "commit": commit,
                        "overlap_files": list(overlap),
                        "confidence": confidence,
                    }
                )

        return matches

    def link_by_time(self, error: dict, commits: list, window_min: int = 30) -> list:
        """2단계: 에러 발생 후 window 내의 fix 커밋 후보."""
        error_ts_str = error.get("ts", "")
        if not error_ts_str:
            return []

        try:
            error_ts = datetime.fromisoformat(error_ts_str)
        except ValueError:
            return []

        candidates = []
        for commit in commits:
            try:
                # git log timestamp: "2026-02-26 18:48:04 +0900"
                commit_ts = datetime.fromisoformat(
                    commit["timestamp"][:19].replace(" ", "T")
                )
            except ValueError:
                continue

            delta = (commit_ts - error_ts).total_seconds() / 60
            if 0 < delta <= window_min:
                confidence = "medium" if commit["type"] == "fix" else "low"
                candidates.append(
                    {
                        "commit": commit,
                        "delta_min": round(delta, 1),
                        "confidence": confidence,
                    }
                )

        return candidates

    def extract_session_context(self, error: dict, prompts: list) -> dict:
        """3단계: 동일 세션의 프롬프트에서 작업 맥락 추출."""
        session_id = error.get("session_id", "")
        error_ts = error.get("ts", "")
        result = {"work_context": "", "fix_context": ""}

        if not session_id:
            return result

        session_prompts = [
            p
            for p in prompts
            if p.get("session_id", "") == session_id
            # task-notification은 제외
            and not p.get("prompt", "").startswith("<task-notification>")
        ]

        before = [p for p in session_prompts if p.get("ts", "") <= error_ts]
        after = [p for p in session_prompts if p.get("ts", "") > error_ts]

        if before:
            # 에러 직전 지시에서 작업 맥락 추출
            recent = before[-3:]
            result["work_context"] = " → ".join(
                p.get("prompt", "")[:80] for p in recent
            )

        if after:
            # 에러 직후 지시에서 수정 맥락 추출
            next_actions = after[:3]
            result["fix_context"] = " → ".join(
                p.get("prompt", "")[:80] for p in next_actions
            )

        return result

    def determine_fix_status(
        self, cluster: list, linked_commits: list, all_errors_after: list
    ) -> FixStatus:
        """수정 상태 판단."""
        has_fix_commit = any(
            lc["commit"]["type"] == "fix" for lc in linked_commits if "commit" in lc
        )
        has_any_commit = len(linked_commits) > 0
        cluster_count = len(cluster)

        # 이후 동일 패턴 재발 확인
        rep_norm = normalize_snippet(cluster[0].get("error_snippet", ""))
        reoccurred = False
        last_error_ts = max(e.get("ts", "") for e in cluster)

        for err in all_errors_after:
            if err.get("ts", "") <= last_error_ts:
                continue
            err_norm = normalize_snippet(err.get("error_snippet", ""))
            if (
                err.get("category", "") == cluster[0].get("category", "")
                and SequenceMatcher(None, rep_norm, err_norm).ratio() > 0.6
            ):
                reoccurred = True
                break

        if has_fix_commit and not reoccurred:
            return FixStatus.FIXED
        if has_fix_commit and reoccurred:
            return FixStatus.WORKAROUND
        if has_any_commit and not reoccurred:
            return FixStatus.LIKELY_FIXED
        if cluster_count >= 3:
            return FixStatus.RECURRING
        return FixStatus.UNRESOLVED

    def assess_recurrence(
        self,
        error: dict,
        fix_status: FixStatus,
        linked_commits: list,
        cluster_count: int,
    ) -> RecurrenceRisk:
        """재발 가능성 판단."""
        category = error.get("category", "other")

        # 환경 의존적 카테고리
        if category in ("docker", "migration"):
            return RecurrenceRisk.HIGH

        # 반복 발생
        if cluster_count >= 3:
            return RecurrenceRisk.HIGH

        # 미해결
        if fix_status == FixStatus.UNRESOLVED:
            return RecurrenceRisk.HIGH

        # fix 커밋에 테스트 파일이 포함되어 있는지 확인
        has_test = False
        for lc in linked_commits:
            commit = lc.get("commit", {})
            for f in commit.get("files", []):
                if "test" in f.lower() or f.endswith("_test.py") or "spec." in f:
                    has_test = True
                    break

        if fix_status == FixStatus.FIXED and has_test:
            return RecurrenceRisk.LOW
        if fix_status in (FixStatus.FIXED, FixStatus.LIKELY_FIXED):
            return RecurrenceRisk.MEDIUM

        return RecurrenceRisk.HIGH

    def extract_fix_reason(self, linked_commits: list) -> str:
        """연결된 커밋에서 수정 취지를 추출."""
        if not linked_commits:
            return ""

        # fix 커밋 우선
        fix_commits = [
            lc for lc in linked_commits if lc.get("commit", {}).get("type") == "fix"
        ]
        target = fix_commits[0] if fix_commits else linked_commits[0]
        commit = target.get("commit", {})

        subject = commit.get("subject", "")
        body = commit.get("body", "")

        # conventional commit에서 설명 부분 추출
        match = re.match(r"^\w+(?:\([^)]+\))?[!]?:\s*(.+)", subject)
        reason = match.group(1) if match else subject

        if body:
            reason += f" — {body[:100]}"

        return reason.strip()

    def link_all(self, errors: list, commits: list, prompts: list) -> list:
        """모든 에러에 대해 수정 커밋 연결 시도."""
        if not errors:
            return []

        # 에러 클러스터링
        clusters = cluster_errors(errors)

        # 대상 날짜 이후의 전체 에러 (재발 판단용)
        all_errors_after = errors  # 같은 날짜 내 재발만 체크

        linked_results = []

        for cluster in clusters:
            representative = cluster[0]

            # 3단계 연결
            file_links = self.link_by_file(representative, commits)
            time_links = self.link_by_time(representative, commits)
            context = self.extract_session_context(representative, prompts)

            # 최선의 연결 선택: file > time
            best_links = file_links if file_links else time_links

            # 수정 상태 및 재발 가능성
            fix_status = self.determine_fix_status(
                cluster, best_links, all_errors_after
            )
            recurrence = self.assess_recurrence(
                representative, fix_status, best_links, len(cluster)
            )

            confidence = "none"
            if best_links:
                confidence = best_links[0].get("confidence", "low")

            linked_results.append(
                LinkedError(
                    error=representative,
                    cluster_count=len(cluster),
                    fix_commits=best_links,
                    fix_status=fix_status,
                    fix_reason=self.extract_fix_reason(best_links),
                    work_context=context["work_context"],
                    fix_context=context["fix_context"],
                    recurrence_risk=recurrence,
                    link_confidence=confidence,
                )
            )

        return linked_results
