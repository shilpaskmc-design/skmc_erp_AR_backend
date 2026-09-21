from uuid import uuid4

import pytest
from pydantic import ValidationError

from skmc_erp.core.cost_center.schema import (
    BusinessSegmentCreate,
    CompanyCostCenterSettingsUpdate,
    TeamCreate,
)


def test_settings_accept_none_one_two_or_all_bases() -> None:
    for business_segment, team, location in (
        (False, False, False),
        (True, False, False),
        (True, True, False),
        (True, True, True),
    ):
        settings = CompanyCostCenterSettingsUpdate(
            cost_center_reporting_enabled=True,
            business_segment_enabled=business_segment,
            team_enabled=team,
            location_enabled=location,
        )
        assert settings.cost_center_reporting_enabled

    disabled = CompanyCostCenterSettingsUpdate(
        cost_center_reporting_enabled=False,
        business_segment_enabled=False,
        team_enabled=False,
        location_enabled=False,
    )
    assert not disabled.cost_center_reporting_enabled


def test_disabled_reporting_rejects_enabled_basis() -> None:
    with pytest.raises(ValidationError):
        CompanyCostCenterSettingsUpdate(
            cost_center_reporting_enabled=False,
            business_segment_enabled=True,
            team_enabled=False,
            location_enabled=False,
        )


def test_master_inputs_strip_names_and_reject_system_fields() -> None:
    assert BusinessSegmentCreate(name="  Advisory  ").name == "Advisory"
    assert TeamCreate(name="  BIS Team  ").name == "BIS Team"

    with pytest.raises(ValidationError):
        BusinessSegmentCreate(
            name="Advisory",
            company_id=uuid4(),
        )
    with pytest.raises(ValidationError):
        TeamCreate(name="BIS Team", cost_center_team_id=uuid4())
