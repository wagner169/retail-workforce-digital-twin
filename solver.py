import pandas as pd
from ortools.linear_solver import pywraplp


def solve_schedule(
    max_weekly_hours=32,
    demand_multiplier=1.0,
    absent_employees=None,
    data_path="data"
):
    if absent_employees is None:
        absent_employees = []

    # =========================
    # LOAD DATASETS
    # =========================

    employees = pd.read_csv(f"{data_path}/employees.csv")
    activities = pd.read_csv(f"{data_path}/activities.csv")
    demand = pd.read_csv(f"{data_path}/demand.csv")
    skills = pd.read_csv(f"{data_path}/skills.csv")
    availability = pd.read_csv(f"{data_path}/availability.csv")

    # =========================
    # CREATE SETS
    # =========================

    EMPLOYEES = employees["employee_id"].tolist()
    ACTIVITIES = activities["activity_id"].tolist()

    DAYS = [
        "Monday", "Tuesday", "Wednesday",
        "Thursday", "Friday", "Saturday", "Sunday"
    ]

    TIME_SLOTS = sorted(
        demand["time_slot"].astype(int).unique().tolist()
    )

    # =========================
    # CREATE PARAMETERS
    # =========================

    max_daily_hours = dict(
        zip(employees["employee_id"], employees["max_daily_hours"])
    )

    priority = dict(
        zip(activities["activity_id"], activities["priority"])
    )

    skill = {
        (row.employee_id, row.activity_id): int(row.can_perform)
        for row in skills.itertuples(index=False)
    }

    availability_param = {
        (row.employee_id, row.day, int(row.time_slot)): int(row.available)
        for row in availability.itertuples(index=False)
    }

    demand_param = {}

    for row in demand.itertuples(index=False):
        adjusted_demand = int(round(row.required_workers * demand_multiplier))
        demand_param[(row.day, int(row.time_slot), row.activity_id)] = adjusted_demand

    # Force absent employees unavailable
    for employee in absent_employees:
        for day in DAYS:
            for slot in TIME_SLOTS:
                availability_param[(employee, day, slot)] = 0

    # =========================
    # CREATE SOLVER
    # =========================

    solver = pywraplp.Solver.CreateSolver("SCIP")

    if solver is None:
        raise RuntimeError("SCIP solver not available. Check OR-Tools installation.")

    # =========================
    # VARIABLES
    # =========================

    # x[e,a,d,t] = 1 if employee e works activity a on day d at slot t
    x = {}

    for e in EMPLOYEES:
        for a in ACTIVITIES:
            for d in DAYS:
                for t in TIME_SLOTS:
                    x[e, a, d, t] = solver.BoolVar(f"x_{e}_{a}_{d}_{t}")

    # z[e,d] = 1 if employee e works on day d
    z = {}

    for e in EMPLOYEES:
        for d in DAYS:
            z[e, d] = solver.BoolVar(f"z_{e}_{d}")

    # unmet[d,t,a] = uncovered demand
    unmet = {}

    for d in DAYS:
        for t in TIME_SLOTS:
            for a in ACTIVITIES:
                required = demand_param.get((d, t, a), 0)

                if required > 0:
                    unmet[d, t, a] = solver.IntVar(
                        0,
                        solver.infinity(),
                        f"unmet_{d}_{t}_{a}"
                    )

    # =========================
    # CONSTRAINTS
    # =========================

    # 1. One employee can do at most one activity per time slot
    for e in EMPLOYEES:
        for d in DAYS:
            for t in TIME_SLOTS:
                solver.Add(
                    sum(x[e, a, d, t] for a in ACTIVITIES) <= 1
                )

    # 2. Skill compatibility
    for e in EMPLOYEES:
        for a in ACTIVITIES:
            if skill.get((e, a), 0) == 0:
                for d in DAYS:
                    for t in TIME_SLOTS:
                        solver.Add(x[e, a, d, t] == 0)

    # 3. Availability
    for e in EMPLOYEES:
        for d in DAYS:
            for t in TIME_SLOTS:
                if availability_param.get((e, d, t), 0) == 0:
                    for a in ACTIVITIES:
                        solver.Add(x[e, a, d, t] == 0)

    # 4. Link z[e,d] with daily working hours
    for e in EMPLOYEES:
        for d in DAYS:
            daily_hours = sum(
                x[e, a, d, t]
                for a in ACTIVITIES
                for t in TIME_SLOTS
            )

            solver.Add(daily_hours <= max_daily_hours[e] * z[e, d])
            solver.Add(daily_hours >= 3 * z[e, d])  # minimum 3-hour shift

    # 5. Maximum weekly hours
    for e in EMPLOYEES:
        solver.Add(
            sum(
                x[e, a, d, t]
                for a in ACTIVITIES
                for d in DAYS
                for t in TIME_SLOTS
            ) <= max_weekly_hours
        )

    # 6. Maximum working days per week
    max_working_days = 5

    for e in EMPLOYEES:
        solver.Add(
            sum(z[e, d] for d in DAYS) <= max_working_days
        )

    # 7. Demand satisfaction
    # assigned workers + unmet workers = required workers
    for d in DAYS:
        for t in TIME_SLOTS:
            for a in ACTIVITIES:
                required = demand_param.get((d, t, a), 0)

                if required > 0:
                    solver.Add(
                        sum(x[e, a, d, t] for e in EMPLOYEES)
                        + unmet[d, t, a]
                        == required
                    )
                else:
                    solver.Add(
                        sum(x[e, a, d, t] for e in EMPLOYEES) == 0
                    )

    # =========================
    # OBJECTIVE
    # =========================

    objective_terms = []

    # Main objective: minimize weighted unmet demand
    for (d, t, a), var in unmet.items():
        objective_terms.append(1000 * priority[a] * var)

    # Secondary objective: avoid unnecessary working days
    for e in EMPLOYEES:
        for d in DAYS:
            objective_terms.append(5 * z[e, d])

    # Small assignment cost to avoid unnecessary work
    for e in EMPLOYEES:
        for a in ACTIVITIES:
            for d in DAYS:
                for t in TIME_SLOTS:
                    objective_terms.append(x[e, a, d, t])

    solver.Minimize(sum(objective_terms))

    # =========================
    # SOLVE
    # =========================

    status = solver.Solve()

    if status not in [pywraplp.Solver.OPTIMAL, pywraplp.Solver.FEASIBLE]:
        return pd.DataFrame(), pd.DataFrame(), {
            "status": "No feasible solution",
            "objective_value": None,
            "total_assigned_hours": 0,
            "total_unmet_workers": None,
            "demand_fulfillment_rate": 0,
        }

    # =========================
    # CREATE OUTPUTS
    # =========================

    schedule_rows = []

    for e in EMPLOYEES:
        for d in DAYS:
            for t in TIME_SLOTS:
                for a in ACTIVITIES:
                    if x[e, a, d, t].solution_value() > 0.5:
                        schedule_rows.append([e, d, t, a])

    schedule = pd.DataFrame(
        schedule_rows,
        columns=["employee_id", "day", "time_slot", "activity_id"]
    )

    if not schedule.empty:
        schedule = schedule.merge(employees, on="employee_id", how="left")
        schedule = schedule.merge(activities, on="activity_id", how="left")

    unmet_rows = []

    for (d, t, a), var in unmet.items():
        value = var.solution_value()

        if value > 0:
            unmet_rows.append([d, t, a, value])

    unmet_df = pd.DataFrame(
        unmet_rows,
        columns=["day", "time_slot", "activity_id", "unmet_workers"]
    )

    if not unmet_df.empty:
        unmet_df = unmet_df.merge(activities, on="activity_id", how="left")

    # =========================
    # KPIs
    # =========================

    total_required = sum(demand_param.values())
    total_unmet = 0 if unmet_df.empty else unmet_df["unmet_workers"].sum()
    total_assigned = len(schedule)

    fulfillment_rate = (
        (total_required - total_unmet) / total_required
        if total_required > 0 else 0
    )

    status_text = (
        "Optimal"
        if status == pywraplp.Solver.OPTIMAL
        else "Feasible"
    )

    kpis = {
        "status": status_text,
        "objective_value": solver.Objective().Value(),
        "total_required_workers": total_required,
        "total_assigned_hours": total_assigned,
        "total_unmet_workers": total_unmet,
        "demand_fulfillment_rate": fulfillment_rate,
        "employees_used": schedule["employee_id"].nunique() if not schedule.empty else 0,
        "activities_covered": schedule["activity_id"].nunique() if not schedule.empty else 0,
    }

    return schedule, unmet_df, kpis


if __name__ == "__main__":
    schedule, unmet_df, kpis = solve_schedule()

    print("\n=== KPIs ===")
    for key, value in kpis.items():
        print(f"{key}: {value}")

    print("\n=== SCHEDULE SAMPLE ===")
    print(schedule.head(30))

    print("\n=== UNMET DEMAND ===")
    print(unmet_df)

    schedule.to_csv("data/optimized_schedule.csv", index=False)
    unmet_df.to_csv("data/unmet_demand.csv", index=False)

    print("\nFiles exported:")
    print("data/optimized_schedule.csv")
    print("data/unmet_demand.csv")