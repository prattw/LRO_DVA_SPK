from __future__ import annotations

from pathlib import Path

import typer

from vantage_preprocess.chunking.config import ChunkingConfig
from vantage_preprocess.logging_config import configure_logging
from vantage_preprocess.pipeline.run import run_pipeline

app = typer.Typer(
    name="vantage-preprocess",
    help="Preprocess documents into JSONL/CSV/XLSX for Vantage-style ingestion.",
)


@app.command("run")
def run_cmd(
    input_path: Path = typer.Argument(..., exists=True, help="File or directory to process"),
    out: Path = typer.Option(Path("./out"), "--out", "-o", help="Output directory"),
    formats: str = typer.Option(
        "jsonl,csv,txt",
        "--formats",
        "-f",
        help="Comma-separated: jsonl, csv, xlsx, txt (portal .txt for Army Vantage web upload)",
    ),
    recursive: bool = typer.Option(False, "--recursive", "-r", help="Recurse into subfolders"),
    max_words: int = typer.Option(2000, "--max-words", help="Hard maximum words per chunk"),
    min_words: int = typer.Option(500, "--min-words", help="Target minimum words per chunk"),
    verbose: bool = typer.Option(False, "--verbose", "-v"),
) -> None:
    configure_logging("DEBUG" if verbose else "INFO")

    fmt_list = [x.strip() for x in formats.split(",") if x.strip()]
    chunking = ChunkingConfig(min_words=min_words, max_words=max_words)
    result = run_pipeline(
        input_path=input_path,
        out_dir=out,
        formats=fmt_list,
        recursive=recursive,
        chunking=chunking,
    )

    typer.echo(f"Processed {result.files_processed} file(s), {result.rows_written} chunk row(s).")
    typer.echo(f"Manifest: {result.manifest_path}")
    if result.errors:
        typer.echo(typer.style("Errors:", fg=typer.colors.RED))
        for e in result.errors:
            typer.echo(f"  {e}")


def main() -> None:
    app()


if __name__ == "__main__":
    main()
