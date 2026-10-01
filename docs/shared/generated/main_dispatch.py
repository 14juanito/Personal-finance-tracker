def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    # Symbols such as "✓" or "█" cannot be encoded by some Windows consoles; replace
    # them with "?" instead of crashing with UnicodeEncodeError.
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(errors="replace")
    # Concept: decision structure — one branch per execution mode
    if args.mode == "cli":
        from finance_tracker import cli

        cli.run(args.data or USER_DATA_FILE)
    elif args.mode == "gui":
        # Imported lazily so that cli/demo work even where Tk is not installed.
        from finance_tracker import gui_tkinter

        gui_tkinter.run(args.data or USER_DATA_FILE)
    else:
        data_file = args.data or SAMPLE_JSON
        if not data_file.exists():
            print(f"Error: data file not found: {data_file}", file=sys.stderr)
            return 1
        run_demo(data_file, args.output)
    return 0
