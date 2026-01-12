"""Main CLI entry point."""

import click
from pathlib import Path

from sgt.cli import task, convoy, worker, init as init_commands


@click.group()
@click.version_option(version="0.1.0")
def cli():
    """Simple Gas Town - Multi-agent task orchestration."""
    pass


# Add subcommands
cli.add_command(init_commands.init)
cli.add_command(init_commands.project)
cli.add_command(task.task)
cli.add_command(convoy.convoy)
cli.add_command(worker.worker)
cli.add_command(init_commands.assign)
cli.add_command(init_commands.status)


def main():
    """Entry point for the CLI."""
    return cli()


if __name__ == "__main__":
    main()
