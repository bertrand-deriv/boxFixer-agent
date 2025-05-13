import typer
import time
from typing import List, Optional, Dict
from rich.emoji import Emoji
from rich.table import Table
from rich.panel import Panel
from rich import box
from rich.text import Text
from rich.progress import Progress, TextColumn, BarColumn
from rich.markdown import Markdown
from rich.theme import Theme
from rich.console import Console

custom_theme = Theme({
    "heading.level2": "bold blue",
    "strong": "bold yellow",
    "code": "bold cyan on black",
    "block.code": "cyan on black",
    "link": "bold blue underline",
    "blockquote": "bold cyan on black",
})

def display_markdown_response(message):
    """Display agent response as rendered markdown with typing effect and colors"""
    console = Console(theme=custom_theme, highlight=True)
    markdown = Markdown(message)

    # Render the markdown to a string with ANSI codes
    with console.capture() as capture:
        console.print(markdown)
    rendered_text = capture.get()
    
    # Display with typing effect
    for char in rendered_text:
        typer.echo(char, nl=False)
        time.sleep(0.0002)
    typer.echo()

def display_service_category(category_name: str, services: Optional[List] = None):
    """Display a category of services in a styled table"""
    if not services:
        return None
        
    table = Table(
        box=box.ROUNDED,
        expand=True,
        title=f"{category_name}",
        title_style="bold cyan",
        header_style="bold",
        border_style="blue"
    )
    
    # Define columns
    table.add_column("Status", justify="center", width=6)
    table.add_column("Service Name", style="cyan")
    table.add_column("Status", width=12)
    table.add_column("Message", style="dim", no_wrap=False)
    
    # Add rows
    sorted_services = sorted(services, key=lambda svc: (not svc.running, svc.name))
    for service in sorted_services:
        status_emoji = "✅" if service.running else "❌"
        status_color = "green" if service.running else "red"
        error_text = f"\n[bold red]Error:[/bold red] {service.error}" if service.error else ""
        
        table.add_row(
            status_emoji,
            service.name,
            f"[{status_color}]{service.status}[/{status_color}]",
            f"{service.message}{error_text}"
        )
    
    return table

def create_resource_panel(resources):
    """Create a panel displaying system resource usage"""
    def get_color(value):
        try:
            if isinstance(value, str) and '%' in value:
                percent = float(value.replace('%', ''))
                if percent > 90:
                    return "bold red"
                elif percent > 70:
                    return "bold yellow"
                return "bold green"
        except ValueError:
            pass
        return "bold"
    
    cpu_line = f"[{get_color(resources.cpu_usage)}]CPU Usage:[/{get_color(resources.cpu_usage)}] {resources.cpu_usage}"
    mem_line = f"[{get_color(resources.memory_usage)}]Memory Usage:[/{get_color(resources.memory_usage)}] {resources.memory_usage}"
    disk_line = f"[{get_color(resources.disk_usage)}]Disk Usage:[/{get_color(resources.disk_usage)}] {resources.disk_usage}"
    
    content = f"{cpu_line}\n{mem_line}\n{disk_line}"
    
    return Panel(
        content,
        title="🔋 System Resources",
        border_style="cyan",
        box=box.ROUNDED
    )

def display_structured_output(structured_output, console):
    """Display the structured output in a visually appealing format"""
    # Create progress bar
    with Progress(
        TextColumn("[bold blue]Generating diagnostic report..."),
        BarColumn(bar_width=40),
        TextColumn("[bold green]{task.percentage:.0f}%"),
        transient=True
    ) as progress:
        task = progress.add_task("", total=100)
        for i in range(101):
            progress.update(task, completed=i)
            time.sleep(0.01)
    
    # Banner
    console.print("\n")
    console.rule("[bold white on blue]⛑️  DIAGNOSTIC REPORT  ⛑️[/bold white on blue]", style="blue")
    
    # Summary section
    console.print("\n")
    summary_panel = Panel(
        structured_output.summary,
        title="📋 Summary",
        border_style="cyan",
        box=box.ROUNDED
    )
    console.print(summary_panel)
    console.print("\n")
    
    # Resource section
    resource_panel = create_resource_panel(structured_output.resources)
    console.print(resource_panel)
    console.print("\n")
    
    # Services section
    
    # Calculate overall service health
    all_services = []
    
    kyc_services = structured_output.services.kyc_services or []
    passkeys_services = structured_output.services.passkeys_services or []
    crypto_services = structured_output.services.crypto_services or []
    other_services = structured_output.services.other_services or []
    
    all_services.extend(kyc_services)
    all_services.extend(passkeys_services)
    all_services.extend(crypto_services)
    all_services.extend(other_services)
    
    total_services = len(all_services)
    running_services = sum(1 for svc in all_services if svc.running)
    
    if total_services > 0:
        health_percentage = (running_services / total_services) * 100
        health_color = "green" if health_percentage >= 90 else "yellow" if health_percentage >= 70 else "red"
        health_text = f"[bold]System Health:[/bold] [bold {health_color}]{health_percentage:.1f}%[/bold {health_color}] ({running_services} of {total_services} services running)"
        health_text_panel = Panel(
            health_text,
            title="🔌 Services",
            border_style="cyan",
            box=box.ROUNDED
        )
        console.print(health_text_panel)
        console.print("\n")

    # Display services by category
    if kyc_services:
        kyc_table = display_service_category("KYC Services", kyc_services)
        console.print(kyc_table)
        console.print("\n")
        
    if passkeys_services:
        passkeys_table = display_service_category("Passkeys Services", passkeys_services)
        console.print(passkeys_table)
        console.print("\n")
        
    if crypto_services:
        crypto_table = display_service_category("Crypto Services", crypto_services)
        console.print(crypto_table)
        console.print("\n")
        
    if other_services:
        other_table = display_service_category("Other Services", other_services)
        console.print(other_table)
        console.print("\n")
    
    # Display recommendations
    recommendations = structured_output.recommendations
    if recommendations:
        console.rule("[bold blue]💡 Recommendations[/bold blue]", style="blue")
        console.print("\n")
        
        for i, recommendation in enumerate(recommendations, 1):
            rec_panel = Panel(
                recommendation,
                title=f"Recommendation #{i}",
                border_style="cyan",
                box=box.ROUNDED
            )
            console.print(rec_panel)
            console.print("\n")
    
    # Footer
    timestamp = time.strftime("%Y-%m-%d %H:%M:%S")
    footer = Text(f"Report generated by BoxFixer at {timestamp}", style="italic dim")
    console.print(footer, justify="center")
    console.rule(style="blue")