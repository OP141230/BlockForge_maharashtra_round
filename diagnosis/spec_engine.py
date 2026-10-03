from typing import Any, Dict, List, Optional


def _safe_dict(value: Any) -> Dict[str, Any]:
    """
    Returns value if it is a dict, otherwise returns an empty dict.
    """
    if isinstance(value, dict):
        return value
    return {}


def _contains_by_id(items: Any, selected: Any, id_field: str) -> bool:
    """
    Checks whether selected item is present in items.

    If selected has an id field, compare by id.
    Otherwise compare by full equality.
    """
    if selected is None:
        return False

    if not isinstance(items, list):
        return False

    if isinstance(selected, dict):
        selected_id = selected.get(id_field)

        if selected_id is not None:
            for item in items:
                if isinstance(item, dict) and item.get(id_field) == selected_id:
                    return True
            return False

    for item in items:
        if item == selected:
            return True

    return False


def _add_violation(
    violations: List[Dict[str, Any]],
    step_id: Any,
    step_name: str,
    invariant: str,
    expected: Any,
    observed: Any,
    details: Optional[str] = None,
) -> None:
    """
    Adds a structured violation record.
    """
    violation = {
        "step_id": step_id,
        "step_name": step_name,
        "invariant": invariant,
        "expected": expected,
        "observed": observed,
    }

    if details is not None:
        violation["details"] = details

    violations.append(violation)


