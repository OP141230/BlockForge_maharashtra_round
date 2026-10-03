"""
BLACKBOX Itinerary Lab — FastAPI Routes
Integrated into the existing BLACKBOX API router (prefix /api).
"""
from __future__ import annotations
from datetime import datetime, timezone
import json
import uuid
from typing import Any, Dict, List, Optional

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session

from backend.database import get_db
from backend.models import Itinerary, ItineraryValidationRun
from backend.itinerary_validator import validator as itin_validator

itinerary_router = APIRouter(prefix="/itinerary", tags=["Itinerary Lab"])


# ── Pydantic schemas ──────────────────────────────────────────────────────────

class ItineraryItemSchema(BaseModel):
    title: str = ""
    category: str = ""          # transport, accommodation, food, attraction, tour, other
    location: str = ""
    date: str = ""              # YYYY-MM-DD
    start_time: str = ""        # HH:MM
    end_time: str = ""          # HH:MM
    cost: float = 0.0
    currency: str = "EUR"
    booking_status: str = ""    # confirmed, unconfirmed, pending
    notes: str = ""

class CreateItinerarySchema(BaseModel):
    name: str
    destination: str
    start_date: str
    end_date: str
    travelers: int = 1
    budget: float = 0.0
    currency: str = "EUR"
    preferences: List[str] = Field(default_factory=list)
    items: List[ItineraryItemSchema] = Field(default_factory=list)
    linked_run_id: Optional[str] = None

class ApplyFixSchema(BaseModel):
    finding_rule_id: str
    item_index: int
    fix_payload: Dict[str, Any] = Field(default_factory=dict)

class ImportItinerarySchema(BaseModel):
    """Allow importing a full itinerary JSON directly."""
    raw: Dict[str, Any]


# ── DEMO SEED DATA ────────────────────────────────────────────────────────────
# Deliberately contains: budget overrun, impossible transfer, duplicate,
# preference mismatch (vegetarian), overloaded day.
# The validator must *detect* these — they are not hard-coded in the UI.

