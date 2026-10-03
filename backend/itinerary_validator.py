"""
BLACKBOX Itinerary Lab — Deterministic Validation Engine
=========================================================
All rules are deterministic and reproducible.
No external APIs, no LLMs, no randomness.
Travel-time estimates use a small fixture of known city coordinates.
"""
from __future__ import annotations
import math
import re
from datetime import date, datetime, time, timedelta
from typing import Any, Dict, List, Optional, Tuple


# ─────────────────────────────────────────────────────────────────────────────
# COORDINATE FIXTURE  (lat, lon) — used for travel-time estimation only
# ─────────────────────────────────────────────────────────────────────────────
COORD_FIXTURE: Dict[str, Tuple[float, float]] = {
    # Paris landmarks
    "eiffel tower": (48.8584, 2.2945),
    "louvre museum": (48.8606, 2.3376),
    "louvre": (48.8606, 2.3376),
    "musée d'orsay": (48.8600, 2.3266),
    "musee d'orsay": (48.8600, 2.3266),
    "notre-dame cathedral": (48.8530, 2.3499),
    "notre dame": (48.8530, 2.3499),
    "palace of versailles": (48.8049, 2.1204),
    "versailles": (48.8049, 2.1204),
    "sacré-cœur": (48.8867, 2.3431),
    "sacre coeur": (48.8867, 2.3431),
    "arc de triomphe": (48.8738, 2.2950),
    "musée rodin": (48.8554, 2.3160),
    "centre pompidou": (48.8607, 2.3522),
    "marais district": (48.8573, 2.3541),
    "champs-élysées": (48.8698, 2.3078),
    "seine river cruise": (48.8566, 2.3522),
    "galeries lafayette": (48.8738, 2.3319),
    "jardin des tuileries": (48.8634, 2.3274),
    "palais royal": (48.8638, 2.3370),
    # Generic hotel placeholder
    "hotel": (48.8566, 2.3522),
}

# Walking speed ~5 km/h, transit adds ~10 min boarding overhead
# Driving: 30 km/h average in Paris
WALK_SPEED_KMH = 5.0
TRANSIT_SPEED_KMH = 25.0
TRANSIT_OVERHEAD_MIN = 10
# We assume transit for distances > 1.5 km
TRANSIT_THRESHOLD_KM = 1.5


def _haversine_km(lat1: float, lon1: float, lat2: float, lon2: float) -> float:
    R = 6371.0
    phi1, phi2 = math.radians(lat1), math.radians(lat2)
    dphi = math.radians(lat2 - lat1)
    dlambda = math.radians(lon2 - lon1)
    a = math.sin(dphi / 2) ** 2 + math.cos(phi1) * math.cos(phi2) * math.sin(dlambda / 2) ** 2
    return R * 2 * math.atan2(math.sqrt(a), math.sqrt(1 - a))


def _travel_minutes(loc_a: str, loc_b: str) -> Optional[int]:
    """Return estimated travel time in minutes using fixture coordinates.
    Returns None if either location is not in the fixture."""
    key_a = loc_a.strip().lower()
    key_b = loc_b.strip().lower()
    # fuzzy-match: check if any fixture key is a substring of the input
    coord_a = coord_b = None
    for k, v in COORD_FIXTURE.items():
        if k in key_a or key_a in k:
            coord_a = v
        if k in key_b or key_b in k:
            coord_b = v
    if coord_a is None or coord_b is None:
        return None
    dist_km = _haversine_km(*coord_a, *coord_b)
    if dist_km < 0.1:
        return 5  # same venue, minimal movement
    if dist_km <= TRANSIT_THRESHOLD_KM:
        return int((dist_km / WALK_SPEED_KMH) * 60) + 3
    return int((dist_km / TRANSIT_SPEED_KMH) * 60) + TRANSIT_OVERHEAD_MIN


def _parse_time(t: Any) -> Optional[datetime]:
    """Parse HH:MM or ISO datetime string to datetime (date-less, uses 1900-01-01)."""
    if not t:
        return None
    s = str(t).strip()
    for fmt in ("%H:%M", "%H:%M:%S", "%Y-%m-%dT%H:%M", "%Y-%m-%dT%H:%M:%S"):
        try:
            return datetime.strptime(s, fmt)
        except ValueError:
            pass
    return None