def check_step_invariants(trace: Dict[str, Any]) -> List[Dict[str, Any]]:
    """
    Checks step-level rules using the original task constraints.

    This does not use ground truth labels.
    """
    violations: List[Dict[str, Any]] = []

    task = _safe_dict(trace.get("task"))

    expected_origin = task.get("origin")
    expected_destination = task.get("destination")
    expected_date = task.get("date")

    expected_budget = task.get("budget", 0)
    if expected_budget is None:
        expected_budget = 0

    expected_hotel_checkin_after = task.get("hotel_checkin_after", "00:00")
    if expected_hotel_checkin_after is None:
        expected_hotel_checkin_after = "00:00"

    steps = trace.get("steps", [])
    if not isinstance(steps, list):
        steps = []

    for step in steps:
        step = _safe_dict(step)

        step_id = step.get("step_id")
        step_name = step.get("name")

        step_input = _safe_dict(step.get("input"))
        step_output = _safe_dict(step.get("output"))
        state_before = _safe_dict(step.get("state_before"))

        # --------------------------------------------------
        # search_flights invariants
        # --------------------------------------------------
        if step_name == "search_flights":
            if step_input.get("origin") != expected_origin:
                _add_violation(
                    violations=violations,
                    step_id=step_id,
                    step_name=step_name,
                    invariant="search_flights.origin_matches_task",
                    expected=expected_origin,
                    observed=step_input.get("origin"),
                    details="Flight search origin does not match the user's requested origin.",
                )

            if step_input.get("destination") != expected_destination:
                _add_violation(
                    violations=violations,
                    step_id=step_id,
                    step_name=step_name,
                    invariant="search_flights.destination_matches_task",
                    expected=expected_destination,
                    observed=step_input.get("destination"),
                    details="Flight search destination does not match the user's requested destination.",
                )

            if step_input.get("date") != expected_date:
                _add_violation(
                    violations=violations,
                    step_id=step_id,
                    step_name=step_name,
                    invariant="search_flights.date_matches_task",
                    expected=expected_date,
                    observed=step_input.get("date"),
                    details="Flight search date does not match the user's requested date.",
                )

        # --------------------------------------------------
        # filter_flights_by_budget invariants
        # --------------------------------------------------
        elif step_name == "filter_flights_by_budget":
            filtered_flights = step_output.get("filtered_flights")

            if isinstance(filtered_flights, list):
                for flight in filtered_flights:
                    flight = _safe_dict(flight)
                    price = flight.get("price", 0)

                    if price > expected_budget:
                        _add_violation(
                            violations=violations,
                            step_id=step_id,
                            step_name=step_name,
                            invariant="filter_flights_by_budget.all_flights_within_budget",
                            expected=f"<= {expected_budget}",
                            observed=price,
                            details="Filtered flight list contains a flight above the user's budget.",
                        )

        # --------------------------------------------------
        # select_cheapest_flight invariants
        # --------------------------------------------------
        elif step_name == "select_cheapest_flight":
            filtered_flights = step_input.get("filtered_flights")
            selected_flight = step_output.get("selected_flight")

            if isinstance(selected_flight, dict):
                if not _contains_by_id(
                    items=filtered_flights,
                    selected=selected_flight,
                    id_field="flight_id",
                ):
                    _add_violation(
                        violations=violations,
                        step_id=step_id,
                        step_name=step_name,
                        invariant="select_cheapest_flight.selected_flight_in_filtered_list",
                        expected="selected_flight must be present in filtered_flights",
                        observed="selected_flight not found in filtered_flights",
                        details="The selected flight was not present in the filtered flight list.",
                    )

                selected_price = selected_flight.get("price", 0)

                if selected_price > expected_budget:
                    _add_violation(
                        violations=violations,
                        step_id=step_id,
                        step_name=step_name,
                        invariant="select_cheapest_flight.selected_flight_within_budget",
                        expected=f"<= {expected_budget}",
                        observed=selected_price,
                        details="The selected flight price exceeds the user's budget.",
                    )

                if selected_flight.get("origin") != expected_origin:
                    _add_violation(
                        violations=violations,
                        step_id=step_id,
                        step_name=step_name,
                        invariant="select_cheapest_flight.selected_flight_origin_matches_task",
                        expected=expected_origin,
                        observed=selected_flight.get("origin"),
                        details="The selected flight origin does not match the user's requested origin.",
                    )

                if selected_flight.get("destination") != expected_destination:
                    _add_violation(
                        violations=violations,
                        step_id=step_id,
                        step_name=step_name,
                        invariant="select_cheapest_flight.selected_flight_destination_matches_task",
                        expected=expected_destination,
                        observed=selected_flight.get("destination"),
                        details="The selected flight destination does not match the user's requested destination.",
                    )

                if selected_flight.get("date") != expected_date:
                    _add_violation(
                        violations=violations,
                        step_id=step_id,
                        step_name=step_name,
                        invariant="select_cheapest_flight.selected_flight_date_matches_task",
                        expected=expected_date,
                        observed=selected_flight.get("date"),
                        details="The selected flight date does not match the user's requested date.",
                    )

        # --------------------------------------------------
        # search_hotels invariants
        # --------------------------------------------------
        elif step_name == "search_hotels":
            if step_input.get("city") != expected_destination:
                _add_violation(
                    violations=violations,
                    step_id=step_id,
                    step_name=step_name,
                    invariant="search_hotels.city_matches_task",
                    expected=expected_destination,
                    observed=step_input.get("city"),
                    details="Hotel search city does not match the user's requested destination.",
                )

            if step_input.get("checkin_date") != expected_date:
                _add_violation(
                    violations=violations,
                    step_id=step_id,
                    step_name=step_name,
                    invariant="search_hotels.checkin_date_matches_task",
                    expected=expected_date,
                    observed=step_input.get("checkin_date"),
                    details="Hotel search check-in date does not match the user's requested date.",
                )

        # --------------------------------------------------
        # filter_hotels_by_checkin invariants
        # --------------------------------------------------
        elif step_name == "filter_hotels_by_checkin":
            filtered_hotels = step_output.get("filtered_hotels")

            if isinstance(filtered_hotels, list):
                for hotel in filtered_hotels:
                    hotel = _safe_dict(hotel)

                    checkin_time = hotel.get("checkin_time", "00:00")
                    if checkin_time is None:
                        checkin_time = "00:00"

                    if checkin_time < expected_hotel_checkin_after:
                        _add_violation(
                            violations=violations,
                            step_id=step_id,
                            step_name=step_name,
                            invariant="filter_hotels_by_checkin.all_hotels_satisfy_checkin",
                            expected=f">= {expected_hotel_checkin_after}",
                            observed=checkin_time,
                            details="Filtered hotel list contains a hotel with invalid check-in time.",
                        )

                    checkin_date = hotel.get("checkin_date")

                    if checkin_date != expected_date:
                        _add_violation(
                            violations=violations,
                            step_id=step_id,
                            step_name=step_name,
                            invariant="filter_hotels_by_checkin.all_hotels_have_correct_date",
                            expected=expected_date,
                            observed=checkin_date,
                            details="Filtered hotel list contains a hotel with incorrect check-in date.",
                        )

        # --------------------------------------------------
        # select_hotel invariants
        # --------------------------------------------------
        elif step_name == "select_hotel":
            filtered_hotels = step_input.get("filtered_hotels")
            selected_hotel = step_output.get("selected_hotel")

            if isinstance(selected_hotel, dict):
                if not _contains_by_id(
                    items=filtered_hotels,
                    selected=selected_hotel,
                    id_field="hotel_id",
                ):
                    _add_violation(
                        violations=violations,
                        step_id=step_id,
                        step_name=step_name,
                        invariant="select_hotel.selected_hotel_in_filtered_list",
                        expected="selected_hotel must be present in filtered_hotels",
                        observed="selected_hotel not found in filtered_hotels",
                        details="The selected hotel was not present in the filtered hotel list.",
                    )

                if selected_hotel.get("city") != expected_destination:
                    _add_violation(
                        violations=violations,
                        step_id=step_id,
                        step_name=step_name,
                        invariant="select_hotel.selected_hotel_city_matches_task",
                        expected=expected_destination,
                        observed=selected_hotel.get("city"),
                        details="The selected hotel city does not match the user's requested destination.",
                    )

                if selected_hotel.get("checkin_date") != expected_date:
                    _add_violation(
                        violations=violations,
                        step_id=step_id,
                        step_name=step_name,
                        invariant="select_hotel.selected_hotel_date_matches_task",
                        expected=expected_date,
                        observed=selected_hotel.get("checkin_date"),
                        details="The selected hotel check-in date does not match the user's requested date.",
                    )

                selected_checkin_time = selected_hotel.get("checkin_time", "00:00")
                if selected_checkin_time is None:
                    selected_checkin_time = "00:00"

                if selected_checkin_time < expected_hotel_checkin_after:
                    _add_violation(
                        violations=violations,
                        step_id=step_id,
                        step_name=step_name,
                        invariant="select_hotel.selected_hotel_checkin_time_valid",
                        expected=f">= {expected_hotel_checkin_after}",
                        observed=selected_checkin_time,
                        details="The selected hotel check-in time violates the user's constraint.",
                    )

        # --------------------------------------------------
        # create_booking invariants
        # --------------------------------------------------
        elif step_name == "create_booking":
            input_selected_flight = step_input.get("selected_flight")
            input_selected_hotel = step_input.get("selected_hotel")

            previous_selected_flight = state_before.get("selected_flight")
            previous_selected_hotel = state_before.get("selected_hotel")

            if previous_selected_flight and not input_selected_flight:
                _add_violation(
                    violations=violations,
                    step_id=step_id,
                    step_name=step_name,
                    invariant="create_booking.selected_flight_not_lost",
                    expected="selected_flight should remain available",
                    observed=None,
                    details="A previously selected flight was missing when booking was created.",
                )

            if previous_selected_hotel and not input_selected_hotel:
                _add_violation(
                    violations=violations,
                    step_id=step_id,
                    step_name=step_name,
                    invariant="create_booking.selected_hotel_not_lost",
                    expected="selected_hotel should remain available",
                    observed=None,
                    details="A previously selected hotel was missing when booking was created.",
                )

            booking = step_output.get("booking")

            if input_selected_flight and input_selected_hotel and not booking:
                _add_violation(
                    violations=violations,
                    step_id=step_id,
                    step_name=step_name,
                    invariant="create_booking.booking_created_despite_valid_inputs",
                    expected="booking should be created",
                    observed=None,
                    details="Booking was not created even though flight and hotel inputs were available.",
                )

            if isinstance(booking, dict):
                booking_flight = _safe_dict(booking.get("flight"))
                booking_hotel = _safe_dict(booking.get("hotel"))

                input_flight_dict = _safe_dict(input_selected_flight)
                input_hotel_dict = _safe_dict(input_selected_hotel)

                input_flight_id = input_flight_dict.get("flight_id")
                booking_flight_id = booking_flight.get("flight_id")

                if input_flight_id is not None and booking_flight_id != input_flight_id:
                    _add_violation(
                        violations=violations,
                        step_id=step_id,
                        step_name=step_name,
                        invariant="create_booking.booking_flight_matches_input",
                        expected=input_flight_id,
                        observed=booking_flight_id,
                        details="The booked flight does not match the selected flight input.",
                    )

                input_hotel_id = input_hotel_dict.get("hotel_id")
                booking_hotel_id = booking_hotel.get("hotel_id")

                if input_hotel_id is not None and booking_hotel_id != input_hotel_id:
                    _add_violation(
                        violations=violations,
                        step_id=step_id,
                        step_name=step_name,
                        invariant="create_booking.booking_hotel_matches_input",
                        expected=input_hotel_id,
                        observed=booking_hotel_id,
                        details="The booked hotel does not match the selected hotel input.",
                    )

    return violations


