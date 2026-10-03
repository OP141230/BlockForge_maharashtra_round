from typing import Any, Dict, Optional


class FaultInjector:
    """
    Injects controlled faults into agent execution.
    """

    def __init__(self, fault_config: Optional[Dict[str, Any]] = None) -> None:
        self.config = fault_config

    def _fault_type(self) -> Optional[str]:
        if not self.config:
            return None
        return self.config.get("fault_type")

    def before_step(self, step_name: str, state: Dict[str, Any]) -> None:
        fault_type = self._fault_type()
        if not fault_type:
            return

        if fault_type == "wrong_date" and step_name == "search_flights":
            constraints = state.setdefault("constraints", {})
            constraints["date"] = "2026-10-03"

        elif fault_type == "wrong_destination" and step_name == "search_flights":
            constraints = state.setdefault("constraints", {})
            constraints["destination"] = "Goa"

        elif fault_type == "wrong_origin" and step_name == "search_flights":
            constraints = state.setdefault("constraints", {})
            constraints["origin"] = "Goa"

        elif fault_type == "hotel_wrong_city" and step_name == "search_hotels":
            constraints = state.setdefault("constraints", {})
            constraints["destination"] = "Mumbai"

        elif fault_type == "hotel_wrong_date" and step_name == "search_hotels":
            constraints = state.setdefault("constraints", {})
            constraints["date"] = "2026-10-03"

        elif fault_type == "ignored_empty_result" and step_name == "search_flights":
            state["_force_empty_flights"] = True

        elif fault_type == "state_overwrite" and step_name == "create_booking":
            state["selected_flight"] = None
            
        elif fault_type == "budget_filter_disabled" and step_name == "filter_flights_by_budget":
            # Flag the state so the next step picks the worst flight
            state["_force_expensive_selection"] = True

    def after_step(
        self,
        step_name: str,
        state: Dict[str, Any],
        output: Dict[str, Any],
    ) -> Dict[str, Any]:
        fault_type = self._fault_type()
        if not fault_type:
            return output

        output = dict(output)

        if (
            fault_type == "budget_violation"
            and step_name == "select_cheapest_flight"
        ):
            flights = state.get("flights", [])
            if flights:
                expensive_flight = max(
                    flights,
                    key=lambda flight: flight.get("price", 0),
                )
                state["selected_flight"] = expensive_flight
                output["selected_flight"] = expensive_flight

        elif (
            fault_type == "budget_filter_disabled"
            and step_name == "select_cheapest_flight"
        ):
            if state.get("_force_expensive_selection"):
                flights = state.get("flights", [])
                if flights:
                    expensive_flight = max(flights, key=lambda f: f.get("price", 0))
                    state["selected_flight"] = expensive_flight
                    output["selected_flight"] = expensive_flight

        elif (
            fault_type == "ignored_empty_result"
            and step_name == "select_cheapest_flight"
        ):
            constraints = state.get("constraints", {})
            budget = constraints.get("flight_price_max", 0)
            if budget is None:
                budget = 0

            hallucinated_flight = {
                "flight_id": "HAL-001",
                "origin": constraints.get("origin"),
                "destination": constraints.get("destination"),
                "date": constraints.get("date"),
                "price": budget + 100,
                "arrival_time": "19:00",
            }

            state["selected_flight"] = hallucinated_flight
            output["selected_flight"] = hallucinated_flight

        elif (
            fault_type == "hotel_checkin_violation"
            and step_name == "select_hotel"
        ):
            constraints = state.get("constraints", {})
            required_checkin_after = constraints.get("hotel_checkin_after", "00:00")
            hotels = state.get("hotels", [])

            invalid_hotel = next(
                (
                    hotel
                    for hotel in hotels
                    if hotel.get("checkin_time", "00:00") < required_checkin_after
                ),
                None,
            )

            if invalid_hotel:
                state["selected_hotel"] = invalid_hotel
                output["selected_hotel"] = invalid_hotel

        return output