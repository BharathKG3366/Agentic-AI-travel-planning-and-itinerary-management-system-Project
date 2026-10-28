"""Supervisor-controlled workflow, using LangGraph when installed.

This graph makes the project's orchestration explicit: goal decomposition ->
place research -> weather research -> transport research -> planning -> constraint
validation -> human approval gate. A sequential fallback keeps unit tests/simple
local use resilient if LangGraph cannot be imported.
"""
from __future__ import annotations

from datetime import timedelta
from typing import Any, TypedDict

from agents.memory import log_events, save_profile, save_trip
from agents.planner import TripRequest, build_itinerary, decompose_goal, validate_itinerary
from providers.flights import search_flights
from providers.places import search_places
from providers.railways import search_trains
from providers.weather import get_weather


class TravelState(TypedDict, total=False):
    request_json: dict[str, Any]
    selected_transport: dict[str, Any] | None
    tasks: list[dict[str, str]]
    place_result: dict[str, Any]
    weather_result: dict[str, Any]
    transport_result: dict[str, Any] | None
    transport_options: list[dict[str, Any]]
    itinerary: dict[str, Any]
    trace: list[dict[str, str]]
    errors: list[str]


def _request(state: TravelState) -> TripRequest:
    return TripRequest.model_validate(state["request_json"])


def _trace(state: TravelState, agent: str, status: str, detail: str) -> list[dict[str, str]]:
    return list(state.get("trace", [])) + [{"agent": agent, "status": status, "detail": detail}]


def _flight_as_transport(offer: dict[str, Any]) -> dict[str, Any]:
    return {**offer, "mode": "Flight", "price": offer.get("price"), "currency": offer.get("currency", "INR"),
            "fare_note": offer.get("fare_note", "Confirm fare at provider checkout.")}


def _train_as_transport(train: dict[str, Any]) -> dict[str, Any]:
    return {**train, "mode": "Train", "price": train.get("indicative_fare"), "currency": "INR",
            "fare_note": train.get("fare_basis", "Verify fare and availability on IRCTC.")}


def _goal_node(state: TravelState) -> dict[str, Any]:
    request = _request(state)
    tasks = decompose_goal(request)
    return {"tasks": tasks, "trace": _trace(state, "Goal Decomposition Agent", "completed", f"Decomposed the request into {len(tasks)} sub-tasks.")}


def _places_node(state: TravelState) -> dict[str, Any]:
    request = _request(state)
    try:
        result = search_places(request.destination)
    except Exception as exc:
        result = {"ok": False, "places": [], "source": "OpenStreetMap", "message": f"Place connector error: {exc}"}
    status = "completed" if result.get("ok") else "needs review"
    detail = f"Mapped places: {len(result.get('places', []))}. {result.get('message', '')}"
    return {"place_result": result, "trace": _trace(state, "Travel Research Agent", status, detail)}


def _weather_node(state: TravelState) -> dict[str, Any]:
    request = _request(state)
    try:
        result = get_weather(request.destination, request.departure_date, request.departure_date + timedelta(days=request.days - 1))
    except Exception as exc:
        result = {"ok": False, "forecast": [], "source": "Open-Meteo", "message": f"Weather connector error: {exc}"}
    status = "completed" if result.get("ok") else "unavailable"
    return {"weather_result": result, "trace": _trace(state, "Weather Research Agent", status, f"Forecast days: {len(result.get('forecast', []))}. {result.get('message', '')}")}


def _transport_node(state: TravelState) -> dict[str, Any]:
    request = _request(state)
    mode = request.transport_mode.casefold()
    options: list[dict[str, Any]] = []
    result: dict[str, Any] | None = None
    try:
        if mode in {"flight", "flights"}:
            result = search_flights(request.origin_code, request.destination_code, request.departure_date, request.travelers)
            options = [_flight_as_transport(x) for x in result.get("offers", [])]
        elif mode in {"train", "trains"}:
            result = search_trains(request.origin_code, request.destination_code, request.departure_date, request.travelers)
            options = [_train_as_transport(x) for x in result.get("trains", [])]
        elif mode in {"use selected", "selected", "selected transport"} and state.get("selected_transport"):
            options = [state["selected_transport"]]
            result = {"ok": True, "message": "Using the option selected during transport search."}
    except Exception as exc:
        result = {"ok": False, "message": f"Transport tool error: {exc}"}
    if result is not None:
        status = "completed" if result.get("ok") else "needs review"
        trace = _trace(state, "Transport Research Agent", status, f"{mode.title()} search returned {len(options)} option(s). {result.get('message', '')}")
    else:
        trace = _trace(state, "Transport Research Agent", "skipped", "No transport search requested; no fare has been assumed.")
    return {"transport_result": result, "transport_options": options, "trace": trace}


