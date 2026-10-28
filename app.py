from __future__ import annotations

import json
import os
from datetime import date, timedelta
from html import escape
from typing import Any

import streamlit as st
from dotenv import load_dotenv

from agents.memory import clear_memory, list_events, list_trips, load_profile, save_trip
from agents.planner import TripRequest, apply_transport_option, replan_from_feedback
from agents.workflow import run_workflow
from providers.flights import configured as flight_configured, search_flights
from providers.places import search_places
from providers.railways import configured as train_configured, search_stations, search_trains
from providers.weather import get_weather

load_dotenv()
st.set_page_config(page_title="VoyageWise AI · Travel intelligence", page_icon="✦", layout="wide", initial_sidebar_state="expanded")

CSS = r"""
<style>
:root { --vw-violet:#7768F8; --vw-violet-soft:rgba(119,104,248,.14); --vw-mint:#48D9C7; --vw-gold:#FFC978; }
.block-container { max-width: 1460px; padding-top: 1.15rem; padding-bottom: 3rem; }
[data-testid="stAppViewContainer"] { background-image: radial-gradient(ellipse at 0% 0%, rgba(119,104,248,.12), transparent 33%), radial-gradient(ellipse at 100% 4%, rgba(72,217,199,.08), transparent 27%); }
[data-testid="stSidebar"] { border-right: 1px solid var(--st-border-color); background-image: linear-gradient(180deg, rgba(119,104,248,.06), transparent 42%); }
[data-testid="stSidebar"] [data-testid="stRadio"] label { font-weight: 650; }
.vw-brand { display:flex; align-items:center; gap:.72rem; padding:.35rem .2rem 1rem; }
.vw-brand-mark { display:flex; align-items:center; justify-content:center; width:42px; height:42px; border-radius:15px; color:white; font-size:1.3rem; background:linear-gradient(135deg,#7768F8,#48D9C7); box-shadow:0 10px 28px rgba(119,104,248,.24), inset 0 1px 0 rgba(255,255,255,.45); }
.vw-brand-name { font-weight:850; letter-spacing:-.04em; font-size:1.15rem; line-height:1.1; }
.vw-brand-sub { font-size:.72rem; opacity:.68; margin-top:.18rem; }
.vw-hero { position:relative; isolation:isolate; overflow:hidden; padding:2rem 2.2rem; border-radius:28px; border:1px solid var(--st-border-color); background:linear-gradient(118deg,rgba(119,104,248,.18),rgba(72,217,199,.10) 55%,rgba(255,201,120,.12)); box-shadow:0 18px 55px rgba(25,30,68,.08),inset 0 1px 0 rgba(255,255,255,.24); }
.vw-hero:after { content:""; position:absolute; z-index:-1; width:280px; height:280px; right:-55px; top:-105px; border-radius:50%; background:radial-gradient(circle,rgba(255,255,255,.38),rgba(119,104,248,.16),transparent 70%); pointer-events:none; }
.vw-kicker { text-transform:uppercase; letter-spacing:.16em; font-size:.7rem; font-weight:850; color:var(--st-primary-color); }
.vw-hero h1 { margin:.45rem 0 .65rem; font-size:clamp(2.15rem,4vw,3.55rem); line-height:1.02; letter-spacing:-.065em; font-weight:880; }
.vw-hero p { max-width:800px; line-height:1.65; font-size:1.02rem; opacity:.82; margin-bottom:.3rem; }
.vw-pills { margin-top:1rem; display:flex; flex-wrap:wrap; gap:.42rem; }
.vw-pill { display:inline-block; border-radius:99px; border:1px solid var(--st-border-color); padding:.33rem .7rem; font-size:.73rem; font-weight:740; background:rgba(127,127,127,.06); backdrop-filter:blur(10px); }
.vw-section { margin-top:1.65rem; margin-bottom:.55rem; }
.vw-section h2 { font-size:1.43rem; font-weight:820; letter-spacing:-.04em; margin-bottom:.1rem; }
.vw-muted { font-size:.87rem; opacity:.67; line-height:1.5; }
.vw-card { height:100%; border:1px solid var(--st-border-color); border-radius:21px; padding:1.12rem 1.18rem; background:linear-gradient(145deg,rgba(255,255,255,.075),rgba(127,127,127,.025)); box-shadow:0 12px 34px rgba(20,25,60,.045),inset 0 1px 0 rgba(255,255,255,.14); }
.vw-card h3 { font-size:1.02rem; letter-spacing:-.025em; margin:.48rem 0 .28rem; }
.vw-card p { font-size:.84rem; line-height:1.5; opacity:.76; margin-bottom:.2rem; }
.vw-icon { display:inline-flex; align-items:center; justify-content:center; width:42px; height:42px; border-radius:15px; font-size:1.25rem; background:linear-gradient(135deg,rgba(119,104,248,.21),rgba(72,217,199,.18)); box-shadow:inset 0 1px 0 rgba(255,255,255,.20); }
.vw-status { display:inline-block; border-radius:9px; padding:.28rem .52rem; font-size:.7rem; font-weight:800; background:rgba(127,127,127,.09); border:1px solid var(--st-border-color); margin-top:.45rem; }
.vw-dot { display:inline-block; width:7px; height:7px; border-radius:50%; background:#2CCB9C; margin-right:.35rem; }
[data-testid="stMetric"] { border:1px solid var(--st-border-color); border-radius:18px; padding:.92rem 1rem .78rem; background:linear-gradient(145deg,rgba(127,127,127,.07),rgba(127,127,127,.02)); box-shadow:inset 0 1px 0 rgba(255,255,255,.10); }
[data-testid="stMetricLabel"] { font-weight:700; }
.stButton>button,.stDownloadButton>button,.stLinkButton>a { border-radius:13px; font-weight:740; transition:transform .18s ease,box-shadow .18s ease; }
.stButton>button:hover,.stDownloadButton>button:hover,.stLinkButton>a:hover { transform:translateY(-1px); box-shadow:0 9px 25px rgba(119,104,248,.18); }
[data-testid="stForm"] { border:1px solid var(--st-border-color); border-radius:20px; padding:1.1rem 1.15rem; background:rgba(127,127,127,.025); }
[data-testid="stExpander"] { border-radius:15px; border-color:var(--st-border-color); }
[data-testid="stTabs"] [data-baseweb="tab-list"] { gap:.4rem; }
[data-testid="stTabs"] [data-baseweb="tab"] { border-radius:12px; padding:.6rem .95rem; }
.vw-timeline { border-left:2px solid rgba(119,104,248,.5); padding-left:1rem; margin:.5rem 0 .2rem .45rem; }
.vw-time { font-size:.74rem; font-weight:850; color:var(--st-primary-color); letter-spacing:.04em; }
.vw-small { font-size:.78rem; opacity:.72; }
hr { border-color:var(--st-border-color); opacity:.75; }
@media(max-width:750px) { .vw-hero{padding:1.35rem;border-radius:21px}.block-container{padding-left:1rem;padding-right:1rem}.vw-hero h1{font-size:2.25rem} }
</style>
"""
st.markdown(CSS, unsafe_allow_html=True)


