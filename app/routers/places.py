from typing import Optional
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import func
from sqlalchemy.orm import Session

from ..database import get_db
from ..models import Place, User
from ..schemas import PlaceCreate, PlaceUpdate, PlaceOut
from ..deps import get_current_user

router = APIRouter(prefix="/places", tags=["places"])


@router.get("", response_model=list[PlaceOut])
def list_places(category: Optional[str] = None, db: Session = Depends(get_db)):
    """Public — the guide's frontend calls this with no login required."""
    query = db.query(Place)
    if category:
        query = query.filter(Place.category == category)
    # sort_order first (the intended display order), Place.id as a stable
    # tiebreaker only for rows that happen to share a sort_order (or have
    # none set at all, e.g. rows created before this field existed).
    return query.order_by(Place.category, Place.sort_order, Place.id).all()


@router.get("/{place_id}", response_model=PlaceOut)
def get_place(place_id: str, db: Session = Depends(get_db)):
    place = db.query(Place).filter(Place.id == place_id).first()
    if place is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Place not found")
    return place


@router.post("", response_model=PlaceOut, status_code=status.HTTP_201_CREATED)
def create_place(
    payload: PlaceCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),  # login required
):
    # Generate a readable, collision-resistant id: "<category>-custom-<n>"
    existing_count = db.query(Place).filter(Place.category == payload.category).count()
    import time

    new_id = f"{payload.category}-custom-{int(time.time() * 1000)}"

    # New places go to the end of their section by default, unless the
    # caller explicitly specified a sort_order.
    if payload.sort_order is None:
        max_order = (
            db.query(func.max(Place.sort_order))
            .filter(Place.category == payload.category)
            .scalar()
        )
        next_order = (max_order or 0) + 1
    else:
        next_order = payload.sort_order

    place = Place(
        id=new_id,
        category=payload.category,
        n=payload.n or str(existing_count + 1),
        name=payload.name,
        blurb=payload.blurb,
        address=payload.address,
        address_label=payload.address_label,
        hours=payload.hours,
        phone=payload.phone,
        website=payload.website,
        walk_time=payload.walk_time,
        image=payload.image,
        lat=payload.lat,
        lng=payload.lng,
        map_url=payload.map_url,
        sort_order=next_order,
    )
    db.add(place)
    db.commit()
    db.refresh(place)
    return place


@router.put("/{place_id}", response_model=PlaceOut)
def update_place(
    place_id: str,
    payload: PlaceUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),  # login required
):
    place = db.query(Place).filter(Place.id == place_id).first()
    if place is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Place not found")

    for field, value in payload.model_dump(exclude_unset=True).items():
        setattr(place, field, value)

    db.commit()
    db.refresh(place)
    return place


@router.delete("/{place_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_place(
    place_id: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),  # login required
):
    place = db.query(Place).filter(Place.id == place_id).first()
    if place is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Place not found")
    db.delete(place)
    db.commit()
    return None