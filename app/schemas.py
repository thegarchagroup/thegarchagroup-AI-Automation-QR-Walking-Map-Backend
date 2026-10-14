from typing import Optional
from pydantic import BaseModel, ConfigDict, EmailStr, Field, field_validator


# ---------------------------------------------------------------------------
# Places
# ---------------------------------------------------------------------------

class PlaceBase(BaseModel):
    n: Optional[str] = None
    name: str
    blurb: Optional[str] = None
    address: Optional[str] = None
    address_label: Optional[str] = None
    hours: Optional[str] = None
    phone: Optional[str] = None
    website: Optional[str] = None
    walk_time: Optional[int] = None
    image: Optional[str] = None
    lat: Optional[float] = None
    lng: Optional[float] = None
    map_url: Optional[str] = None
    sort_order: Optional[int] = None


class PlaceCreate(PlaceBase):
    category: str  # see | do | eat | drive


class PlaceUpdate(BaseModel):
    """All fields optional — a PATCH-style partial update."""

    n: Optional[str] = None
    name: Optional[str] = None
    blurb: Optional[str] = None
    address: Optional[str] = None
    address_label: Optional[str] = None
    hours: Optional[str] = None
    phone: Optional[str] = None
    website: Optional[str] = None
    walk_time: Optional[int] = None
    image: Optional[str] = None
    lat: Optional[float] = None
    lng: Optional[float] = None
    map_url: Optional[str] = None
    category: Optional[str] = None
    sort_order: Optional[int] = None


class PlaceOut(PlaceBase):
    id: str
    category: str

    model_config = ConfigDict(from_attributes=True)


# ---------------------------------------------------------------------------
# Auth
# ---------------------------------------------------------------------------

class LoginRequest(BaseModel):
    email: EmailStr
    password: str


class Token(BaseModel):
    access_token: str
    token_type: str = "bearer"


class UserOut(BaseModel):
    id: int
    email: EmailStr

    model_config = ConfigDict(from_attributes=True)


class UserCreate(BaseModel):
    email: EmailStr
    password: str


# ---------------------------------------------------------------------------
# Menu items (the 6 home-screen sections)
# ---------------------------------------------------------------------------

class MenuItemUpdate(BaseModel):
    """All optional — a partial update. `sort_order` is set directly by
    the reorder (swap-with-neighbor) actions; `label`/`tagline` by the
    content edit form."""

    label: Optional[str] = None
    tagline: Optional[str] = None
    sort_order: Optional[int] = None


class MenuItemOut(BaseModel):
    key: str
    label: str
    tagline: Optional[str] = None
    sort_order: int

    model_config = ConfigDict(from_attributes=True)


# ---------------------------------------------------------------------------
# Site settings (home page title + intro)
# ---------------------------------------------------------------------------

class SettingsUpdate(BaseModel):
    """Partial update — only the keys sent are changed."""

    home_title: Optional[str] = None
    home_intro: Optional[str] = None

    @field_validator("home_title", "home_intro")
    @classmethod
    def not_blank(cls, v):
        if v is None:
            return v
        v = v.strip()
        if not v:
            raise ValueError("cannot be blank")
        return v


# ---------------------------------------------------------------------------
# Running Map route
# ---------------------------------------------------------------------------

class RouteStop(BaseModel):
    name: str
    lat: float = Field(ge=-90, le=90)
    lng: float = Field(ge=-180, le=180)
    # True for stops guests can choose as their starting point (the hotels).
    is_start: bool = False

    @field_validator("name")
    @classmethod
    def name_not_blank(cls, v):
        v = v.strip()
        if not v:
            raise ValueError("every stop needs a name")
        return v


class RouteUpdate(BaseModel):
    """Partial update. The route is a closed loop: the last stop connects
    back to the first, so `stops` is just the ordered list."""

    subtitle: Optional[str] = None
    distance_label: Optional[str] = None
    safety_note: Optional[str] = None
    stops: Optional[list[RouteStop]] = Field(default=None, min_length=2, max_length=20)


class RouteOut(BaseModel):
    subtitle: str
    distance_label: str
    safety_note: str
    stops: list[RouteStop]
    # Real walking line, [[lat, lng], ...]; null until first computed.
    geometry: Optional[list[list[float]]] = None
    # Distance of the computed line in km (null if it couldn't be computed).
    computed_km: Optional[float] = None
    routing_status: Optional[str] = None  # "ok" | "fallback"
    routing_provider: Optional[str] = None
    # Human-readable outcome of the last save/recalculate (not stored).
    routing_message: Optional[str] = None
