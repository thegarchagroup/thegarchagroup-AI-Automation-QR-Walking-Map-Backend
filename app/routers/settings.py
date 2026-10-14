from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from ..database import get_db
from ..models import SiteSetting, User
from ..schemas import SettingsUpdate
from ..deps import get_current_user

router = APIRouter(prefix="/settings", tags=["settings"])

# Built-in copy, used until someone edits it in the content editor. A
# missing database row just means "use this", so no seed step is needed.
# The title may contain a line break (the home page shows it on two lines).
DEFAULT_SETTINGS = {
    "home_title": "Little India &\nKampong Gelam",
    "home_intro": (
        "A walking guide to Singapore's Little India and Kampong Gelam, from "
        "the temples, studios and kitchens on your doorstep to a few Garcha "
        "Group favorites worth the trip."
    ),
}


def _merged(db: Session) -> dict[str, str]:
    stored = {row.key: row.value for row in db.query(SiteSetting).all()}
    return {key: stored.get(key, default) for key, default in DEFAULT_SETTINGS.items()}


@router.get("")
def get_settings(db: Session = Depends(get_db)):
    """Public — the home page reads its title and intro from here."""
    return _merged(db)


@router.put("")
def update_settings(
    payload: SettingsUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),  # login required
):
    for key, value in payload.model_dump(exclude_unset=True).items():
        if value is None or key not in DEFAULT_SETTINGS:
            continue
        row = db.query(SiteSetting).filter(SiteSetting.key == key).first()
        if row is None:
            db.add(SiteSetting(key=key, value=value))
        else:
            row.value = value
    db.commit()
    return _merged(db)
