from typing import List, Optional, Dict, Any
from datetime import datetime
from pydantic import BaseModel, Field

class GPSCoordinate(BaseModel):
    latitude: float = Field(..., example=16.7040, description="Latitude coordinate")
    longitude: float = Field(..., example=74.2380, description="Longitude coordinate")

class DefectIngest(BaseModel):
    defect_id: int = Field(..., example=1, description="Persistent tracking ID from ByteTrack")
    class_name: str = Field(..., example="pothole", description="Damage class: pothole or alligator_crack")
    severity: str = Field(..., example="High", description="Estimated severity: Low, Medium, or High")
    confidence: float = Field(..., example=0.892, description="Detector confidence score")
    timestamp: Optional[str] = Field(default=None, description="ISO timestamp of defect detection")
    gps: GPSCoordinate
    bbox_norm: List[float] = Field(..., example=[0.25, 0.45, 0.15, 0.12], description="Normalized [x, y, w, h]")
    zone_id: Optional[str] = Field(None, example="central_kolhapur", description="Unique identifier of operational zone")
    zone_name: Optional[str] = Field(None, example="Central Kolhapur", description="Human-readable operational zone name")
    zone: Optional[str] = Field(None, example="Central Kolhapur", description="Legacy zone name alias")
    area: Optional[str] = Field(None, example="Shahupuri", description="Specific locality/area")
    street: Optional[str] = Field(None, example="Station Road, Shahupuri", description="Street name")
    image_snapshot: Optional[str] = Field(None, description="Optional base64 or URL to image crop")

class DefectStatusUpdate(BaseModel):
    status: str = Field(..., example="in_progress", description="New workflow status: reported, inspected, in_progress, repaired")
    assigned_contractor: Optional[str] = Field(None, example="Apex Infrastructure Ltd")
    notes: Optional[str] = Field(None, example="Scheduled for asphalt hot-mix patching")

class DefectRecord(BaseModel):
    id: str
    defect_id: int
    class_name: str
    severity: str
    confidence: float
    status: str
    created_at: str
    updated_at: str
    latitude: float
    longitude: float
    bbox_norm: List[float]
    zone_id: Optional[str] = None
    zone_name: Optional[str] = None
    zone: Optional[str] = None
    area: Optional[str] = None
    street: Optional[str] = None
    assigned_contractor: Optional[str] = None
    notes: Optional[str] = None

class AuthLoginRequest(BaseModel):
    username: Optional[str] = Field(default="ward_officer", example="officer_central")
    password: Optional[str] = Field(default="")
    zone: str = Field(..., example="Central Kolhapur")

class OfficerProfile(BaseModel):
    name: str
    role: str
    zone: str
    zone_id: Optional[str] = None
    jurisdiction_areas: str
    center_gps: List[float]
    default_zoom: int
    challenges: Optional[str] = None
    color: Optional[str] = None

class AnalyticsSummary(BaseModel):
    zone: Optional[str] = None
    zone_id: Optional[str] = None
    total_defects: int
    total_potholes: int
    total_alligator_cracks: int
    high_priority_hazards: int
    medium_hazards: int
    low_hazards: int
    repaired_count: int
    pending_count: int
    repair_rate_percent: float

class ZoneIncidentMetrics(BaseModel):
    zone_id: str
    zone_name: str
    center: List[float]
    localities: List[str]
    challenges: str
    color: str
    total_incidents: int
    potholes: int
    alligator_cracks: int
    severity: Dict[str, int]
    status: Dict[str, int]

class ZoneBreakdownResponse(BaseModel):
    case_study: str = "KOLHAPUR 5-ZONE OPERATIONAL ROAD-DAMAGE MAP"
    subtitle: str = "Project-defined operational zones for regional case-study analysis."
    disclaimer: str = "IMPORTANT: These are PROJECT-DEFINED OPERATIONAL ZONES for academic/case-study analysis, NOT official Kolhapur Municipal Corporation (KMC) legal ward boundaries."
    zones: Dict[str, ZoneIncidentMetrics]
    outside_study_area_count: int
