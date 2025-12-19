"""
CLI interface for Greek Legal Document RAG system.
"""

import click
from rich.console import Console
from rich.table import Table
from rich.panel import Panel
from rich.progress import track
from pathlib import Path

from .agents.ingestion_agent import ingestion_agent
from .agents.graph import run_multi_agent_query_sync
from .vectorstore.vector_store import get_collection_stats, delete_collection
from .config import get_documents_path

console = Console()


@click.group()
def cli():
    """Greek Legal Document RAG System - Multi-Agent CLI"""
    pass


@cli.command()
@click.option('--force', is_flag=True, help='Re-ingest even if documents already processed')
@click.option('--single', type=str, help='Ingest a single PDF file by name')
def ingest(force, single):
    """Ingest PDF documents into vector store."""
    console.print(Panel("[bold blue]Document Ingestion[/bold blue]"))

    if single:
        # Ingest single document
        docs_path = get_documents_path()
        pdf_path = docs_path / single

        if not pdf_path.exists():
            console.print(f"[red]Error: PDF not found: {single}[/red]")
            return

        console.print(f"Ingesting: {single}")
        result = ingestion_agent.ingest_single_document(pdf_path, force=force)

        if result["status"] == "success":
            console.print(f"[green]✓ Success![/green]")
            console.print(f"  Chunks created: {result['chunks_created']}")
            if result["metadata"]:
                console.print(f"  ΦΕΚ: {result['metadata'].get('fek_number', 'N/A')}")
                console.print(f"  Type: {result['metadata'].get('doc_type', 'N/A')}")
        else:
            console.print(f"[yellow]Skipped or failed: {result['message']}[/yellow]")

    else:
        # Ingest all documents
        console.print("Starting ingestion of all PDFs...")
        result = ingestion_agent.ingest_all_documents(force=force)

        # Display results
        table = Table(title="Ingestion Results")
        table.add_column("Metric", style="cyan")
        table.add_column("Value", style="green")

        table.add_row("Total Documents", str(result["total_docs"]))
        table.add_row("Success", str(result["success"]))
        table.add_row("Failed", str(result["failed"]))
        table.add_row("Skipped", str(result["skipped"]))
        table.add_row("Total Chunks", str(result["total_chunks"]))

        console.print(table)

        if result["failed_files"]:
            console.print("\n[red]Failed files:[/red]")
            for file in result["failed_files"]:
                console.print(f"  - {file}")


@cli.command()
@click.option('--question', '-q', type=str, help='Question to ask')
@click.option('--interactive', '-i', is_flag=True, help='Interactive mode')
def query(question, interactive):
    """Query the document store using multi-agent system."""
    console.print(Panel("[bold blue]Multi-Agent Query System[/bold blue]"))

    if interactive:
        # Interactive mode
        console.print("[dim]Enter 'exit' or 'quit' to stop[/dim]\n")

        while True:
            question = console.input("[bold cyan]Your question:[/bold cyan] ")

            if question.lower() in ['exit', 'quit', 'q']:
                console.print("[green]Goodbye![/green]")
                break

            if not question.strip():
                continue

            # Run query
            _execute_query(question)
            console.print()  # Blank line

    elif question:
        # Single question mode
        _execute_query(question)

    else:
        console.print("[red]Error: Please provide a question with -q or use -i for interactive mode[/red]")


def _execute_query(question: str):
    """Execute a query and display results."""
    with console.status("[bold green]Processing query (agents running in parallel)..."):
        result = run_multi_agent_query_sync(question)

    # Display answer
    console.print(Panel(result["answer"], title="[bold green]Answer[/bold green]", border_style="green"))

    # Display confidence scores
    console.print(f"\n[bold]Confidence:[/bold] {result['confidence']:.1%}")
    console.print(f"[bold]Primary Source:[/bold] {result['primary_source']}")

    # Agent-specific confidences
    console.print("\n[bold]Agent Confidences:[/bold]")
    console.print(f"  • RAG (Local): {result['rag_confidence']:.1%}")
    console.print(f"  • Temporal: {result['temporal_confidence']:.1%}")

    # Display RAG source metadata
    if result.get('rag_source_metadata'):
        metadata = result['rag_source_metadata']
        source_mix = metadata.get('source_mix', 'unknown')
        console.print(f"\n[bold]RAG Information Source:[/bold] {source_mix}")
        if metadata.get('has_pretrained_info'):
            console.print("  [dim](Response includes pretrained knowledge supplementation)[/dim]")

    # Display sources
    if result["sources"]:
        console.print(f"\n[bold]Sources ({len(result['sources'])}):[/bold]")
        for i, source in enumerate(result["sources"][:10], 1):  # Top 10
            text = source.get("text", str(source))
            console.print(f"  [{i}] {text}")


