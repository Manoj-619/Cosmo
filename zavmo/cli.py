#!/usr/bin/env python
"""
Zavmo CLI - Command line interface for interacting with Zavmo agents locally.
"""

import os
import sys
import click
import json
from rich.console import Console
from rich.panel import Panel
from rich.syntax import Syntax
from rich.table import Table
import django
# Note this is only for a singular message and a agent test

# Initialize Django settings
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "zavmo.settings")
django.setup()

from agents import get_agent
from agents.common import Deps

console = Console()

@click.group()
def cli():
    """Zavmo CLI - Interact with Zavmo agents from the command line."""
    pass

@cli.command()
@click.option("--stage", "-s", default="profile", help="Stage name (profile, discover, tna_assessment, discuss, deliver, demonstrate)")
@click.option("--email", "-e", required=True, help="User email for context")
@click.option("--message", "-m", default="Hello", help="Message to send to agent")
@click.option("--pretty/--no-pretty", default=True, help="Pretty print the output")
def run_agent(stage, email, message, pretty):
    """Run a specific agent with a message."""
    try:
        agent = get_agent(stage)
        deps = Deps(email=email, stage_name=stage)
        
        console.print(f"\n[bold blue]Running {stage} agent with message:[/bold blue] [italic]{message}[/italic]")
        
        response = agent.run_sync(message, deps=deps)
        
        if pretty:
            console.print(Panel(response.data, title=f"[bold green]{stage.capitalize()} Agent Response[/bold green]", 
                               border_style="green", expand=False))
        else:
            print(response.data)
            
    except Exception as e:
        console.print(f"[bold red]Error:[/bold red] {str(e)}", style="red")

@cli.command()
def list_agents():
    """List all available agents."""
    table = Table(title="Available Zavmo Agents")
    table.add_column("Stage", style="cyan")
    table.add_column("Description", style="green")
    
    agents = [
        ("profile", "User profile creation and management"),
        ("discover", "Discovery of learning goals and knowledge assessment"),
        ("tna_assessment", "Training Needs Analysis assessment"),
        ("discuss", "Discussion of curriculum and learning plan"),
        ("deliver", "Delivery of learning content"),
        ("demonstrate", "Demonstration of acquired knowledge")
    ]
    
    for stage, description in agents:
        table.add_row(stage, description)
    
    console.print(table)

if __name__ == "__main__":
    cli()