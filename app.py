from datetime import datetime, timedelta

import pandas as pd
import streamlit as st

from src.database.sql_tools import PlantOpsSQLTool


STAGE_LABELS = {
    "investigator": "Incident telemetry investigated",
    "knowledge": "Knowledge retrieved",
    "evidence_synthesizer": "Evidence packaged",
    "evidence_analyst": "Evidence analyzed",
    "rca": "Root cause determined",
    "safety_agent": "Safety controls generated",
    "work_order_agent": "Work order created",
    "resource_planner": "Resources matched"
}


@st.cache_resource
def get_sql_tool():
    return PlantOpsSQLTool()


@st.cache_resource
def get_graph():
    from src.agents.graph.plantops_graph import graph

    return graph


@st.cache_data
def load_machines():
    return get_sql_tool().list_machines()


@st.cache_data
def load_time_bounds(machine_id):
    return get_sql_tool().get_machine_time_bounds(
        machine_id
    )


def clear_current_result():
    st.session_state.pop(
        "plantops_result",
        None
    )
    st.session_state.pop(
        "plantops_result_meta",
        None
    )


def inject_styles():
    st.markdown(
        """
        <style>
        .block-container {
            max-width: 1500px;
            padding-top: 1.5rem;
            padding-bottom: 3rem;
        }

        .plantops-hero {
            padding: 1.5rem 1.75rem;
            margin-bottom: 1.5rem;
            border: 1px solid rgba(245, 158, 11, 0.35);
            border-radius: 16px;
            background:
                linear-gradient(
                    135deg,
                    rgba(245, 158, 11, 0.15),
                    rgba(30, 41, 59, 0.45)
                );
        }

        .plantops-hero h1 {
            margin: 0;
            font-size: 2.2rem;
        }

        .plantops-hero p {
            margin: 0.5rem 0 0;
            opacity: 0.8;
        }

        [data-testid="stMetric"] {
            padding: 1rem;
            border: 1px solid rgba(148, 163, 184, 0.2);
            border-radius: 12px;
            background: rgba(30, 41, 59, 0.25);
        }

        [data-testid="stMetricValue"] {
            font-size: 1.25rem;
        }

        [data-testid="stSidebar"] {
            border-right: 1px solid
                rgba(148, 163, 184, 0.18);
        }
        </style>
        """,
        unsafe_allow_html=True
    )


def render_cited_items(
    items,
    empty_message
):
    if not items:
        st.info(empty_message)
        return

    for index, item in enumerate(
        items,
        start=1
    ):
        st.markdown(
            f"**{index}. {item.get('text', '')}**"
        )
        st.caption(
            item.get("citation", "No citation")
        )


def render_string_list(
    items,
    empty_message
):
    if not items:
        st.info(empty_message)
        return

    for item in items:
        st.markdown(f"- {item}")


def run_pipeline(input_state):
    graph = get_graph()
    result = dict(input_state)
    completed_stages = set()

    with st.status(
        "Running PlantOps investigation...",
        expanded=True
    ) as status:
        status.write(
            "Incident request accepted"
        )

        try:
            events = graph.stream(
                input_state,
                stream_mode="updates"
            )

            for event in events:
                if not isinstance(event, dict):
                    continue

                for node_name, node_update in event.items():
                    if isinstance(node_update, dict):
                        result.update(node_update)

                    if node_name in completed_stages:
                        continue

                    completed_stages.add(node_name)

                    label = STAGE_LABELS.get(
                        node_name,
                        node_name.replace("_", " ").title()
                    )

                    status.write(f"✅ {label}")

            status.update(
                label="Investigation complete",
                state="complete",
                expanded=False
            )

            return result

        except Exception:
            status.update(
                label="Investigation failed",
                state="error",
                expanded=True
            )
            raise


