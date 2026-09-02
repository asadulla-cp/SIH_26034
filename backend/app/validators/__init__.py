"""Validator type registry — implementations live in services/rule_engine.py so rules.json can add types later."""
VALIDATORS = [
    "required_present",
    "address_quality",
    "net_quantity_with_unit",
    "mrp_format",
    "date_parseable",
    "consumer_care_contact",
    "origin_if_imported",
    "standard_unit",
    "no_conflicting_mrp",
]