@cli.command()
def stats():
    """Show vector store statistics."""
    console.print(Panel("[bold blue]Vector Store Statistics[/bold blue]"))

    stats = get_collection_stats()

    table = Table(title="Collection Stats")
    table.add_column("Metric", style="cyan")
    table.add_column("Value", style="green")

    table.add_row("Total Documents", str(stats.get("total_documents", 0)))

    doc_types = stats.get("document_types", [])
    if doc_types:
        table.add_row("Document Types", ", ".join(doc_types))

    authorities = stats.get("authorities", [])
    if authorities:
        table.add_row("Authorities", f"{len(authorities)} unique")

    date_range = stats.get("date_range", {})
    if date_range.get("earliest") and date_range.get("latest"):
        table.add_row("Date Range", f"{date_range['earliest']} to {date_range['latest']}")

    console.print(table)


@cli.command()
@click.confirmation_option(prompt='Are you sure you want to delete the entire vector store?')
def reset():
    """Reset (delete) the vector store."""
    console.print("[yellow]Deleting vector store...[/yellow]")

    try:
        delete_collection()
        console.print("[green]✓ Vector store deleted successfully![/green]")
    except Exception as e:
        console.print(f"[red]Error: {e}[/red]")


@cli.command()
def validate():
    """Validate PDFs in documents directory."""
    console.print(Panel("[bold blue]PDF Validation[/bold blue]"))

    docs_path = get_documents_path()
    pdf_files = list(docs_path.glob("*.pdf"))

    if not pdf_files:
        console.print(f"[red]No PDF files found in {docs_path}[/red]")
        return

    console.print(f"Found {len(pdf_files)} PDF files\n")

    from .utils.validators import validate_pdf_file
    from .utils.pdf_extractor import is_text_extractable

    valid_count = 0
    invalid_files = []

    for pdf_path in track(pdf_files, description="Validating PDFs"):
        try:
            validate_pdf_file(pdf_path)

            # Check if text is extractable
            if not is_text_extractable(pdf_path):
                invalid_files.append(f"{pdf_path.name} (no extractable text - may be scanned)")
            else:
                valid_count += 1

        except Exception as e:
            invalid_files.append(f"{pdf_path.name} ({str(e)})")

    # Display results
    console.print(f"\n[green]Valid PDFs: {valid_count}[/green]")

    if invalid_files:
        console.print(f"\n[red]Invalid/Problematic PDFs ({len(invalid_files)}):[/red]")
        for file in invalid_files:
            console.print(f"  - {file}")


@cli.command()
def config_info():
    """Show current configuration."""
    from .config import settings

    console.print(Panel("[bold blue]Configuration[/bold blue]"))

    table = Table()
    table.add_column("Setting", style="cyan")
    table.add_column("Value", style="green")

    table.add_row("OpenAI Model", settings.OPENAI_MODEL)
    table.add_row("Embedding Model", settings.OPENAI_EMBEDDING_MODEL)
    table.add_row("Chunk Size", str(settings.CHUNK_SIZE))
    table.add_row("Retrieval Top K", str(settings.RETRIEVAL_TOP_K))
    table.add_row("", "")
    table.add_row("RAG Agent", "✓" if settings.ENABLE_RAG_AGENT else "✗")
    table.add_row("Temporal Agent", "✓" if settings.ENABLE_TEMPORAL_AGENT else "✗")

    console.print(table)


if __name__ == "__main__":
    cli()