def check_final_state(trace: Dict[str, Any]) -> List[Dict[str, Any]]:
    """
    Converts final validation violations into structured evidence.
    """
    final_state = _safe_dict(trace.get("final_state"))
    final_validation = _safe_dict(final_state.get("final_validation"))
    task = _safe_dict(trace.get("task"))

    raw_violations = final_validation.get("violations")
    if not isinstance(raw_violations, list):
        raw_violations = []

    booking = final_state.get("booking")
    booking_dict = _safe_dict(booking)

    flight = _safe_dict(booking_dict.get("flight")) if booking_dict else {}
    hotel = _safe_dict(booking_dict.get("hotel")) if booking_dict else {}

    final_violations: List[Dict[str, Any]] = []

    for violation in raw_violations:
        expected: Any = "unknown"
        observed: Any = "unknown"

        if violation == "booking_missing":
            expected = "booking exists"
            observed = booking

        elif violation == "flight_origin_mismatch":
            expected = task.get("origin")
            observed = flight.get("origin") if flight else None

        elif violation == "flight_destination_mismatch":
            expected = task.get("destination")
            observed = flight.get("destination") if flight else None

        elif violation == "flight_date_mismatch":
            expected = task.get("date")
            observed = flight.get("date") if flight else None

        elif violation == "flight_budget_violation":
            expected = f"<= {task.get('budget')}"
            observed = flight.get("price") if flight else None

        elif violation == "hotel_city_mismatch":
            expected = task.get("destination")
            observed = hotel.get("city") if hotel else None

        elif violation == "hotel_date_mismatch":
            expected = task.get("date")
            observed = hotel.get("checkin_date") if hotel else None

        elif violation == "hotel_checkin_time_violation":
            expected = f">= {task.get('hotel_checkin_after')}"
            observed = hotel.get("checkin_time") if hotel else None

        else:
            expected = "no violation"
            observed = violation

        final_violations.append(
            {
                "violation": violation,
                "expected": expected,
                "observed": observed,
            }
        )

    return final_violations


