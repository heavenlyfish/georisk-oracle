#!/usr/bin/env python3
"""
main.py — GeoRisk Oracle CLI

Usage:
    python main.py --event "Taiwan Strait military exercises escalate"
    python main.py --pipeline "Taiwan Strait military exercises escalate"
    python main.py --demo          # Nemotron only
    python main.py --demo --pipeline   # full 3-model pipeline
    python main.py --scan          # auto-scan watchlist via NewsAPI
    python main.py --models        # list available NIM models
"""

import argparse
import sys

from dotenv import load_dotenv
load_dotenv()

from rich.console import Console
from rich.panel import Panel
from rich.table import Table
from rich.rule import Rule
from rich import box

from agents.reasoning_agent import ReasoningAgent
from agents.data_agent import DataAgent
from agents.alert_agent import AlertAgent, URGENCY_EMOJI
from agents.orchestrator import Orchestrator
from config.settings import get_settings

console = Console()

DEMO_EVENT = (
    "China announces sweeping export restrictions on gallium, germanium, and "
    "antimony — critical materials for semiconductor manufacturing — effective "
    "immediately, citing national security. This follows escalating US chip export controls."
)


# ── Display helpers ──────────────────────────────────────────────────────────

def print_assessment(assessment, show_chain: bool = True) -> None:
    urgency_icon = URGENCY_EMOJI.get(assessment.urgency, "⚪")
    score_color = "red" if assessment.risk_score >= 80 else "yellow" if assessment.risk_score >= 60 else "green"

    console.print(Panel(
        f"[bold]{assessment.event_summary}[/bold]\n\n"
        f"{urgency_icon} Urgency: [bold]{assessment.urgency}[/bold]  |  "
        f"Risk Score: [{score_color}]{assessment.risk_score}/100[/{score_color}]  |  "
        f"Horizon: {assessment.time_horizon}",
        title="[bold blue]Nemotron — Risk Assessment[/bold blue]",
        border_style="blue",
    ))

    if show_chain and assessment.causal_chain:
        table = Table(title="Causal Chain", box=box.SIMPLE_HEAVY, show_lines=True)
        table.add_column("Step", style="cyan", no_wrap=True)
        table.add_column("Entities", style="yellow")
        table.add_column("Impact", style="white")
        table.add_column("Conf", style="green", justify="right")
        for cs in assessment.causal_chain:
            table.add_row(
                cs.step,
                ", ".join(cs.entities[:3]),
                cs.impact,
                f"{cs.confidence:.0%}",
            )
        console.print(table)

    console.print(Panel(
        f"[bold]Sectors:[/bold]  {', '.join(assessment.affected_sectors)}\n"
        f"[bold]Companies:[/bold] {', '.join(assessment.affected_companies) or '—'}\n"
        f"[bold]Commodities:[/bold] {', '.join(assessment.affected_commodities) or '—'}",
        title="Exposure",
        border_style="yellow",
    ))

    hedge_text = "\n".join(f"• {h}" for h in assessment.hedge_signals) or "None"
    console.print(Panel(hedge_text, title="Nemotron Hedge Signals", border_style="green"))
    console.print(Panel(assessment.reasoning, title="Nemotron Reasoning", border_style="dim"))


def print_pipeline_result(result) -> None:
    """Pretty-print a full PipelineResult (all 3 models)."""
    settings = get_settings()

    # ── Stage 1: Llama screener ──
    console.print(Rule("[bold cyan]Stage 1 — Llama 3.3 70B: Triage[/bold cyan]"))
    rel_icon = "✅" if result.screen.relevant else "❌"
    console.print(Panel(
        f"{rel_icon} Relevant: [bold]{result.screen.relevant}[/bold]  |  "
        f"Confidence: {result.screen.confidence:.0%}  |  "
        f"Severity: [bold]{result.screen.estimated_severity}[/bold]\n\n"
        f"Reason: {result.screen.reason}\n"
        f"Entities: {', '.join(result.screen.key_entities)}",
        title=f"[cyan]Screener ({settings.llama_model})[/cyan]",
        border_style="cyan",
    ))

    if result.skipped:
        console.print(f"\n[yellow]Event filtered as non-relevant. Pipeline stopped.[/yellow]")
        return

    # ── Stage 2: Nemotron assessment ──
    console.print(Rule("[bold blue]Stage 2 — Nemotron: Causal Chain Reasoning[/bold blue]"))
    if result.assessment:
        print_assessment(result.assessment)

    # ── Stage 3: Nemotron synthesis memo ──
    console.print(Rule("[bold magenta]Stage 3 — Nemotron: Investor Memo Synthesis[/bold magenta]"))
    if result.memo:
        console.print(Panel(result.memo, title="[magenta]Nemotron Investor Memo[/magenta]", border_style="magenta"))

    # ── Alert status ──
    if result.alert_sent:
        console.print("\n[green]Telegram alert sent.[/green]")
    elif result.assessment and result.assessment.risk_score >= settings.risk_threshold:
        console.print(f"\n[dim]Alert suppressed (--no-alert). Score: {result.assessment.risk_score}/100.[/dim]")
    else:
        score = result.assessment.risk_score if result.assessment else "?"
        console.print(f"\n[dim]No alert — score {score} below threshold {settings.risk_threshold}.[/dim]")


# ── Commands ─────────────────────────────────────────────────────────────────

