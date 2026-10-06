# SKMC ERP Accounting Configuration ERD

## Scope

This Entity Relationship Diagram shows only the **current approved Accounting Configuration design** from [`requirements/database.md`](requirements/database.md), especially **Accounting Setup / Chart of Accounts Tables**. It deliberately excludes journals, journal lines, balances, reconciliation, accounting periods, Account Types/classifications, future Account Determination, and transaction tables.

The diagram is landscape-oriented, uses Crow's Foot cardinality, and keeps the current separation between hierarchy structure, GL identity/placement, automatic account resolution, and supporting references.

## Complete ERD

```mermaid
%%{init: {"theme":"base", "themeVariables":{"fontFamily":"Inter, Segoe UI, Arial, sans-serif", "lineColor":"#64748B", "primaryTextColor":"#172033"}}}%%
erDiagram
    direction LR

    companies {
        UUID id PK
        VARCHAR legal_name "Company context"
    }

    account_hierarchies {
        UUID id PK
        UUID company_id FK
        VARCHAR hierarchy_name
        VARCHAR purpose_code "ACCOUNTING currently"
        BOOLEAN is_primary
        VARCHAR status
    }

    account_groups {
        UUID id PK
        UUID company_id FK
        UUID hierarchy_id FK
        VARCHAR group_name
        VARCHAR group_code "nullable"
        VARCHAR status
    }

    account_group_relationships {
        UUID id PK
        UUID company_id FK
        UUID hierarchy_id FK
        UUID parent_group_id FK
        UUID child_group_id FK
        DATE valid_from
        DATE valid_to "nullable"
    }

    gl_accounts {
        UUID id PK
        UUID company_id FK
        VARCHAR account_code "nullable"
        VARCHAR account_name
        DATE valid_from
        DATE valid_to "nullable"
        VARCHAR status
    }

    gl_account_group_mappings {
        UUID id PK
        UUID company_id FK
        UUID hierarchy_id FK
        UUID gl_account_id FK
        UUID account_group_id FK "nullable = intentional root"
        DATE valid_from
        DATE valid_to "nullable"
    }

    revenue_gl_mappings {
        UUID id PK
        UUID company_id FK
        VARCHAR supply_type_code "controlled; no hard FK approved"
        UUID company_hsn_sac_code_id FK "nullable"
        UUID gl_account_id FK
        DATE valid_from
        DATE valid_to "nullable"
        VARCHAR status
    }

    tax_gl_account_mappings {
        UUID id PK
        UUID company_id FK
        UUID tax_statutory_code_id FK
        UUID gl_account_id FK
        DATE valid_from
        DATE valid_to "nullable"
        VARCHAR status
    }

    company_accounting_settings {
        UUID company_id PK, FK
        UUID default_receivable_gl_account_id FK
        TIMESTAMPTZ updated_at
        UUID updated_by "nullable"
    }

    company_bank_accounts {
        UUID id PK
        UUID company_id FK
        VARCHAR account_number
        VARCHAR currency_code FK
        UUID gl_account_id FK "nullable"
        BOOLEAN is_default_for_billing
        VARCHAR status
    }

    company_hsn_sac_codes {
        UUID id PK
        UUID company_id FK
        VARCHAR classification_type "HSN or SAC"
        VARCHAR code
        VARCHAR status
    }

    tax_statutory_codes {
        UUID id PK
        UUID tax_type_id FK
        VARCHAR code
        VARCHAR code_kind "COMPONENT or SECTION"
        VARCHAR country_code
        VARCHAR status
    }

    supply_types {
        UUID id PK "proposed if table retained"
        VARCHAR code "controlled vocabulary"
        VARCHAR name
        VARCHAR category
        VARCHAR status
    }

    companies ||--o{ account_hierarchies : "owns views"
    companies ||--o{ account_groups : "owns folders"
    account_hierarchies ||--o{ account_groups : "contains"

    companies ||--o{ account_group_relationships : "scopes"
    account_hierarchies ||--o{ account_group_relationships : "defines tree in"
    account_groups ||--o{ account_group_relationships : "parent_group_id"
    account_groups ||--o{ account_group_relationships : "child_group_id"

    companies ||--o{ gl_accounts : "owns ledgers"
    companies ||--o{ gl_account_group_mappings : "scopes"
    account_hierarchies ||--o{ gl_account_group_mappings : "receives placements"
    gl_accounts ||--o{ gl_account_group_mappings : "is placed by"
    account_groups o|--o{ gl_account_group_mappings : "optional group target"

    companies ||--o{ revenue_gl_mappings : "owns revenue rules"
    companies ||--o{ company_hsn_sac_codes : "owns classifications"
    company_hsn_sac_codes o|--o{ revenue_gl_mappings : "optional condition"
    supply_types o|..o{ revenue_gl_mappings : "conditional code dependency - REVIEW"
    gl_accounts ||--o{ revenue_gl_mappings : "resolved Revenue GL"

    companies ||--o{ tax_gl_account_mappings : "owns tax rules"
    tax_statutory_codes ||--o{ tax_gl_account_mappings : "statutory identity"
    gl_accounts ||--o{ tax_gl_account_mappings : "resolved Tax GL"

    companies ||--|| company_accounting_settings : "has one current setting"
    gl_accounts ||--o{ company_accounting_settings : "default Receivable GL"

    companies ||--o{ company_bank_accounts : "owns"
    gl_accounts o|--o{ company_bank_accounts : "optional Bank GL"

    classDef company fill:#F8FAFC,stroke:#475569,stroke-width:2px,color:#172033
    classDef hierarchy fill:#EAF3FF,stroke:#2F6F9F,stroke-width:2px,color:#172033
    classDef glidentity fill:#FFF6D8,stroke:#A66B00,stroke-width:2px,color:#172033
    classDef resolution fill:#F3EAFF,stroke:#7450A8,stroke-width:2px,color:#172033
    classDef supporting fill:#EAF8EE,stroke:#3B7A57,stroke-width:2px,color:#172033

    class companies company
    class account_hierarchies,account_groups,account_group_relationships hierarchy
    class gl_accounts,gl_account_group_mappings glidentity
    class revenue_gl_mappings,tax_gl_account_mappings,company_accounting_settings resolution
    class company_hsn_sac_codes,tax_statutory_codes,supply_types,company_bank_accounts supporting
```