def _parse_date(d: Any) -> Optional[date]:
    if not d:
        return None
    s = str(d).strip()
    for fmt in ("%Y-%m-%d", "%d/%m/%Y", "%m/%d/%Y"):
        try:
            return datetime.strptime(s, fmt).date()
        except ValueError:
            pass
    return None


def _minutes_between(start: datetime, end: datetime) -> int:
    return int((end - start).total_seconds() / 60)


# ─────────────────────────────────────────────────────────────────────────────
# FINDING STRUCTURE
# ─────────────────────────────────────────────────────────────────────────────
SEVERITIES = ("CRITICAL", "HIGH", "MEDIUM", "LOW", "OPTIMIZATION")


def _finding(
    rule_id: str,
    severity: str,
    title: str,
    affected_item_indices: List[int],
    related_item_indices: List[int],
    evidence: Dict[str, Any],
    expected: str,
    actual: str,
    why_it_matters: str,
    suggested_fix: str,
    fix_type: str = "MANUAL",         # MANUAL | AUTO_RESCHEDULE | AUTO_REMOVE | AUTO_BUDGET
    fix_payload: Optional[Dict] = None,
    linked_run_id: Optional[str] = None,
    linked_step_id: Optional[str] = None,
) -> Dict[str, Any]:
    assert severity in SEVERITIES, f"Bad severity: {severity}"
    return {
        "rule_id": rule_id,
        "severity": severity,
        "title": title,
        "affected_item_indices": affected_item_indices,
        "related_item_indices": related_item_indices,
        "evidence": evidence,
        "expected": expected,
        "actual": actual,
        "why_it_matters": why_it_matters,
        "suggested_fix": suggested_fix,
        "fix_type": fix_type,
        "fix_payload": fix_payload or {},
        "linked_run_id": linked_run_id,
        "linked_step_id": linked_step_id,
    }


# ─────────────────────────────────────────────────────────────────────────────
# VALIDATION ENGINE
# ─────────────────────────────────────────────────────────────────────────────