def hero(kicker: str, title: str, description: str, pills: list[str] | None = None) -> None:
    safe_pills = "".join(f"<span class='vw-pill'>{escape(p)}</span>" for p in (pills or []))
    st.markdown(f"<div class='vw-hero'><div class='vw-kicker'>{escape(kicker)}</div><h1>{escape(title).replace(chr(10), '<br>')}</h1><p>{escape(description)}</p><div class='vw-pills'>{safe_pills}</div></div>", unsafe_allow_html=True)


def section(title: str, note: str = "") -> None:
    st.markdown(f"<div class='vw-section'><h2>{escape(title)}</h2>{f'<div class=vw-muted>{escape(note)}</div>' if note else ''}</div>", unsafe_allow_html=True)


def inr(value: Any) -> str:
    try:
        if value is None:
            return "Not supplied"
        return f"₹{float(value):,.0f}"
    except (TypeError, ValueError):
        return "Not supplied"


def safe_link(label: str, url: str, key: str) -> None:
    st.link_button(label, url or "https://www.google.com/travel/", key=key, use_container_width=False)


def save_current_trip() -> None:
    itinerary = st.session_state.get("itinerary")
    request_data = st.session_state.get("trip_request_json")
    if not itinerary or not request_data:
        return
    try:
        trip_id = save_trip(request_data, itinerary, st.session_state.get("trip_id"))
        st.session_state["trip_id"] = trip_id
        st.session_state["itinerary"]["trip_id"] = trip_id
    except Exception as exc:
        st.warning(f"Local trip memory could not be updated: {exc}")


def render_status_card(title: str, subtitle: str, ready: bool, key_text: str) -> None:
    status = "Configured" if ready else "Setup required"
    cls = "vw-status" if ready else "vw-status"
    st.markdown(f"<div class='vw-card'><div class='vw-icon'>{escape(key_text.split()[0])}</div><h3>{escape(title)}</h3><p>{escape(subtitle)}</p><span class='{cls}'>{'● ' if ready else '○ '}{status}</span></div>", unsafe_allow_html=True)


def overview_page() -> None:
    hero("YOUR AI TRAVEL COPILOT", "Plan smarter. Travel further.", "A multi-agent travel workspace that researches destinations, compares flight and train options, balances a trip budget and adapts when your plans change.", ["Agentic planning", "Flights + Indian Railways", "Live weather & mapped places", "Human approval"])
    st.write("")
    c1, c2, c3, c4 = st.columns(4)
    c1.metric("Planning engine", "Ready", "Rule-based + optional LLM")
    c2.metric("Flight search", "Connected" if flight_configured() else "Needs key", "SerpApi / Google Flights")
    c3.metric("Train search", "Connected" if train_configured() else "Needs key", "RapidAPI provider")
    c4.metric("Weather + places", "Public data", "No key required")
    section("Your travel workspace", "Start from a destination goal or compare transport options first. Search results are time-sensitive and must be checked before booking.")
    cols = st.columns(3)
    with cols[0]:
        st.markdown("<div class='vw-card'><div class='vw-icon'>✈️</div><h3>Compare flights</h3><p>Search returned offers by IATA airport code and departure date.</p></div>", unsafe_allow_html=True)
        if st.button("Open flight search →", key="go_flights", use_container_width=True):
            st.session_state["page"] = "Transport Search"
            st.session_state["transport_kind"] = "Flights"
            st.rerun()
    with cols[1]:
        st.markdown("<div class='vw-card'><div class='vw-icon'>🚆</div><h3>Compare trains</h3><p>Look up Indian train routes and provider-returned indicative fares.</p></div>", unsafe_allow_html=True)
        if st.button("Open train search →", key="go_trains", use_container_width=True):
            st.session_state["page"] = "Transport Search"
            st.session_state["transport_kind"] = "Trains"
            st.rerun()
    with cols[2]:
        st.markdown("<div class='vw-card'><div class='vw-icon'>✦</div><h3>Build an itinerary</h3><p>Coordinate research, constraints, memory, approval and replanning.</p></div>", unsafe_allow_html=True)
        if st.button("Plan a trip →", key="go_plan", type="primary", use_container_width=True):
            st.session_state["page"] = "Plan a Trip"
            st.rerun()
    section("How the agent workflow operates")
    process = st.columns(5)
    for col, num, label, detail in zip(process, ["01", "02", "03", "04", "05"], ["Understand", "Research", "Plan", "Validate", "Replan"], ["Decompose your goal", "Call travel & weather tools", "Arrange researched places", "Check costs and constraints", "Adapt to new feedback"]):
        with col:
            st.markdown(f"<div class='vw-card'><div class='vw-kicker'>{num}</div><h3>{label}</h3><p>{detail}</p></div>", unsafe_allow_html=True)
    st.info("Transparency promise: flight results come from the configured search provider; train results/fare are third-party data; mapped places come from OpenStreetMap; weather comes from Open-Meteo. If a source is unavailable, the app labels it instead of inventing data.")


