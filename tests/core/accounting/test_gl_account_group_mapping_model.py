from datetime import date
from uuid import uuid4

from sqlalchemy import CheckConstraint, ForeignKeyConstraint
from sqlalchemy.dialects.postgresql import ExcludeConstraint

from skmc_erp.core.accounting.model import AccountGroupMapping
from skmc_erp.model_base import Base


def test_gl_account_group_mapping_metadata_matches_contract() -> None:
    table = AccountGroupMapping.__table__

    assert table is Base.metadata.tables["core.gl_account_group_mappings"]
    assert table.schema == "core"
    assert table.name == "gl_account_group_mappings"
    assert list(table.columns.keys()) == [
        "id",
        "company_id",
        "hierarchy_id",
        "gl_account_id",
        "account_group_id",
        "valid_from",
        "valid_to",
        "created_at",
        "updated_at",
    ]
    assert table.primary_key.name == "pk_gl_account_group_mappings"
    assert table.c.id.type.as_uuid
    assert not table.c.id.nullable
    assert str(table.c.id.server_default.arg) == "gen_random_uuid()"

    for column_name in (
        "company_id",
        "hierarchy_id",
        "gl_account_id",
        "valid_from",
    ):
        assert not table.c[column_name].nullable
        assert table.c[column_name].server_default is None

    assert table.c.account_group_id.nullable
    assert table.c.account_group_id.server_default is None
    assert table.c.valid_to.nullable
    assert table.c.valid_to.server_default is None

    for timestamp_column in (table.c.created_at, table.c.updated_at):
        assert timestamp_column.type.timezone
        assert not timestamp_column.nullable
        assert str(timestamp_column.server_default.arg) == "CURRENT_TIMESTAMP"

    forbidden_columns = {
        "status",
        "placement_type",
        "is_root",
        "is_unplaced",
        "sort_order",
        "display_order",
        "balance",
        "posting_flag",
        "debit_credit_nature",
        "created_by",
        "updated_by",
    }
    assert forbidden_columns.isdisjoint(table.columns.keys())


def test_gl_account_group_mapping_constraints_match_contract() -> None:
    table = AccountGroupMapping.__table__

    checks = {
        constraint.name: str(constraint.sqltext)
        for constraint in table.constraints
        if isinstance(constraint, CheckConstraint)
    }
    assert checks == {
        "ck_gl_account_group_mappings_valid_range": (
            "valid_to IS NULL OR valid_to >= valid_from"
        )
    }

    foreign_keys = {
        constraint.name: (
            tuple(element.parent.name for element in constraint.elements),
            tuple(element.target_fullname for element in constraint.elements),
            constraint.ondelete,
            constraint.match,
        )
        for constraint in table.constraints
        if isinstance(constraint, ForeignKeyConstraint)
    }
    assert foreign_keys == {
        "fk_gl_account_group_mappings_company_id_companies": (
            ("company_id",),
            ("core.companies.id",),
            "NO ACTION",
            None,
        ),
        "fk_gl_account_group_mappings_company_hierarchy": (
            ("company_id", "hierarchy_id"),
            (
                "core.account_hierarchies.company_id",
                "core.account_hierarchies.id",
            ),
            "NO ACTION",
            None,
        ),
        "fk_gl_account_group_mappings_company_gl_account": (
            ("company_id", "gl_account_id"),
            ("core.gl_accounts.company_id", "core.gl_accounts.id"),
            "NO ACTION",
            None,
        ),
        "fk_gl_account_group_mappings_company_hierarchy_group": (
            ("company_id", "hierarchy_id", "account_group_id"),
            (
                "core.account_groups.company_id",
                "core.account_groups.hierarchy_id",
                "core.account_groups.id",
            ),
            "NO ACTION",
            None,
        ),
    }

    exclusions = [
        constraint
        for constraint in table.constraints
        if isinstance(constraint, ExcludeConstraint)
    ]
    assert len(exclusions) == 1
    assert exclusions[0].name == (
        "ex_gl_account_group_mappings_gl_hierarchy_period_overlap"
    )
    assert exclusions[0].using == "gist"
    assert exclusions[0].where is None

    assert [
        (rendered_name or str(expression), operator)
        for expression, rendered_name, operator in exclusions[0]._render_exprs
    ] == [
        ("gl_account_id", "="),
        ("hierarchy_id", "="),
        ("daterange(valid_from, valid_to, '[]')", "&&"),
    ]


def test_gl_account_group_mapping_index_matches_contract() -> None:
    table = AccountGroupMapping.__table__
    assert len(table.indexes) == 1
    index = next(iter(table.indexes))
    assert index.name == (
        "ix_gl_account_group_mappings_company_hierarchy_group_dates"
    )
    assert not index.unique
    assert [column.name for column in index.columns] == [
        "company_id",
        "hierarchy_id",
        "account_group_id",
        "valid_from",
        "valid_to",
    ]


def test_gl_account_group_mapping_represents_group_and_root_placements() -> None:
    company_id = uuid4()
    hierarchy_id = uuid4()
    gl_account_id = uuid4()
    account_group_id = uuid4()

    group_placement = AccountGroupMapping(
        company_id=company_id,
        hierarchy_id=hierarchy_id,
        gl_account_id=gl_account_id,
        account_group_id=account_group_id,
        valid_from=date(2027, 4, 1),
        valid_to=None,
    )
    root_placement = AccountGroupMapping(
        company_id=company_id,
        hierarchy_id=hierarchy_id,
        gl_account_id=gl_account_id,
        account_group_id=None,
        valid_from=date(2028, 4, 1),
        valid_to=None,
    )

    assert group_placement.account_group_id == account_group_id
    assert root_placement.account_group_id is None