class ItineraryValidator:
    """
    Modular deterministic itinerary validation engine.
    Each rule is a private method that appends to the findings list.
    Rules never modify the itinerary — they only observe.
    """

    def validate(
        self,
        itinerary: Dict[str, Any],
        items: List[Dict[str, Any]],
        linked_run_id: Optional[str] = None,
        linked_step_id: Optional[str] = None,
    ) -> Dict[str, Any]:
        findings: List[Dict[str, Any]] = []

        ctx = {
            "itinerary": itinerary,
            "items": items,
            "linked_run_id": linked_run_id,
            "linked_step_id": linked_step_id,
        }

        rules = [
            self._rule_budget_overrun,
            self._rule_impossible_transfer,
            self._rule_overlapping_activities,
            self._rule_duplicate_activities,
            self._rule_preference_mismatch,
            self._rule_overloaded_day,
            self._rule_date_violations,
            self._rule_missing_critical_info,
            self._rule_unconfirmed_important_bookings,
            self._rule_suspicious_costs,
            self._rule_hotel_checkin_consistency,
            self._rule_flight_timeline_conflict,
            self._rule_inefficient_routing,
        ]

        for rule in rules:
            try:
                rule(ctx, findings)
            except Exception as e:
                # Rule errors must not crash the validator
                findings.append(_finding(
                    rule_id="rule_error",
                    severity="LOW",
                    title=f"Validation rule error: {rule.__name__}",
                    affected_item_indices=[],
                    related_item_indices=[],
                    evidence={"error": str(e)},
                    expected="Rule runs without error",
                    actual=str(e),
                    why_it_matters="Internal validator issue — does not indicate an itinerary problem.",
                    suggested_fix="Report this to the BLACKBOX team.",
                ))

        summary = self._summarise(items, findings)
        return {"findings": findings, "summary": summary}

    # ── helpers ───────────────────────────────────────────────────────────────

    @staticmethod
    def _item_times(item: Dict) -> Tuple[Optional[datetime], Optional[datetime]]:
        return _parse_time(item.get("start_time")), _parse_time(item.get("end_time"))

    # ── RULE 1: Budget overrun ────────────────────────────────────────────────
    def _rule_budget_overrun(self, ctx: Dict, findings: List) -> None:
        itin = ctx["itinerary"]
        items = ctx["items"]
        budget = float(itin.get("budget", 0))
        currency = itin.get("currency", "EUR")
        if budget <= 0:
            return

        total = sum(float(item.get("cost", 0) or 0) for item in items)
        if total > budget:
            excess = total - budget
            findings.append(_finding(
                rule_id="BUDGET_OVERRUN",
                severity="CRITICAL",
                title="Budget Overrun",
                affected_item_indices=list(range(len(items))),
                related_item_indices=[],
                evidence={
                    "total_cost": round(total, 2),
                    "budget_limit": budget,
                    "excess": round(excess, 2),
                    "currency": currency,
                    "item_breakdown": [
                        {"title": it.get("title", f"Item {i}"), "cost": it.get("cost", 0)}
                        for i, it in enumerate(items)
                    ],
                },
                expected=f"Total cost ≤ {budget} {currency}",
                actual=f"Total cost = {round(total, 2)} {currency} (+{round(excess, 2)} over budget)",
                why_it_matters="The itinerary exceeds the stated budget. Users may be unable to complete the trip as planned.",
                suggested_fix=(
                    f"Reduce total costs by at least {round(excess, 2)} {currency}. "
                    "Consider removing or substituting lower-priority activities."
                ),
                fix_type="MANUAL",
                linked_run_id=ctx.get("linked_run_id"),
                linked_step_id=ctx.get("linked_step_id"),
            ))

    # ── RULE 2: Impossible transfer (too little time between adjacent items) ──
    def _rule_impossible_transfer(self, ctx: Dict, findings: List) -> None:
        items = ctx["items"]
        # Sort by date then start_time
        dated = []
        for i, item in enumerate(items):
            st, et = self._item_times(item)
            d = _parse_date(item.get("date"))
            if d and st and et:
                dated.append((i, item, d, st, et))

        dated.sort(key=lambda x: (x[2], x[3]))

        for idx in range(len(dated) - 1):
            i_a, item_a, date_a, st_a, et_a = dated[idx]
            i_b, item_b, date_b, st_b, et_b = dated[idx + 1]

            if date_a != date_b:
                continue  # different days — no transfer issue
            if et_a > st_b:
                continue  # overlap handled separately

            gap_min = _minutes_between(et_a, st_b)
            loc_a = item_a.get("location", "")
            loc_b = item_b.get("location", "")
            travel = _travel_minutes(loc_a, loc_b)

            if travel is not None and gap_min < travel:
                findings.append(_finding(
                    rule_id="IMPOSSIBLE_TRANSFER",
                    severity="CRITICAL",
                    title="Impossible Transfer",
                    affected_item_indices=[i_b],
                    related_item_indices=[i_a],
                    evidence={
                        "from_activity": item_a.get("title"),
                        "from_end_time": item_a.get("end_time"),
                        "from_location": loc_a,
                        "to_activity": item_b.get("title"),
                        "to_start_time": item_b.get("start_time"),
                        "to_location": loc_b,
                        "gap_available_min": gap_min,
                        "travel_time_estimated_min": travel,
                        "shortfall_min": travel - gap_min,
                    },
                    expected=f"≥{travel} min gap between '{item_a.get('title')}' and '{item_b.get('title')}'",
                    actual=f"Only {gap_min} min available — {travel - gap_min} min short",
                    why_it_matters=(
                        "Users will miss the start of the next activity or need to leave the "
                        "previous one early."
                    ),
                    suggested_fix=(
                        f"Move '{item_b.get('title')}' start time to at least "
                        f"{(datetime(1900, 1, 1) + timedelta(minutes=int((et_a - datetime(1900, 1, 1)).total_seconds() / 60) + travel + 5)).strftime('%H:%M')}."
                    ),
                    fix_type="AUTO_RESCHEDULE",
                    fix_payload={
                        "item_index": i_b,
                        "new_start_time": (
                            datetime(1900, 1, 1) + timedelta(
                                minutes=int((et_a - datetime(1900, 1, 1)).total_seconds() / 60) + travel + 5
                            )
                        ).strftime("%H:%M"),
                    },
                ))

    # ── RULE 3: Overlapping activities ────────────────────────────────────────
    def _rule_overlapping_activities(self, ctx: Dict, findings: List) -> None:
        items = ctx["items"]
        dated = []
        for i, item in enumerate(items):
            st, et = self._item_times(item)
            d = _parse_date(item.get("date"))
            if d and st and et:
                dated.append((i, item, d, st, et))

        for a in range(len(dated)):
            for b in range(a + 1, len(dated)):
                i_a, item_a, d_a, st_a, et_a = dated[a]
                i_b, item_b, d_b, st_b, et_b = dated[b]
                if d_a != d_b:
                    continue
                # Overlap: start_b < end_a AND start_a < end_b
                if st_b < et_a and st_a < et_b:
                    overlap_min = _minutes_between(max(st_a, st_b), min(et_a, et_b))
                    findings.append(_finding(
                        rule_id="OVERLAPPING_ACTIVITIES",
                        severity="CRITICAL",
                        title="Overlapping Activities",
                        affected_item_indices=[i_a, i_b],
                        related_item_indices=[],
                        evidence={
                            "activity_a": item_a.get("title"),
                            "a_start": item_a.get("start_time"),
                            "a_end": item_a.get("end_time"),
                            "activity_b": item_b.get("title"),
                            "b_start": item_b.get("start_time"),
                            "b_end": item_b.get("end_time"),
                            "overlap_minutes": overlap_min,
                        },
                        expected="Activities on the same day must not overlap in time",
                        actual=f"'{item_a.get('title')}' and '{item_b.get('title')}' overlap by {overlap_min} min",
                        why_it_matters="The user cannot attend both activities simultaneously.",
                        suggested_fix=f"Reschedule '{item_b.get('title')}' to start after '{item_a.get('title')}' ends.",
                        fix_type="AUTO_RESCHEDULE",
                        fix_payload={"item_index": i_b, "new_start_time": item_a.get("end_time")},
                    ))

    # ── RULE 4: Duplicate activities ──────────────────────────────────────────
    def _rule_duplicate_activities(self, ctx: Dict, findings: List) -> None:
        items = ctx["items"]
        seen: Dict[str, int] = {}
        for i, item in enumerate(items):
            key = item.get("title", "").strip().lower()
            if not key:
                continue
            if key in seen:
                findings.append(_finding(
                    rule_id="DUPLICATE_ACTIVITY",
                    severity="HIGH",
                    title="Duplicate Activity",
                    affected_item_indices=[i],
                    related_item_indices=[seen[key]],
                    evidence={
                        "title": item.get("title"),
                        "first_occurrence_index": seen[key],
                        "duplicate_index": i,
                        "first_date": items[seen[key]].get("date"),
                        "duplicate_date": item.get("date"),
                    },
                    expected="Each activity should appear at most once",
                    actual=f"'{item.get('title')}' appears at index {seen[key]} and {i}",
                    why_it_matters="Duplicate activities waste time and inflate the budget.",
                    suggested_fix=f"Remove the duplicate '{item.get('title')}' entry (item #{i + 1}).",
                    fix_type="AUTO_REMOVE",
                    fix_payload={"item_index": i},
                ))
            else:
                seen[key] = i

    # ── RULE 5: Preference mismatch ───────────────────────────────────────────
    def _rule_preference_mismatch(self, ctx: Dict, findings: List) -> None:
        itin = ctx["itinerary"]
        items = ctx["items"]
        prefs = [p.strip().lower() for p in itin.get("preferences", [])]
        if not prefs:
            return

        VEGETARIAN_TRIGGERS = {
            "meat", "beef", "pork", "chicken", "steak", "lamb",
            "burger", "bacon", "seafood", "fish", "sushi", "brasserie",
            "steakhouse", "bbq", "barbecue",
        }
        FAMILY_FRIENDLY_TRIGGERS = {
            "bar", "nightclub", "casino", "adult", "lounge",
            "wine bar", "cocktail bar",
        }

        for i, item in enumerate(items):
            if item.get("category", "").lower() not in ("food", "restaurant", "dining"):
                continue
            title_lower = (item.get("title", "") + " " + item.get("notes", "")).lower()

            if "vegetarian" in prefs:
                for trigger in VEGETARIAN_TRIGGERS:
                    if trigger in title_lower:
                        findings.append(_finding(
                            rule_id="PREFERENCE_MISMATCH_VEGETARIAN",
                            severity="HIGH",
                            title="Preference Mismatch — Vegetarian",
                            affected_item_indices=[i],
                            related_item_indices=[],
                            evidence={
                                "preference": "Vegetarian",
                                "conflicting_item": item.get("title"),
                                "trigger_word": trigger,
                                "item_notes": item.get("notes", ""),
                            },
                            expected="Dining choices should be vegetarian-compatible",
                            actual=f"'{item.get('title')}' contains '{trigger}' which is not vegetarian",
                            why_it_matters="A non-vegetarian restaurant may not serve adequate food for the travellers.",
                            suggested_fix=f"Replace '{item.get('title')}' with a vegetarian restaurant.",
                            fix_type="MANUAL",
                        ))
                        break

            if "family-friendly" in prefs or "family friendly" in prefs:
                for trigger in FAMILY_FRIENDLY_TRIGGERS:
                    if trigger in title_lower:
                        findings.append(_finding(
                            rule_id="PREFERENCE_MISMATCH_FAMILY",
                            severity="MEDIUM",
                            title="Preference Mismatch — Family-Friendly",
                            affected_item_indices=[i],
                            related_item_indices=[],
                            evidence={
                                "preference": "Family-friendly",
                                "conflicting_item": item.get("title"),
                                "trigger_word": trigger,
                            },
                            expected="Venues should be suitable for families with children",
                            actual=f"'{item.get('title')}' appears to be an adult venue ('{trigger}')",
                            why_it_matters="Children may not be admitted or comfortable at this venue.",
                            suggested_fix=f"Replace '{item.get('title')}' with a family-friendly dining option.",
                            fix_type="MANUAL",
                        ))
                        break

    # ── RULE 6: Overloaded day ────────────────────────────────────────────────
    def _rule_overloaded_day(self, ctx: Dict, findings: List) -> None:
        items = ctx["items"]
        MAX_ACTIVITIES_PER_DAY = 5
        MAX_ACTIVE_HOURS = 12

        by_day: Dict[str, List[Tuple[int, Dict]]] = {}
        for i, item in enumerate(items):
            d = item.get("date")
            if d:
                by_day.setdefault(d, []).append((i, item))

        for day, day_items in by_day.items():
            if len(day_items) > MAX_ACTIVITIES_PER_DAY:
                indices = [i for i, _ in day_items]
                findings.append(_finding(
                    rule_id="OVERLOADED_DAY_COUNT",
                    severity="MEDIUM",
                    title="Overloaded Day (Too Many Activities)",
                    affected_item_indices=indices,
                    related_item_indices=[],
                    evidence={
                        "date": day,
                        "activity_count": len(day_items),
                        "max_recommended": MAX_ACTIVITIES_PER_DAY,
                        "activities": [it.get("title") for _, it in day_items],
                    },
                    expected=f"≤{MAX_ACTIVITIES_PER_DAY} activities per day (family-friendly threshold)",
                    actual=f"{len(day_items)} activities on {day}",
                    why_it_matters="Cramming too many activities into one day leads to exhaustion, especially for families.",
                    suggested_fix=f"Move some activities from {day} to a less busy day or remove lower-priority ones.",
                    fix_type="MANUAL",
                ))

            # Also check total active hours
            active_min = 0
            for _, item in day_items:
                st, et = self._item_times(item)
                if st and et and et > st:
                    active_min += _minutes_between(st, et)
            if active_min > MAX_ACTIVE_HOURS * 60:
                indices = [i for i, _ in day_items]
                findings.append(_finding(
                    rule_id="OVERLOADED_DAY_HOURS",
                    severity="MEDIUM",
                    title="Overloaded Day (Excessive Active Hours)",
                    affected_item_indices=indices,
                    related_item_indices=[],
                    evidence={
                        "date": day,
                        "active_hours": round(active_min / 60, 1),
                        "max_recommended_hours": MAX_ACTIVE_HOURS,
                    },
                    expected=f"≤{MAX_ACTIVE_HOURS} active hours per day",
                    actual=f"{round(active_min / 60, 1)} active hours on {day}",
                    why_it_matters="More than 12 hours of scheduled activity leaves no buffer for meals, rest, or delays.",
                    suggested_fix=f"Trim activities on {day} to reduce active hours.",
                    fix_type="MANUAL",
                ))

    # ── RULE 7: Date violations ───────────────────────────────────────────────
    def _rule_date_violations(self, ctx: Dict, findings: List) -> None:
        itin = ctx["itinerary"]
        items = ctx["items"]
        start = _parse_date(itin.get("start_date"))
        end   = _parse_date(itin.get("end_date"))

        if not start or not end:
            return
        if end < start:
            findings.append(_finding(
                rule_id="TRIP_DATE_REVERSED",
                severity="CRITICAL",
                title="Trip End Date Before Start Date",
                affected_item_indices=[],
                related_item_indices=[],
                evidence={"start_date": str(start), "end_date": str(end)},
                expected="end_date >= start_date",
                actual=f"end_date ({end}) is before start_date ({start})",
                why_it_matters="The trip cannot exist with these dates.",
                suggested_fix="Swap start_date and end_date, or correct the dates.",
                fix_type="MANUAL",
            ))
            return

        for i, item in enumerate(items):
            d = _parse_date(item.get("date"))
            if d is None:
                continue
            if d < start or d > end:
                findings.append(_finding(
                    rule_id="ITEM_DATE_OUT_OF_RANGE",
                    severity="HIGH",
                    title="Activity Outside Trip Date Range",
                    affected_item_indices=[i],
                    related_item_indices=[],
                    evidence={
                        "item_title": item.get("title"),
                        "item_date": str(d),
                        "trip_start": str(start),
                        "trip_end": str(end),
                    },
                    expected=f"Activity date between {start} and {end}",
                    actual=f"Activity '{item.get('title')}' is on {d} which is outside the trip",
                    why_it_matters="The activity is scheduled when travellers are not at the destination.",
                    suggested_fix=f"Move '{item.get('title')}' to a date within the trip range.",
                    fix_type="MANUAL",
                ))

    # ── RULE 8: Missing critical information ──────────────────────────────────
    def _rule_missing_critical_info(self, ctx: Dict, findings: List) -> None:
        items = ctx["items"]
        REQUIRED = ["title", "date", "category"]
        HIGH_VALUE_CATS = {"transport", "flight", "accommodation", "hotel"}

        for i, item in enumerate(items):
            missing = [f for f in REQUIRED if not item.get(f)]
            if missing:
                findings.append(_finding(
                    rule_id="MISSING_REQUIRED_FIELDS",
                    severity="MEDIUM",
                    title="Missing Required Fields",
                    affected_item_indices=[i],
                    related_item_indices=[],
                    evidence={"missing_fields": missing, "item": item.get("title", f"Item #{i + 1}")},
                    expected=f"Fields {REQUIRED} must be populated",
                    actual=f"Missing: {missing}",
                    why_it_matters="Incomplete items cannot be validated and may cause planning errors.",
                    suggested_fix=f"Fill in {missing} for item #{i + 1}.",
                    fix_type="MANUAL",
                ))

            cat = item.get("category", "").lower()
            if cat in HIGH_VALUE_CATS:
                if not item.get("start_time") or not item.get("end_time"):
                    findings.append(_finding(
                        rule_id="MISSING_TIMES_HIGH_VALUE",
                        severity="HIGH",
                        title=f"Missing Times on {item.get('category', 'Critical')} Item",
                        affected_item_indices=[i],
                        related_item_indices=[],
                        evidence={"item": item.get("title"), "category": item.get("category")},
                        expected="start_time and end_time required for transport/accommodation items",
                        actual="One or both time fields are missing",
                        why_it_matters="Missing times on transport/hotel items make schedule verification impossible.",
                        suggested_fix=f"Add start_time and end_time to '{item.get('title')}'.",
                        fix_type="MANUAL",
                    ))

    # ── RULE 9: Unconfirmed important bookings ────────────────────────────────
    def _rule_unconfirmed_important_bookings(self, ctx: Dict, findings: List) -> None:
        items = ctx["items"]
        IMPORTANT_CATS = {"transport", "flight", "accommodation", "hotel", "tour"}

        for i, item in enumerate(items):
            cat = item.get("category", "").lower()
            if cat not in IMPORTANT_CATS:
                continue
            status = (item.get("booking_status") or "").lower()
            if status in ("unconfirmed", "pending", "", "none"):
                findings.append(_finding(
                    rule_id="UNCONFIRMED_BOOKING",
                    severity="HIGH",
                    title="Important Booking Not Confirmed",
                    affected_item_indices=[i],
                    related_item_indices=[],
                    evidence={
                        "item": item.get("title"),
                        "category": item.get("category"),
                        "booking_status": item.get("booking_status", "not set"),
                    },
                    expected="Booking status = CONFIRMED for transport/accommodation",
                    actual=f"Status is '{item.get('booking_status', 'not set')}'",
                    why_it_matters="Unconfirmed bookings for flights/hotels risk losing the reservation.",
                    suggested_fix=f"Confirm booking for '{item.get('title')}' before finalising the itinerary.",
                    fix_type="MANUAL",
                ))

    # ── RULE 10: Suspicious costs ─────────────────────────────────────────────
    def _rule_suspicious_costs(self, ctx: Dict, findings: List) -> None:
        items = ctx["items"]
        if len(items) < 2:
            return

        costs = [float(it.get("cost", 0) or 0) for it in items if float(it.get("cost", 0) or 0) > 0]
        if len(costs) < 2:
            return

        mean = sum(costs) / len(costs)
        variance = sum((c - mean) ** 2 for c in costs) / len(costs)
        std = math.sqrt(variance)
        THRESHOLD_SIGMA = 3.0

        for i, item in enumerate(items):
            cost = float(item.get("cost", 0) or 0)
            if std > 0 and cost > 0 and abs(cost - mean) > THRESHOLD_SIGMA * std:
                findings.append(_finding(
                    rule_id="SUSPICIOUS_COST",
                    severity="MEDIUM",
                    title="Suspicious Cost (Statistical Outlier)",
                    affected_item_indices=[i],
                    related_item_indices=[],
                    evidence={
                        "item": item.get("title"),
                        "cost": cost,
                        "mean_cost": round(mean, 2),
                        "std_dev": round(std, 2),
                        "sigma_distance": round(abs(cost - mean) / std, 1),
                    },
                    expected=f"Cost within 3σ of mean ({round(mean, 2)} ± {round(std * 3, 2)})",
                    actual=f"Cost {cost} is {round(abs(cost - mean) / std, 1)}σ from mean",
                    why_it_matters="The cost may be a data entry error, double-booking, or pricing mistake.",
                    suggested_fix=f"Verify the cost of '{item.get('title')}' — it is unusually high/low compared to other items.",
                    fix_type="MANUAL",
                ))

    # ── RULE 11: Hotel check-in consistency ───────────────────────────────────
    def _rule_hotel_checkin_consistency(self, ctx: Dict, findings: List) -> None:
        itin = ctx["itinerary"]
        items = ctx["items"]
        start = _parse_date(itin.get("start_date"))
        end   = _parse_date(itin.get("end_date"))
        if not start or not end:
            return

        hotel_items = [
            (i, it) for i, it in enumerate(items)
            if it.get("category", "").lower() in ("accommodation", "hotel")
        ]
        if not hotel_items:
            return

        hotel_dates = {_parse_date(it.get("date")) for _, it in hotel_items if it.get("date")}
        trip_nights = (end - start).days
        # Each night after arrival to night before departure needs coverage
        required_nights = {start + timedelta(days=d) for d in range(trip_nights)}
        missing = required_nights - hotel_dates
        if missing:
            findings.append(_finding(
                rule_id="HOTEL_NIGHT_GAP",
                severity="HIGH",
                title="Hotel Night Coverage Gap",
                affected_item_indices=[i for i, _ in hotel_items],
                related_item_indices=[],
                evidence={
                    "missing_nights": sorted([str(d) for d in missing]),
                    "covered_nights": sorted([str(d) for d in hotel_dates]),
                    "trip_nights": trip_nights,
                },
                expected=f"Accommodation for every night ({trip_nights} nights)",
                actual=f"Missing accommodation for {len(missing)} night(s): {sorted([str(d) for d in missing])}",
                why_it_matters="Travellers have no confirmed accommodation for these nights.",
                suggested_fix="Add accommodation entries for the missing nights.",
                fix_type="MANUAL",
            ))

    # ── RULE 12: Flight/transport timeline conflict ────────────────────────────
    def _rule_flight_timeline_conflict(self, ctx: Dict, findings: List) -> None:
        items = ctx["items"]
        transport_items = [
            (i, it) for i, it in enumerate(items)
            if it.get("category", "").lower() in ("transport", "flight")
        ]
        if not transport_items:
            return

        for i, item in transport_items:
            st, et = self._item_times(item)
            if not st or not et:
                continue
            if et <= st:
                findings.append(_finding(
                    rule_id="TRANSPORT_TIME_REVERSED",
                    severity="CRITICAL",
                    title="Transport End Time Before Start Time",
                    affected_item_indices=[i],
                    related_item_indices=[],
                    evidence={
                        "item": item.get("title"),
                        "start_time": item.get("start_time"),
                        "end_time": item.get("end_time"),
                    },
                    expected="end_time > start_time for all transport items",
                    actual=f"end_time ({item.get('end_time')}) ≤ start_time ({item.get('start_time')})",
                    why_it_matters="This transport item is logically inconsistent and may indicate a data entry error.",
                    suggested_fix=f"Correct start/end times for '{item.get('title')}'.",
                    fix_type="MANUAL",
                ))

    # ── RULE 13: Inefficient geographic routing ────────────────────────────────
    def _rule_inefficient_routing(self, ctx: Dict, findings: List) -> None:
        items = ctx["items"]
        by_day: Dict[str, List[Tuple[int, Dict, Optional[datetime]]]] = {}
        for i, item in enumerate(items):
            d = item.get("date")
            if d:
                st, _ = self._item_times(item)
                by_day.setdefault(d, []).append((i, item, st))

        for day, day_items in by_day.items():
            # Sort by start time
            timed = [(i, it, st) for i, it, st in day_items if st is not None]
            timed.sort(key=lambda x: x[2])
            if len(timed) < 3:
                continue

            # Look for a "backtrack": A → B → C where C is closer to A than B is
            for k in range(len(timed) - 2):
                i_a, it_a, _ = timed[k]
                i_b, it_b, _ = timed[k + 1]
                i_c, it_c, _ = timed[k + 2]

                loc_a = it_a.get("location", "")
                loc_b = it_b.get("location", "")
                loc_c = it_c.get("location", "")

                d_ab = _travel_minutes(loc_a, loc_b)
                d_bc = _travel_minutes(loc_b, loc_c)
                d_ac = _travel_minutes(loc_a, loc_c)

                if d_ab and d_bc and d_ac:
                    # A backtrack: going A→B→C is longer than A→C→B
                    total_abc = d_ab + d_bc
                    total_acb = d_ac + (_travel_minutes(loc_c, loc_b) or d_bc)
                    wasted = total_abc - total_acb
                    if wasted >= 20:  # only flag significant waste
                        findings.append(_finding(
                            rule_id="INEFFICIENT_ROUTING",
                            severity="OPTIMIZATION",
                            title="Inefficient Geographic Routing",
                            affected_item_indices=[i_a, i_b, i_c],
                            related_item_indices=[],
                            evidence={
                                "date": day,
                                "route": f"{it_a.get('title')} → {it_b.get('title')} → {it_c.get('title')}",
                                "total_travel_current_min": total_abc,
                                "total_travel_optimised_min": total_acb,
                                "wasted_min": wasted,
                            },
                            expected=f"Optimised route saves ~{wasted} min",
                            actual=f"Current order wastes ~{wasted} min of travel vs optimal",
                            why_it_matters="Reordering saves travel time that could be spent at attractions.",
                            suggested_fix=(
                                f"Swap order of '{it_b.get('title')}' and '{it_c.get('title')}' "
                                f"on {day} to reduce travel by ~{wasted} min."
                            ),
                            fix_type="MANUAL",
                        ))
                        break  # one per day is enough

    # ── Summary ───────────────────────────────────────────────────────────────
    @staticmethod
    def _summarise(items: List[Dict], findings: List[Dict]) -> Dict[str, int]:
        sev_counts: Dict[str, int] = {s: 0 for s in SEVERITIES}
        for f in findings:
            sev_counts[f["severity"]] = sev_counts.get(f["severity"], 0) + 1
        total_checks = 13 * max(len(items), 1)
        passed = max(0, total_checks - len(findings))
        return {
            "passed": passed,
            "critical": sev_counts["CRITICAL"],
            "high": sev_counts["HIGH"],
            "medium": sev_counts["MEDIUM"],
            "low": sev_counts["LOW"],
            "optimization": sev_counts["OPTIMIZATION"],
            "total_findings": len(findings),
        }


# Singleton
validator = ItineraryValidator()
