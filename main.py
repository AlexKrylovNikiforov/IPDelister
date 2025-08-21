from __future__ import annotations
from pathlib import Path
from typing import Optional, List, Tuple 
import typer
from rich.console import Console
from rich.table import Table

from config import load_config, save_config, AppConfig
from ipgetter import get_ip_list
from file_manager import FileManager
from delisting_barracuda import BarracudaDelist, Browser

app = typer.Typer(add_completion=False)
console = Console()

def _prompt_input_source(ips: Optional[str], file: Optional[Path], interactive: bool) -> Tuple[Optional[str], Optional[Path]]:
    """
    Спрашиваем источник адресов, если интерактив включён ИЛИ источники не заданы вовсе.
    Так пользователю не нужно помнить флаги; продвинутые могут запустить с --no-interactive.
    """
    if not ips and not file:
        interactive = True

    if interactive:
        choice = typer.prompt("Источник адресов? [manual/file]", default="manual").strip().lower()

        if choice in ("manual", "m", "1"):
            ips_text = typer.prompt("Введите IP/CIDR/список (через пробел/запятую/;)").strip()
            return ips_text, None

        if choice in ("file", "f", "2"):
            file_str = typer.prompt("Путь к файлу со списком IP/CIDR").strip()
            p = Path(file_str)
            if not p.exists() or not p.is_file():
                raise typer.BadParameter(f"Файл не найден или не является файлом: {p}")
            return None, p

        raise typer.BadParameter("Нужно выбрать 'manual' или 'file'.")

    # неинтерактивно — уважаем переданные флаги
    return ips, file

def _collect_ips(ips: Optional[str], file: Optional[Path]) -> List[str]:
    text = ips or ""
    if file:
        if not file.exists():
            raise typer.BadParameter(f"File not found: {file}")
        file_text = file.read_text(encoding="utf-8-sig")
        text = (text + "\n" + file_text).strip()
    lst = get_ip_list(text)
    if not lst:
        raise typer.BadParameter("No valid IPs found in input.")
    return lst

@app.command()
def init_config(
    email: str = typer.Option(..., prompt=True, help="Contact email for Barracuda form"),
    phone: str = typer.Option(..., prompt=True, help="Contact phone for Barracuda form"),
    reason: str = typer.Option("The user was blocked. Spam was stopped. Please delist it.", prompt=True, help="Comments/reason for delisting"),
    headless: bool = typer.Option(True, help="Run browser headless"),
    timeout: int = typer.Option(60, help="Page wait timeout in seconds"),
):
    cfg = AppConfig(email=email, phone=phone, reason=reason, headless=headless, timeout_seconds=timeout)
    save_config(cfg)
    console.print("[green]Saved config to[/green] ~/.IPDelisting/config.toml")

@app.command()
def run(
    ips: Optional[str] = typer.Option(None, help="IPs/CIDRs separated by commas or spaces"),
    file: Optional[Path] = typer.Option(None, exists=False, dir_okay=False, help="Path to file containing IPs/CIDRs (one per line supported)"),
    email: Optional[str] = typer.Option(None, help="Email (overrides saved config)"),
    phone: Optional[str] = typer.Option(None, help="Phone (overrides saved config)"),
    reason: Optional[str] = typer.Option(None, help="Reason/comments for delisting"),
    headless: Optional[bool] = typer.Option(None, help="Override headless setting"),
    timeout: Optional[int] = typer.Option(None, help="Override timeout in seconds"),
    browser: Browser = typer.Option(Browser.chrome, case_sensitive=False, help="Browser: firefox | chrome | edge"),  # ← Chrome по умолчанию
    save_defaults: bool = typer.Option(False, help="Save provided values as new defaults"),
    interactive: bool = typer.Option(
        True,
        "--interactive/--no-interactive",
        help="Пошаговый диалог (manual/file). Отключите, если передаёте --ips/--file.",
    ),  # ← интерактив включён по умолчанию
):
    cfg = load_config()
    # Подтягиваем/запрашиваем контактные данные
    if not email:
        email = typer.prompt("Email", default=cfg.email or "")
    if not phone:
        phone = typer.prompt("Phone", default=cfg.phone or "")
    if reason is None:
        reason = typer.prompt("Reason (comments)", default=cfg.reason or "The user was blocked. Spam was stopped. Please delist it.")
    hless = cfg.headless if headless is None else headless
    tmo = cfg.timeout_seconds if timeout is None else timeout

    # Определяем источник IP
    ips, file = _prompt_input_source(ips, file, interactive)

    # Сохраняем как дефолты, если изменилось или явно просили
    changed = (
        cfg.email != email
        or cfg.phone != phone
        or cfg.reason != reason
        or cfg.headless != hless
        or cfg.timeout_seconds != tmo
    )
    if save_defaults or changed:
        save_config(AppConfig(email=email, phone=phone, reason=reason, headless=hless, timeout_seconds=tmo))
        console.print("[green]Saved your details as new defaults.[/green]")

    ip_list = _collect_ips(ips, file)

    console.rule("Barracuda Delisting")
    console.print(f"Total targets: [bold]{len(ip_list)}[/bold]")
    results = []
    for ip in ip_list:
        console.print(f"→ Processing [bold]{ip}[/bold] ...", end=" ")
        worker = BarracudaDelist(ip, headless=hless, timeout=tmo, browser=browser)
        try:
            worker.connect()
            worker.set_data(email=email, phone=phone, reason=reason or "")
            worker.submit()
            worker.check_error_presence()
            results.append(worker.report_entry)
            console.print("[green]done[/green]")
        except Exception as e:
            results.append({"ip": ip, "status": f"Exception: {e}"})
            console.print(f"[red]error: {e}[/red]")

    fm = FileManager(results)
    paths = fm.create_report()
    console.print(f"\nReports saved: [cyan]{paths['txt']}[/cyan], [cyan]{paths['json']}[/cyan]")

    # Summary
    table = Table(title="Summary", show_lines=True)
    table.add_column("IP")
    table.add_column("Status")
    table.add_column("Confirmation", no_wrap=True)
    for row in results:
        table.add_row(row.get("ip", ""), row.get("status", ""), row.get("confirmation", ""))
    console.print(table)

if __name__ == "__main__":
    import sys
    if len(sys.argv) == 1:
        # Запуск без аргументов
        sys.argv.append("run")
    app()
