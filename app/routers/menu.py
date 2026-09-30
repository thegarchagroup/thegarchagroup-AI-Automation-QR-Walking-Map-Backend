from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from ..database import get_db
from ..models import MenuItem, User
from ..schemas import MenuItemUpdate, MenuItemOut
from ..deps import get_current_user

router = APIRouter(prefix="/menu", tags=["menu"])


@router.get("", response_model=list[MenuItemOut])
def list_menu_items(db: Session = Depends(get_db)):
    """Public — the home screen calls this with no login required."""
    return db.query(MenuItem).order_by(MenuItem.sort_order).all()


@router.put("/{key}", response_model=MenuItemOut)
def update_menu_item(
    key: str,
    payload: MenuItemUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),  # login required
):
    item = db.query(MenuItem).filter(MenuItem.key == key).first()
    if item is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Menu item not found")

    for field, value in payload.model_dump(exclude_unset=True).items():
        setattr(item, field, value)

    db.commit()
    db.refresh(item)
    return item