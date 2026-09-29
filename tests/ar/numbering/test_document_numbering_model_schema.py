from uuid import uuid4

import pytest
from pydantic import ValidationError
from sqlalchemy import CheckConstraint, ForeignKeyConstraint, UniqueConstraint

from skmc_erp.ar.numbering.model import (
    DocumentSequence,
    DocumentSequenceCondition,
    DocumentType,
)
from skmc_erp.ar.numbering.schema import DocumentSequenceCreate


def _constraint_names(model: type, kind: type) -> set[str]:
    return {
        constraint.name
        for constraint in model.__table__.constraints
        if isinstance(constraint, kind)
    }


def test_document_numbering_models_match_approved_contract() -> None:
    assert list(DocumentSequence.__table__.columns.keys()) == [
        "id",
        "company_id",
        "financial_year_id",
        "document_type",
        "series_name",
        "format",
        "prefix",
        "start_number",
        "next_number",
        "padding",
        "priority",
        "status",
        "created_at",
        "updated_at",
    ]
    assert list(DocumentSequenceCondition.__table__.columns.keys()) == [
        "id",
        "document_sequence_id",
        "condition_type",
        "operator",
        "condition_value",
        "created_at",
        "updated_at",
    ]
    assert _constraint_names(DocumentSequence, CheckConstraint) == {
        "ck_document_sequences_document_type",
        "ck_document_sequences_start_number",
        "ck_document_sequences_next_number",
        "ck_document_sequences_padding",
        "ck_document_sequences_status",
    }
    assert _constraint_names(DocumentSequence, UniqueConstraint) == {
        "uq_document_sequences_company_fy_type_name"
    }
    assert _constraint_names(DocumentSequence, ForeignKeyConstraint) == {
        "fk_document_sequences_company_id_companies",
        "fk_document_sequences_company_financial_year",
    }
    assert _constraint_names(DocumentSequenceCondition, ForeignKeyConstraint) == {
        "fk_document_sequence_conditions_sequence_id_sequences"
    }
    assert DocumentSequence.__table__.c.prefix.nullable
    assert DocumentSequence.__table__.c.priority.nullable
    for column in DocumentSequence.__table__.columns:
        assert column.server_default is None
    for column in DocumentSequenceCondition.__table__.columns:
        assert column.server_default is None


def test_document_sequence_create_accepts_only_approved_fields() -> None:
    financial_year_id = uuid4()
    value = DocumentSequenceCreate.model_validate(
        {
            "financial_year_id": str(financial_year_id),
            "document_type": "TI",
            "series_name": "  Main Series  ",
            "format": "  {PREFIX}/{FY}/{NUMBER}  ",
            "prefix": "  INV  ",
            "start_number": 1,
            "next_number": 1,
            "padding": 6,
            "priority": None,
        }
    )
    assert value.financial_year_id == financial_year_id
    assert value.document_type is DocumentType.TI
    assert value.series_name == "Main Series"
    assert value.prefix == "INV"

    for payload in (
        {"status": "ACTIVE"},
        {"company_id": str(uuid4())},
        {"start_number": 0},
        {"padding": 0},
    ):
        with pytest.raises(ValidationError):
            DocumentSequenceCreate.model_validate(
                {
                    "financial_year_id": str(financial_year_id),
                    "document_type": "TI",
                    "series_name": "Main",
                    "format": "{NUMBER}",
                    "start_number": 1,
                    "next_number": 1,
                    "padding": 1,
                    **payload,
                }
            )