def render_incident_data(result):
    context = result.get(
        "incident_context",
        {}
    )

    machine = context.get(
        "machine_info",
        {}
    ).get("machine", {})

    if machine:
        st.subheader("Machine information")

        machine_columns = st.columns(4)

        machine_columns[0].metric(
            "Machine",
            machine.get("machine_id", "Unknown")
        )
        machine_columns[1].metric(
            "Type",
            machine.get("machine_type", "Unknown")
        )
        machine_columns[2].metric(
            "Criticality",
            machine.get("criticality", "Unknown")
        )
        machine_columns[3].metric(
            "Location",
            machine.get("location", "Unknown")
        )

    sensor_summary = context.get(
        "sensor_summary",
        {}
    )

    st.subheader("Telemetry summary")

    stats_rows = []

    for metric, values in sensor_summary.get(
        "stats",
        {}
    ).items():
        stats_rows.append(
            {
                "Metric": metric,
                "Minimum": values.get("min"),
                "Maximum": values.get("max"),
                "Mean": values.get("mean"),
                "First": values.get("first"),
                "Last": values.get("last"),
                "Change": values.get("change")
            }
        )

    if stats_rows:
        st.dataframe(
            pd.DataFrame(stats_rows),
            hide_index=True,
            use_container_width=True
        )
    else:
        st.info("No telemetry summary is available.")

    st.subheader("Operating-limit violations")

    violations = sensor_summary.get(
        "limit_violations",
        []
    )

    if violations:
        st.dataframe(
            pd.DataFrame(violations),
            hide_index=True,
            use_container_width=True
        )
    else:
        st.success(
            "No configured operating-limit violations."
        )

    st.subheader("Alarm timeline")

    alarms = context.get("alarms", [])

    if alarms:
        st.dataframe(
            pd.DataFrame(alarms),
            hide_index=True,
            use_container_width=True
        )
    else:
        st.info(
            "No alarms occurred during this window."
        )


def render_rca(result):
    report = result["rca_report"]

    st.subheader("Incident summary")
    st.write(report["incident_summary"])

    st.subheader("Likely root cause")

    with st.container(border=True):
        st.markdown(
            f"### {report['likely_root_cause']}"
        )

    st.subheader("Supporting evidence")
    render_string_list(
        report.get("supporting_evidence", []),
        "No supporting evidence was returned."
    )

    st.subheader("Contradictory evidence")
    render_string_list(
        report.get("contradictory_evidence", []),
        "No contradictory evidence was identified."
    )

    st.subheader("Recommendations")
    render_string_list(
        report.get("recommendations", []),
        "No recommendations were generated."
    )

    st.subheader("Citations")
    render_string_list(
        report.get("citations", []),
        "No citations were returned."
    )


def render_safety(result):
    report = result["safety_report"]

    st.subheader("Required safety steps")
    render_cited_items(
        report.get("required_safety_steps", []),
        "No required safety steps were identified."
    )

    st.subheader("Required PPE")
    render_cited_items(
        report.get("required_ppe", []),
        "No PPE requirements were identified."
    )

    st.subheader("Prohibited actions")
    render_cited_items(
        report.get("prohibited_actions", []),
        "No prohibited actions were identified."
    )

    st.subheader("Supervisor approval")
    render_cited_items(
        report.get(
            "supervisor_approval_required",
            []
        ),
        "Supervisor approval is not required."
    )


def render_work_order(result):
    report = result["work_order_report"]

    st.markdown(
        f"## {report.get('work_order_title', 'Work Order')}"
    )

    columns = st.columns(2)

    columns[0].metric(
        "Priority",
        report.get("priority", "Unknown")
    )
    columns[1].metric(
        "Estimated duration",
        report.get("estimated_duration", "Unknown")
    )

    st.subheader("Maintenance steps")
    render_cited_items(
        report.get("maintenance_steps", []),
        "No maintenance steps were generated."
    )

    st.subheader("Required tools")
    render_cited_items(
        report.get("required_tools", []),
        "No required tools were identified."
    )

    st.subheader("Required skills")
    render_cited_items(
        report.get("required_skills", []),
        "No required skills were identified."
    )

    st.subheader("Safety requirements")
    render_cited_items(
        report.get("safety_requirements", []),
        "No safety requirements were identified."
    )

    st.subheader("Success criteria")
    render_cited_items(
        report.get("success_criteria", []),
        "No success criteria were identified."
    )


