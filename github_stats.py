#!/usr/bin/python3
"""Fetch GitHub user stats via GraphQL and REST APIs."""

from __future__ import annotations

import asyncio
import os
from typing import Optional

import aiohttp
import requests

###############################################################################
# Main Classes
###############################################################################


class Queries:
    """
    Class with functions to query the GitHub GraphQL (v4) API and the REST (v3)
    API. Also includes functions to dynamically generate GraphQL queries.
    """

    def __init__(
        self,
        username: str,
        access_token: str,
        session: aiohttp.ClientSession,
        max_connections: int = 10,
    ):
        self.username = username
        self.access_token = access_token
        self.session = session
        self.semaphore = asyncio.Semaphore(max_connections)

    async def query(self, generated_query: str) -> dict:
        """
        Make a request to the GraphQL API using the authentication token from
        the environment.
        :param generated_query: string query to be sent to the API
        :return: decoded GraphQL JSON output
        """
        headers = {"Authorization": f"Bearer {self.access_token}"}
        try:
            async with self.semaphore:
                r = await self.session.post(
                    "https://api.github.com/graphql",
                    headers=headers,
                    json={"query": generated_query},
                )
            return await r.json()
        except (aiohttp.ClientError, asyncio.TimeoutError) as exc:
            print(f"aiohttp failed for GraphQL query: {exc}")
            async with self.semaphore:
                return await asyncio.to_thread(
                    lambda: requests.post(
                        "https://api.github.com/graphql",
                        headers=headers,
                        json={"query": generated_query},
                        timeout=30,
                    ).json()
                )

    async def query_rest(self, path: str, params: Optional[dict] = None) -> dict:
        """
        Make a request to the REST API.
        :param path: API path to query
        :param params: Query parameters to be passed to the API
        :return: deserialized REST JSON output
        """
        headers = {"Authorization": f"token {self.access_token}"}
        params = params or {}
        path = path.lstrip("/")
        url = f"https://api.github.com/{path}"

        for _ in range(60):
            try:
                async with self.semaphore:
                    r = await self.session.get(
                        url, headers=headers, params=tuple(params.items())
                    )
                if r.status == 202:
                    print("A path returned 202. Retrying...")
                    await asyncio.sleep(2)
                    continue
                result = await r.json()
                if result is not None:
                    return result
            except (aiohttp.ClientError, asyncio.TimeoutError) as exc:
                print(f"aiohttp failed for rest query: {exc}")
                response = await asyncio.to_thread(
                    lambda: requests.get(
                        url,
                        headers=headers,
                        params=tuple(params.items()),
                        timeout=30,
                    )
                )
                if response.status_code == 202:
                    print("A path returned 202. Retrying...")
                    await asyncio.sleep(2)
                    continue
                if response.status_code == 200:
                    return response.json()

        print("There were too many 202s. Data for this repository will be incomplete.")
        return {}

    @staticmethod
    def repos_overview(
        contrib_cursor: Optional[str] = None, owned_cursor: Optional[str] = None
    ) -> str:
        """
        :return: GraphQL query with overview of user repositories
        """
        owned_after = "null" if owned_cursor is None else f'"{owned_cursor}"'
        contrib_after = "null" if contrib_cursor is None else f'"{contrib_cursor}"'
        return f"""{{
  viewer {{
    login,
    name,
    repositories(
        first: 100,
        orderBy: {{field: UPDATED_AT, direction: DESC}},
        isFork: false,
        after: {owned_after}
    ) {{
      pageInfo {{
        hasNextPage
        endCursor
      }}
      nodes {{
        nameWithOwner
        stargazers {{
          totalCount
        }}
        forkCount
        languages(first: 10, orderBy: {{field: SIZE, direction: DESC}}) {{
          edges {{
            size
            node {{
              name
              color
            }}
          }}
        }}
      }}
    }}
    repositoriesContributedTo(
        first: 100,
        includeUserRepositories: false,
        orderBy: {{field: UPDATED_AT, direction: DESC}},
        contributionTypes: [COMMIT, PULL_REQUEST, REPOSITORY, PULL_REQUEST_REVIEW],
        after: {contrib_after}
    ) {{
      pageInfo {{
        hasNextPage
        endCursor
      }}
      nodes {{
        nameWithOwner
        stargazers {{
          totalCount
        }}
        forkCount
        languages(first: 10, orderBy: {{field: SIZE, direction: DESC}}) {{
          edges {{
            size
            node {{
              name
              color
            }}
          }}
        }}
      }}
    }}
  }}
}}
"""

    @staticmethod
    def contrib_years() -> str:
        """
        :return: GraphQL query to get all years the user has been a contributor
        """
        return """
query {
  viewer {
    contributionsCollection {
      contributionYears
    }
  }
}
"""

    @staticmethod
    def contribs_by_year(year: str) -> str:
        """
        :param year: year to query for
        :return: portion of a GraphQL query with desired info for a given year
        """
        return f"""
    year{year}: contributionsCollection(
        from: "{year}-01-01T00:00:00Z",
        to: "{int(year) + 1}-01-01T00:00:00Z"
    ) {{
      contributionCalendar {{
        totalContributions
      }}
    }}
"""

    @classmethod
    def all_contribs(cls, years: list[str]) -> str:
        """
        :param years: list of years to get contributions for
        :return: query to retrieve contribution information for all user years
        """
        by_years = "\n".join(map(cls.contribs_by_year, years))
        return f"""
query {{
  viewer {{
    {by_years}
  }}
}}
"""


