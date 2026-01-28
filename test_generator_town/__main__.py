"""
CLI entry point for test_generator_town.

Usage:
    python -m test_generator_town path/to/config.yaml
    python -m test_generator_town config.yaml --quiet
"""
import argparse
import asyncio
import sys
from pathlib import Path

from .runner import Runner


def main():
    parser = argparse.ArgumentParser(
        description="Test Generator Town - Generate tests using Simple Gas Town agents",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
    python -m test_generator_town configs/gastown_playground.yaml
    python -m test_generator_town config.yaml --quiet
    python -m test_generator_town config.yaml --no-readme
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
    
    parser.add_argument(
        "--verify",
        action="store_true",
        help="Verify generated tests by running pytest on worker branches"
    )
    
    parser.add_argument(
        "--verify-only",
        action="store_true",
        help="Only run verification (skip test generation)"
    )
    
    args = parser.parse_args()
    
    # Validate config file exists
    if not args.config.exists():
        print(f"Error: Configuration file not found: {args.config}", file=sys.stderr)
        sys.exit(1)
    
    # Load and run
    try:
        runner = Runner.from_config(args.config)
        
        if args.verify_only:
            # Just run verification
            verify_results = runner.verify_generated_tests(verbose=not args.quiet)
            if verify_results["failed"] > 0 or verify_results["errors"]:
                sys.exit(1)
            sys.exit(0)
        
        if args.no_cleanup:
            runner.config.cleanup_on_start = False
        
        results = asyncio.run(runner.run(verbose=not args.quiet))
        
        if not args.no_readme:
            readme_path = runner.save_readme()
            if not args.quiet:
                print(f"\n📖 README saved: {readme_path}")
        
        # Optionally verify generated tests
        if args.verify:
            verify_results = runner.verify_generated_tests(verbose=not args.quiet)
            if verify_results["failed"] > 0:
                sys.exit(1)
        
        # Exit with error if any tasks failed
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