def render_resources(result):
    plan = result["resource_plan"]

    warnings = plan.get(
        "resource_warnings",
        []
    )

    if warnings:
        for warning in warnings:
            st.warning(warning)
    else:
        st.success(
            "All required tools and skills are available."
        )

    st.subheader("Matched tools")

    tools = plan.get("matched_tools", [])

    if tools:
        st.dataframe(
            pd.DataFrame(tools),
            hide_index=True,
            use_container_width=True
        )
    else:
        st.info("No tools were matched.")

    st.subheader("Matched skills")

    skills = plan.get("matched_skills", [])

    if skills:
        st.dataframe(
            pd.DataFrame(skills),
            hide_index=True,
            use_container_width=True
        )
    else:
        st.info("No skills were matched.")

    st.subheader("Technician candidates")

    technicians = plan.get(
        "technician_candidates",
        []
    )

    if technicians:
        technician_rows = []

        for technician in technicians:
            technician_rows.append(
                {
                    "ID": technician["tech_id"],
                    "Name": technician["tech_name"],
                    "Shift": technician["shift"],
                    "Availability":
                        technician["availability"],
                    "Matched skills": ", ".join(
                        technician["matched_skills"]
                    ),
                    "Covers all skills":
                        technician[
                            "covers_all_required_skills"
                        ],
                    "Eligible": technician["eligible"]
                }
            )

        st.dataframe(
            pd.DataFrame(technician_rows),
            hide_index=True,
            use_container_width=True
        )
    else:
        st.info(
            "No technician candidates were found."
        )

    st.subheader("Compatible spare parts")
    st.caption(
        "These parts are compatible with the machine. "
        "Replacement is not automatically required."
    )

    spare_parts = plan.get(
        "compatible_spare_parts",
        []
    )

    if spare_parts:
        st.dataframe(
            pd.DataFrame(spare_parts),
            hide_index=True,
            use_container_width=True
        )
    else:
        st.info(
            "No compatible spare parts were found."
        )


def render_result(result):
    rca = result["rca_report"]
    work_order = result["work_order_report"]
    resource_plan = result["resource_plan"]

    eligible_technicians = [
        technician
        for technician in resource_plan.get(
            "technician_candidates",
            []
        )
        if technician.get("eligible")
    ]

    assigned_technician = (
        eligible_technicians[0]["tech_name"]
        if eligible_technicians
        else "Unassigned"
    )

    resource_warnings = resource_plan.get(
        "resource_warnings",
        []
    )

    resource_status = (
        "Ready"
        if not resource_warnings
        and eligible_technicians
        else "Review needed"
    )

    st.subheader("Incident conclusion")

    with st.container(border=True):
        st.caption("LIKELY ROOT CAUSE")
        st.markdown(
            f"### {rca.get('likely_root_cause', 'Unknown')}"
        )
        st.write(
            rca.get("incident_summary", "")
        )

    overview_columns = st.columns(4)

    overview_columns[0].metric(
        "Priority",
        work_order.get("priority", "Unknown")
    )
    overview_columns[1].metric(
        "Duration",
        work_order.get(
            "estimated_duration",
            "Unknown"
        )
    )
    overview_columns[2].metric(
        "Assigned technician",
        assigned_technician
    )
    overview_columns[3].metric(
        "Resource status",
        resource_status
    )

    tabs = st.tabs(
        [
            "Incident Data",
            "Root Cause",
            "Safety",
            "Work Order",
            "Resources"
        ]
    )

    with tabs[0]:
        render_incident_data(result)

    with tabs[1]:
        render_rca(result)

    with tabs[2]:
        render_safety(result)

    with tabs[3]:
        render_work_order(result)

    with tabs[4]:
        render_resources(result)


