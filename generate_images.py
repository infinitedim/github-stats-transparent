#!/usr/bin/python3
"""Generate GitHub stats SVG images from templates."""

import asyncio
import os
from pathlib import Path

import aiohttp

from github_stats import Stats

TEMPLATES_DIR = Path("templates")
OUTPUT_DIR = Path("generated")

################################################################################
# Individual Image Generation Functions
################################################################################


async def generate_overview(s: Stats) -> None:
    """
    Generate an SVG badge with summary statistics.
    :param s: Represents user's GitHub statistics
    """
    template = (TEMPLATES_DIR / "overview.svg").read_text(encoding="utf-8")
    lines_changed = (await s.lines_changed)[0] + (await s.lines_changed)[1]

    output = (
        template
        .replace("{{ name }}", await s.name)
        .replace("{{ stars }}", f"{await s.stargazers:,}")
        .replace("{{ forks }}", f"{await s.forks:,}")
        .replace("{{ contributions }}", f"{await s.total_contributions:,}")
        .replace("{{ lines_changed }}", f"{lines_changed:,}")
        .replace("{{ views }}", f"{await s.views:,}")
        .replace("{{ repos }}", f"{len(await s.all_repos):,}")
    )

    OUTPUT_DIR.mkdir(exist_ok=True)
    (OUTPUT_DIR / "overview.svg").write_text(output, encoding="utf-8")


async def generate_languages(s: Stats) -> None:
    """
    Generate an SVG badge with language usage statistics.
    :param s: Represents user's GitHub statistics
    """
    template = (TEMPLATES_DIR / "languages.svg").read_text(encoding="utf-8")

    progress = ""
    lang_list = ""
    sorted_languages = sorted(
        (await s.languages).items(), reverse=True, key=lambda t: t[1].get("size")
    )
    delay_between = 150
    last_index = len(sorted_languages) - 1

    for i, (lang, data) in enumerate(sorted_languages):
        color = data.get("color") or "#000000"
        prop = data.get("prop", 0)

        if i == last_index:
            ratio = (1.0, 0.0)
        elif prop > 50:
            ratio = (0.99, 0.01)
        else:
            ratio = (0.98, 0.02)

        progress += (
            f'<span style="background-color: {color};'
            f"width: {ratio[0] * prop:0.3f}%;"
            f'margin-right: {ratio[1] * prop:0.3f}%;" '
            f'class="progress-item"></span>'
        )
        lang_list += (
            f'\n<li style="animation-delay: {i * delay_between}ms;">\n'
            f'<svg xmlns="http://www.w3.org/2000/svg" class="octicon" style="fill:{color};"\n'
            f'viewBox="0 0 16 16" version="1.1" width="16" height="16"><path\n'
            f'fill-rule="evenodd" d="M8 4a4 4 0 100 8 4 4 0 000-8z"></path></svg>\n'
            f'<span class="lang">{lang}</span>\n'
            f'<span class="percent">{prop:0.2f}%</span>\n'
            f"</li>\n"
        )

    output = (
        template
        .replace("{{ progress }}", progress)
        .replace("{{ lang_list }}", lang_list)
    )

    OUTPUT_DIR.mkdir(exist_ok=True)
    (OUTPUT_DIR / "languages.svg").write_text(output, encoding="utf-8")


################################################################################
# Main Function
################################################################################


async def main() -> None:
    """Generate all stats SVG badges."""
    access_token = os.getenv("ACCESS_TOKEN") or os.getenv("GITHUB_TOKEN")
    if not access_token:
        raise ValueError("A personal access token is required to proceed!")

    user = os.getenv("GITHUB_ACTOR")
    if not user:
        raise ValueError("GITHUB_ACTOR environment variable is not set!")

    raw_excluded = os.getenv("EXCLUDED", "")
    exclude_repos = {r.strip() for r in raw_excluded.split(",") if r.strip()} or None

    raw_excluded_langs = os.getenv("EXCLUDED_LANGS", "")
    exclude_langs = {l.strip() for l in raw_excluded_langs.split(",") if l.strip()} or None

    consider_forked_repos = bool(os.getenv("COUNT_STATS_FROM_FORKS", ""))

    async with aiohttp.ClientSession() as session:
        s = Stats(
            user,
            access_token,
            session,
            exclude_repos=exclude_repos,
            exclude_langs=exclude_langs,
            consider_forked_repos=consider_forked_repos,
        )
        await asyncio.gather(generate_languages(s), generate_overview(s))


if __name__ == "__main__":
    asyncio.run(main())
