import json
from pathlib import Path
from fastapi import APIRouter

router = APIRouter(prefix="/config", tags=["config"])

_SEED_PATH = Path(__file__).resolve().parent.parent / "seed_content.json"
_seed = json.loads(_SEED_PATH.read_text())


@router.get("")
def get_config():
    """
    Public — the menu structure, panel copy, hotel coordinates, and the
    Running Map's route anchors. These change far less often than places do,
    so for now they're served straight from the same seed file rather than
    living in the database. If they ever need in-app editing too, they can
    move into their own DB table later the same way Place did.
    """
    return {
        "menu": _seed["MENU"],
        "panelCopy": _seed["PANEL_COPY"],
        "hotels": _seed["HOTELS"],
        "route": _seed["ROUTE"],
    }
