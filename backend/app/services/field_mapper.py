"""
Flexible field mapper for GroMo API responses.
Maps varying API response structures to our internal Product schema.
"""
from typing import Any, Dict, List, Optional


# Default field mappings: internal_field -> list of possible API field names
DEFAULT_MAPPINGS = {
    "name": ["name", "product_name", "title", "productName"],
    "description": ["description", "desc", "product_description", "about", "productDescription"],
    "category": ["category", "category_name", "categoryName", "product_category", "type"],
    "category_id": ["category_id", "categoryId", "cat_id"],
    "product_id": ["id", "product_id", "productId", "sku"],
    "features": ["features", "key_features", "keyFeatures", "highlights"],
    "eligibility": ["eligibility", "eligibility_criteria", "eligibilityCriteria", "requirements"],
    "fees": ["fees", "charges", "pricing", "fee_structure", "feeStructure"],
    "benefits": ["benefits", "advantages", "perks", "rewards"],
    "faqs": ["faqs", "faq", "frequently_asked_questions", "questions"],
}


def extract_field(data: Dict[str, Any], field_keys: List[str]) -> Any:
    """Try multiple possible keys to extract a field from API response."""
    for key in field_keys:
        # Support nested keys with dot notation
        if "." in key:
            parts = key.split(".")
            val = data
            for part in parts:
                if isinstance(val, dict):
                    val = val.get(part)
                else:
                    val = None
                    break
            if val is not None:
                return val
        elif key in data and data[key] is not None:
            return data[key]
    return None


def map_product(raw_data: Dict[str, Any], custom_mappings: Optional[Dict] = None) -> Dict[str, Any]:
    """Map a raw API product response to our internal schema."""
    mappings = {**DEFAULT_MAPPINGS}
    if custom_mappings:
        mappings.update(custom_mappings)

    return {
        "name": extract_field(raw_data, mappings["name"]) or "Unknown Product",
        "description": extract_field(raw_data, mappings["description"]),
        "category_name": extract_field(raw_data, mappings["category"]),
        "category_id": extract_field(raw_data, mappings["category_id"]),
        "product_id": str(extract_field(raw_data, mappings["product_id"]) or ""),
        "features": _ensure_dict_or_list(extract_field(raw_data, mappings["features"])),
        "eligibility": _ensure_dict_or_list(extract_field(raw_data, mappings["eligibility"])),
        "fees": _ensure_dict_or_list(extract_field(raw_data, mappings["fees"])),
        "benefits": _ensure_dict_or_list(extract_field(raw_data, mappings["benefits"])),
        "faqs": _ensure_dict_or_list(extract_field(raw_data, mappings["faqs"])),
        "raw_data": raw_data,
    }


def _ensure_dict_or_list(value: Any) -> Any:
    """Ensure value is a dict or list, wrapping strings in a list."""
    if value is None:
        return None
    if isinstance(value, (dict, list)):
        return value
    if isinstance(value, str):
        return [value]
    return None
