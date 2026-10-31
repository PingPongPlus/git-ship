"""Bounded standard-library GitHub client. Tokens never enter normalized data."""

from __future__ import annotations

import json
import time
from collections.abc import Iterator
from dataclasses import asdict, replace
from datetime import UTC, datetime
from datetime import time as day_time
from typing import Any
from urllib.error import HTTPError, URLError
from urllib.parse import quote, urlencode, urlparse
from urllib.request import Request, urlopen

from .config import Config
from .languages import file_language
from .model import (
    CARGO_LIMIT,
    Commit,
    Profile,
    Repository,
    commit_window,
    parse_timestamp,
    rank_languages,
    selected,
)

API = "https://api.github.com"


class GitHubError(RuntimeError):
    pass


class GitHubClient:
    def __init__(self, token: str | None = None) -> None:
        self._token = token
        self.warnings: list[str] = []
        self.requests = 0

    def request(
        self, path: str, body: dict[str, Any] | None = None, *, anonymous: bool = False
    ) -> tuple[Any, dict[str, str]]:
        url = path if path.startswith("https://") else API + path
        parsed = urlparse(url)
        if parsed.scheme != "https" or parsed.netloc != "api.github.com":
            raise GitHubError("GitHub returned an unexpected pagination host")
        headers = {
            "Accept": "application/vnd.github+json",
            "User-Agent": "git-ship/0.1",
            "X-GitHub-Api-Version": "2026-03-10",
        }
        if self._token and not anonymous:
            headers["Authorization"] = f"Bearer {self._token}"
        payload = json.dumps(body).encode() if body is not None else None
        if payload:
            headers["Content-Type"] = "application/json"
        for attempt in range(3):
            self.requests += 1
            if self.requests > 2000:
                raise GitHubError("request budget exceeded; narrow repository filters")
            try:
                with urlopen(Request(url, data=payload, headers=headers), timeout=30) as response:
                    data = response.read(10_000_001)
                    if len(data) > 10_000_000:
                        raise GitHubError("GitHub response exceeds 10 MB")
                    return json.loads(data), {k.lower(): v for k, v in response.headers.items()}
            except HTTPError as exc:
                # Secondary limits can be 403 with remaining primary quota and
                # no Retry-After. Inspect only for classification; never log it.
                try:
                    detail = exc.read(8192).decode("utf-8", errors="replace").lower()
                finally:
                    exc.close()
                if exc.code == 401:
                    raise GitHubError(
                        "GitHub rejected GITHUB_TOKEN (401); check or unset it"
                    ) from None
                if exc.code in (403, 429) and (
                    exc.headers.get("X-RateLimit-Remaining") == "0"
                    or exc.code == 429
                    or exc.headers.get("Retry-After")
                    or "rate limit" in detail
                    or "abuse detection" in detail
                ):
                    reset = exc.headers.get("X-RateLimit-Reset", "unknown")
                    raise GitHubError(
                        f"GitHub rate limit reached; retry later (reset epoch {reset})"
                    ) from None
                if exc.code in (403, 404) and body is None and self._token and not anonymous:
                    if (
                        "Public REST data fetched without authentication due to token scope."
                        not in self.warnings
                    ):
                        self.warnings.append(
                            "Public REST data fetched without authentication due to token scope."
                        )
                    return self.request(path, anonymous=True)
                if exc.code == 404:
                    raise GitHubError("GitHub user or public repository not found (404)") from None
                if exc.code >= 500 and attempt < 2:
                    time.sleep(attempt + 1)
                    continue
                raise GitHubError(
                    f"GitHub API failed (HTTP {exc.code}); check access and retry"
                ) from None
            except (URLError, TimeoutError, OSError):
                if attempt < 2:
                    time.sleep(attempt + 1)
                    continue
                raise GitHubError(
                    "unable to reach GitHub after 3 attempts; check network connectivity"
                ) from None
            except (ValueError, UnicodeError):
                raise GitHubError("GitHub returned invalid JSON") from None
        raise GitHubError("GitHub request exhausted retries")

    @staticmethod
    def next_page(headers: dict[str, str]) -> str:
        for link in headers.get("link", "").split(","):
            if 'rel="next"' in link:
                return link.strip().split(">", 1)[0].lstrip("<")
        return ""

    def iter_pages(self, path: str, kind: str = "repository") -> Iterator[list[dict[str, Any]]]:
        seen: set[str] = set()
        while path:
            if path in seen or len(seen) >= 10:
                raise GitHubError(
                    f"{kind} pagination exceeds 10 pages or repeats; "
                    "narrow repository filters or the data window"
                )
            seen.add(path)
            data, headers = self.request(path)
            if not isinstance(data, list) or any(not isinstance(x, dict) for x in data):
                raise GitHubError(f"unexpected GitHub {kind} response")
            yield data
            path = self.next_page(headers)

    def pages(self, path: str) -> list[dict[str, Any]]:
        return [item for page in self.iter_pages(path) for item in page]

    def changed_languages(self, base: str, sha: str, available: dict[str, int]) -> tuple[str, ...]:
        path = f"{base}/commits/{sha}?per_page=100"
        languages = set()
        seen: set[str] = set()
        file_count = 0
        while path:
            if path in seen or len(seen) >= 30:
                raise GitHubError("commit file pagination exceeds 30 pages or repeats")
            seen.add(path)
            data, headers = self.request(path)
            if (
                not isinstance(data, dict)
                or data.get("sha") != sha
                or not isinstance(data.get("files"), list)
            ):
                raise GitHubError("unexpected GitHub changed-files response")
            for entry in data["files"]:
                if not isinstance(entry, dict) or not isinstance(entry.get("filename"), str):
                    raise GitHubError("unexpected GitHub changed-file name")
                # Renames can change a file's language; count each affected
                # language once, whether the change adds, deletes or renames it.
                for name in (entry["filename"], entry.get("previous_filename")):
                    if isinstance(name, str) and (language := file_language(name, available)):
                        languages.add(language)
            file_count += len(data["files"])
            if file_count >= 3000:
                raise GitHubError(
                    "commit reaches GitHub's 3000-file limit; attribution may be incomplete; "
                    "exclude this repository"
                )
            path = self.next_page(headers)
        return tuple(sorted(languages))

    def load_cargo(
        self, profile: Profile, config: Config, observed: datetime
    ) -> tuple[Repository, ...]:
        targets = {language.name for language in rank_languages(profile, config)[: config.ships]}
        shas: dict[str, set[str]] = {name: set() for name in targets}
        repositories = list(profile.repositories)
        start, end = commit_window(observed, config.activity_window)
        query = urlencode(
            {
                "author": profile.username,
                "since": start.isoformat(),
                "until": end.isoformat(),
                "per_page": 100,
            }
        )
        for index, repo in enumerate(repositories):
            if not targets or all(len(values) >= CARGO_LIMIT for values in shas.values()):
                break
            if not any(name in targets and count > 0 for name, count in repo.languages.items()):
                continue
            if all(
                len(shas[name]) >= CARGO_LIMIT
                for name in targets
                if repo.languages.get(name, 0) > 0
            ):
                continue
            base = f"/repos/{quote(repo.owner, safe='')}/{quote(repo.name, safe='')}"
            records = []
            seen: set[str] = set()
            for page in self.iter_pages(f"{base}/commits?{query}", kind="commit"):
                for item in page:
                    try:
                        author = item["author"]
                        if (
                            not isinstance(author, dict)
                            or author.get("login", "").casefold() != profile.username.casefold()
                        ):
                            continue
                        sha = item["sha"]
                        timestamp = item["commit"]["committer"]["date"]
                        if not start < parse_timestamp(timestamp) <= end or sha in seen:
                            continue
                        # Validate an API SHA before using it in a request path.
                        Commit.from_dict(
                            {
                                "sha": sha,
                                "author": profile.username,
                                "committed_at": timestamp,
                                "languages": [],
                            }
                        )
                        seen.add(sha)
                    except (KeyError, TypeError, AttributeError, ValueError):
                        raise GitHubError("unexpected GitHub commit metadata") from None
                    languages = self.changed_languages(base, sha, repo.languages)
                    records.append(Commit(sha, profile.username, timestamp, languages))
                    for name in languages:
                        if name in shas:
                            shas[name].add(sha)
                    if all(
                        len(shas[name]) >= CARGO_LIMIT
                        for name in targets
                        if repo.languages.get(name, 0) > 0
                    ):
                        break
                else:
                    continue
                break
            repositories[index] = replace(repo, commits=tuple(records))
        return tuple(repositories)

    def contributions(self, username: str, observed: datetime, days: int = 30) -> int | None:
        if not self._token:
            self.warnings.append(
                "Contribution total unavailable without a token; peaceful baseline used."
            )
            return None
        start, end = commit_window(observed, days)
        query = """query($login:String!, $from:DateTime!, $to:DateTime!) {
          user(login:$login) { contributionsCollection(from:$from, to:$to) {
            contributionCalendar { totalContributions }
          } }
        }"""
        try:
            data, _ = self.request(
                "/graphql",
                {
                    "query": query,
                    "variables": {
                        "login": username,
                        "from": start.isoformat(),
                        "to": end.isoformat(),
                    },
                },
            )
            value = data["data"]["user"]["contributionsCollection"]["contributionCalendar"][
                "totalContributions"
            ]
            if type(value) is not int or value < 0:
                raise ValueError("invalid contribution count")
            return value
        except (GitHubError, KeyError, TypeError, ValueError):
            self.warnings.append(
                "Contribution total unavailable from GraphQL; peaceful baseline used."
            )
            return None

    def fetch(self, config: Config) -> Profile:
        if not config.username:
            raise ValueError("live rendering requires --username or a username in the config")
        username = config.username
        # Confirms the user even when their repository list is empty.
        user, _ = self.request(f"/users/{quote(username)}")
        if not isinstance(user, dict) or user.get("type") != "User":
            raise GitHubError("username must identify a GitHub user, not an organization")
        raw = self.pages(f"/users/{quote(username)}/repos?type=owner&sort=full_name&per_page=100")
        repos = []
        for item in raw:
            if item.get("private", False):
                continue
            try:
                repo = Repository(
                    item["name"],
                    item["owner"]["login"],
                    item["fork"],
                    item["archived"],
                    item.get("pushed_at"),
                    {},
                )
                if not selected(repo, username, config):
                    continue
                owner, name = quote(repo.owner, safe=""), quote(repo.name, safe="")
                languages, _ = self.request(f"/repos/{owner}/{name}/languages")
                repos.append(
                    Repository(
                        repo.name, repo.owner, repo.fork, repo.archived, repo.pushed_at, languages
                    )
                )
            except (KeyError, TypeError):
                raise GitHubError("unexpected repository metadata from GitHub") from None
        observed = (
            datetime.combine(config.observation_date, day_time.max, UTC)
            if config.observation_date
            else datetime.now(UTC)
        )
        profile = Profile(username, observed.date(), tuple(repos), observed_at=observed.isoformat())
        repos = self.load_cargo(profile, config, observed)
        total = self.contributions(username, observed, config.activity_window)
        # Validate the same contract as offline fixtures before rendering.
        return Profile.from_dict(
            {
                "schema_version": 2,
                "username": username,
                "observed_on": str(observed.date()),
                "observed_at": observed.isoformat(),
                "cargo_window": config.activity_window,
                "repositories": [asdict(r) for r in repos],
                "contributions": total,
                "warnings": self.warnings,
            }
        )