The standalone editable Mermaid source is [`accounting_configuration_erd.mmd`](accounting_configuration_erd.mmd).

`currency_code` and `tax_type_id` remain marked as foreign keys, but their `currencies` and `tax_types` targets are intentionally not expanded because the requested supporting-reference boundary contains only Company HSN/SAC, Tax Statutory Code, and conditional Supply Type context.

## Legend

| Visual / term | Meaning |
|---|---|
| Light blue — Hierarchy Structure | The whole hierarchy view, its non-posting Group folders, and effective-dated Group-to-Group tree placement. |
| Light amber — GL Identity & Placement | Stable posting-ledger identity and effective-dated GL-to-Group/root placement. |
| Light violet — Account Resolution | Rules/settings that automatically select Revenue, Tax, or default Receivable GL Accounts. |
| Light green — Supporting References | Tax/catalogue reference data and the optional Bank-to-GL association; these are not accounting-core tables. |
| Solid Crow's Foot relationship | Current physical FK relationship. |
| Dashed relationship | Conditional/reference dependency only; no hard FK is approved. |
| Hierarchy | The entire Company-created accounting/reporting view. |
| Group | A non-posting folder/node inside a hierarchy. |
| GL Account | A stable posting ledger/account identity. |
| Group Relationship | Effective-dated **Group → Group** parent/child placement. |
| GL Placement | Effective-dated **GL Account → Group/root** placement. |
| Revenue/Tax Mapping | An automatic account-selection rule, not a posting or transaction. |

## Business Distinctions Preserved

1. `account_hierarchies` represents the whole accounting/reporting view.
2. `account_groups` contains non-posting folders. It has no permanent `parent_group_id`.
3. `account_group_relationships` alone defines the effective-dated Group tree: **Parent Group → Child Group**.
4. `gl_accounts` contains stable posting-ledger identities, not Groups, hierarchy placement, classifications, or balances.
5. `gl_account_group_mappings` places a GL Account in a Group or intentionally at hierarchy root without changing the GL identity.
6. `revenue_gl_mappings` resolves a Revenue GL from Company, Supply Type, and optional Company HSN/SAC.
7. `tax_gl_account_mappings` resolves a GL for a GST COMPONENT or TDS/TCS SECTION statutory identity.
8. `company_accounting_settings` holds the Company's single current default Receivable GL Account.
9. `company_bank_accounts.gl_account_id` is nullable; no separate Bank-to-GL mapping table exists.
10. `supply_types` remains REVIEW/table-versus-enum unresolved, so its connection is intentionally dashed and `supply_type_code` is not shown as a hard FK.