def _render_flight_results(result: dict[str, Any]) -> None:
    if not result.get("ok"):
        st.error(result.get("message", "Flight search did not succeed."))
        st.caption("Configure SERPAPI_KEY in .env. Do not paste the key into this chat.")
        return
    st.caption(f"Source: {result.get('source')} · {result.get('mode')} · Fetched UTC: {result.get('retrieved_at_utc', 'not supplied')}")
    st.info(f"{result.get('freshness', '')} {result.get('message', '')}")
    offers = result.get("offers", [])
    if not offers:
        st.warning("The provider returned no flight offers for this query. Try another date or airport code.")
        return
    for index, offer in enumerate(offers):
        with st.container(border=True):
            c1, c2, c3 = st.columns([2.2, 2.1, 1.05])
            with c1:
                st.markdown(f"**✈️ {offer.get('airline', 'Airline not supplied')}**")
                st.caption(f"{offer.get('origin', '')} → {offer.get('destination', '')} · {offer.get('stops', 0)} stop(s)")
                st.caption(f"Duration: {offer.get('duration', 'Not supplied')}")
            with c2:
                st.markdown(f"**{offer.get('departure', '—')}**")
                st.caption("Departure")
                st.markdown(f"**{offer.get('arrival', '—')}**")
                st.caption("Arrival")
            with c3:
                st.markdown(f"### {inr(offer.get('price'))}")
                st.caption("Provider price")
                if st.button("Use in trip", key=f"use_flight_{index}", use_container_width=True):
                    st.session_state["selected_transport"] = {**offer, "mode": "Flight"}
                    st.success("Flight option saved to this session.")
            st.caption(offer.get("fare_note", "Verify all conditions before purchase."))
            if offer.get("booking_link"):
                st.link_button("Compare / verify ↗", offer["booking_link"], key=f"flight_link_{index}")


def _render_train_results(result: dict[str, Any]) -> None:
    if not result.get("ok"):
        st.error(result.get("message", "Train search did not succeed."))
        st.caption("Configure RAPIDAPI_KEY in .env. Never submit real payment details to this application.")
        return
    st.caption(f"Source: {result.get('source')} · Fetched UTC: {result.get('retrieved_at_utc', 'not supplied')} · Provider timestamp: {result.get('generated_timestamp', 'not supplied')}")
    st.warning("These are route/schedule results and indicative fare data from a third-party provider. Live seat inventory is not checked by this connector. Confirm schedule, quota, fare and availability on IRCTC.")
    trains = result.get("trains", [])
    if not trains:
        st.info("No trains returned. Check both station codes, date and provider subscription.")
        return
    for index, train in enumerate(trains):
        with st.container(border=True):
            c1, c2, c3 = st.columns([2.2, 1.5, 1.1])
            with c1:
                st.markdown(f"**🚆 {train.get('train_name', 'Train')}** · `{train.get('train_no', '')}`")
                st.caption(f"{train.get('from_station', '')} → {train.get('to_station', '')}")
                st.caption(f"Runs on: {', '.join(train.get('runs_on', [])) if isinstance(train.get('runs_on'), list) else train.get('runs_on', 'Not supplied')}")
            with c2:
                st.markdown(f"**{train.get('departure', '—')} → {train.get('arrival', '—')}**")
                st.caption(f"Journey duration: {train.get('duration', '—')}")
            with c3:
                st.markdown(f"### {inr(train.get('indicative_fare'))}")
                st.caption(f"Indicative {train.get('fare_class') or 'class not supplied'} fare")
                if st.button("Use in trip", key=f"use_train_{index}", use_container_width=True):
                    st.session_state["selected_transport"] = {**train, "mode": "Train", "price": train.get("indicative_fare")}
                    st.success("Train option saved to this session.")
            st.caption(train.get("fare_basis", "Fare was not supplied by provider."))
            st.link_button("Verify / book on IRCTC ↗", train.get("booking_link", "https://www.irctc.co.in/nget/train-search"), key=f"train_link_{index}")


