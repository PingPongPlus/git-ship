"""Credential-free normalized public data and the documented ranking formulas."""

from __future__ import annotations

import json
import re
from dataclasses import asdict, dataclass
from datetime import UTC, date, datetime, time, timedelta
from fnmatch import fnmatchcase
from pathlib import Path
from typing import Any

from .config import Config
from .languages import is_programming

CARGO_LIMIT = 20
COMMIT_COVERAGE = {
    "sampled-language",
    "complete-metadata",
    "complete-language",
    "complete-primary-language",
    "complete-file-language",
}


def commit_filter_signature(config: Config) -> dict[str, Any]:
    """Store the repository selection used to establish complete live coverage."""
    return {
        "include_forks": config.include_forks,
        "include_archived": config.include_archived,
        "include": list(config.include),
        "exclude": list(config.exclude),
        "include_non_code": config.include_non_code,
    }


@dataclass(frozen=True)
class Commit:
    sha: str
    author: str
    committed_at: str
    languages: tuple[str, ...]

    @classmethod
    def from_dict(cls, raw: dict[str, Any]) -> Commit:
        sha = raw["sha"]
        if not isinstance(sha, str) or not re.fullmatch(r"[0-9a-f]{40}", sha):
            raise ValueError("commit sha must be a full 40-character lowercase SHA")
        author = raw["author"]
        if not isinstance(author, str) or not author or not Config(username=author).username:
            raise ValueError("commit author must be a GitHub login")
        parse_timestamp(raw["committed_at"])
        languages = raw["languages"]
        if not isinstance(languages, (list, tuple)) or not all(
            isinstance(name, str) and name for name in languages
        ):
            raise ValueError("commit languages must be an array of language names")
        return cls(sha, author, raw["committed_at"], tuple(sorted(set(languages))))


@dataclass(frozen=True)
class Repository:
    name: str
    owner: str
    fork: bool
    archived: bool
    pushed_at: str | None
    languages: dict[str, int]
    commits: tuple[Commit, ...] | None = None


@dataclass(frozen=True)
class Profile:
    username: str
    observed_on: date
    repositories: tuple[Repository, ...]
    contributions: int | None = None
    warnings: tuple[str, ...] = ()
    observed_at: str | None = None
    cargo_window: int | None = None
    commit_coverage: str = "sampled-language"
    commit_filters: dict[str, Any] | None = None
    commit_total: int | None = None
    authored_total: int | None = None

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> Profile:
        schema = data.get("schema_version")
        if schema not in (1, 2, 3):
            raise ValueError("unsupported profile schema; expected schema_version = 1, 2 or 3")
        config = Config(username=data["username"])
        observed = date.fromisoformat(data["observed_on"])
        repos = []
        for raw in data["repositories"]:
            langs = raw["languages"]
            if not isinstance(langs, dict) or any(
                not isinstance(k, str) or type(v) is not int or v < 0 for k, v in langs.items()
            ):
                raise ValueError("language byte counts must be nonnegative integers")
            if type(raw["fork"]) is not bool or type(raw["archived"]) is not bool:
                raise ValueError("repository fork/archived fields must be booleans")
            if not isinstance(raw["name"], str) or not isinstance(raw["owner"], str):
                raise ValueError("repository name and owner must be strings")
            if raw["pushed_at"] is not None:
                parse_timestamp(raw["pushed_at"])
            commits = raw.get("commits")
            if commits is not None:
                if not isinstance(commits, (list, tuple)):
                    raise ValueError("repository commits must be null or an array")
                commits = tuple(Commit.from_dict(c) for c in commits)
            repos.append(
                Repository(
                    raw["name"],
                    raw["owner"],
                    raw["fork"],
                    raw["archived"],
                    raw["pushed_at"],
                    langs,
                    commits,
                )
            )
        total = data.get("contributions")
        if total is not None and (type(total) is not int or total < 0):
            raise ValueError("contributions must be null or a nonnegative integer")
        warnings = data.get("warnings", [])
        if not isinstance(warnings, list) or not all(isinstance(w, str) for w in warnings):
            raise ValueError("warnings must be an array of strings")
        instant = data.get("observed_at")
        if instant is not None and parse_timestamp(instant).astimezone(UTC).date() != observed:
            raise ValueError("observed_at must be on observed_on in UTC")
        cargo_window = data.get("cargo_window")
        if cargo_window is not None and (
            type(cargo_window) is not int or not 1 <= cargo_window <= 365
        ):
            raise ValueError("cargo_window must be null or an integer in 1..365")
        # Old caches may contain only a capped or selected language sample.
        # Never infer full commit history from a non-null commits array.
        coverage = (
            data.get("commit_coverage", "sampled-language") if schema == 3 else "sampled-language"
        )
        if not isinstance(coverage, str) or coverage not in COMMIT_COVERAGE:
            raise ValueError("commit_coverage must identify sampled or complete commit data")
        filters = data.get("commit_filters") if schema == 3 else None
        if filters is not None:
            # Older complete caches counted documentation/config/unknown commits.
            if isinstance(filters, dict):
                filters = {"include_non_code": True, **filters}
            if (
                not isinstance(filters, dict)
                or filters.keys()
                != {"include_forks", "include_archived", "include", "exclude", "include_non_code"}
                or any(
                    type(filters[name]) is not bool
                    for name in ("include_forks", "include_archived", "include_non_code")
                )
                or any(
                    not isinstance(filters[name], (list, tuple))
                    or not all(isinstance(pattern, str) for pattern in filters[name])
                    for name in ("include", "exclude")
                )
            ):
                raise ValueError("commit_filters must contain the repository selection signature")
            filters = {
                **filters,
                "include": list(filters["include"]),
                "exclude": list(filters["exclude"]),
            }
        commit_total = data.get("commit_total") if schema == 3 else None
        if commit_total is not None and (type(commit_total) is not int or commit_total < 0):
            raise ValueError("commit_total must be null or a nonnegative integer")
        authored_total = data.get("authored_total") if schema == 3 else None
        if authored_total is not None and (type(authored_total) is not int or authored_total < 0):
            raise ValueError("authored_total must be null or a nonnegative integer")
        if (
            authored_total is not None
            and commit_total is not None
            and authored_total < commit_total
        ):
            raise ValueError("authored_total cannot be smaller than the cargo commit_total")
        full_fixture = coverage == "complete-language" and cargo_window is None and filters is None
        if (
            commit_total is not None
            or authored_total is not None
            or (coverage != "sampled-language" and not full_fixture)
        ):
            if cargo_window is None or instant is None or filters is None:
                raise ValueError(
                    "complete live commit data requires its window, instant and filters"
                )
        return cls(
            config.username,
            observed,
            tuple(repos),
            total,
            tuple(warnings),
            instant,
            cargo_window,
            coverage,
            filters,
            commit_total,
            authored_total,
        )

    @classmethod
    def read(cls, path: Path) -> Profile:
        try:
            return cls.from_dict(json.loads(path.read_text(encoding="utf-8")))
        except (KeyError, TypeError, AttributeError, ValueError) as exc:
            raise ValueError(f"invalid normalized profile {path.name}: {exc}") from None

    def write(self, path: Path) -> None:
        data = asdict(self)
        data["schema_version"] = 3
        data["observed_on"] = self.observed_on.isoformat()
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(json.dumps(data, indent=2, sort_keys=True) + "\n", encoding="utf-8")


