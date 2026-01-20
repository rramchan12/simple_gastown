#!/usr/bin/env python3
"""
Demo: Test Suite Generator
==========================
Simple wrapper that uses the tester module to generate pytest tests.

For the full-featured tester, use:
    python -m tester tester/configs/calculator_tests.yaml

This demo script is kept for backward compatibility.
"""

import asyncio
import sys
from pathlib import Path

# Add parent to path for imports
sys.path.insert(0, str(Path(__file__).parent))


def main():
    """Run the test generator demo."""
    from tester import TestRunner
    from tester.setup_samples import main as setup_samples
    
    # Ensure sample repo is initialized
    print("🔧 Setting up sample repository...")
    setup_samples()
    print()
    
    # Load config and run
    config_path = Path(__file__).parent / "tester" / "configs" / "calculator_tests.yaml"
    
    if not config_path.exists():
        print(f"❌ Config not found: {config_path}")
        sys.exit(1)
    
    runner = TestRunner.from_config(config_path)
    results = asyncio.run(runner.run(verbose=True))
    
    # Save README
    readme_path = runner.save_readme()
    print(f"\n📖 README saved: {readme_path}")
    
    # Print validation commands
    print("\n" + "=" * 60)
    print("🔍 VALIDATE WITH CLI")
    print("=" * 60)
    print(f"""
cd {runner.config.town_root}
sgt project list
sgt task list --project {runner.config.name}
sgt convoy list
git -C {runner.config.repo_path} branch -a
""")
    
    print("🎉 Demo complete!")
    
    if results["failed"] > 0:
        sys.exit(1)


if __name__ == "__main__":
    main()