def transport_page() -> None:
    hero("TRANSPORT DISCOVERY", "Choose the route that fits.", "Search flight offers or Indian train routes, inspect provider-returned information, then send your preferred option to the itinerary budget check.", ["External data providers", "Freshness timestamp", "No booking inside the app"])
    flight_tab, train_tab = st.tabs(["✈️ Flights", "🚆 Trains"])
    with flight_tab:
        st.markdown("#### Flight offers")
        trip_type = st.radio("Journey type", ["One-way", "Round trip"], horizontal=True, key="flight_trip_type")
        with st.form("flight_search_form"):
            c1, c2, c3 = st.columns(3)
            origin = c1.text_input("From airport code", value="BLR", max_chars=3, help="Three-letter IATA code, e.g. BLR, DEL, BOM, MAA.").strip().upper()
            destination = c2.text_input("To airport code", value="DEL", max_chars=3).strip().upper()
            departure = c3.date_input("Departure date", value=date.today() + timedelta(days=14), min_value=date.today(), key="flight_departure")
            c4, c5 = st.columns(2)
            adults = c4.number_input("Adult travellers", min_value=1, max_value=9, value=1, key="flight_adults")
            return_date = c5.date_input("Return date", value=departure + timedelta(days=4), min_value=departure, key="flight_return") if trip_type == "Round trip" else None
            submitted = st.form_submit_button("Search flight offers", type="primary", use_container_width=True)
        if submitted:
            with st.spinner("Searching the configured flight provider…"):
                st.session_state["flight_result"] = search_flights(origin, destination, departure, int(adults), return_date)
        if st.session_state.get("flight_result"):
            _render_flight_results(st.session_state["flight_result"])
    with train_tab:
        st.markdown("#### Indian train route search")
        with st.form("station_lookup_form"):
            station_query = st.text_input("Find a station name or code", placeholder="e.g. Bengaluru or New Delhi")
            lookup_submit = st.form_submit_button("Find station code")
        if lookup_submit:
            with st.spinner("Searching station directory…"):
                st.session_state["station_result"] = search_stations(station_query)
        station_result = st.session_state.get("station_result")
        if station_result:
            if station_result.get("ok"):
                matches = station_result.get("results", [])
                if matches:
                    st.dataframe([{"Station": x.get("station_name", x.get("name", "")), "Code": x.get("station_code", x.get("code", ""))} for x in matches], use_container_width=True, hide_index=True)
                else:
                    st.info("No station matches were returned.")
            else:
                st.warning(station_result.get("message", "Station lookup unavailable."))
        with st.form("train_search_form"):
            a, b, c = st.columns(3)
            origin_code = a.text_input("From station code", value="SBC", max_chars=8, help="Use the provider's station code.").strip().upper()
            destination_code = b.text_input("To station code", value="NDLS", max_chars=8).strip().upper()
            travel_date = c.date_input("Journey date", value=date.today() + timedelta(days=14), min_value=date.today(), key="train_date")
            adults = st.number_input("Adult passengers for fare lookup", min_value=1, max_value=9, value=1, key="train_adults")
            train_submit = st.form_submit_button("Search trains", type="primary", use_container_width=True)
        if train_submit:
            with st.spinner("Searching the railway provider…"):
                st.session_state["train_result"] = search_trains(origin_code, destination_code, travel_date, int(adults))
        if st.session_state.get("train_result"):
            _render_train_results(st.session_state["train_result"])
    selected = st.session_state.get("selected_transport")
    if selected:
        section("Selected for your trip", "This option is saved only in this browser session until you build and save a trip.")
        st.success(f"{selected.get('mode', 'Transport')}: {selected.get('airline', selected.get('train_name', 'Option'))} · {selected.get('origin', selected.get('from_station', ''))} → {selected.get('destination', selected.get('to_station', ''))} · {inr(selected.get('price', selected.get('indicative_fare')))}")
        if st.button("Clear selected transport"):
            st.session_state.pop("selected_transport", None)
            st.rerun()