def cmd_event(event_text: str, verbose: bool, no_alert: bool) -> None:
    settings = get_settings()
    agent = ReasoningAgent(verbose=verbose)
    alert_agent = AlertAgent()

    console.print(f"\n[bold]Analyzing (Nemotron only):[/bold] {event_text}\n")
    with console.status(f"[cyan]Calling {settings.nim_model}...[/cyan]"):
        try:
            assessment = agent.analyze(event_text)
        except Exception as e:
            console.print(f"[red][ERROR] {e}[/red]")
            sys.exit(1)

    print_assessment(assessment)
    if not no_alert and alert_agent.should_alert(assessment):
        alert_agent.process(assessment)


def cmd_pipeline(event_text: str, verbose: bool, no_alert: bool) -> None:
    settings = get_settings()
    orch = Orchestrator(verbose=verbose)

    console.print(f"\n[bold]Full pipeline (Llama → Nemotron → Claude):[/bold]\n{event_text}\n")

    with console.status("[cyan]Running multi-model pipeline...[/cyan]"):
        try:
            result = orch.run(event_text, skip_screen=False)
        except Exception as e:
            console.print(f"[red][ERROR] Pipeline failed: {e}[/red]")
            sys.exit(1)

    # Override alert if --no-alert
    if no_alert and result.alert_sent:
        result.alert_sent = False

    print_pipeline_result(result)


def cmd_scan(verbose: bool, no_alert: bool, use_pipeline: bool) -> None:
    settings = get_settings()
    data_agent = DataAgent()

    console.print("\n[bold]Scanning watchlist...[/bold]\n")
    if settings.news_api_key:
        events = data_agent.fetch_news()
    else:
        console.print("[yellow]No NEWS_API_KEY — using watchlist hotspot events.[/yellow]\n")
        events = data_agent.get_watchlist_events()[:3]

    if not events:
        console.print("[red]No events found.[/red]")
        sys.exit(1)

    console.print(f"Found [bold]{len(events)}[/bold] events.\n")

    if use_pipeline:
        orch = Orchestrator(verbose=verbose)
        for i, event in enumerate(events, 1):
            console.print(f"\n[bold cyan]─── Event {i}/{len(events)} ───[/bold cyan]")
            try:
                result = orch.run(event)
                print_pipeline_result(result)
            except Exception as e:
                console.print(f"[red][ERROR] {e}[/red]")
    else:
        agent = ReasoningAgent(verbose=verbose)
        alert_agent = AlertAgent()
        for i, event in enumerate(events, 1):
            console.print(f"\n[bold cyan]─── Event {i}/{len(events)} ───[/bold cyan]")
            try:
                assessment = agent.analyze(event)
                print_assessment(assessment, show_chain=False)
                if not no_alert:
                    alert_agent.process(assessment)
            except Exception as e:
                console.print(f"[red][ERROR] {e}[/red]")


def cmd_models() -> None:
    settings = get_settings()
    agent = ReasoningAgent()
    console.print("\n[bold]Available NIM models:[/bold]\n")
    models = agent.list_models()
    if models:
        for m in models:
            tags = []
            if m == settings.nim_model:
                tags.append("[blue]Nemotron[/blue]")
            if m == settings.llama_model:
                tags.append("[cyan]Llama screener[/cyan]")
            tag_str = f"  ← {', '.join(tags)}" if tags else ""
            console.print(f"  • {m}{tag_str}")
    else:
        console.print("[yellow]Could not retrieve model list (check NIM_API_KEY).[/yellow]")


def cmd_demo(use_pipeline: bool, verbose: bool) -> None:
    console.print(f"\n[bold yellow]DEMO MODE[/bold yellow] — event:\n")
    console.print(f"[italic]{DEMO_EVENT}[/italic]\n")
    if use_pipeline:
        cmd_pipeline(DEMO_EVENT, verbose=verbose, no_alert=True)
    else:
        cmd_event(DEMO_EVENT, verbose=verbose, no_alert=True)


# ── Entry point ───────────────────────────────────────────────────────────────

def main():
    parser = argparse.ArgumentParser(
        description="GeoRisk Oracle — Multi-model geopolitical risk agent (Llama + Nemotron + Claude)"
    )
    group = parser.add_mutually_exclusive_group(required=True)
    group.add_argument("--event", "-e", type=str, metavar="TEXT",
                       help="Analyze with Nemotron only")
    group.add_argument("--pipeline", "-p", type=str, metavar="TEXT",
                       help="Run full Llama → Nemotron → Claude pipeline")
    group.add_argument("--scan", "-s", action="store_true",
                       help="Scan watchlist headlines")
    group.add_argument("--models", "-m", action="store_true",
                       help="List available NIM models")
    group.add_argument("--demo", "-d", action="store_true",
                       help="Run built-in demo event")

    parser.add_argument("--verbose", "-v", action="store_true")
    parser.add_argument("--no-alert", action="store_true")
    parser.add_argument("--full", action="store_true",
                        help="Use full pipeline with --scan or --demo")

    args = parser.parse_args()

    if args.event:
        cmd_event(args.event, args.verbose, args.no_alert)
    elif args.pipeline:
        cmd_pipeline(args.pipeline, args.verbose, args.no_alert)
    elif args.scan:
        cmd_scan(args.verbose, args.no_alert, use_pipeline=args.full)
    elif args.models:
        cmd_models()
    elif args.demo:
        cmd_demo(use_pipeline=args.full, verbose=args.verbose)


if __name__ == "__main__":
    main()
