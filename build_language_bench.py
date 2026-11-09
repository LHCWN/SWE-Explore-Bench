"""Build a per-language benchmark file from the released SWE-Explore-Bench.

Selects the instances of one language's repositories and attaches each issue
text, taken from SWE-bench Multilingual, as ``problem_statement``. eval_runner
reads that field when no ``--issue-map`` is given.

Usage:
    uv run python build_language_bench.py BENCH.jsonl --language cpp
"""

import json
from collections import Counter
from collections.abc import Iterable
from pathlib import Path

import typer
from rich.console import Console

console = Console()
app = typer.Typer()

# "cpp" covers both C and C++ repositories.
LANGUAGE_REPOS = {
    "cpp": (
        "fmtlib/fmt",
        "nlohmann/json",
        "micropython/micropython",
        "valkey-io/valkey",
        "redis/redis",
        "jqlang/jq",
    ),
}


def get_org_repo(instance_id: str) -> str:
    """org__repo-123 -> org/repo; empty when the id has no org."""
    if "__" not in instance_id:
        return ""
    org, rest = instance_id.split("__", 1)
    return f"{org}/{rest.rsplit('-', 1)[0]}"


def select_instances(rows: Iterable[dict], repos: Iterable[str]) -> list[dict]:
    wanted = set(repos)
    return [row for row in rows if get_org_repo(row.get("instance_id", "")) in wanted]


def attach_issues(
    instances: Iterable[dict], issues: dict[str, str]
) -> tuple[list[dict], list[str]]:
    """Return the instances with ``problem_statement`` and the ids lacking issue text."""
    attached: list[dict] = []
    missing: list[str] = []
    for instance in instances:
        text = issues.get(instance["instance_id"], "")
        if text.strip():
            attached.append({**instance, "problem_statement": text})
        else:
            missing.append(instance["instance_id"])
    return attached, missing


def load_multilingual_issues() -> dict[str, str]:
    from datasets import load_dataset

    console.print("[cyan]Loading SWE-bench Multilingual dataset...[/cyan]")
    ds = load_dataset("SWE-bench/SWE-bench_Multilingual", split="test")
    return {item["instance_id"]: item["problem_statement"] for item in ds}


@app.command()
def build(
    bench: Path = typer.Argument(
        ..., exists=True, dir_okay=False, help="Released benchmark JSONL (bench.final.public.jsonl)"
    ),
    language: str = typer.Option(
        ..., "-l", "--language", help=f"One of: {', '.join(LANGUAGE_REPOS)}"
    ),
    output: Path | None = typer.Option(
        None, "-o", "--output", help="Output JSONL (default: bench.<language>.jsonl)"
    ),
):
    """Write the benchmark instances of one language, with their issue text."""
    if language not in LANGUAGE_REPOS:
        raise typer.BadParameter(f"unknown language {language!r}", param_hint="--language")
    output = output or Path(f"bench.{language}.jsonl")

    with bench.open(encoding="utf-8") as f:
        rows = [json.loads(line) for line in f if line.strip()]
    instances = select_instances(rows, LANGUAGE_REPOS[language])
    console.print(f"[green]Selected {len(instances)} of {len(rows)} instances[/green]")
    counts = Counter(get_org_repo(i["instance_id"]) for i in instances)
    for repo in LANGUAGE_REPOS[language]:
        line = f"  {repo}: {counts[repo]}"
        console.print(line if counts[repo] else f"[yellow]{line}[/yellow]")
    if not instances:
        console.print(f"[red]No {language} instances in {bench}.[/red]")
        raise typer.Exit(1)

    attached, missing = attach_issues(instances, load_multilingual_issues())
    if missing:
        console.print(f"[red]No issue text for {len(missing)} instances:[/red]")
        for instance_id in missing:
            console.print(f"  [red]{instance_id}[/red]")
        raise typer.Exit(1)

    output.parent.mkdir(parents=True, exist_ok=True)
    with output.open("w", encoding="utf-8", newline="\n") as f:
        for instance in attached:
            f.write(json.dumps(instance, ensure_ascii=False) + "\n")
    console.print(f"\n[bold green]Done![/bold green] Saved {len(attached)} instances to {output}")


if __name__ == "__main__":
    app()