def evaluate_trace(trace: Dict[str, Any]) -> Dict[str, Any]:
    """
    Produces a full failure-detection report for one trace.
    """
    trace = _safe_dict(trace)

    task = _safe_dict(trace.get("task"))
    final_state = _safe_dict(trace.get("final_state"))
    final_validation = _safe_dict(final_state.get("final_validation"))

    step_violations = check_step_invariants(trace)
    final_violations = check_final_state(trace)

    status = trace.get("status", "unknown")
    final_success = bool(final_validation.get("success", False))

    total_step_violations = len(step_violations)
    total_final_violations = len(final_violations)
    total_violations = total_step_violations + total_final_violations

    step_ids = [
        violation.get("step_id")
        for violation in step_violations
        if violation.get("step_id") is not None
    ]

    earliest_step_signal = min(step_ids) if step_ids else None

    detected_failure = (status != "success") or (total_violations > 0)
    expected_failure = status != "success"
    detection_matches_status = detected_failure == expected_failure

    report = {
        "trace_id": trace.get("trace_id"),
        "status": status,
        "ground_truth": trace.get("ground_truth"),
        "task": {
            "origin": task.get("origin"),
            "destination": task.get("destination"),
            "date": task.get("date"),
            "budget": task.get("budget"),
            "hotel_checkin_after": task.get("hotel_checkin_after"),
        },
        "final_success": final_success,
        "step_violations": step_violations,
        "final_violations": final_violations,
        "total_step_violations": total_step_violations,
        "total_final_violations": total_final_violations,
        "total_violations": total_violations,
        "earliest_step_signal": earliest_step_signal,
        "detected_failure": detected_failure,
        "detection_matches_status": detection_matches_status,
    }

    return report