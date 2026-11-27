#!/usr/bin/env python3
"""
CLI Runner for Enterprise Database Discovery & Governance Framework (agentic-discovery).
Features:
  - Zero-secret connection profiles (connections.json)
  - Masked runtime password prompting (getpass)
  - Auto-provisioning for Claude Managed Agents
  - Step-by-step telemetry across Gates G1-G6
  - Comprehensive audit trail and executive report generation
  - Post-run Natural Language Q&A assistant (NLP)
"""
from __future__ import annotations

import argparse
import getpass
import os
from pathlib import Path
import sys

# Ensure project root is in sys.path
ROOT_DIR = Path(__file__).resolve().parent
sys.path.insert(0, str(ROOT_DIR))

from core.connections import ConnectionManager, ConnectionProfile
from core.managed_agents import check_managed_agents, ensure_managed_agents_provisioned, provision
from core.orchestrator import DiscoveryOrchestrator
from core.qa_engine import DiscoveryQAEngine
from core.state import StateManager

try:
    from rich.console import Console
    from rich.table import Table
    from rich.panel import Panel
    from rich.prompt import Prompt
    console = Console()
except ImportError:
    console = None
    Prompt = None


def print_banner():
    msg = """
╔══════════════════════════════════════════════════════════════════════════════╗
║  🛡️  AGENTIC DISCOVERY: DATABASE PROFILING & DATA QUALITY AUDITING (S1-S7)    ║
║  Managed Agents Architecture: Direct DB Connection & Step Enforcement        ║
╚══════════════════════════════════════════════════════════════════════════════╝
"""
    if console:
        console.print(Panel(msg.strip(), style="bold #D97746"))
    else:
        print(msg)


def prompt_user(text_prompt: str, default: str = "") -> str:
    if console and Prompt:
        val = Prompt.ask(f"[bold #D97746]{text_prompt}[/bold #D97746]", default=default)
        return val.strip()
    default_hint = f" [{default}]" if default else ""
    try:
        val = input(f"{text_prompt}{default_hint}: ").strip()
        return val if val else default
    except (EOFError, KeyboardInterrupt):
        print("\nAborted.")
        sys.exit(0)


def display_connections_table(conns: list[ConnectionProfile]):
    if console:
        tbl = Table(title="Saved Zero-Secret Connection Templates (connections.json)", style="#D97746")
        tbl.add_column("#", style="bold cyan", width=4)
        tbl.add_column("Profile Name", style="bold #ECE8E1", width=18)
        tbl.add_column("Dialect", style="bold", width=12)
        tbl.add_column("Target Destination", style="dim", width=35)
        tbl.add_column("Schema", style="dim", width=10)
        tbl.add_column("Password Env Var", style="dim")
        for i, c in enumerate(conns, 1):
            tbl.add_row(str(i), c.name, c.dialect.upper(), c.display_target, c.schema, c.password_env_var or "—")
        console.print(tbl)
    else:
        print("\nSaved Zero-Secret Connection Templates:")
        for i, c in enumerate(conns, 1):
            print(f"  [{i}] {c.name:<18} ({c.dialect.upper():<10}) -> {c.display_target}")


