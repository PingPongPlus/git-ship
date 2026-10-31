import io
import json
from datetime import UTC, date, datetime
from pathlib import Path
from urllib.error import HTTPError, URLError

import pytest

import git_ship.github as api
from git_ship.config import Config

FIXTURES = Path(__file__).parent / "fixtures"


def test_fetch_pagination_filters_and_contribution_fallback(monkeypatch):
    client = api.GitHubClient("secret-not-for-output")
    calls = []

    def request(path, body=None):
        calls.append(path)
        if path == "/users/sailor":
            return {"type": "User"}, {}
        if "/repos?" in path and "page=2" not in path:
            return json.loads((FIXTURES / "repos-page-1.json").read_text()), {
                "link": '<https://api.github.com/users/sailor/repos?page=2>; rel="next"'
            }
        if "page=2" in path:
            return json.loads((FIXTURES / "repos-page-2.json").read_text()), {}
        if path == "/graphql":
            return {"errors": [{"message": "Resource not accessible by integration"}]}, {}
        if "/commits?" in path:
            return [], {}
        return {"Python": 100}, {}

    monkeypatch.setattr(client, "request", request)
    profile = client.fetch(Config(username="sailor", observation_date=date(2026, 10, 1)))
    assert [r.name for r in profile.repositories] == ["harbor", "chart"]
    assert not any("forked/languages" in p or "secret/languages" in p for p in calls)
    assert profile.contributions is None
    assert "GraphQL" in profile.warnings[0]
    assert "secret-not-for-output" not in repr(profile)


class Response(io.BytesIO):
    headers = {"X-RateLimit-Remaining": "59"}


def test_request_headers_and_no_credentials_in_response(monkeypatch):
    seen = []

    def urlopen(request, timeout):
        seen.append(request)
        assert timeout == 30
        return Response(b'{"Python":123}')

    monkeypatch.setattr(api, "urlopen", urlopen)
    data, headers = api.GitHubClient("private-token").request("/repos/a/b/languages")
    assert data == {"Python": 123}
    assert headers["x-ratelimit-remaining"] == "59"
    assert seen[0].get_header("Authorization") == "Bearer private-token"


@pytest.mark.parametrize(
    "status,headers,match",
    [
        (401, {}, "rejected"),
        (404, {}, "not found"),
        (403, {"X-RateLimit-Remaining": "0", "X-RateLimit-Reset": "123"}, "rate limit"),
        (429, {"Retry-After": "10"}, "rate limit"),
        (500, {}, "HTTP 500"),
    ],
)
def test_http_errors_are_clear_and_never_leak_token(monkeypatch, status, headers, match):
    def fail(*args, **kwargs):
        raise HTTPError("https://api.github.com/x", status, "private-token", headers, None)

    monkeypatch.setattr(api, "urlopen", fail)
    monkeypatch.setattr(api.time, "sleep", lambda _: None)
    with pytest.raises(api.GitHubError, match=match) as error:
        api.GitHubClient().request("/x")
    assert "private-token" not in str(error.value)


def test_public_rest_retries_without_scoped_token(monkeypatch):
    seen = []

    def scoped(request, timeout):
        seen.append(request.get_header("Authorization"))
        if len(seen) == 1:
            raise HTTPError(request.full_url, 403, "scope", {}, None)
        return Response(b"[]")

    monkeypatch.setattr(api, "urlopen", scoped)
    client = api.GitHubClient("secret")
    assert client.request("/users/sailor/repos")[0] == []
    assert seen == ["Bearer secret", None]
    assert client.warnings


def test_secondary_rate_limit_does_not_fall_back_to_anonymous(monkeypatch):
    calls = []

    def limited(*args, **kwargs):
        calls.append(1)
        raise HTTPError(
            "https://api.github.com/x",
            403,
            "limited",
            {},
            io.BytesIO(b'{"message":"You have exceeded a secondary rate limit"}'),
        )

    monkeypatch.setattr(api, "urlopen", limited)
    with pytest.raises(api.GitHubError, match="rate limit"):
        api.GitHubClient("secret").request("/x")
    assert len(calls) == 1


def test_network_retry_and_untrusted_pagination(monkeypatch):
    def fail(*args, **kwargs):
        raise URLError("private-token")

    monkeypatch.setattr(api, "urlopen", fail)
    monkeypatch.setattr(api.time, "sleep", lambda _: None)
    with pytest.raises(api.GitHubError, match="3 attempts"):
        api.GitHubClient().request("/users/x")
    with pytest.raises(api.GitHubError, match="host"):
        api.GitHubClient("secret").request("https://evil.example/x")
    client = api.GitHubClient()
    monkeypatch.setattr(client, "request", lambda _: ([], {"link": '</x>; rel="next"'}))
    with pytest.raises(api.GitHubError, match="pagination"):
        client.pages("/x")


@pytest.mark.parametrize("days", [1, 7, 30])
def test_contribution_query_uses_the_selected_rolling_window(monkeypatch, days):
    client = api.GitHubClient("secret")
    seen = []

    def request(path, body):
        seen.append(body["variables"])
        return {
            "data": {
                "user": {
                    "contributionsCollection": {"contributionCalendar": {"totalContributions": 321}}
                }
            }
        }, {}

    monkeypatch.setattr(client, "request", request)
    observed = datetime(2026, 10, 1, 3, 23, tzinfo=UTC)
    assert client.contributions("sailor", observed, days) == 321
    start = datetime.fromisoformat(seen[0]["from"])
    end = datetime.fromisoformat(seen[0]["to"])
    assert (end - start).total_seconds() == days * 86400
    assert end == observed
