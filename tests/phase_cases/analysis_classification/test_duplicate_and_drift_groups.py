"""Duplicate and drift grouping tests for Analysis_Classification phase."""
from backend.phases.analysis_classification import run_analysis_classification
from tests.case_builder.analysis_classification_case_builder import Analysis_ClassificationInputBuilder


class TestDuplicateAndDriftGroups:
    """Groups must be built from Scan evidence without hiding individual decisions."""

    def test_duplicate_group_preserved(self, tmp_path):
        inp = (
            Analysis_ClassificationInputBuilder()
            .with_duplicate_groups([
                {
                    "group_type": "duplicate_implementation",
                    "member_paths": [
                        "isolated_target/src/a.py",
                        "isolated_target/src/b.py",
                    ],
                    "representative_path": "isolated_target/src/a.py",
                },
            ])
            .build()
        )
        result = run_analysis_classification(inp, tmp_path)
        assert result.duplicate_group_count == 1
        assert len(result.groups) == 1
        group = result.groups[0]
        assert group.group_type == "duplicate_implementation"
        assert len(group.member_source_item_ids) >= 1

    def test_drift_record_preserved(self, tmp_path):
        inp = (
            Analysis_ClassificationInputBuilder()
            .with_drift_records([
                {
                    "drift_type": "interface_drift",
                    "affected_path": "isolated_target/src/a.py",
                    "reference_path": "isolated_target/src/b.py",
                },
            ])
            .build()
        )
        result = run_analysis_classification(inp, tmp_path)
        assert result.drift_group_count == 1
        assert len(result.groups) == 1
        group = result.groups[0]
        assert group.group_type == "interface_drift"

    def test_individual_decisions_remain_visible(self, tmp_path):
        inp = (
            Analysis_ClassificationInputBuilder()
            .with_duplicate_groups([
                {
                    "group_type": "duplicate_implementation",
                    "member_paths": ["isolated_target/src/module.py"],
                    "representative_path": "isolated_target/src/module.py",
                },
            ])
            .build()
        )
        result = run_analysis_classification(inp, tmp_path)
        # The duplicate group itself becomes an item and decision.
        assert len(result.items) == 5  # 3 files + 1 surface + 1 duplicate group
        assert len(result.decisions) == 5
        assert any(d.classification_category == "duplication" for d in result.decisions)

    def test_no_invented_groups(self, tmp_path):
        inp = Analysis_ClassificationInputBuilder().build()
        result = run_analysis_classification(inp, tmp_path)
        assert result.duplicate_group_count == 0
        assert result.drift_group_count == 0
        assert result.groups == []