DEMO_PARIS_ITINERARY = {
    "id": "itin_paris_demo",
    "name": "Paris Family Trip",
    "destination": "Paris, France",
    "start_date": "2026-07-10",
    "end_date": "2026-07-14",
    "travelers": 4,
    "budget": 2500.0,
    "currency": "EUR",
    "preferences": ["family-friendly", "vegetarian"],
    "linked_run_id": "run_travel_paris_fail",
    "is_demo": True,
    "items": [
        # Day 1 — arrival
        {
            "title": "CDG Airport → Hotel Le Marais",
            "category": "transport",
            "location": "CDG Airport",
            "date": "2026-07-10",
            "start_time": "11:00",
            "end_time": "12:30",
            "cost": 60.0,
            "currency": "EUR",
            "booking_status": "confirmed",
            "notes": "Taxi transfer",
        },
        {
            "title": "Hotel Le Marais Check-in",
            "category": "accommodation",
            "location": "Marais District",
            "date": "2026-07-10",
            "start_time": "14:00",
            "end_time": "15:00",
            "cost": 580.0,
            "currency": "EUR",
            "booking_status": "confirmed",
            "notes": "4 nights, family room",
        },
        # ── Fault 5: accommodation for 2026-07-11 through 2026-07-13 not listed
        # (hotel_checkin rule fires because there are missing nights)
        {
            "title": "Dinner at Le Steakhouse Marais",     # Fault 4: preference mismatch (vegetarian)
            "category": "food",
            "location": "Marais District",
            "date": "2026-07-10",
            "start_time": "19:30",
            "end_time": "21:30",
            "cost": 120.0,
            "currency": "EUR",
            "booking_status": "confirmed",
            "notes": "Famous steakhouse",
        },
        # Day 2 — Versailles + Louvre (Fault 2: impossible transfer)
        {
            "title": "Palace of Versailles",
            "category": "attraction",
            "location": "Versailles",
            "date": "2026-07-11",
            "start_time": "09:00",
            "end_time": "11:30",    # ends 11:30 — Louvre is ~55 min away
            "cost": 100.0,
            "currency": "EUR",
            "booking_status": "confirmed",
            "notes": "Family tickets",
        },
        {
            "title": "Louvre Museum",                      # Fault 2: starts at 12:00 — only 30 min gap, need 55
            "category": "attraction",
            "location": "Louvre",
            "date": "2026-07-11",
            "start_time": "12:00",
            "end_time": "15:00",
            "cost": 60.0,
            "currency": "EUR",
            "booking_status": "confirmed",
            "notes": "Guided family tour",
        },
        {
            "title": "Eiffel Tower",
            "category": "attraction",
            "location": "Eiffel Tower",
            "date": "2026-07-11",
            "start_time": "16:00",
            "end_time": "18:00",
            "cost": 80.0,
            "currency": "EUR",
            "booking_status": "confirmed",
            "notes": "Second floor tickets",
        },
        {
            "title": "Seine River Cruise",
            "category": "attraction",
            "location": "Seine River Cruise",
            "date": "2026-07-11",
            "start_time": "19:00",
            "end_time": "20:30",
            "cost": 60.0,
            "currency": "EUR",
            "booking_status": "confirmed",
            "notes": "Evening cruise",
        },
        {
            "title": "Sacré-Cœur at Night",
            "category": "attraction",
            "location": "Sacré-Cœur",
            "date": "2026-07-11",
            "start_time": "21:00",
            "end_time": "22:30",
            "cost": 0.0,
            "currency": "EUR",
            "booking_status": "confirmed",
            "notes": "Free",
        },
        {
            "title": "Arc de Triomphe",                   # Fault 5: 7th activity on same day
            "category": "attraction",
            "location": "Arc de Triomphe",
            "date": "2026-07-11",
            "start_time": "23:00",
            "end_time": "23:45",
            "cost": 20.0,
            "currency": "EUR",
            "booking_status": "confirmed",
            "notes": "Night view",
        },
        # Day 3 — Musée d'Orsay + duplicate Louvre
        {
            "title": "Musée d'Orsay",
            "category": "attraction",
            "location": "Musée d'Orsay",
            "date": "2026-07-12",
            "start_time": "10:00",
            "end_time": "13:00",
            "cost": 60.0,
            "currency": "EUR",
            "booking_status": "confirmed",
            "notes": "",
        },
        {
            "title": "Louvre Museum",                      # Fault 3: exact duplicate
            "category": "attraction",
            "location": "Louvre",
            "date": "2026-07-12",
            "start_time": "14:00",
            "end_time": "17:00",
            "cost": 60.0,
            "currency": "EUR",
            "booking_status": "confirmed",
            "notes": "Second visit — duplicate!",
        },
        {
            "title": "Jardin des Tuileries",
            "category": "attraction",
            "location": "Jardin des Tuileries",
            "date": "2026-07-12",
            "start_time": "17:30",
            "end_time": "19:00",
            "cost": 0.0,
            "currency": "EUR",
            "booking_status": "confirmed",
            "notes": "Free garden",
        },
        # Day 4 — departure
        {
            "title": "Galeries Lafayette Shopping",
            "category": "attraction",
            "location": "Galeries Lafayette",
            "date": "2026-07-13",
            "start_time": "10:00",
            "end_time": "12:30",
            "cost": 200.0,
            "currency": "EUR",
            "booking_status": "confirmed",
            "notes": "Estimated spend",
        },
        {
            "title": "Hotel Le Marais Check-out",
            "category": "accommodation",
            "location": "Marais District",
            "date": "2026-07-14",
            "start_time": "10:00",
            "end_time": "11:00",
            "cost": 0.0,
            "currency": "EUR",
            "booking_status": "confirmed",
            "notes": "Check-out day",
        },
        {
            "title": "Hotel Le Marais → CDG",
            "category": "transport",
            "location": "Marais District",
            "date": "2026-07-14",
            "start_time": "12:00",
            "end_time": "13:30",
            "cost": 65.0,
            "currency": "EUR",
            "booking_status": "confirmed",
            "notes": "Return taxi",
        },
    ],
}
# Fault 1: budget check — sum all costs
# 60+580+120+100+60+80+60+0+20+60+60+0+200+0+65 = 1465 … under budget
# We'll push budget overrun by adding a suspiciously large item:
DEMO_PARIS_ITINERARY["items"].append({
    "title": "Premium Paris City Pass (4 days × 4 people)",
    "category": "attraction",
    "location": "Paris",
    "date": "2026-07-10",
    "start_time": "",
    "end_time": "",
    "cost": 1280.0,               # this tips total to 2745 > budget 2500
    "currency": "EUR",
    "booking_status": "unconfirmed",
    "notes": "Optional add-on — not yet confirmed",
})


