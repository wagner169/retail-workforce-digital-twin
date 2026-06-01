import time
import streamlit as st
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
from solver import solve_schedule

st.set_page_config(page_title="MILP Workforce Scheduler", layout="wide")

st.title("MILP Workforce Scheduling Dashboard")

# =========================
# SIDEBAR
# =========================

st.sidebar.header("Scenario Controls")

demand_multiplier = st.sidebar.slider(
    "Demand multiplier", 0.5, 2.0, 1.0, 0.1
)

max_weekly_hours = st.sidebar.slider(
    "Max weekly hours per employee", 10, 40, 20, 1
)

absent_employees = st.sidebar.multiselect(
    "Absent employees",
    options=["E1", "E2", "E3", "E4", "E5", "E6", "E7", "E8"]
)

show_operational_heatmap = st.sidebar.checkbox(
    "Show Operational Heatmap", value=True
)

show_employee_movement = st.sidebar.checkbox(
    "Show Employee Movement", value=True
)

show_congestion_zones = st.sidebar.checkbox(
    "Show Congestion Zones", value=True
)

auto_play_simulation = st.sidebar.checkbox(
    "Auto Play Simulation", value=False
)

selected_day = st.sidebar.selectbox(
    "3D View Day",
    ["Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Saturday", "Sunday"]
)

selected_slot = st.sidebar.slider(
    "3D View Time Slot", 1, 8, 1, 1
)

if auto_play_simulation:
    selected_slot = int(time.time() % 8) + 1

run_button = st.sidebar.button("Run Optimization")

if run_button:
    schedule, unmet_df, kpis = solve_schedule(
        max_weekly_hours=max_weekly_hours,
        demand_multiplier=demand_multiplier,
        absent_employees=absent_employees
    )

    st.session_state["schedule"] = schedule
    st.session_state["unmet_df"] = unmet_df
    st.session_state["kpis"] = kpis

if "schedule" not in st.session_state:
    st.info("Adjust the scenario controls and click Run Optimization.")
    st.stop()

schedule = st.session_state["schedule"]
unmet_df = st.session_state["unmet_df"]
kpis = st.session_state["kpis"]

# =========================
# STATUS
# =========================

fulfillment = kpis["demand_fulfillment_rate"]
unmet = kpis["total_unmet_workers"]

if fulfillment == 1:
    st.success("System Status: Stable — all demand covered.")
elif fulfillment >= 0.85:
    st.warning("System Status: Under Pressure — most demand covered.")
else:
    st.error("System Status: Critical — significant uncovered demand.")

# =========================
# KPIs
# =========================

st.subheader("Optimization KPIs")

col1, col2, col3, col4 = st.columns(4)

col1.metric("Status", kpis["status"])
col2.metric("Fulfillment Rate", f"{fulfillment:.2%}")
col3.metric("Unmet Demand", unmet)
col4.metric("Objective Value", round(kpis["objective_value"], 2))

col5, col6, col7, col8 = st.columns(4)

col5.metric("Total Required", kpis["total_required_workers"])
col6.metric("Assigned Hours", kpis["total_assigned_hours"])
col7.metric("Employees Used", kpis["employees_used"])
col8.metric("Activities Covered", kpis["activities_covered"])

# =========================
# SCENARIO SUMMARY
# =========================

st.subheader("Scenario Summary")

scenario_summary = pd.DataFrame([{
    "Demand Multiplier": demand_multiplier,
    "Max Weekly Hours": max_weekly_hours,
    "Absent Employees": ", ".join(absent_employees) if absent_employees else "None",
    "Operational Heatmap": "On" if show_operational_heatmap else "Off",
    "Employee Movement": "On" if show_employee_movement else "Off",
    "Congestion Zones": "On" if show_congestion_zones else "Off",
    "Auto Play": "On" if auto_play_simulation else "Off",
    "Fulfillment Rate": f"{fulfillment:.2%}",
    "Unmet Demand": unmet,
    "Assigned Hours": kpis["total_assigned_hours"],
}])

st.dataframe(scenario_summary, use_container_width=True)

# =========================
# TABLES
# =========================

st.subheader("Optimized Schedule")
st.dataframe(schedule, use_container_width=True)

st.subheader("Unmet Demand")
st.dataframe(unmet_df, use_container_width=True)

if schedule.empty:
    st.stop()

# =========================
# HOURS BY EMPLOYEE
# =========================

st.subheader("Hours by Employee")

hours_by_employee = (
    schedule.groupby(["employee_id", "name"])
    .size()
    .reset_index(name="assigned_hours")
)

fig_emp = px.bar(
    hours_by_employee,
    x="name",
    y="assigned_hours",
    title="Assigned Hours by Employee",
    text="assigned_hours"
)

