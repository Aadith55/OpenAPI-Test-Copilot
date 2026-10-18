"""Command-line interface."""
import argparse
from pathlib import Path
from .generator import augment_with_llm, generate_scenarios, load_spec, write_outputs


def main() -> int:
    parser = argparse.ArgumentParser(description="Generate contract-derived test plans and pytest scenarios from an OpenAPI spec")
    parser.add_argument("spec", help="Path to an OpenAPI JSON/YAML file")
    parser.add_argument("--out", default="testcopilot_output", help="Output directory (default: testcopilot_output)")
    parser.add_argument("--ai", action="store_true", help="Ask an optional OpenAI-compatible model for additional manual-review ideas")
    args = parser.parse_args()
    try:
        spec = load_spec(args.spec)
        cases = generate_scenarios(spec)
        note = None
        if args.ai:
            cases, note = augment_with_llm(spec, cases)
        write_outputs(spec, cases, args.out, note)
        print(f"Generated {len(cases)} test scenarios from {args.spec}")
        print(f"Outputs: {Path(args.out).resolve()}")
        if note: print(f"Note: {note}")
        return 0
    except (OSError, ValueError, RuntimeError, TypeError, KeyError, AttributeError, ArithmeticError) as exc:
        parser.error(str(exc))
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