def _render_itinerary(itinerary: dict[str, Any]) -> None:
    cost = itinerary.get("cost_summary", {})
    metrics = st.columns(4)
    metrics[0].metric("Estimated total", inr(cost.get("total_estimated_inr")))
    metrics[1].metric("Budget", inr(cost.get("budget_inr")))
    metrics[2].metric("Remaining", inr(cost.get("remaining_inr")))
    metrics[3].metric("Draft status", itinerary.get("approval_status", "Pending"))
    try:
        ratio = float(cost.get("total_estimated_inr", 0)) / max(1, float(cost.get("budget_inr", 1)))
        st.progress(min(1.0, max(0.0, ratio)), text=f"Budget used: {ratio:.0%} · estimate includes only the components listed below")
    except (TypeError, ValueError):
        pass
    if itinerary.get("validation_issues"):
        for issue in itinerary["validation_issues"]:
            st.warning(issue)
    else:
        st.success("The current estimate passed the implemented structural and budget checks. This is not a guarantee that the trip is bookable.")
    with st.expander("Estimated trip costs and assumptions", expanded=True):
        cost_rows = [
            {"Component": "Transport", "Estimate": inr(cost.get("transport_inr")), "Basis": cost.get("transport_basis", "")},
            {"Component": "Food", "Estimate": inr(cost.get("food_inr")), "Basis": cost.get("food_basis", "")},
            {"Component": "Accommodation", "Estimate": inr(cost.get("accommodation_inr")), "Basis": cost.get("accommodation_basis", "")},
            {"Component": "Local transport", "Estimate": inr(cost.get("local_transport_inr")), "Basis": cost.get("local_transport_basis", "")},
            {"Component": "Attraction entry", "Estimate": inr(cost.get("known_attraction_fees_inr")), "Basis": cost.get("attraction_basis", "")},
        ]
        st.dataframe(cost_rows, use_container_width=True, hide_index=True)
        for assumption in itinerary.get("assumptions", []):
            st.caption(f"• {assumption}")
    for day in itinerary.get("days", []):
        with st.container(border=True):
            title_col, weather_col = st.columns([2.5, 1])
            with title_col:
                st.markdown(f"### {day.get('title', f'Day {day.get('day')}')}")
                st.caption(day.get("date", ""))
            with weather_col:
                st.caption(day.get("weather_note", "Forecast unavailable"))
            for activity in day.get("activities", []):
                st.markdown(f"**{activity.get('time', '—')}  ·  {activity.get('activity', 'Activity')}**")
                st.caption(f"{activity.get('location', itinerary.get('destination', ''))} · {activity.get('category', 'Suggested activity')} · Cost: {inr(activity.get('estimated_cost_inr', 0))}")
                if activity.get("reason"):
                    st.write(activity["reason"])
                if activity.get("indoor_alternative"):
                    st.caption(f"Weather alternative: {activity['indoor_alternative']}")
                link_col1, link_col2 = st.columns([1, 4])
                if activity.get("map_url"):
                    link_col1.link_button("Open map ↗", activity["map_url"], key=f"map_{day.get('day')}_{activity.get('time')}_{abs(hash(activity.get('place_name', '')))%100000}")
                if activity.get("source_url"):
                    link_col2.link_button("Place source ↗", activity["source_url"], key=f"source_{day.get('day')}_{activity.get('time')}_{abs(hash(activity.get('place_name', '')))%100000}")
                st.divider()
    if itinerary.get("transport"):
        t = itinerary["transport"]
        st.markdown("#### Transport option currently included")
        st.write(f"**{t.get('mode', 'Transport')}** · {t.get('airline', t.get('train_name', 'Provider option'))} · {inr(t.get('price', t.get('indicative_fare')))}")
        st.caption(t.get("fare_note", "Verify the full fare before purchase."))
    with st.expander("Agent execution trace"):
        trace = itinerary.get("agent_trace", [])
        if trace:
            st.dataframe(trace, use_container_width=True, hide_index=True)
        else:
            st.info("Agent trace will be available after the first workflow run.")


