from sqlalchemy import CheckConstraint, ForeignKeyConstraint, UniqueConstraint

from skmc_erp.core.accounting.model import (
    AccountGroup,
    AccountGroupStatus,
    AccountHierarchy,
    AccountHierarchyPurpose,
    AccountHierarchyStatus,
)


def _constraint_names(table, constraint_type):
    return {
        constraint.name
        for constraint in table.constraints
        if isinstance(constraint, constraint_type)
    }


def test_account_hierarchy_metadata_matches_contract():
    table = AccountHierarchy.__table__

    assert table.schema == "core"
    assert table.name == "account_hierarchies"

    assert {
        "id",
        "company_id",
        "hierarchy_name",
        "purpose_code",
        "is_primary",
        "status",
        "created_at",
        "updated_at",
    } == set(table.columns.keys())

    assert table.c.hierarchy_name.nullable is False
    assert table.c.purpose_code.nullable is False
    assert table.c.is_primary.nullable is False
    assert table.c.status.nullable is False

    assert table.c.status.server_default is None
    assert table.c.purpose_code.server_default is None


def test_account_hierarchy_constraints_match_contract():
    table = AccountHierarchy.__table__

    assert {
        "ck_account_hierarchies_name_not_blank",
        "ck_account_hierarchies_purpose_code",
        "ck_account_hierarchies_status",
    } <= _constraint_names(table, CheckConstraint)

    assert {
        "uq_account_hierarchies_company_id_id",
        "uq_account_hierarchies_company_purpose_name",
    } <= _constraint_names(table, UniqueConstraint)

    assert {
        "fk_account_hierarchies_company_id_companies",
    } <= _constraint_names(table, ForeignKeyConstraint)

    indexes = {index.name: index for index in table.indexes}

    primary_index = indexes[
        "uq_account_hierarchies_active_primary_accounting"
    ]
    assert primary_index.unique is True


def test_account_hierarchy_enums_contain_only_approved_values():
    assert {item.value for item in AccountHierarchyPurpose} == {"ACCOUNTING"}
    assert {item.value for item in AccountHierarchyStatus} == {
        "ACTIVE",
        "INACTIVE",
    }


def test_account_group_metadata_matches_contract():
    table = AccountGroup.__table__

    assert table.schema == "core"
    assert table.name == "account_groups"

    assert {
        "id",
        "company_id",
        "hierarchy_id",
        "group_name",
        "group_code",
        "status",
        "created_at",
        "updated_at",
    } == set(table.columns.keys())

    assert table.c.company_id.nullable is False
    assert table.c.hierarchy_id.nullable is False
    assert table.c.group_name.nullable is False
    assert table.c.group_code.nullable is True
    assert table.c.status.nullable is False

    assert table.c.status.server_default is None


def test_account_group_constraints_match_contract():
    table = AccountGroup.__table__

    assert {
        "ck_account_groups_name_not_blank",
        "ck_account_groups_code_not_blank",
        "ck_account_groups_status",
    } <= _constraint_names(table, CheckConstraint)

    assert {
        "uq_account_groups_company_hierarchy_id",
        "uq_account_groups_company_hierarchy_name",
    } <= _constraint_names(table, UniqueConstraint)

    assert {
        "fk_account_groups_company_id_companies",
        "fk_account_groups_company_hierarchy",
    } <= _constraint_names(table, ForeignKeyConstraint)

    indexes = {index.name: index for index in table.indexes}

    code_index = indexes[
        "uq_account_groups_company_hierarchy_code"
    ]
    assert code_index.unique is True


def test_account_group_status_contains_only_approved_values():
    assert {item.value for item in AccountGroupStatus} == {
        "ACTIVE",
        "INACTIVE",
    }
