"""
MetaLex Font Size & Readability Analyzer
Analyzes OCR bounding box dimensions to estimate actual printed text height in mm
and verifies compliance with Legal Metrology (Packaged Commodities) Rule 7 minimum font size standards.
"""

from typing import Dict, Any, List, Optional, Tuple

# Minimum legal font heights in mm per Legal Metrology Rules
MIN_FONT_SIZES_MM = {
    "net_quantity": 2.0,       # Rule 7: Net quantity numeral height (min 2mm for standard retail)
    "mrp": 2.0,                # Rule 7 / Rule 6: MRP declaration (min 2mm)
    "manufacturer": 1.5,       # Rule 6(1)(a): Manufacturer name & address (min 1.5mm)
    "date": 1.0,               # Rule 6(1)(d): Month & year of mfg/pkd (min 1mm)
    "consumer_care": 1.0,      # Rule 6(2): Consumer care details (min 1mm)
    "country_of_origin": 1.0,  # Rule 6(1)(a): Country of origin (min 1mm)
    "product_name": 1.5,       # Rule 6(1)(b): Commodity name (min 1.5mm)
    "default": 1.0             # General minimum for other declarations
}


def estimate_dpi(image_shape: Optional[Tuple[int, ...]] = None, assumed_package_height_mm: float = 150.0) -> float:
    """
    Estimate image DPI based on package frame resolution.
    Assumes standard packaged retail commodity captured filling ~75% of frame.
    """
    if image_shape is None or len(image_shape) < 2:
        return 180.0  # Safe default DPI for package inspection photos
    
    img_h, img_w = image_shape[:2]
    max_dim_px = max(img_h, img_w)
    
    # Effective physical package dimension ~150mm
    # DPI = (pixels / mm) * 25.4
    px_per_mm = (max_dim_px * 0.75) / assumed_package_height_mm
    dpi = px_per_mm * 25.4
    
    # Bound between 100 DPI and 400 DPI
    return max(100.0, min(400.0, dpi))


def calculate_font_size_mm(
    bbox: Optional[List[int]], 
    image_shape: Optional[Tuple[int, ...]] = None,
    custom_dpi: Optional[float] = None
) -> Optional[float]:
    """
    Calculate text height in mm from bounding box [x1, y1, x2, y2].
    
    Args:
        bbox: [x1, y1, x2, y2] in pixels
        image_shape: (height, width, channels)
        custom_dpi: Optional calibrated DPI override
        
    Returns:
        Estimated text height in mm (rounded to 1 decimal place), or None if bbox is invalid.
    """
    if not bbox or len(bbox) < 4:
        return None
    
    x1, y1, x2, y2 = bbox
    height_px = abs(y2 - y1)
    if height_px <= 0:
        return None
        
    dpi = custom_dpi or estimate_dpi(image_shape)
    
    # Text glyph height is typically ~70-80% of bounding box line height
    glyph_height_px = height_px * 0.75
    height_mm = (glyph_height_px / dpi) * 25.4
    
    return round(height_mm, 1)


def get_min_font_size(field_name: str) -> float:
    """Get the Legal Metrology minimum required font size in mm for a given field."""
    return MIN_FONT_SIZES_MM.get(field_name, MIN_FONT_SIZES_MM["default"])


def analyze_font_compliance(
    fields: Dict[str, Dict[str, Any]], 
    image_shape: Optional[Tuple[int, ...]] = None,
    custom_dpi: Optional[float] = None
) -> Dict[str, Any]:
    """
    Perform font size & readability analysis across all extracted declarations.
    
    Returns:
        Dict with field measurements, violations, and summary stats.
    """
    dpi = custom_dpi or estimate_dpi(image_shape)
    results = {}
    violations = []
    total_measured = 0
    total_violations = 0
    
    for field_name, fdata in fields.items():
        bbox = fdata.get("bounding_box")
        detected_val = fdata.get("value")
        
        min_required = get_min_font_size(field_name)
        measured_mm = calculate_font_size_mm(bbox, image_shape, dpi)
        
        if measured_mm is not None and detected_val:
            total_measured += 1
            is_compliant = measured_mm >= min_required
            
            field_result = {
                "field_name": field_name,
                "detected_value": detected_val,
                "font_size_mm": measured_mm,
                "min_required_mm": min_required,
                "is_compliant": is_compliant,
                "status": "PASS" if is_compliant else "NON_COMPLIANT",
                "bounding_box": bbox,
            }
            
            if not is_compliant:
                total_violations += 1
                violations.append({
                    "field": field_name,
                    "font_size_mm": measured_mm,
                    "min_required_mm": min_required,
                    "reason": f"Font height {measured_mm}mm is below Legal Metrology minimum of {min_required}mm for {field_name.replace('_', ' ').title()}.",
                    "bounding_box": bbox,
                })
        else:
            field_result = {
                "field_name": field_name,
                "detected_value": detected_val,
                "font_size_mm": None,
                "min_required_mm": min_required,
                "is_compliant": None,
                "status": "NOT_MEASURED",
                "bounding_box": bbox,
            }
            
        results[field_name] = field_result
        
    violation_rate = round((total_violations / total_measured * 100), 1) if total_measured > 0 else 0.0
    
    return {
        "field_results": results,
        "violations": violations,
        "total_measured": total_measured,
        "total_violations": total_violations,
        "violation_rate": violation_rate,
        "calibrated_dpi": round(dpi, 1),
    }