def _seed_demo_itinerary(db: Session) -> None:
    existing = db.query(Itinerary).filter(Itinerary.id == DEMO_PARIS_ITINERARY["id"]).first()
    if existing:
        return
    itin = Itinerary(
        id=DEMO_PARIS_ITINERARY["id"],
        name=DEMO_PARIS_ITINERARY["name"],
        destination=DEMO_PARIS_ITINERARY["destination"],
        start_date=DEMO_PARIS_ITINERARY["start_date"],
        end_date=DEMO_PARIS_ITINERARY["end_date"],
        travelers=DEMO_PARIS_ITINERARY["travelers"],
        budget=DEMO_PARIS_ITINERARY["budget"],
        currency=DEMO_PARIS_ITINERARY["currency"],
        preferences=json.dumps(DEMO_PARIS_ITINERARY["preferences"]),
        items_json=json.dumps(DEMO_PARIS_ITINERARY["items"]),
        linked_run_id=DEMO_PARIS_ITINERARY.get("linked_run_id"),
        is_demo=True,
        created_at=datetime.now(timezone.utc),
    )
    db.add(itin)
    db.commit()


# ── Routes ────────────────────────────────────────────────────────────────────

@itinerary_router.get("")
def list_itineraries(db: Session = Depends(get_db)):
    """List all saved itineraries."""
    _seed_demo_itinerary(db)
    rows = db.query(Itinerary).order_by(Itinerary.created_at.desc()).all()
    return {"itineraries": [r.to_dict() for r in rows], "total": len(rows)}


@itinerary_router.get("/{itin_id}")
def get_itinerary(itin_id: str, db: Session = Depends(get_db)):
    """Get a single itinerary with its validation run history."""
    _seed_demo_itinerary(db)
    itin = db.query(Itinerary).filter(Itinerary.id == itin_id).first()
    if not itin:
        raise HTTPException(status_code=404, detail=f"Itinerary '{itin_id}' not found.")
    result = itin.to_dict()
    runs = (
        db.query(ItineraryValidationRun)
        .filter(ItineraryValidationRun.itinerary_id == itin_id)
        .order_by(ItineraryValidationRun.created_at)
        .all()
    )
    result["validation_runs"] = [r.to_dict() for r in runs]
    return result


@itinerary_router.post("")
def create_itinerary(body: CreateItinerarySchema, db: Session = Depends(get_db)):
    """Create a new itinerary."""
    itin_id = f"itin_{uuid.uuid4().hex[:12]}"
    itin = Itinerary(
        id=itin_id,
        name=body.name,
        destination=body.destination,
        start_date=body.start_date,
        end_date=body.end_date,
        travelers=body.travelers,
        budget=body.budget,
        currency=body.currency,
        preferences=json.dumps(body.preferences),
        items_json=json.dumps([i.model_dump() for i in body.items]),
        linked_run_id=body.linked_run_id,
        is_demo=False,
        created_at=datetime.now(timezone.utc),
    )
    db.add(itin)
    db.commit()
    return itin.to_dict()


@itinerary_router.post("/import")
def import_itinerary(body: ImportItinerarySchema, db: Session = Depends(get_db)):
    """
    Import an itinerary from raw JSON.
    Only DATA fields are accepted — no code is executed from imported content.
    """
    raw = body.raw
    itin_id = f"itin_{uuid.uuid4().hex[:12]}"
    items = raw.get("items", [])
    # Sanitise — accept only known scalar fields per item
    ALLOWED_ITEM_KEYS = {
        "title", "category", "location", "date", "start_time", "end_time",
        "cost", "currency", "booking_status", "notes",
    }
    clean_items = [
        {k: v for k, v in item.items() if k in ALLOWED_ITEM_KEYS}
        for item in items
        if isinstance(item, dict)
    ]
    itin = Itinerary(
        id=itin_id,
        name=str(raw.get("name", "Imported Itinerary"))[:256],
        destination=str(raw.get("destination", "Unknown"))[:256],
        start_date=str(raw.get("start_date", ""))[:32],
        end_date=str(raw.get("end_date", ""))[:32],
        travelers=int(raw.get("travelers", 1)),
        budget=float(raw.get("budget", 0)),
        currency=str(raw.get("currency", "EUR"))[:8],
        preferences=json.dumps(
            [str(p) for p in raw.get("preferences", []) if isinstance(p, str)]
        ),
        items_json=json.dumps(clean_items),
        linked_run_id=str(raw.get("linked_run_id", "") or "")[:64] or None,
        is_demo=False,
        created_at=datetime.now(timezone.utc),
    )
    db.add(itin)
    db.commit()
    return {"imported_id": itin_id, **itin.to_dict()}


