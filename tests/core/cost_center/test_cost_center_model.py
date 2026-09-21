from sqlalchemy import CheckConstraint, ForeignKeyConstraint, UniqueConstraint

from skmc_erp.ar.catalogue.model import ServiceType, Sku
from skmc_erp.core.company_location.model import CompanyLocation
from skmc_erp.core.cost_center.model import (
    CompanyCostCenterSettings,
    CostCenterBusinessSegment,
    CostCenterLocation,
    CostCenterStatus,
    CostCenterTeam,
    Team,
    TeamStatus,
)
from skmc_erp.model_base import Base


def test_cost_center_metadata_contains_only_approved_tables() -> None:
    expected_models = (
        CostCenterLocation,
        CostCenterBusinessSegment,
        CostCenterTeam,
        Team,
        CompanyCostCenterSettings,
    )
    for model in expected_models:
        assert model.__table__.schema == "core"

    assert "core.team_memberships" not in Base.metadata.tables
    assert "core.cost_centers" not in Base.metadata.tables
    assert "core.cost_center_types" not in Base.metadata.tables


def test_reporting_bucket_columns_and_constraints_match_contract() -> None:
    for model in (
        CostCenterLocation,
        CostCenterBusinessSegment,
        CostCenterTeam,
    ):
        table = model.__table__
        assert list(table.columns.keys()) == [
            "id",
            "company_id",
            "name",
            "code",
            "status",
            "created_at",
            "updated_at",
        ]
        assert str(table.c.id.server_default.arg) == "gen_random_uuid()"
        assert table.c.name.type.length == 150
        assert table.c.code.type.length == 50
        assert table.c.code.nullable
        assert table.c.status.server_default is None
        assert not table.c.status.type.native_enum
        assert {
            tuple(column.name for column in constraint.columns)
            for constraint in table.constraints
            if isinstance(constraint, UniqueConstraint)
        } == {("company_id", "name"), ("company_id", "id")}


def test_actual_team_is_separate_and_optionally_references_bucket() -> None:
    table = Team.__table__
    assert list(table.columns.keys()) == [
        "id",
        "company_id",
        "cost_center_team_id",
        "name",
        "status",
        "created_at",
        "updated_at",
    ]
    assert table.c.cost_center_team_id.nullable
    foreign_keys = {
        constraint.name: (
            tuple(element.parent.name for element in constraint.elements),
            tuple(element.target_fullname for element in constraint.elements),
        )
        for constraint in table.constraints
        if isinstance(constraint, ForeignKeyConstraint)
    }
    assert foreign_keys["fk_teams_company_cost_center_team"] == (
        ("company_id", "cost_center_team_id"),
        ("core.cost_center_teams.company_id", "core.cost_center_teams.id"),
    )


def test_settings_allow_enabled_without_selected_basis() -> None:
    table = CompanyCostCenterSettings.__table__
    assert table.c.company_id.primary_key
    for column_name in (
        "cost_center_reporting_enabled",
        "business_segment_enabled",
        "team_enabled",
        "location_enabled",
    ):
        column = table.c[column_name]
        assert not column.nullable
        assert str(column.server_default.arg) == "false"

    checks = {
        constraint.name: str(constraint.sqltext)
        for constraint in table.constraints
        if isinstance(constraint, CheckConstraint)
    }
    assert "ck_company_cost_center_settings_disabled_bases" in checks
    assert "business_segment_enabled OR team_enabled" not in checks[
        "ck_company_cost_center_settings_disabled_bases"
    ]


def test_direct_relationships_are_nullable_and_company_scoped() -> None:
    expected = {
        ServiceType: "fk_service_types_company_business_segment",
        Sku: "fk_skus_company_business_segment",
        CompanyLocation: "fk_company_locations_company_cost_center_location",
    }
    for model, constraint_name in expected.items():
        table = model.__table__
        column_name = (
            "cost_center_location_id"
            if model is CompanyLocation
            else "business_segment_id"
        )
        assert table.c[column_name].nullable
        constraint = next(
            constraint
            for constraint in table.constraints
            if isinstance(constraint, ForeignKeyConstraint)
            and constraint.name == constraint_name
        )
        assert len(constraint.elements) == 2
        assert constraint.ondelete == "NO ACTION"


def test_statuses_contain_only_approved_values() -> None:
    assert {status.value for status in CostCenterStatus} == {
        "ACTIVE",
        "INACTIVE",
    }
    assert {status.value for status in TeamStatus} == {"ACTIVE", "INACTIVE"}
