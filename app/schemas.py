from typing import Optional
from pydantic import BaseModel, ConfigDict, EmailStr


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