@itinerary_router.post("/{itin_id}/validate")
def validate_itinerary(itin_id: str, db: Session = Depends(get_db)):
    """Run the deterministic validation engine and store results."""
    _seed_demo_itinerary(db)
    itin = db.query(Itinerary).filter(Itinerary.id == itin_id).first()
    if not itin:
        raise HTTPException(status_code=404, detail=f"Itinerary '{itin_id}' not found.")

    itin_dict = itin.to_dict()
    items = itin_dict["items"]

    result = itin_validator.validate(
        itinerary=itin_dict,
        items=items,
        linked_run_id=itin.linked_run_id,
        linked_step_id=None,
    )

    # Annotate findings with existing BLACKBOX run/step links
    for f in result["findings"]:
        if not f.get("linked_run_id") and itin.linked_run_id:
            f["linked_run_id"] = itin.linked_run_id

    run_id = f"valrun_{uuid.uuid4().hex[:10]}"
    existing_runs = (
        db.query(ItineraryValidationRun)
        .filter(ItineraryValidationRun.itinerary_id == itin_id)
        .count()
    )
    label = "BEFORE" if existing_runs == 0 else f"RUN_{existing_runs + 1}"

    vrun = ItineraryValidationRun(
        id=run_id,
        itinerary_id=itin_id,
        findings_json=json.dumps(result["findings"]),
        summary_json=json.dumps(result["summary"]),
        patched_items_json=None,
        label=label,
        created_at=datetime.now(timezone.utc),
    )
    db.add(vrun)
    db.commit()

    return {
        "validation_run_id": run_id,
        "label": label,
        "findings": result["findings"],
        "summary": result["summary"],
        "itinerary_id": itin_id,
        "linked_run_id": itin.linked_run_id,
    }


@itinerary_router.post("/{itin_id}/apply-fix")
def apply_fix(itin_id: str, body: ApplyFixSchema, db: Session = Depends(get_db)):
    """
    Apply a deterministic suggested fix to the itinerary and re-run validation.
    Never silently modifies — always returns the diff and new findings.
    """
    itin = db.query(Itinerary).filter(Itinerary.id == itin_id).first()
    if not itin:
        raise HTTPException(status_code=404, detail=f"Itinerary '{itin_id}' not found.")

    items: List[Dict] = json.loads(itin.items_json)
    idx = body.item_index

    if idx < 0 or idx >= len(items):
        raise HTTPException(status_code=400, detail=f"item_index {idx} out of range.")

    original_item = dict(items[idx])
    fix = body.fix_payload

    # Apply fix based on rule type
    patched_items = [dict(it) for it in items]

    if body.finding_rule_id == "AUTO_REMOVE" or fix.get("action") == "remove":
        patched_items.pop(idx)
        change_description = f"Removed item #{idx + 1}: '{original_item.get('title')}'"
    elif body.finding_rule_id == "AUTO_RESCHEDULE" or "new_start_time" in fix:
        new_start = fix.get("new_start_time", "")
        patched_items[idx]["start_time"] = new_start
        change_description = (
            f"Rescheduled '{original_item.get('title')}' start_time "
            f"from {original_item.get('start_time')} → {new_start}"
        )
    else:
        # Generic patch: apply all provided fields
        for k, v in fix.items():
            if k in {"title","category","location","date","start_time","end_time","cost","currency","booking_status","notes"}:
                patched_items[idx][k] = v
        change_description = f"Patched item #{idx + 1}: {list(fix.keys())}"

    # Re-validate with patched items
    itin_dict = itin.to_dict()
    result = itin_validator.validate(
        itinerary=itin_dict,
        items=patched_items,
        linked_run_id=itin.linked_run_id,
    )

    # Persist patched run
    run_id = f"valrun_{uuid.uuid4().hex[:10]}"
    existing_runs = (
        db.query(ItineraryValidationRun)
        .filter(ItineraryValidationRun.itinerary_id == itin_id)
        .count()
    )
    vrun = ItineraryValidationRun(
        id=run_id,
        itinerary_id=itin_id,
        findings_json=json.dumps(result["findings"]),
        summary_json=json.dumps(result["summary"]),
        patched_items_json=json.dumps(patched_items),
        label="AFTER",
        created_at=datetime.now(timezone.utc),
    )
    db.add(vrun)
    db.commit()

    return {
        "validation_run_id": run_id,
        "label": "AFTER",
        "change_applied": change_description,
        "original_item": original_item,
        "patched_item": patched_items[idx] if idx < len(patched_items) else None,
        "findings": result["findings"],
        "summary": result["summary"],
        "patched_items": patched_items,
    }


@itinerary_router.get("/{itin_id}/runs")
def get_validation_runs(itin_id: str, db: Session = Depends(get_db)):
    """Get all validation run history for an itinerary."""
    runs = (
        db.query(ItineraryValidationRun)
        .filter(ItineraryValidationRun.itinerary_id == itin_id)
        .order_by(ItineraryValidationRun.created_at)
        .all()
    )
    return {"itinerary_id": itin_id, "runs": [r.to_dict() for r in runs]}