st.plotly_chart(fig_emp, use_container_width=True)

# =========================
# EMPLOYEE STRESS SCORE
# =========================

st.subheader("Employee Stress Score")

hours_by_employee["stress_score"] = (
    hours_by_employee["assigned_hours"] / max_weekly_hours
)

fig_stress = px.bar(
    hours_by_employee,
    x="name",
    y="stress_score",
    title="Employee Stress Score",
    text=hours_by_employee["stress_score"].apply(lambda x: f"{x:.0%}")
)

fig_stress.update_yaxes(tickformat=".0%")

st.plotly_chart(fig_stress, use_container_width=True)

# =========================
# HOURS BY ACTIVITY
# =========================

st.subheader("Hours by Activity")

hours_by_activity = (
    schedule.groupby("activity_name")
    .size()
    .reset_index(name="assigned_hours")
)

fig_act = px.bar(
    hours_by_activity,
    x="activity_name",
    y="assigned_hours",
    title="Assigned Hours by Activity",
    text="assigned_hours"
)

st.plotly_chart(fig_act, use_container_width=True)

# =========================
# HEATMAP BY DAY AND SLOT
# =========================

st.subheader("Operational Workload Heatmap")

heatmap_data = (
    schedule.groupby(["day", "time_slot"])
    .size()
    .reset_index(name="active_workers")
)

heatmap_pivot = heatmap_data.pivot(
    index="time_slot",
    columns="day",
    values="active_workers"
).fillna(0)

day_order = ["Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Saturday", "Sunday"]
heatmap_pivot = heatmap_pivot.reindex(columns=day_order)

fig_heatmap = px.imshow(
    heatmap_pivot,
    labels=dict(x="Day", y="Time Slot", color="Active Workers"),
    title="Active Workers by Day and Time Slot",
    aspect="auto"
)

st.plotly_chart(fig_heatmap, use_container_width=True)

# =========================
# GANTT VIEW
# =========================

st.subheader("Employee Schedule Timeline")

gantt_data = schedule.copy()
gantt_data["employee_day"] = gantt_data["name"] + " - " + gantt_data["day"]

fig_gantt = px.bar(
    gantt_data,
    x="time_slot",
    y="employee_day",
    color="activity_name",
    orientation="h",
    title="Employee Schedule Timeline",
    hover_data=["activity_name", "day"]
)

fig_gantt.update_layout(
    xaxis_title="Time Slot",
    yaxis_title="Employee - Day",
    height=900
)

fig_gantt.update_yaxes(autorange="reversed")

st.plotly_chart(fig_gantt, use_container_width=True)

# =========================
# 3D RETAIL STORE DIGITAL TWIN
# =========================

st.subheader("3D Retail Store Digital Twin")

st.caption(
    f"Showing optimized retail operations for {selected_day}, slot {selected_slot}."
)

slot_schedule = schedule[
    (schedule["day"] == selected_day) &
    (schedule["time_slot"] == selected_slot)
]

zone_counts = (
    slot_schedule.groupby("activity_name")
    .size()
    .to_dict()
)

fig_3d = go.Figure()


def get_heatmap_color(workers, default_color):
    if not show_operational_heatmap:
        return default_color

    if workers == 0:
        return "mediumseagreen"
    elif workers == 1:
        return "gold"
    elif workers == 2:
        return "orange"
    return "red"


def add_box(fig, x0, x1, y0, y1, z0, z1, color, name, opacity=0.75):
    x = [x0, x1, x1, x0, x0, x1, x1, x0]
    y = [y0, y0, y1, y1, y0, y0, y1, y1]
    z = [z0, z0, z0, z0, z1, z1, z1, z1]

    i = [0, 0, 0, 1, 2, 3, 4, 4, 5, 6, 7, 7]
    j = [1, 2, 3, 5, 6, 7, 5, 6, 6, 7, 4, 6]
    k = [2, 3, 1, 4, 5, 4, 6, 7, 1, 2, 6, 3]

    fig.add_trace(go.Mesh3d(
        x=x,
        y=y,
        z=z,
        i=i,
        j=j,
        k=k,
        color=color,
        opacity=opacity,
        name=name,
        hovertext=name,
        hoverinfo="text"
    ))


# Floor
add_box(
    fig_3d,
    x0=0, x1=14,
    y0=0, y1=9,
    z0=0, z1=0.08,
    color="lightgray",
    name="Retail Store Floor",
    opacity=0.35
)

zones = {
    "Cashier": {
        "coords": (0.5, 4.0, 0.5, 2.2),
        "color": "royalblue",
        "label": "Cashier Area"
    },
    "Stocking": {
        "coords": (4.8, 9.2, 5.2, 8.3),
        "color": "orange",
        "label": "Stock / Backroom"
    },
    "Cleaning": {
        "coords": (10.0, 13.4, 0.5, 2.2),
        "color": "mediumseagreen",
        "label": "Cleaning / Service"
    },
    "Sales Floor": {
        "coords": (0.8, 13.2, 2.8, 4.8),
        "color": "lightblue",
        "label": "Sales Floor"
    }
}

