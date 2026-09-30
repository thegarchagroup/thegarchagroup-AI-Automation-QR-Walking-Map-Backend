from sqlalchemy import Column, String, Float, Integer, DateTime
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