def plan_page() -> None:
    hero("MULTI-AGENT WORKSPACE", "Build your journey, intelligently.", "Describe your trip once. The workflow decomposes your goal, researches real data sources, drafts an itinerary, validates estimates and waits for your approval.", ["Goal decomposition", "Tool calls", "Constraint checks", "Memory + replanning"])
    profile = load_profile()
    selected_transport = st.session_state.get("selected_transport")
    if selected_transport:
        st.info(f"Selected transport available: {selected_transport.get('mode')} · {selected_transport.get('airline', selected_transport.get('train_name', 'Option'))} · {inr(selected_transport.get('price', selected_transport.get('indicative_fare')))}")
    with st.form("trip_request_form"):
        st.markdown("#### 1 · Trip basics")
        c1, c2 = st.columns(2)
        origin_city = c1.text_input("Starting city", value=str(profile.get("last_origin_city", "Bengaluru")))
        destination = c2.text_input("Destination city", value=str(profile.get("last_destination", "Kochi")))
        c3, c4, c5 = st.columns(3)
        departure = c3.date_input("Departure date", value=date.today() + timedelta(days=14), min_value=date.today(), key="plan_departure")
        days = c4.number_input("Trip duration (days)", min_value=1, max_value=21, value=4)
        travellers = c5.number_input("Travellers", min_value=1, max_value=9, value=int(profile.get("travelers", 2)))
        c6, c7 = st.columns(2)
        budget = c6.number_input("Total budget (INR)", min_value=1000, max_value=10000000, value=25000, step=1000)
        interest_default = ", ".join(profile.get("interests", ["nature", "local food"])) if profile.get("interests") else "nature, local food"
        interests = c7.text_input("Interests, comma-separated", value=interest_default, help="Examples: nature, beaches, museums, photography, local food")
        notes = st.text_area("Additional instructions", placeholder="Example: avoid overnight journeys, prefer a relaxed pace, include indoor alternatives.", height=75)
        st.markdown("#### 2 · Transport and budget estimates")
        mode_options = ["None", "Use selected option", "Search flights", "Search trains"]
        default_mode = "Use selected option" if selected_transport else "None"
        transport_choice = st.selectbox("Transport plan", mode_options, index=mode_options.index(default_mode))
        flight_origin_code, flight_destination_code, train_origin_code, train_destination_code = "", "", "", ""
        if transport_choice == "Search flights":
            a, b = st.columns(2)
            flight_origin_code = a.text_input("Flight origin airport code", value="BLR", max_chars=3).strip().upper()
            flight_destination_code = b.text_input("Flight destination airport code", value="COK", max_chars=3).strip().upper()
        elif transport_choice == "Search trains":
            a, b = st.columns(2)
            train_origin_code = a.text_input("Train origin station code", value="SBC", max_chars=8).strip().upper()
            train_destination_code = b.text_input("Train destination station code", value="ERS", max_chars=8).strip().upper()
        a, b, c = st.columns(3)
        food_pp = a.number_input("Food budget / person / day (₹)", min_value=0, max_value=20000, value=int(profile.get("food_budget_per_person_per_day", 800)), step=100)
        hotel_room = b.number_input("Accommodation / room / night (₹)", min_value=0, max_value=100000, value=int(profile.get("accommodation_per_room_per_night", 1800)), step=100)
        local_pp = c.number_input("Local transport / person / day (₹)", min_value=0, max_value=10000, value=int(profile.get("local_transport_per_person_per_day", 350)), step=50)
        run = st.form_submit_button("✦ Research & build itinerary", type="primary", use_container_width=True)
    if run:
        interests_list = [x.strip() for x in interests.split(",") if x.strip()]
        mode = {"Search flights": "Flight", "Search trains": "Train", "Use selected option": "Use selected", "None": "None"}[transport_choice]
        if mode == "Use selected" and not selected_transport:
            st.error("No transport option selected. Open Transport Search and click 'Use in trip', or choose None.")
        else:
            try:
                request = TripRequest(origin_city=origin_city.strip(), destination=destination.strip(), departure_date=departure,
                                      days=int(days), travelers=int(travellers), budget_inr=float(budget), interests=interests_list,
                                      transport_mode=mode, origin_code=flight_origin_code if mode == "Flight" else train_origin_code,
                                      destination_code=flight_destination_code if mode == "Flight" else train_destination_code,
                                      food_budget_per_person_per_day=float(food_pp), accommodation_per_room_per_night=float(hotel_room),
                                      local_transport_per_person_per_day=float(local_pp), notes=notes.strip())
                with st.spinner("Running supervisor → research tools → planner → validator…"):
                    state = run_workflow(request, selected_transport if mode == "Use selected" else None)
                st.session_state["trip_request_json"] = request.model_dump(mode="json")
                st.session_state["itinerary"] = state["itinerary"]
                st.session_state["place_result"] = state["place_result"]
                st.session_state["weather_result"] = state["weather_result"]
                st.session_state["transport_options"] = state["transport_options"]
                st.session_state["trip_id"] = state["itinerary"].get("trip_id")
                st.success("Workflow completed. Review the results and approve only after checking the assumptions.")
            except Exception as exc:
                st.error(f"Could not build the itinerary: {exc}")
    itinerary = st.session_state.get("itinerary")
    if not itinerary:
        section("What the workflow will do")
        cols = st.columns(4)
        for col, emoji, name, text in zip(cols, ["🧭", "🌍", "🗓️", "🛡️"], ["Decompose", "Research", "Plan & check", "Human gate"], ["Break your trip into tasks", "Query places, weather and transport tools", "Balance the estimated budget and timings", "Require approval before treating the plan as final"]):
            col.markdown(f"<div class='vw-card'><div class='vw-icon'>{emoji}</div><h3>{name}</h3><p>{text}</p></div>", unsafe_allow_html=True)
        return

    section("Your generated itinerary", f"Generated by: {itinerary.get('generated_by', 'Planner')} · Trip ID: {itinerary.get('trip_id', 'local session')}")
    options = st.session_state.get("transport_options", [])
    req_json = st.session_state.get("trip_request_json", {})
    if len(options) > 1:
        def option_label(item: dict[str, Any]) -> str:
            amount = item.get("price", item.get("indicative_fare"))
            mode_name = item.get("airline", item.get("train_name", item.get("mode", "Transport")))
            route = f"{item.get('origin', item.get('from_station', ''))} → {item.get('destination', item.get('to_station', ''))}"
            return f"{mode_name} · {route} · {inr(amount)}"
        labels = [option_label(item) for item in options]
        chosen_index = st.selectbox("Choose the transport result to include in the budget", range(len(labels)), format_func=lambda i: labels[i], key="plan_transport_choice")
        if st.button("Apply chosen transport to budget", type="secondary"):
            request = TripRequest.model_validate(req_json)
            current = apply_transport_option(itinerary, request, options[chosen_index], itinerary.get("places_data", []))
            current["transport_options"] = options
            st.session_state["itinerary"] = current
            save_current_trip()
            st.rerun()
    _render_itinerary(st.session_state["itinerary"])
    itinerary = st.session_state["itinerary"]
    c1, c2, c3 = st.columns([1.3, 1.3, 2])
    if c1.button("✓ Approve draft", type="primary", use_container_width=True, disabled=not itinerary.get("requires_human_approval", True)):
        itinerary["approval_status"] = "Approved by user as an itinerary draft"
        itinerary["requires_human_approval"] = False
        itinerary.setdefault("agent_trace", []).append({"agent": "Human Approval Gate", "status": "approved", "detail": "User approved the itinerary draft. No ticket/hotel was booked."})
        st.session_state["itinerary"] = itinerary
        save_current_trip()
        st.success("Draft approval saved. This did not book transport or accommodation.")
        st.rerun()
    if c2.button("↺ Mark for revision", use_container_width=True):
        st.session_state["show_replan"] = True
    if c3.button("Save current draft", use_container_width=True):
        save_current_trip()
        st.success("Current draft saved to local SQLite memory.")
    if st.session_state.get("show_replan"):
        with st.form("replanning_form"):
            feedback = st.text_area("What should change?", placeholder="Examples: rain is expected on Day 2; prioritize nature and viewpoints; make the pace slower with fewer places; reduce the budget to INR 20000.", height=90)
            replan_submit = st.form_submit_button("Run dynamic replanning", type="primary")
        if replan_submit:
            request = TripRequest.model_validate(st.session_state["trip_request_json"])
            with st.spinner("Replanning affected activities and rechecking constraints…"):
                new_plan = replan_from_feedback(st.session_state["itinerary"], feedback, request,
                                                st.session_state["itinerary"].get("places_data", []),
                                                st.session_state.get("weather_result", {}))
            st.session_state["itinerary"] = new_plan
            st.session_state["trip_request_json"] = request.model_dump(mode="json")
            st.session_state["show_replan"] = False
            save_current_trip()
            st.success("Replanning finished. The revised version requires approval again.")
            st.rerun()
    with st.expander("Data provenance and trip research"):
        st.write("**Places:**", itinerary.get("research", {}).get("places", {}))
        st.caption("Map data: © OpenStreetMap contributors (ODbL). Place listings do not verify opening hours or ticket prices.")
        st.write("**Weather:**", itinerary.get("research", {}).get("weather", {}))
        st.caption("Weather source: Open-Meteo; forecasts are model output and may change.")
        st.write("**Replan history:**", itinerary.get("change_log", []))
    st.download_button("Download itinerary JSON", data=json.dumps(itinerary, indent=2, ensure_ascii=False, default=str), file_name="voyagewise_itinerary.json", mime="application/json")
    if itinerary.get("days"):
        csv_lines = ["day,date,time,activity,location,estimate_inr,source_url"]
        for day in itinerary["days"]:
            for a in day.get("activities", []):
                vals = [day.get("day"), day.get("date"), a.get("time", ""), a.get("activity", ""), a.get("location", ""), a.get("estimated_cost_inr", 0), a.get("source_url", "")]
                csv_lines.append(",".join('"' + str(v).replace('"', '""') + '"' for v in vals))
        st.download_button("Download activities CSV", data="\n".join(csv_lines), file_name="voyagewise_activities.csv", mime="text/csv")