def main():
    st.set_page_config(
        page_title="PlantOps Copilot",
        page_icon="🏭",
        layout="wide",
        initial_sidebar_state="expanded"
    )

    inject_styles()

    st.markdown(
        """
        <div class="plantops-hero">
            <h1>🏭 PlantOps Copilot</h1>
            <p>
                Evidence-grounded incident investigation,
                root-cause analysis, safety planning and
                maintenance coordination.
            </p>
        </div>
        """,
        unsafe_allow_html=True
    )

    machines = load_machines()

    if not machines:
        st.error(
            "No machines were found. Generate the dataset first."
        )
        st.stop()

    machine_labels = {
        (
            f"{machine['machine_id']} — "
            f"{machine['machine_name']}"
        ): machine["machine_id"]
        for machine in machines
    }

    selected_label = st.sidebar.selectbox(
        "Machine",
        options=list(machine_labels),
        key="selected_machine",
        on_change=clear_current_result
    )

    machine_id = machine_labels[selected_label]
    bounds = load_time_bounds(machine_id)

    if not bounds.get("sensor_start"):
        st.error(
            f"No sensor data exists for {machine_id}."
        )
        st.stop()

    sensor_start = datetime.fromisoformat(
        bounds["sensor_start"]
    )
    sensor_end = datetime.fromisoformat(
        bounds["sensor_end"]
    )

    if bounds.get("alarm_start"):
        alarm_start = datetime.fromisoformat(
            bounds["alarm_start"]
        )
        alarm_end = datetime.fromisoformat(
            bounds["alarm_end"]
        )

        suggested_start = max(
            sensor_start,
            alarm_start - timedelta(minutes=15)
        )
        suggested_end = min(
            sensor_end,
            alarm_end + timedelta(minutes=10)
        )
    else:
        suggested_start = sensor_start
        suggested_end = sensor_end

    with st.sidebar.form(
        f"incident_form_{machine_id}"
    ):
        st.subheader("Incident investigation")

        user_query = st.text_area(
            "Incident description",
            value=(
                f"Investigate the abnormal condition "
                f"on {machine_id}."
            ),
            height=110,
            key=f"incident_description_{machine_id}"
        )

        start_date = st.date_input(
            "Start date",
            value=suggested_start.date(),
            key=f"start_date_{machine_id}"
        )

        start_clock = st.time_input(
            "Start time",
            value=suggested_start.time(),
            key=f"start_time_{machine_id}"
        )

        end_date = st.date_input(
            "End date",
            value=suggested_end.date(),
            key=f"end_date_{machine_id}"
        )

        end_clock = st.time_input(
            "End time",
            value=suggested_end.time(),
            key=f"end_time_{machine_id}"
        )

        submitted = st.form_submit_button(
            "Run investigation",
            type="primary",
            use_container_width=True
        )

    if submitted:
        clear_current_result()

        start_time = datetime.combine(
            start_date,
            start_clock
        )

        end_time = datetime.combine(
            end_date,
            end_clock
        )

        if not user_query.strip():
            st.error(
                "Enter an incident description."
            )
            st.stop()

        if start_time > end_time:
            st.error(
                "Start time must be earlier than end time."
            )
            st.stop()

        input_state = {
            "user_query": user_query.strip(),
            "machine_id": machine_id,
            "start_time": start_time.isoformat(
                timespec="seconds"
            ),
            "end_time": end_time.isoformat(
                timespec="seconds"
            )
        }

        try:
            result = run_pipeline(input_state)

            st.session_state[
                "plantops_result"
            ] = result

            st.session_state[
                "plantops_result_meta"
            ] = {
                "machine_id": machine_id,
                "start_time": input_state["start_time"],
                "end_time": input_state["end_time"]
            }

        except Exception as exc:
            clear_current_result()
            st.error(
                f"Investigation failed: {exc}"
            )

    result = st.session_state.get(
        "plantops_result"
    )

    result_meta = st.session_state.get(
        "plantops_result_meta",
        {}
    )

    if (
        result
        and result_meta.get("machine_id") == machine_id
    ):
        render_result(result)
    else:
        st.info(
            "Select a machine and incident window, "
            "then run the investigation."
        )


if __name__ == "__main__":
    main()