# PlotProof API Contracts: OCR (Person 1) & GIS (Person 2) Integration

This document defines the exact, binding API contracts between the **Backend Orchestration & Security Layer (Person 3)**, the **OCR & Document Intelligence Module (Person 1)**, and the **GIS & Spatial Validation Module (Person 2)**.

---

## 1. Person 1: OCR & Document Intelligence Contract

### Endpoints
- `GET /api/v1/documents/{document_id}/ocr` -> Full text, bounding boxes, field items, confidence score.
- `GET /api/v1/documents/{document_id}/fields` -> Structured extracted land title fields.
- `PATCH /api/v1/documents/{document_id}/fields/{field_id}` -> Sub-Registrar / Admin statutory correction.
- `POST /api/v1/documents/{document_id}/ocr/reprocess` -> Forces OCR reprocessing and returns `Layer5HandshakePayload`.

### Layer 5 Handshake Payload Schema (`Layer5HandshakePayload`)
```json
{
  "document_id": 1,
  "land": {
    "survey_number": "142/3A",
    "subdivision_number": "3A",
    "district": "Chennai",
    "taluk": "Tambaram",
    "village": "Selaiyur Village",
    "area": {
      "original": "2,400 Sq.ft (equivalent to 222.96 Sq.meters / 5.5 Cents)",
      "square_meters": 222.96
    }
  },
  "boundaries": {
    "north": "Survey No 142/2 (Road 30ft width)",
    "south": "Survey No 142/4 (Vacant Plot)",
    "east": "Survey No 142/3B (Adjacent Plot)",
    "west": "Survey No 142/1 (Residential Property)"
  },
  "coordinates": {
    "latitude": 12.9252,
    "longitude": 80.1475
  },
  "quality": {
    "overall_confidence": 0.96,
    "review_required": false
  }
}
```

### Standard Field Names & Types
| Field Name | Type | Description / Accepted Format | Example |
|---|---|---|---|
| `survey_number` | `str` | Survey number and subdivision | `"142/3A"` |
| `district` | `str` | Revenue District | `"Chennai"` |
| `taluk` | `str` | Revenue Taluk | `"Tambaram"` |
| `village` | `str` | Revenue Village | `"Selaiyur"` |
| `area` | `str` / `float` | Area string with units (`Sq.ft`, `Sq.m`, `Cents`, `Acres`) | `"2,400 Sq.ft"` |
| `coordinates` | `str` / `dict` | GPS reference bounds or centroid coordinates | `"12.9252 N, 80.1475 E"` |
| `boundary_north` | `str` | North boundary description | `"Survey No 142/2 (Road)"` |
| `boundary_south` | `str` | South boundary description | `"Survey No 142/4"` |
| `boundary_east` | `str` | East boundary description | `"Survey No 142/3B"` |
| `boundary_west` | `str` | West boundary description | `"Survey No 142/1"` |
| `purchaser` | `str` | Purchaser / Title Holder name | `"K. S. Ramanathan"` |

### Confidence Tiers
- **High Tier (`>= 0.85`)**: Automatic progression through pipeline.
- **Medium Tier (`0.70 - 0.84`)**: Logged in telemetry audit trail.
- **Low Tier (`< 0.70`)**: Flags `status = "REVIEW_REQUIRED"` on critical fields for Sub-Registrar review.

---

## 2. Person 2: GIS & Spatial Cadastral Validation Contract

### Endpoints
- `POST /api/v1/documents/{document_id}/spatial/validate` -> Runs spatial validation.
- `GET /api/v1/documents/{document_id}/spatial` -> Returns validation metrics and risk evaluation.
- `GET /api/v1/documents/{document_id}/spatial/map` -> Returns GeoJSON FeatureCollection for MapLibre/Leaflet.
- `POST /api/gis/check-overlap` -> Standalone collision verification endpoint.

### Spatial Validation Response Schema (`SpatialValidationResponse`)
```json
{
  "document_id": 1,
  "parcel": {
    "matched": true,
    "survey_number": "142/3A",
    "district": "Chennai",
    "taluk": "Tambaram",
    "village": "Selaiyur",
    "area_sq_m": 222.96
  },
  "geometry": {
    "valid": true,
    "repaired": false,
    "crs": "EPSG:4326"
  },
  "spatial_relationship": {
    "relationship": "DISJOINT",
    "overlap_detected": false,
    "overlap_area_sq_m": 0.0,
    "overlap_percentage": 0.0
  },
  "area_validation": {
    "deed_area_sq_m": 222.96,
    "cadastral_area_sq_m": 222.96,
    "difference_percent": 0.0,
    "status": "CONSISTENT"
  },
  "risk": {
    "score": 0.0,
    "level": "LOW"
  },
  "decision": "APPROVED"
}
```

### Conventions & Geometric Standards
1. **Coordinate Ordering**: GeoJSON coordinates are in `[longitude, latitude]` order (e.g. `[80.1472, 12.9249]`).
2. **Metric Area Calculations**: Area calculations in GIS layer are in square meters (`sq_m`).
3. **Spatial Relationships**: Permitted values: `"DISJOINT"`, `"TOUCHING"`, `"WITHIN"`, `"CONTAINS"`, `"OVERLAPPING"`.
4. **Collision Decisioning**: If `overlap_detected == True` or `relationship == "OVERLAPPING"`, `decision = "REVIEW_REQUIRED"`.