def interactive_wizard(conn_mgr: ConnectionManager) -> tuple[str, str, list[str], str]:
    """Interactive startup wizard: choose connection or add new connection."""
    conns = conn_mgr.list_connections()

    if console:
        console.print("\n[bold #ECE8E1]🧙 Interactive Setup Wizard[/bold #ECE8E1]\n"
                      "[dim]Select an existing database connection profile or register a new one:[/dim]\n")
    else:
        print("\n🧙 Interactive Setup Wizard\nSelect an existing database connection profile or register a new one:\n")

    display_connections_table(conns)

    if console:
        console.print(f"  [bold cyan][{len(conns) + 1}][/bold cyan] [bold green]➕ Add a New Database Connection Profile[/bold green]\n")
    else:
        print(f"  [{len(conns) + 1}] ➕ Add a New Database Connection Profile\n")

    choice_str = prompt_user("Select Connection Choice", default="1")
    try:
        choice_idx = int(choice_str)
    except ValueError:
        choice_idx = 1

    selected_url = ""
    selected_schema = "main"

    if choice_idx == len(conns) + 1:
        # Add new connection flow
        if console:
            console.print("\n[bold #D97746]➕ Registering New Zero-Secret Connection Template[/bold #D97746]")
        else:
            print("\n➕ Registering New Zero-Secret Connection Template")

        new_name = prompt_user("Profile Name (e.g. prod_dw, crm_stage)", default="my_db")
        dialect = prompt_user("Database Dialect (sqlite, postgresql, snowflake, oracle, mysql, mssql)", default="postgresql").lower()

        if dialect == "sqlite":
            new_url = prompt_user("Enter SQLite DB Path (e.g. sample/sample.db)", default="sample/sample.db")
            if not new_url.startswith("sqlite:///"):
                new_url = f"sqlite:///{new_url}"
            new_schema = "main"
            ok, msg, prof = conn_mgr.add_connection(new_name, dialect=dialect, url=new_url, schema=new_schema)
            selected_url = new_url
            selected_schema = new_schema
        else:
            host = prompt_user("Database Host / Account", default="localhost")
            port_str = prompt_user("Database Port (press Enter for default)", default="5432" if dialect == "postgresql" else "1521" if dialect == "oracle" else "3306")
            port = int(port_str) if port_str.isdigit() else None
            db_name = prompt_user("Database Name", default="mydb")
            user = prompt_user("Database Username", default="db_user")
            new_schema = prompt_user("Target Schema", default="public")

            ok, msg, prof = conn_mgr.add_connection(
                name=new_name,
                dialect=dialect,
                host=host,
                port=port,
                database=db_name,
                username=user,
                schema=new_schema
            )
            selected_schema = new_schema
            # Prompt securely for password
            runtime_pw = getpass.getpass(f"Enter password for {new_name} ({user}@{host}): ")
            selected_url = conn_mgr.resolve_url(prof, runtime_password=runtime_pw)

        if console:
            console.print(f"[bold green]✔ {msg}[/bold green]")
        else:
            print(f"✔ {msg}")

    else:
        # Selected existing profile
        chosen_profile = conns[choice_idx - 1] if (1 <= choice_idx <= len(conns)) else conns[0]
        selected_schema = chosen_profile.schema
        selected_url = conn_mgr.resolve_url(chosen_profile, prompt_if_needed=True)

        if console:
            console.print(f"\n[bold green]✔ Selected profile:[/bold green] [bold]{chosen_profile.name}[/bold] ({chosen_profile.display_target})")
        else:
            print(f"\n✔ Selected profile: {chosen_profile.name} ({chosen_profile.display_target})")

    # Target table filter
    tables_input = prompt_user("Enter Table Names to profile (comma-separated, or 'ALL')", default="ALL")
    target_tables = None
    if tables_input.upper() != "ALL" and tables_input.strip():
        target_tables = [t.strip() for t in tables_input.split(",") if t.strip()]

    # Mode selection
    if console:
        console.print("\n[bold]Select Execution Output Option:[/bold]\n"
                      "  [cyan]1)[/cyan] [bold]Both[/bold] (Statistical Profiling + 6-Dimension DQ Checks) [Recommended]\n"
                      "  [cyan]2)[/cyan] [bold]Profiling[/bold] only\n"
                      "  [cyan]3)[/cyan] [bold]Quality Checks[/bold] only\n")
    else:
        print("\nSelect Execution Output Option:\n  1) Both (Profiling + DQ Checks)\n  2) Profiling only\n  3) Quality Checks only\n")

    mode_choice = prompt_user("Enter choice (1/2/3 or Both/Profiling/Checks)", default="1")
    if mode_choice in ("1", "both", "Both"):
        mode = "both"
    elif mode_choice in ("2", "profiling", "Profiling"):
        mode = "profiling"
    elif mode_choice in ("3", "checks", "Checks"):
        mode = "checks"
    else:
        mode = "both"

    return selected_url, selected_schema, target_tables, mode


