from amd_track1.benchmarking.cli import build_parser, main


def test_benchmark_cli_supports_listing_and_smoke() -> None:
    parser = build_parser()
    args = parser.parse_args(["list-capabilities"])
    assert args.command == "list-capabilities"

    result = main(["list-capabilities"], output_stream=None)
    assert result["status"] == "ok"
    assert result["count"] >= 8

    smoke = main(["smoke"], output_stream=None)
    assert smoke["status"] == "ok"
    assert smoke["suite_count"] >= 1