def weather_page() -> None:
    hero("WEATHER INTELLIGENCE", "Plan around the forecast.", "Use a public forecast to inform activity choices. Forecasts are probabilistic, and distant travel dates may be outside the available horizon.", ["Open-Meteo", "No key required", "Use for replanning"])
    with st.form("weather_form"):
        c1, c2, c3 = st.columns([2, 1, 1])
        city = c1.text_input("Destination city", value="Kochi")
        start = c2.date_input("Start date", value=date.today(), min_value=date.today(), key="wx_start")
        end = c3.date_input("End date", value=date.today() + timedelta(days=4), min_value=start, key="wx_end")
        submitted = st.form_submit_button("Fetch forecast", type="primary")
    if submitted:
        with st.spinner("Resolving location and querying Open-Meteo…"):
            st.session_state["weather_page_result"] = get_weather(city, start, end)
    result = st.session_state.get("weather_page_result")
    if result:
        if not result.get("ok"):
            st.warning(result.get("message", "Forecast unavailable."))
        else:
            loc = result["location"]
            st.markdown(f"### {loc['name']}, {loc.get('admin1', '')} {loc.get('country', '')}")
            cols = st.columns(4)
            forecasts = result.get("forecast", [])
            for index, item in enumerate(forecasts):
                with cols[index % 4]:
                    with st.container(border=True):
                        st.markdown(f"**{item['date']}**")
                        st.markdown(f"### {item.get('description', 'Conditions unavailable')}")
                        st.write(f"{item.get('temperature_min_c')}°C – {item.get('temperature_max_c')}°C")
                        st.caption(f"Rain chance: {item.get('precipitation_probability', 'N/A')}%")
            st.caption(f"{result.get('source')} · {result.get('retrieved_at_utc')} · {result.get('message')}")
            rainy = [x for x in forecasts if isinstance(x.get("precipitation_probability"), (int, float)) and x["precipitation_probability"] >= 50]
            if rainy:
                st.warning(f"The current forecast reports ≥50% precipitation probability on {len(rainy)} day(s). Consider an indoor alternative and recheck nearer departure.")


def trips_page() -> None:
    hero("YOUR TRIP MEMORY", "Pick up where you left off.", "Trip drafts, approvals and preference memory are stored in a local SQLite database on this computer.", ["Local-only storage", "Trip history", "Preference memory"])
    try:
        trips = list_trips()
        profile = load_profile()
    except Exception as exc:
        st.error(f"Could not open local trip memory: {exc}")
        return
    section("Saved trips", f"{len(trips)} trip record(s) stored locally")
    if trips:
        st.dataframe([{"Trip ID": t["id"], "Trip": t["title"], "Status": t["status"], "Last updated (UTC)": t["updated_at_utc"]} for t in trips], use_container_width=True, hide_index=True)
        labels = [f"#{t['id']} · {t['title']} · {t['status']}" for t in trips]
        choice = st.selectbox("Inspect a saved trip", range(len(trips)), format_func=lambda x: labels[x])
        picked = trips[choice]
        with st.expander("Saved trip details", expanded=True):
            st.json({"request": picked["request"], "approval_status": picked["itinerary"].get("approval_status"), "cost_summary": picked["itinerary"].get("cost_summary"), "change_log": picked["itinerary"].get("change_log", [])})
            if st.button("Load this trip into Plan a Trip", key=f"load_trip_{picked['id']}"):
                st.session_state["trip_request_json"] = picked["request"]
                st.session_state["itinerary"] = picked["itinerary"]
                st.session_state["trip_id"] = picked["id"]
                st.session_state["place_result"] = {"ok": True, "places": picked["itinerary"].get("places_data", [])}
                st.session_state["weather_result"] = {"ok": True, "forecast": picked["itinerary"].get("weather_data", [])}
                st.session_state["page"] = "Plan a Trip"
                st.rerun()
    else:
        st.info("No trips saved yet. Build an itinerary and choose Save current draft.")
    section("Remembered preferences")
    if profile:
        st.json(profile)
    else:
        st.caption("Preferences will appear after the first planning workflow.")
    with st.expander("Reset local memory", expanded=False):
        st.warning("This removes saved trips, agent events and remembered preferences from the local project database. It cannot be undone.")
        confirm = st.checkbox("I understand and want to permanently clear local memory.")
        if st.button("Clear local memory", disabled=not confirm):
            clear_memory()
            st.session_state.pop("itinerary", None)
            st.session_state.pop("trip_request_json", None)
            st.success("Local memory cleared.")
            st.rerun()