def parse_timestamp(value: str) -> datetime:
    result = datetime.fromisoformat(value.replace("Z", "+00:00"))
    if result.tzinfo is None:
        raise ValueError("timestamps must include a timezone")
    return result


def selected(repo: Repository, username: str, config: Config) -> bool:
    if repo.owner.casefold() != username.casefold():
        return False
    if repo.fork and not config.include_forks:
        return False
    if repo.archived and not config.include_archived:
        return False
    names = (repo.name.casefold(), f"{repo.owner}/{repo.name}".casefold())

    def matches(patterns: tuple[str, ...]) -> bool:
        return any(fnmatchcase(n, p.casefold()) for n in names for p in patterns)

    return (not config.include or matches(config.include)) and not matches(config.exclude)


@dataclass(frozen=True)
class Language:
    name: str
    bytes: int
    share: float
    activity: float
    cargo: int | None = None


def observation_time(profile: Profile, config: Config) -> datetime:
    if config.observation_date is not None:
        return datetime.combine(config.observation_date, time.max, UTC)
    if profile.observed_at is not None:
        return parse_timestamp(profile.observed_at)
    return datetime.combine(profile.observed_on, time.max, UTC)


def commit_window(observed: datetime, days: int) -> tuple[datetime, datetime]:
    """Rolling UTC time window, with an exclusive start and inclusive end."""
    return observed - timedelta(days=days), observed


def aggregate_commits(profile: Profile, config: Config, *, all_authored: bool = False) -> int:
    """Count eligible cargo SHAs, or all authored SHAs for the independent counter."""
    if config.username and config.username.casefold() != profile.username.casefold():
        raise ValueError("aggregate profile username differs; fetch a fresh profile")
    cached_total = profile.authored_total if all_authored else profile.commit_total
    if all_authored and config.include_non_code and cached_total is None:
        cached_total = profile.commit_total
    if cached_total is None and profile.commit_coverage not in (
        "complete-metadata",
        "complete-language",
        "complete-primary-language",
        "complete-file-language",
    ):
        raise ValueError(
            "aggregate commits require complete history; fetch a fresh aggregate profile"
        )
    observed = observation_time(profile, config)
    full_fixture = (
        profile.commit_coverage == "complete-language"
        and profile.cargo_window is None
        and profile.commit_filters is None
        and profile.commit_total is None
        and profile.authored_total is None
    )
    if not full_fixture:
        if (
            profile.observed_at is None
            or profile.cargo_window != config.activity_window
            or observed != parse_timestamp(profile.observed_at)
            or profile.commit_filters != commit_filter_signature(config)
        ):
            raise ValueError(
                "aggregate cache window, observation or filters differ; "
                "fetch a fresh aggregate profile"
            )
    if cached_total is not None:
        return cached_total
    if (
        not all_authored
        and not config.include_non_code
        and profile.commit_coverage != "complete-language"
        and (profile.commit_coverage != "complete-file-language")
    ):
        raise ValueError("programming-only totals need classified commits; fetch a fresh profile")
    start, end = commit_window(observed, config.activity_window)
    shas = set()
    for repo in profile.repositories:
        if not selected(repo, profile.username, config):
            continue
        if repo.commits is None:
            raise ValueError(
                "aggregate commit history is incomplete; fetch a fresh aggregate profile"
            )
        for commit in repo.commits:
            if (
                commit.author.casefold() == profile.username.casefold()
                and start < parse_timestamp(commit.committed_at) <= end
                and (
                    all_authored
                    or config.include_non_code
                    or any(is_programming(n) for n in commit.languages)
                )
            ):
                shas.add(commit.sha)
    return len(shas)