def _planning_node(state: TravelState) -> dict[str, Any]:
    request = _request(state)
    options = state.get("transport_options", [])
    selected = state.get("selected_transport")
    mode = request.transport_mode.casefold()
    if not selected and mode in {"flight", "flights", "train", "trains"} and options:
        # Providers normalize results in ascending price when fares exist. This is a
        # proposed default, and the UI offers a selector before final approval.
        selected = options[0]
    elif not selected and options:
        selected = options[0]
    itinerary = build_itinerary(request, state.get("place_result"), state.get("weather_result"), selected)
    itinerary["workflow_tasks"] = state.get("tasks", [])
    itinerary["transport_search"] = state.get("transport_result")
    itinerary["transport_options"] = options
    itinerary["places_data"] = state.get("place_result", {}).get("places", [])
    itinerary["weather_data"] = state.get("weather_result", {}).get("forecast", [])
    trace = _trace(state, "Itinerary Planning Agent", "completed", f"Constructed a {request.days}-day draft using {itinerary.get('generated_by', 'planner')}.")
    return {"itinerary": itinerary, "trace": trace}


def _validation_node(state: TravelState) -> dict[str, Any]:
    request = _request(state)
    itinerary = dict(state["itinerary"])
    places = state.get("place_result", {}).get("places", [])
    itinerary["validation_issues"] = validate_itinerary(itinerary, request, places)
    issues = itinerary["validation_issues"]
    trace = _trace(state, "Constraint Validation Agent", "completed" if not issues else "needs review", f"Validation finished with {len(issues)} issue(s).")
    itinerary["agent_trace"] = trace
    return {"itinerary": itinerary, "trace": trace}


def _approval_node(state: TravelState) -> dict[str, Any]:
    itinerary = dict(state["itinerary"])
    itinerary["requires_human_approval"] = True
    itinerary["approval_status"] = "Pending approval"
    trace = _trace(state, "Human Approval Gate", "waiting", "The draft must be reviewed by a person. No ticket, hotel or payment action is enabled.")
    itinerary["agent_trace"] = trace
    # Save local long-term preference and trip record, but never silently approve.
    request = _request(state)
    try:
        save_profile({"last_origin_city": request.origin_city, "last_destination": request.destination,
                      "interests": request.interests, "travelers": request.travelers,
                      "food_budget_per_person_per_day": request.food_budget_per_person_per_day,
                      "accommodation_per_room_per_night": request.accommodation_per_room_per_night,
                      "local_transport_per_person_per_day": request.local_transport_per_person_per_day})
        trip_id = save_trip(request.model_dump(mode="json"), itinerary)
        itinerary["trip_id"] = trip_id
        log_events(trace, trip_id)
    except Exception as exc:
        itinerary.setdefault("system_notes", []).append(f"Local memory persistence error: {exc}")
    return {"itinerary": itinerary, "trace": trace}


def run_workflow(request: TripRequest, selected_transport: dict[str, Any] | None = None) -> dict[str, Any]:
    """Run the explicit multi-step graph and return its final typed state."""
    initial: TravelState = {"request_json": request.model_dump(mode="json"), "selected_transport": selected_transport,
                            "tasks": [], "transport_options": [], "trace": [], "errors": []}
    initial["trace"] = [{"agent": "Supervisor Agent", "status": "started", "detail": "Accepted the travel goal and delegated the workflow to specialized agents."}]
    nodes = [_goal_node, _places_node, _weather_node, _transport_node, _planning_node, _validation_node, _approval_node]
    try:
        from langgraph.graph import END, START, StateGraph
        builder = StateGraph(TravelState)
        names = ["goal_decomposition", "place_research", "weather_research", "transport_research", "itinerary_planning", "constraint_validation", "human_approval_gate"]
        for name, node in zip(names, nodes):
            builder.add_node(name, node)
        builder.add_edge(START, names[0])
        for left, right in zip(names, names[1:]):
            builder.add_edge(left, right)
        builder.add_edge(names[-1], END)
        graph = builder.compile()
        final_state = graph.invoke(initial)
    except ImportError:
        # Fallback makes local/offline unit tests more forgiving; requirements.txt
        # includes LangGraph so a normal install runs the compiled state graph.
        final_state: TravelState = dict(initial)
        for node in nodes:
            final_state.update(node(final_state))
    itinerary = final_state["itinerary"]
    return {"request": request, "itinerary": itinerary,
            "place_result": final_state.get("place_result", {"ok": False, "places": []}),
            "weather_result": final_state.get("weather_result", {"ok": False, "forecast": []}),
            "transport_result": final_state.get("transport_result"),
            "transport_options": final_state.get("transport_options", []), "trace": final_state.get("trace", [])}