class Stats:
    """
    Retrieve and store statistics about GitHub usage.
    """

    def __init__(
        self,
        username: str,
        access_token: str,
        session: aiohttp.ClientSession,
        exclude_repos: Optional[set] = None,
        exclude_langs: Optional[set] = None,
        consider_forked_repos: bool = False,
    ):
        self.username = username
        self._exclude_repos: set = exclude_repos or set()
        self._exclude_langs: set = exclude_langs or set()
        self._consider_forked_repos = consider_forked_repos
        self.queries = Queries(username, access_token, session)
        self._stats_lock = asyncio.Lock()
        self._stats_loaded = False

        self._name: Optional[str] = None
        self._stargazers: Optional[int] = None
        self._forks: Optional[int] = None
        self._total_contributions: Optional[int] = None
        self._languages: Optional[dict] = None
        self._repos: Optional[set] = None
        self._ignored_repos: set = set()
        self._lines_changed: Optional[tuple[int, int]] = None
        self._views: Optional[int] = None

    async def to_str(self) -> str:
        """
        :return: summary of all available statistics
        """
        languages = await self.languages_proportional
        formatted_languages = "\n  - ".join(
            f"{k}: {v:0.4f}%" for k, v in languages.items()
        )
        lines_changed = await self.lines_changed
        return (
            f"Name: {await self.name}\n"
            f"Stargazers: {await self.stargazers:,}\n"
            f"Forks: {await self.forks:,}\n"
            f"All-time contributions: {await self.total_contributions:,}\n"
            f"Repositories with contributions: {len(await self.all_repos)}\n"
            f"Lines of code added: {lines_changed[0]:,}\n"
            f"Lines of code deleted: {lines_changed[1]:,}\n"
            f"Lines of code changed: {lines_changed[0] + lines_changed[1]:,}\n"
            f"Project page views: {await self.views:,}\n"
            f"Languages:\n  - {formatted_languages}"
        )

    async def get_stats(self) -> None:
        """
        Get lots of summary statistics using one big query. Sets many attributes.
        """
        self._stargazers = 0
        self._forks = 0
        self._languages = {}
        self._repos = set()
        self._ignored_repos = set()

        next_owned = None
        next_contrib = None

        while True:
            raw_results = await self.queries.query(
                Queries.repos_overview(
                    owned_cursor=next_owned, contrib_cursor=next_contrib
                )
            ) or {}

            viewer = raw_results.get("data", {}).get("viewer", {})
            self._name = viewer.get("name") or viewer.get("login", "No Name")

            owned_repos = viewer.get("repositories", {})
            contrib_repos = viewer.get("repositoriesContributedTo", {})

            repos = list(owned_repos.get("nodes", []))
            if self._consider_forked_repos:
                repos += contrib_repos.get("nodes", [])
            else:
                for repo in contrib_repos.get("nodes", []):
                    name = repo.get("nameWithOwner")
                    if name and name not in self._ignored_repos and name not in self._exclude_repos:
                        self._ignored_repos.add(name)

            for repo in repos:
                name = repo.get("nameWithOwner")
                if not name or name in self._repos or name in self._exclude_repos:
                    continue
                self._repos.add(name)
                self._stargazers += repo.get("stargazers", {}).get("totalCount", 0)
                self._forks += repo.get("forkCount", 0)

                for lang in repo.get("languages", {}).get("edges", []):
                    lang_name = lang.get("node", {}).get("name", "Other")
                    if lang_name in self._exclude_langs:
                        continue
                    if lang_name in self._languages:
                        self._languages[lang_name]["size"] += lang.get("size", 0)
                        self._languages[lang_name]["occurrences"] += 1
                    else:
                        self._languages[lang_name] = {
                            "size": lang.get("size", 0),
                            "occurrences": 1,
                            "color": lang.get("node", {}).get("color"),
                        }

            owned_has_next = owned_repos.get("pageInfo", {}).get("hasNextPage", False)
            contrib_has_next = contrib_repos.get("pageInfo", {}).get("hasNextPage", False)

            if owned_has_next or contrib_has_next:
                next_owned = owned_repos.get("pageInfo", {}).get("endCursor", next_owned)
                next_contrib = contrib_repos.get("pageInfo", {}).get("endCursor", next_contrib)
            else:
                break

        langs_total = sum(
            v.get("size", 0) * v.get("occurrences", 1)
            for v in self._languages.values()
        )
        for v in self._languages.values():
            weighted = v.get("size", 0) * v.get("occurrences", 1)
            v["weighted_size"] = weighted
            v["prop"] = 100 * weighted / langs_total if langs_total > 0 else 0

    async def _ensure_stats(self) -> None:
        """Lazily fetch stats if not yet loaded. Thread-safe via asyncio.Lock."""
        async with self._stats_lock:
            if not self._stats_loaded:
                await self.get_stats()
                self._stats_loaded = True

    @property
    async def name(self) -> str:
        """
        :return: GitHub user's name
        """
        await self._ensure_stats()
        assert self._name is not None
        return self._name

    @property
    async def stargazers(self) -> int:
        """
        :return: total number of stargazers on user's repos
        """
        await self._ensure_stats()
        assert self._stargazers is not None
        return self._stargazers

    @property
    async def forks(self) -> int:
        """
        :return: total number of forks on user's repos
        """
        await self._ensure_stats()
        assert self._forks is not None
        return self._forks

    @property
    async def languages(self) -> dict:
        """
        :return: summary of languages used by the user
        """
        await self._ensure_stats()
        assert self._languages is not None
        return self._languages

    @property
    async def languages_proportional(self) -> dict:
        """
        :return: summary of languages used by the user, with proportional usage
        """
        await self._ensure_stats()
        assert self._languages is not None
        return {k: v.get("prop", 0) for k, v in self._languages.items()}

    @property
    async def repos(self) -> set:
        """
        :return: set of user's owned repo names
        """
        await self._ensure_stats()
        assert self._repos is not None
        return self._repos

    @property
    async def all_repos(self) -> set:
        """
        :return: set of user's repos plus all repos they contributed to
        """
        await self._ensure_stats()
        assert self._repos is not None
        return self._repos | self._ignored_repos

    @property
    async def total_contributions(self) -> int:
        """
        :return: count of user's total contributions as defined by GitHub
        """
        if self._total_contributions is not None:
            return self._total_contributions

        years = (
            (await self.queries.query(Queries.contrib_years()))
            .get("data", {})
            .get("viewer", {})
            .get("contributionsCollection", {})
            .get("contributionYears", [])
        )
        by_year = (
            (await self.queries.query(Queries.all_contribs(years)))
            .get("data", {})
            .get("viewer", {})
            .values()
        )
        self._total_contributions = sum(
            year.get("contributionCalendar", {}).get("totalContributions", 0)
            for year in by_year
        )
        return self._total_contributions

    @property
    async def lines_changed(self) -> tuple[int, int]:
        """
        :return: count of total lines added and deleted by the user
        """
        if self._lines_changed is not None:
            return self._lines_changed

        additions = 0
        deletions = 0
        for repo in await self.all_repos:
            r = await self.queries.query_rest(f"/repos/{repo}/stats/contributors")
            for author_obj in r:
                if not isinstance(author_obj, dict) or not isinstance(
                    author_obj.get("author", {}), dict
                ):
                    continue
                author = author_obj.get("author", {}).get("login", "")
                if author.lower() != self.username.lower():
                    continue
                for week in author_obj.get("weeks", []):
                    additions += week.get("a", 0)
                    deletions += week.get("d", 0)

        self._lines_changed = (additions, deletions)
        return self._lines_changed

    @property
    async def views(self) -> int:
        """
        Note: only returns views for the last 14 days (as per GitHub API).
        :return: total number of page views the user's projects have received
        """
        if self._views is not None:
            return self._views

        self._views = sum(
            view.get("count", 0)
            for repo in await self.repos
            for view in (
                await self.queries.query_rest(f"/repos/{repo}/traffic/views")
            ).get("views", [])
        )
        return self._views


###############################################################################
# Main Function
###############################################################################


async def main() -> None:
    """Used mostly for testing; this module is not usually run standalone."""
    access_token = os.getenv("ACCESS_TOKEN")
    user = os.getenv("GITHUB_ACTOR")
    async with aiohttp.ClientSession() as session:
        s = Stats(user, access_token, session)
        print(await s.to_str())


if __name__ == "__main__":
    asyncio.run(main())
