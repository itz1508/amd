"""
Scan phase.
"""

from backend.phases.scan.runner import (
    run_scan,
    main as scan_main,
    validate_snapshot,
    load_snapshot,
    classify_file_type,
    detect_language,
    classify_category,
    identify_surfaces,
    compute_scan_fingerprint,
)
