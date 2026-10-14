from sqlalchemy import Column, String, Float, Integer, DateTime, Text, JSON
from sqlalchemy.sql import func

from .database import Base


class Place(Base):
    """
    One stop in the guide (a temple, restaurant, workshop, etc). `id` is a
    human-readable string like "see-1" or "eat-custom-1730000000" rather
    than an auto-increment integer, matching the ids already used in the
    existing frontend content.
    """

    __tablename__ = "places"

    id = Column(String, primary_key=True, index=True)
    category = Column(String, nullable=False, index=True)  # see | do | eat | drive
    n = Column(String, nullable=True)  # display badge, e.g. "1" or "V"
    name = Column(String, nullable=False)
    blurb = Column(String, nullable=True)
    address = Column(String, nullable=True)
    address_label = Column(String, nullable=True)  # e.g. "Meeting Point"
    hours = Column(String, nullable=True)
    phone = Column(String, nullable=True)
    website = Column(String, nullable=True)
    walk_time = Column(Integer, nullable=True)  # minutes
    image = Column(String, nullable=True)  # filename in src/assets/
    lat = Column(Float, nullable=True)
    lng = Column(Float, nullable=True)
    map_url = Column(String, nullable=True)
    # Controls display order within a category — independent of the `n`
    # badge text (which is free-form and editable) and independent of the
    # database id (which sorts alphabetically, not numerically: "10"
    # comes right after "1" that way, which is the bug this field fixes).
    sort_order = Column(Integer, nullable=True, index=True)

    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())


class User(Base):
    """An editor account. Anyone with a row here can log in and edit content."""

    __tablename__ = "users"

    id = Column(Integer, primary_key=True, index=True)
    email = Column(String, unique=True, index=True, nullable=False)
    hashed_password = Column(String, nullable=False)
    created_at = Column(DateTime(timezone=True), server_default=func.now())


class MenuItem(Base):
    """
    One of the home screen's 6 numbered sections (Neighborhood Map, Worth
    the Detour, ... Running Map). `key` is the stable identifier the
    frontend uses to decide what a section actually does when tapped
    (e.g. 'map' opens the Neighborhood Map, 'see' opens the Worth the
    Detour list) — it is NOT editable. `label`, `tagline`, and
    `sort_order` are all editable from the content editor; the displayed
    "01/02/03..." number is computed from position, not stored here.
    """

    __tablename__ = "menu_items"

    key = Column(String, primary_key=True)  # map | see | do | eat | drive | running
    label = Column(String, nullable=False)
    tagline = Column(String, nullable=True)
    sort_order = Column(Integer, nullable=False, index=True)


class SiteSetting(Base):
    """
    Free-text copy that appears on the home page and is editable from the
    content editor (currently: home_title, home_intro). One row per key.
    A missing row simply means "use the built-in default" — see
    routers/settings.py — so adding a new editable text later needs no
    migration or seed step.
    """

    __tablename__ = "site_settings"

    key = Column(String, primary_key=True)
    value = Column(Text, nullable=False, default="")


class RouteConfig(Base):
    """
    The Running Map. A single row (id = 1) holding everything the editor
    can change: the page subtitle, the distance label, the safety note and
    the ordered list of stops.

    `stops` is a JSON list of {name, lat, lng, is_start}; the route is a
    closed loop, so the last stop connects back to the first. `geometry`
    is the real walking line ([[lat, lng], ...]) computed from those stops
    by a routing service whenever the stops change — guests never trigger
    a routing call, they just draw the stored line.
    """

    __tablename__ = "route_config"

    id = Column(Integer, primary_key=True)  # always 1
    subtitle = Column(Text, nullable=False, default="")
    distance_label = Column(String, nullable=False, default="")
    safety_note = Column(Text, nullable=False, default="")
    stops = Column(JSON, nullable=False)
    geometry = Column(JSON, nullable=True)
    computed_km = Column(Float, nullable=True)
    routing_status = Column(String, nullable=True)  # "ok" | "fallback"
    routing_provider = Column(String, nullable=True)
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())