def run_interactive_qa_loop(qa_engine: DiscoveryQAEngine) -> None:
    """Provides an interactive conversational NLP Q&A session on the run results."""
    banner = (
        "[bold #ECE8E1]💬 Interactive Governance & Data Quality Q&A Session[/bold #ECE8E1]\n"
        "[dim]You can now ask questions about table health, violations, defects, remediation, and schema structure.\n"
        "Examples:\n"
        "  • 'Show all data quality violations'\n"
        "  • 'Why is table customers NEEDS_ATTENTION?'\n"
        "  • 'How to fix defects in table orders?'\n"
        "  • 'Show columns and types of table products'\n"
        "Type your question below, or press Enter / type 'exit' to finish.[/dim]"
    )
    if console:
        console.print(Panel(banner, style="#D97746"))
    else:
        print("\n" + "=" * 65)
        print("💬 Interactive Governance & Data Quality Q&A Session")
        print("Ask any question about table health, violations, or remediation.")
        print("Press Enter or type 'exit' / 'q' to finish.")
        print("=" * 65)

    while True:
        try:
            if console and Prompt:
                user_q = Prompt.ask("\n[bold #D97746]❓ Ask a Question[/bold #D97746] [dim](or 'exit' to quit)[/dim]", default="")
            else:
                user_q = input("\n❓ Ask a Question (or 'exit' to quit): ").strip()
        except (EOFError, KeyboardInterrupt):
            print("\nExiting Q&A session.")
            break

        if not user_q or user_q.lower() in ("exit", "quit", "q", "no", "done", "bye"):
            if console:
                console.print("[bold green]✔ Q&A session completed. Have a great day![/bold green]\n")
            else:
                print("✔ Q&A session completed.\n")
            break

        ans = qa_engine.answer_question(user_q)
        if console:
            console.print(Panel(ans, title=f"🤖 DA_CL_Discovery_GovernanceReviewerAgent (Run: {qa_engine.run_id})", border_style="cyan"))
        else:
            print(f"\n--- 🤖 DA_CL_Discovery_GovernanceReviewerAgent (Run: {qa_engine.run_id}) ---")
            print(ans)
            print("-" * 40)