def aggregate_languages(profile: Profile, config: Config) -> tuple[tuple[str, int], ...]:
    """Assign every distinct commit once; classified fixtures break ties by name."""
    total = aggregate_commits(profile, config)  # Validate cached window and selection first.
    if profile.commit_coverage not in ("complete-language", "complete-file-language"):
        raise ValueError(
            "cargo logos need complete language data; fetch a fresh profile with logos"
        )
    start, end = commit_window(observation_time(profile, config), config.activity_window)
    candidates: dict[str, set[str]] = {}
    for repo in profile.repositories:
        if not selected(repo, profile.username, config):
            continue
        if repo.commits is None:
            raise ValueError("cargo logos need complete language data; fetch a fresh profile")
        for commit in repo.commits:
            if commit.author.casefold() == profile.username.casefold() and (
                start < parse_timestamp(commit.committed_at) <= end
            ):
                names = {
                    n for n in commit.languages if config.include_non_code or is_programming(n)
                }
                if names or config.include_non_code:
                    candidates.setdefault(commit.sha, set()).update(names)
    counts: dict[str, int] = {}
    for names in candidates.values():
        name = min(names, key=lambda n: (n.casefold(), n)) if names else "Git"
        counts[name] = counts.get(name, 0) + 1
    if sum(counts.values()) != total:
        raise ValueError("cargo logo history and commit total differ; fetch a fresh profile")
    return tuple(sorted(counts.items(), key=lambda pair: (-pair[1], pair[0].casefold(), pair[0])))


def rank_languages(profile: Profile, config: Config) -> tuple[Language, ...]:
    counts: dict[str, int] = {}
    recent: dict[str, float] = {}
    commit_shas: dict[str, set[str]] = {}
    missing_commits: set[str] = set()
    observed = observation_time(profile, config)
    start, end = commit_window(observed, config.activity_window)
    cached_window_changed = profile.cargo_window is not None and (
        profile.cargo_window != config.activity_window
        or profile.observed_at is None
        or observed != parse_timestamp(profile.observed_at)
    )
    for repo in profile.repositories:
        if not selected(repo, profile.username, config):
            continue
        age = (
            (observed - parse_timestamp(repo.pushed_at)).total_seconds() / 86400
            if repo.pushed_at
            else None
        )
        recency = (
            max(0.0, 1 - age / config.activity_window) if age is not None and age >= 0 else 0.0
        )
        for name, count in repo.languages.items():
            if not config.include_non_code and not is_programming(name):
                continue
            counts[name] = counts.get(name, 0) + count
            recent[name] = recent.get(name, 0.0) + count * recency
            if count > 0 and (repo.commits is None or cached_window_changed):
                missing_commits.add(name)
        for commit in repo.commits or ():
            if commit.author.casefold() != profile.username.casefold():
                continue
            if not start < parse_timestamp(commit.committed_at) <= end:
                continue
            for name in commit.languages:
                if repo.languages.get(name, 0) > 0 and (
                    config.include_non_code or is_programming(name)
                ):
                    commit_shas.setdefault(name, set()).add(commit.sha)
    total = sum(counts.values())
    cargo: dict[str, int | None] = {
        name: min(CARGO_LIMIT, len(commit_shas.get(name, ()))) for name in counts
    }
    for name in counts:
        if profile.commit_coverage == "complete-metadata" or (
            name in missing_commits and len(commit_shas.get(name, ())) < CARGO_LIMIT
        ):
            cargo[name] = None
    return tuple(
        Language(
            name,
            count,
            count / total,
            recent[name] / count,
            cargo[name],
        )
        for name, count in sorted(counts.items(), key=lambda x: (-x[1], x[0].casefold()))
        if count > 0
    )


def global_activity(profile: Profile) -> float:
    """Unknown contributions use the peaceful baseline; never invent a total."""
    return min(profile.contributions or 0, 1000) / 1000
