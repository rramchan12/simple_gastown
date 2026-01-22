"""
CLI entry point for Test Generator Town.

Usage:
    python -m test_generator_town configs/project.yaml
    python -m test_generator_town config.yaml --quiet
"""
import argparse
import asyncio
import sys
from pathlib import Path

from .runner import Runner


def main():
    parser = argparse.ArgumentParser(
        description="Test Generator Town - Generate tests for external repos",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
    python -m test_generator_town configs/project.yaml
    python -m test_generator_town config.yaml --quiet
        """
    )
    
    parser.add_argument(
        "config",
        type=Path,
        help="Path to configuration file (YAML or JSON)"
    )
    
    parser.add_argument(
        "--quiet", "-q",
        action="store_true",
        help="Suppress progress output"
    )
    
    parser.add_argument(
        "--no-readme",
        action="store_true",
        help="Don't generate README.md in the workspace"
    )
    
    parser.add_argument(
        "--no-cleanup",
        action="store_true",
        help="Don't clean up previous workspace"
    )
    
    args = parser.parse_args()
    
    if not args.config.exists():
        print(f"Error: Configuration file not found: {args.config}", file=sys.stderr)
        sys.exit(1)
    
    try:
        runner = Runner.from_config(args.config)
        
        if args.no_cleanup:
            runner.config.cleanup_on_start = False
        
        results = asyncio.run(runner.run(verbose=not args.quiet))
        
        if not args.no_readme:
            readme_path = runner.save_readme()
            if not args.quiet:
                print(f"\n📖 README saved: {readme_path}")
        
        if results["failed"] > 0:
            sys.exit(1)
            
    except ValueError as e:
        print(f"Configuration error: {e}", file=sys.stderr)
        sys.exit(1)
    except Exception as e:
        print(f"Error: {e}", file=sys.stderr)
        sys.exit(1)


if __name__ == "__main__":
    main()