for zone_name, config in zones.items():
    x0, x1, y0, y1 = config["coords"]

    if zone_name in ["Cashier", "Stocking", "Cleaning"]:
        workers = int(zone_counts.get(zone_name, 0))
    else:
        workers = int(sum(zone_counts.values()))

    zone_color = get_heatmap_color(workers, config["color"])

    add_box(
        fig_3d,
        x0=x0, x1=x1,
        y0=y0, y1=y1,
        z0=0.08, z1=0.20,
        color=zone_color,
        name=config["label"],
        opacity=0.35
    )

    tower_height = max(0.2, workers * 0.65)

    add_box(
        fig_3d,
        x0=x0 + 0.35, x1=x1 - 0.35,
        y0=y0 + 0.25, y1=y1 - 0.25,
        z0=0.20, z1=0.20 + tower_height,
        color=zone_color,
        name=f"{config['label']}: {workers} workers",
        opacity=0.85
    )

    fig_3d.add_trace(go.Scatter3d(
        x=[(x0 + x1) / 2],
        y=[(y0 + y1) / 2],
        z=[0.45 + tower_height],
        mode="text",
        text=[f"{config['label']}<br>{workers} workers"],
        showlegend=False
    ))

    if show_congestion_zones and workers >= 2:
        fig_3d.add_trace(go.Scatter3d(
            x=[(x0 + x1) / 2],
            y=[(y0 + y1) / 2],
            z=[1.2 + tower_height],
            mode="text",
            text=["⚠️ CONGESTION"],
            textposition="middle center",
            showlegend=False
        ))

# Checkout counters
for x in [0.8, 1.6, 2.4, 3.2]:
    add_box(
        fig_3d,
        x0=x, x1=x + 0.35,
        y0=0.7, y1=1.7,
        z0=0.20, z1=0.65,
        color="darkblue",
        name="Checkout Counter",
        opacity=0.85
    )

# Shelves
for x in [1.5, 3.0, 4.5, 6.0, 7.5, 9.0, 10.5, 12.0]:
    add_box(
        fig_3d,
        x0=x, x1=x + 0.18,
        y0=3.0, y1=4.6,
        z0=0.20, z1=1.15,
        color="black",
        name="Sales Shelf",
        opacity=0.50
    )

# Backroom racks
for x in [5.2, 6.2, 7.2, 8.2]:
    add_box(
        fig_3d,
        x0=x, x1=x + 0.22,
        y0=5.5, y1=8.0,
        z0=0.20, z1=1.50,
        color="dimgray",
        name="Backroom Rack",
        opacity=0.60
    )

# Employee markers
employee_positions = {
    "Cashier": [(1.0, 2.0), (1.8, 2.0), (2.6, 2.0), (3.4, 2.0)],
    "Stocking": [(5.4, 6.0), (6.4, 6.0), (7.4, 6.0), (8.4, 6.0)],
    "Cleaning": [(10.8, 1.5), (11.8, 1.5), (12.8, 1.5)],
}

if show_employee_movement:
    for activity, positions in employee_positions.items():
        workers = int(zone_counts.get(activity, 0))

        for idx in range(min(workers, len(positions))):
            x_pos, y_pos = positions[idx]

            fig_3d.add_trace(go.Scatter3d(
                x=[x_pos],
                y=[y_pos],
                z=[1.55],
                mode="markers+text",
                marker=dict(size=8, color="red"),
                text=["👤"],
                textposition="top center",
                name=f"{activity} Employee",
                showlegend=False
            ))

if show_operational_heatmap:
    st.caption("Heatmap: Green = 0 workers | Yellow = 1 | Orange = 2 | Red = 3+")
else:
    st.caption("Heatmap disabled: default activity colors shown.")

fig_3d.update_layout(
    title=f"Retail Store Digital Twin — {selected_day}, Slot {selected_slot}",
    scene=dict(
        xaxis_title="Store X",
        yaxis_title="Store Y",
        zaxis_title="Operational Load",
        xaxis=dict(range=[0, 14]),
        yaxis=dict(range=[0, 9]),
        zaxis=dict(range=[0, 6]),
        aspectmode="manual",
        aspectratio=dict(x=2.0, y=1.25, z=0.65)
    ),
    height=800,
    margin=dict(l=0, r=0, t=50, b=0)
)

st.plotly_chart(fig_3d, use_container_width=True)

if auto_play_simulation:
    time.sleep(1)
    st.rerun()