def status_page() -> None:
    hero("SYSTEM TRANSPARENCY", "Know what is connected.", "Inspect connectors, data limitations, agent events and safe boundaries. No search provider or LLM is treated as infallible.", ["Provenance", "Evaluation", "Responsible autonomy"])
    section("Provider status")
    statuses = [
        {"Provider": "Google Flights through SerpApi", "Configured": flight_configured(), "Credentials needed": "SERPAPI_KEY", "Coverage": "Flight search offers; fare can change; no booking action."},
        {"Provider": "Indian Railways provider via RapidAPI", "Configured": train_configured(), "Credentials needed": "RAPIDAPI_KEY", "Coverage": "Train route/schedule and optional indicative fare; no live seat inventory in this connector."},
        {"Provider": "Open-Meteo", "Configured": True, "Credentials needed": "None for qualifying non-commercial use", "Coverage": "Weather forecast and geocoding; forecast horizon is limited."},
        {"Provider": "OpenStreetMap Overpass", "Configured": True, "Credentials needed": "None", "Coverage": "Mapped POIs; not live opening/closure/price data."},
        {"Provider": "Gemini API", "Configured": bool(os.getenv("GEMINI_API_KEY", "").strip()), "Credentials needed": "GEMINI_API_KEY (optional)", "Coverage": "Optional itinerary scheduling and feedback replanning; fallback works without it."},
    ]
    st.dataframe(statuses, use_container_width=True, hide_index=True)
    section("Recent agent events")
    events = list_events(100)
    if events:
        st.dataframe(events, use_container_width=True, hide_index=True)
    else:
        st.caption("Agent events will be recorded after you build your first itinerary.")
    section("Safety boundaries")
    st.markdown("- The app searches and plans; it does **not** buy tickets, hold seats, book hotels or accept payment details.\n- Never commit `.env` or share API keys.\n- Data freshness labels refer to retrieval/provider metadata, not a guarantee of accuracy.\n- The itinerary requires human review and approval after generation and after every revision.\n- Budget validation checks the cost components you entered or that a provider returned; attraction ticket prices and hotel inventory are not live-linked.\n- OpenStreetMap is a community map source; confirm opening hours, closures and suitability independently.")
    section("Mini-project evaluation checklist")
    evaluation = ["Goal decomposition", "Specialized agent roles", "External tool calling", "Constraint validation", "Local persistent memory", "Human approval checkpoint", "Feedback-driven replanning", "Data provenance and provider-failure handling", "Automated unit tests"]
    for item in evaluation:
        st.checkbox(item, value=True, disabled=True, key="eval_" + item.replace(" ", "_"))


def main() -> None:
    with st.sidebar:
        st.markdown("<div class='vw-brand'><div class='vw-brand-mark'>✦</div><div><div class='vw-brand-name'>VoyageWise AI</div><div class='vw-brand-sub'>Autonomous Travel Workspace</div></div></div>", unsafe_allow_html=True)
        st.markdown("---")
        pages = ["Overview", "Transport Search", "Plan a Trip", "Weather", "Trip Memory", "Agent & API Status"]
        default_page = st.session_state.get("page", "Overview")
        if default_page not in pages:
            default_page = "Overview"
        page = st.radio("WORKSPACE", pages, index=pages.index(default_page), label_visibility="collapsed")
        st.session_state["page"] = page
        st.markdown("---")
        st.caption("DATA CONNECTORS")
        st.markdown(f"{'🟢' if flight_configured() else '⚪'} Flight search")
        st.markdown(f"{'🟢' if train_configured() else '⚪'} Train route search")
        st.markdown("🟢 Weather & mapped places")
        st.markdown(f"{'🟢' if os.getenv('GEMINI_API_KEY', '').strip() else '⚪'} Optional free-tier LLM")
        st.markdown("---")
        st.caption("No ticket booking or payment actions")
        st.caption("Theme: use ⋮ → Settings → Theme")
    if page == "Overview":
        overview_page()
    elif page == "Transport Search":
        transport_page()
    elif page == "Plan a Trip":
        plan_page()
    elif page == "Weather":
        weather_page()
    elif page == "Trip Memory":
        trips_page()
    else:
        status_page()


if __name__ == "__main__":
    main()
