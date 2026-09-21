from sqlalchemy import CheckConstraint, ForeignKeyConstraint
from sqlalchemy.dialects.postgresql import ExcludeConstraint

from skmc_erp.core.accounting.model import AccountGroupRelationship
from skmc_erp.model_base import Base


def test_account_group_relationship_metadata_matches_contract() -> None:
    table = AccountGroupRelationship.__table__

    assert table is Base.metadata.tables["core.account_group_relationships"]
    assert table.schema == "core"
    assert table.name == "account_group_relationships"
    assert list(table.columns.keys()) == [
        "id",
        "company_id",
        "hierarchy_id",
        "child_group_id",
        "parent_group_id",
        "valid_from",
        "valid_to",
        "created_at",
        "updated_at",
    ]
    assert table.primary_key.name == "pk_account_group_relationships"
    assert table.c.id.type.as_uuid
    assert str(table.c.id.server_default.arg) == "gen_random_uuid()"

    for column_name in (
        "company_id",
        "hierarchy_id",
        "child_group_id",
        "parent_group_id",
        "valid_from",
    ):
        assert not table.c[column_name].nullable
        assert table.c[column_name].server_default is None

    assert table.c.valid_to.nullable
    assert table.c.valid_to.server_default is None

    for timestamp_column in (table.c.created_at, table.c.updated_at):
        assert timestamp_column.type.timezone
        assert not timestamp_column.nullable
        assert str(timestamp_column.server_default.arg) == "CURRENT_TIMESTAMP"

    forbidden_columns = {
        "status",
        "sort_order",
        "display_order",
        "sequence",
        "created_by",
        "updated_by",
        "is_root",
        "is_unplaced",
        "depth",
        "path",
        "gl_account_id",
    }
    assert forbidden_columns.isdisjoint(table.columns.keys())


def test_account_group_relationship_constraints_match_contract() -> None:
    table = AccountGroupRelationship.__table__

    checks = {
        constraint.name: str(constraint.sqltext)
        for constraint in table.constraints
        if isinstance(constraint, CheckConstraint)
    }
    assert checks == {
        "ck_account_group_relationships_not_self_parent": (
            "child_group_id <> parent_group_id"
        ),
        "ck_account_group_relationships_valid_range": (
            "valid_to IS NULL OR valid_to >= valid_from"
        ),
    }

    foreign_keys = {
        constraint.name: (
            tuple(element.parent.name for element in constraint.elements),
            tuple(element.target_fullname for element in constraint.elements),
            constraint.ondelete,
        )
        for constraint in table.constraints
        if isinstance(constraint, ForeignKeyConstraint)
    }
    assert foreign_keys == {
        "fk_account_group_relationships_company_id_companies": (
            ("company_id",),
            ("core.companies.id",),
            "NO ACTION",
        ),
        "fk_account_group_relationships_company_hierarchy": (
            ("company_id", "hierarchy_id"),
            (
                "core.account_hierarchies.company_id",
                "core.account_hierarchies.id",
            ),
            "NO ACTION",
        ),
        "fk_account_group_relationships_child_group": (
            ("company_id", "hierarchy_id", "child_group_id"),
            (
                "core.account_groups.company_id",
                "core.account_groups.hierarchy_id",
                "core.account_groups.id",
            ),
            "NO ACTION",
        ),
        "fk_account_group_relationships_parent_group": (
            ("company_id", "hierarchy_id", "parent_group_id"),
            (
                "core.account_groups.company_id",
                "core.account_groups.hierarchy_id",
                "core.account_groups.id",
            ),
            "NO ACTION",
        ),
    }

    exclusions = [
        constraint
        for constraint in table.constraints
        if isinstance(constraint, ExcludeConstraint)
    ]
    assert len(exclusions) == 1
    assert exclusions[0].name == (
        "ex_account_group_relationships_child_period_overlap"
    )
    assert exclusions[0].using == "gist"
    assert exclusions[0].where is None


def test_account_group_relationship_index_matches_contract() -> None:
    table = AccountGroupRelationship.__table__
    assert len(table.indexes) == 1
    index = next(iter(table.indexes))
    assert index.name == (
        "ix_account_group_relationships_company_hierarchy_parent_dates"
    )
    assert not index.unique
    assert [column.name for column in index.columns] == [
        "company_id",
        "hierarchy_id",
        "parent_group_id",
        "valid_from",
        "valid_to",
    ]