def main():
    parser = argparse.ArgumentParser(description="Autonomous Database Discovery & Governance CLI")
    parser.add_argument("command", nargs="?", default=None, choices=["start", "run", "list", "add", "ask", "qa", "provision", "check", "test"], help="Command shortcut")
    parser.add_argument("query", nargs="*", help="Natural language query string for ask command")
    parser.add_argument("--conn", type=str, default=None, help="Name of saved connection profile")
    parser.add_argument("--db-url", type=str, default=None, help="Direct database connection URL")
    parser.add_argument("--schema", type=str, default="main", help="Target schema name")
    parser.add_argument("--tables", type=str, default=None, help="Comma-separated list of target tables")
    parser.add_argument("--mode", type=str, choices=["profiling", "checks", "both"], default="both", help="Execution mode")
    parser.add_argument("--output-dir", type=str, default=None, help="Custom output directory for deliverables")
    parser.add_argument("--list-conns", action="store_true", help="List all saved connection profiles")
    parser.add_argument("--add-conn", nargs="+", help="Add new connection: <name> <dialect> [host] [port] [db] [user] [schema]")
    parser.add_argument("--llm-mode", type=str, choices=["offline", "api", "managed"], default=None, help="LLM runtime mode")
    parser.add_argument("--provision-managed-agents", action="store_true", help="Provision SKILL.md agents into managed_agents.json")
    parser.add_argument("--check-managed-agents", action="store_true", help="Audit drift between skills and managed_agents.json")
    parser.add_argument("--dry-run", action="store_true", help="Preview provisioning plan without saving")
    parser.add_argument("--resume", action="store_true", help="Resume from latest checkpoint")
    parser.add_argument("--qa", action="store_true", help="Launch interactive conversational Q&A session after discovery completes")
    parser.add_argument("--run-id", type=str, default=None, help="Target specific run ID for Q&A or reports (e.g. 20261127T104512_shop)")

    args = parser.parse_args()

    # 1. NLP Ask Question & Interactive QA Command
    if args.command in ("ask", "qa"):
        target_run_id = args.run_id
        query_tokens = list(args.query) if args.query else []

        # Check if first token in query is a specified run ID (e.g. `python run.py ask 20261127T104512_shop ...`)
        if not target_run_id and query_tokens:
            first_tok = query_tokens[0]
            # Match if folder exists in runs/ or follows run_id timestamp pattern
            if (ROOT_DIR / "runs" / first_tok).is_dir() or re.match(r"^\d{8}[_T]\w+$", first_tok):
                target_run_id = first_tok
                query_tokens = query_tokens[1:]

        available_runs = StateManager.list_runs(ROOT_DIR)

        # Interactive picker if run_id not provided and multiple runs exist
        if not target_run_id:
            if not available_runs:
                print("No previous pipeline runs found in runs/. Run `python run.py start` first.")
                sys.exit(1)
            target_run_id = available_runs[0]["run_id"]

        qa = DiscoveryQAEngine(ROOT_DIR, run_id=target_run_id)
        question_text = " ".join(query_tokens).strip()

        # If 'qa' command or no question passed, launch interactive Q&A loop
        if args.command == "qa" or not question_text:
            print_banner()
            if not args.run_id and len(available_runs) > 1 and not (args.query and args.query[0] == target_run_id):
                if console:
                    console.print("\n[bold #D97746]Available Discovery Runs:[/bold #D97746]")
                    for idx, r in enumerate(available_runs[:5], 1):
                        console.print(f"  [cyan]{idx})[/cyan] [bold]{r['run_id']}[/bold] [dim]({r['dialect'].upper()} / {r['schema']}, {r['table_count']} tables, {r['triages_count']} triaged)[/dim]")
                    pick = prompt_user(f"Select Run ID (1-{min(len(available_runs), 5)}, default: 1 ({target_run_id}))", default="1")
                    if pick.isdigit() and 1 <= int(pick) <= len(available_runs):
                        target_run_id = available_runs[int(pick) - 1]["run_id"]
                        qa = DiscoveryQAEngine(ROOT_DIR, run_id=target_run_id)

            run_interactive_qa_loop(qa)
            sys.exit(0)

        ans = qa.answer_question(question_text)
        if console:
            console.print(Panel(ans, title=f"🤖 DA_CL_Discovery_GovernanceReviewerAgent (Run: {qa.run_id})", border_style="cyan"))
        else:
            print(f"\n--- 🤖 DA_CL_Discovery_GovernanceReviewerAgent (Run: {qa.run_id}) ---\n{ans}")
        sys.exit(0)

    print_banner()

    # 2. Auto-Provision Managed Agents if unprovisioned
    auto_plan = ensure_managed_agents_provisioned()
    if auto_plan and console:
        console.print(f"[bold green]✔ Auto-provisioned {len(auto_plan)} Managed Agents into managed_agents.json[/bold green]")

    conn_mgr = ConnectionManager()

    # 3. Connection management commands
    if args.list_conns or args.command == "list":
        display_connections_table(conn_mgr.list_connections())
        sys.exit(0)

    if args.add_conn or args.command == "add":
        parts = args.add_conn or []
        if len(parts) < 2:
            print("Error: --add-conn requires at least <name> and <dialect>.", file=sys.stderr)
            sys.exit(1)
        name, dialect = parts[0], parts[1]
        host = parts[2] if len(parts) > 2 else "localhost"
        port = int(parts[3]) if len(parts) > 3 and parts[3].isdigit() else None
        db_name = parts[4] if len(parts) > 4 else "mydb"
        user = parts[5] if len(parts) > 5 else "db_user"
        schema = parts[6] if len(parts) > 6 else "public"

        ok, msg, _ = conn_mgr.add_connection(name, dialect, host, port, db_name, user, schema)
        if ok:
            print(f"✔ {msg}")
            sys.exit(0)
        else:
            print(f"✖ {msg}", file=sys.stderr)
            sys.exit(1)

    # 4. Managed Agents Control Plane commands
    if args.check_managed_agents or args.command == "check":
        ok, drifts = check_managed_agents()
        if ok:
            if console:
                console.print("[bold green]✔ Managed Agents Registry is fully in sync with skills/.[/bold green]")
            else:
                print("✔ Managed Agents Registry is fully in sync with skills/.")
            sys.exit(0)
        else:
            if console:
                console.print("[bold red]✖ Managed Agents Registry drift detected:[/bold red]")
                for d in drifts:
                    console.print(f"  - {d}")
            else:
                print("✖ Managed Agents Registry drift detected:")
                for d in drifts:
                    print(f"  - {d}")
            sys.exit(1)

    if args.provision_managed_agents or args.command == "provision":
        plan = provision(dry_run=args.dry_run)
        if console:
            tbl = Table(title="Provisioning Plan (Managed Agents)")
            tbl.add_column("Skill / Agent", style="cyan")
            tbl.add_column("Status", style="bold")
            tbl.add_column("Agent ID", style="dim")
            tbl.add_column("Hash", style="dim")
            for skill, details in plan.items():
                tbl.add_row(skill, details.get("status", "unknown"), details.get("agent_id", "-"), details.get("config_hash", "-")[:16])
            console.print(tbl)
            if not args.dry_run:
                console.print("[bold green]✔ Successfully provisioned to managed_agents.json[/bold green]")
        else:
            print("Provisioning Plan:")
            for s, d in plan.items():
                print(f"  {s}: {d.get('status')} ({d.get('agent_id')})")
        sys.exit(0)

    # 5. Interactive vs Direct execution
    is_interactive = (args.command == "start") or (args.conn is None and args.db_url is None and len(sys.argv) <= 2)

    if is_interactive and args.command != "run":
        db_url, schema, target_tables, mode = interactive_wizard(conn_mgr)
    else:
        mode = args.mode
        schema = args.schema
        target_tables = [t.strip() for t in args.tables.split(",")] if args.tables else None

        if args.conn:
            prof = conn_mgr.get_connection(args.conn)
            if not prof:
                print(f"Error: Connection profile '{args.conn}' not found in connections.json.", file=sys.stderr)
                sys.exit(1)
            db_url = conn_mgr.resolve_url(prof, prompt_if_needed=True)
            schema = prof.schema
        else:
            db_url = args.db_url or "sqlite:///sample/sample.db"

    orchestrator = DiscoveryOrchestrator(
        db_url=db_url,
        base_dir=Path(args.output_dir) if args.output_dir else ROOT_DIR,
        llm_mode=args.llm_mode
    )

    if console:
        console.print(f"\n[bold #D97746]🚀 Discovery Pipeline Execution Initialized[/bold #D97746]")
        console.print(f"  • [bold]Run ID:[/bold] <code>{orchestrator.run_id}</code>")
        console.print(f"  • [bold]Database Engine:[/bold] [bold cyan]{orchestrator.db.dialect_label}[/bold cyan]")
        console.print(f"  • [bold]Execution Mode:[/bold] [bold]{mode.upper()}[/bold] | [bold]LLM Mode:[/bold] {orchestrator.llm.mode.upper()}\n")
        console.print("[dim]────────── Live Execution Telemetry & Quality Gates ──────────[/dim]")
    else:
        print(f"\n🚀 Discovery Pipeline Execution Initialized: Run ID {orchestrator.run_id}")
        print(f"Database: {orchestrator.db.dialect_label} ({schema}) | Mode: {mode.upper()}\n")

    def log_progress(stage: str, msg: str):
        if console:
            if "GATE" in stage:
                console.print(f"  [bold green]✔ {stage}:[/bold green] [dim]{msg}[/dim]")
            elif "PHASE" in stage:
                console.print(f"\n[bold #D97746]▶ {stage}:[/bold #D97746] [bold]{msg}[/bold]")
            else:
                console.print(f"    [dim]• {stage}: {msg}[/dim]")
        else:
            print(f"[{stage}] {msg}")

    try:
        reports = orchestrator.run_pipeline(
            schema_name=schema,
            target_tables=target_tables,
            mode=mode,
            progress_callback=log_progress
        )

        audit_summary = orchestrator.audit.summary()

        if console:
            console.print("\n[bold green]✔ Pipeline Completed Successfully (Gates G1–G6 OPEN)[/bold green]\n")

            # Audit metrics summary
            summary_tbl = Table(title="Audit Telemetry Summary (S5 Compliance)", style="#DDA15E")
            summary_tbl.add_column("Audit Metric", style="bold #ECE8E1")
            summary_tbl.add_column("Value", style="cyan")
            summary_tbl.add_row("Total Telemetry Events Logged", str(audit_summary["total_events"]))
            summary_tbl.add_row("Quality Gate Decisions Enforced", str(audit_summary["gate_decisions"]))
            summary_tbl.add_row("SQL Queries Executed (Read-Only)", str(audit_summary["sql_queries_executed"]))
            summary_tbl.add_row("Data Quality Violations Detected", str(audit_summary["total_violations_found"]))
            console.print(summary_tbl)
            console.print("")

            # Generated Deliverables
            tbl = Table(title="Generated Governance Deliverables & Saved Report Locations", style="#D97746")
            tbl.add_column("Deliverable", style="bold #ECE8E1", width=18)
            tbl.add_column("Format", style="dim", width=10)
            tbl.add_column("Size", style="cyan", width=12)
            tbl.add_column("Location / Absolute File Path", style="dim")

            for k, v in reports.items():
                p = Path(v)
                size_str = f"{p.stat().st_size / 1024:.1f} KB" if p.exists() else "-"
                ext = p.suffix.upper().replace(".", "")
                tbl.add_row(k.upper(), ext, size_str, str(p))

            console.print(tbl)
            console.print(f"\n[bold #D97746]🌐 Interactive Claude-Themed Audit Report:[/bold #D97746] [link=file:///{reports.get('html')}]{reports.get('html')}[/link]\n")
        else:
            print("\n✔ Pipeline Completed Successfully (Gates G1–G6 OPEN)")
            print(f"Audit Summary: {audit_summary['total_events']} events, {audit_summary['total_violations_found']} violations found.")
            print("Generated Deliverables:")
            for k, v in reports.items():
                p = Path(v)
                size_str = f"{p.stat().st_size / 1024:.1f} KB" if p.exists() else "-"
                print(f"  - {k.upper()} ({size_str}): {v}")

        # Post-completion interactive conversational NLP Q&A session
        qa_engine = DiscoveryQAEngine(
            base_dir=Path(args.output_dir) if args.output_dir else ROOT_DIR,
            run_id=orchestrator.run_id,
            llm=orchestrator.llm
        )

        if is_interactive or args.qa:
            run_interactive_qa_loop(qa_engine)
        else:
            if console:
                console.print("[dim]💡 Tip: Ask natural language questions anytime: `python run.py ask \"Why is orders DEGRADED?\"` (or run with --qa)[/dim]\n")
            else:
                print("\nTip: Ask natural language questions anytime: python run.py ask \"Why is orders DEGRADED?\" (or run with --qa)\n")

    except Exception as e:
        if console:
            console.print(f"\n[bold red]✖ Pipeline Halted by Quality Gate:[/bold red] {e}")
        else:
            print(f"\n✖ Pipeline Halted by Quality Gate: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()
