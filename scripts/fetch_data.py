"""Fetch public GitHub stats for the profile cards and save them to data/github.json.

Runs inside the GitHub Action. Needs GITHUB_TOKEN (or GH_PAT for private contributions too).
"""
import json
import os
import pathlib
import urllib.request

LOGIN = os.environ.get("GH_LOGIN", "abbishekrajh")
TOKEN = os.environ["GITHUB_TOKEN"]
OUT = pathlib.Path(__file__).resolve().parent.parent / "data" / "github.json"

QUERY = """
query($login: String!) {
  user(login: $login) {
    name
    repositories(privacy: PUBLIC, ownerAffiliations: OWNER, isFork: false, first: 100,
                 orderBy: {field: PUSHED_AT, direction: DESC}) {
      totalCount
      nodes { name description stargazerCount primaryLanguage { name color } url }
    }
    contributionsCollection {
      contributionCalendar {
        totalContributions
        weeks { contributionDays { date contributionCount } }
      }
    }
  }
}
"""


def main() -> None:
    req = urllib.request.Request(
        "https://api.github.com/graphql",
        data=json.dumps({"query": QUERY, "variables": {"login": LOGIN}}).encode(),
        headers={"Authorization": f"bearer {TOKEN}", "Content-Type": "application/json"},
    )
    with urllib.request.urlopen(req, timeout=30) as r:
        payload = json.load(r)
    if "errors" in payload:
        raise SystemExit(f"GraphQL error: {payload['errors']}")
    user = payload["data"]["user"]
    cal = user["contributionsCollection"]["contributionCalendar"]
    days = [d for w in cal["weeks"] for d in w["contributionDays"]]
    data = {
        "login": LOGIN,
        "name": user["name"],
        "total_contributions": cal["totalContributions"],
        "public_repos": user["repositories"]["totalCount"],
        "repos": [
            {
                "name": n["name"],
                "description": n["description"],
                "stars": n["stargazerCount"],
                "language": (n["primaryLanguage"] or {}).get("name"),
                "url": n["url"],
            }
            for n in user["repositories"]["nodes"]
        ],
        "days": [{"date": d["date"], "count": d["contributionCount"]} for d in days],
    }
    OUT.parent.mkdir(parents=True, exist_ok=True)
    OUT.write_text(json.dumps(data, indent=1))
    print(f"saved {len(days)} days, {data['total_contributions']} contributions -> {OUT}")


if __name__ == "__main__":
    main()
