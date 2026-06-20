import sqlite3
from datetime import datetime, timedelta
from pathlib import Path
import random

import numpy as np
import pandas as pd


def resolve_base_dir() -> Path:
    """
    Find the project root by walking upward until we find a folder that already
    contains a `data` directory. If none exists, fall back to the script folder.
    """
    script_dir = Path(__file__).resolve().parent
    for candidate in [script_dir, *script_dir.parents]:
        if (candidate / "data").exists():
            return candidate
    return script_dir


BASE_DIR = resolve_base_dir()

RAW_DIR = BASE_DIR / "data" / "raw"
MANUALS_DIR = RAW_DIR / "manuals"
TICKETS_DIR = RAW_DIR / "tickets"
STRUCTURED_DIR = RAW_DIR / "structured"
PROCESSED_DIR = BASE_DIR / "data" / "processed"

DB_PATH = PROCESSED_DIR / "plantops.db"

random.seed(42)
np.random.seed(42)

MACHINES = [
    {
        "machine_id": "PKG-L3",
        "machine_name": "Line 3 Packaging Machine",
        "machine_type": "Packaging",
        "criticality": "High",
        "location": "Plant A - Line 3",
    },
    {
        "machine_id": "CNV-B2",
        "machine_name": "Conveyor Belt B2",
        "machine_type": "Conveyor",
        "criticality": "Medium",
        "location": "Plant A - Transfer Zone",
    },
    {
        "machine_id": "MIX-R1",
        "machine_name": "Mixer Reactor R1",
        "machine_type": "Mixer",
        "criticality": "High",
        "location": "Plant B - Mixing Area",
    },
    {
        "machine_id": "CMP-A1",
        "machine_name": "Air Compressor A1",
        "machine_type": "Compressor",
        "criticality": "High",
        "location": "Utility Block",
    },
]

TOOLS = [
    {"tool_id": "TL-001", "tool_name": "Belt tension gauge", "qty": 3},
    {"tool_id": "TL-002", "tool_name": "Torque wrench", "qty": 5},
    {"tool_id": "TL-003", "tool_name": "Alignment ruler", "qty": 2},
    {"tool_id": "TL-004", "tool_name": "Bearing puller", "qty": 2},
    {"tool_id": "TL-005", "tool_name": "Bearing inspection light", "qty": 3},
    {"tool_id": "TL-006", "tool_name": "Pressure gauge", "qty": 2},
    {"tool_id": "TL-007", "tool_name": "Filter wrench", "qty": 2},
    {"tool_id": "TL-008", "tool_name": "Grease gun", "qty": 2},
    {"tool_id": "TL-009", "tool_name": "Flashlight", "qty": 6},
    {"tool_id": "TL-010", "tool_name": "Compressed air nozzle", "qty": 4},
]

SKILLS = [
    {"skill_id": "SK-001", "skill_name": "Mechanical Maintenance Technician"},
    {"skill_id": "SK-002", "skill_name": "Electrical Technician"},
    {"skill_id": "SK-003", "skill_name": "Lockout Tagout Certified"},
    {"skill_id": "SK-004", "skill_name": "Conveyor Alignment Training"},
    {"skill_id": "SK-005", "skill_name": "Bearing Replacement Specialist"},
    {"skill_id": "SK-006", "skill_name": "Compressed Air System Technician"},
]

TECHNICIANS = [
    {
        "tech_id": "TECH-001",
        "tech_name": "Arun Kumar",
        "skills": "SK-001|Mechanical Maintenance Technician; SK-003|Lockout Tagout Certified; SK-004|Conveyor Alignment Training",
        "shift": "Day",
        "availability": "Available",
    },
    {
        "tech_id": "TECH-002",
        "tech_name": "Priya Sharma",
        "skills": "SK-001|Mechanical Maintenance Technician; SK-005|Bearing Replacement Specialist",
        "shift": "Day",
        "availability": "Available",
    },
    {
        "tech_id": "TECH-003",
        "tech_name": "Rahul Verma",
        "skills": "SK-002|Electrical Technician; SK-003|Lockout Tagout Certified; SK-006|Compressed Air System Technician",
        "shift": "Night",
        "availability": "Busy",
    },
    {
        "tech_id": "TECH-004",
        "tech_name": "Meena Iyer",
        "skills": "SK-001|Mechanical Maintenance Technician; SK-005|Bearing Replacement Specialist; SK-006|Compressed Air System Technician",
        "shift": "Day",
        "availability": "Available",
    },
]

TECHNICIAN_SKILL_MAPPING = [
    {"tech_id": "TECH-001", "skill_id": "SK-001"},
    {"tech_id": "TECH-001", "skill_id": "SK-003"},
    {"tech_id": "TECH-001", "skill_id": "SK-004"},
    {"tech_id": "TECH-002", "skill_id": "SK-001"},
    {"tech_id": "TECH-002", "skill_id": "SK-005"},
    {"tech_id": "TECH-003", "skill_id": "SK-002"},
    {"tech_id": "TECH-003", "skill_id": "SK-003"},
    {"tech_id": "TECH-003", "skill_id": "SK-006"},
    {"tech_id": "TECH-004", "skill_id": "SK-001"},
    {"tech_id": "TECH-004", "skill_id": "SK-005"},
    {"tech_id": "TECH-004", "skill_id": "SK-006"},
]

SPARE_PARTS = [
    {
        "part_id": "SP-001",
        "part_name": "Packaging Motor Bearing Kit",
        "compatible_machine_type": "Packaging",
        "stock_qty": 4,
        "reorder_level": 2,
    },
    {
        "part_id": "SP-002",
        "part_name": "Conveyor Belt Tracking Roller",
        "compatible_machine_type": "Conveyor",
        "stock_qty": 7,
        "reorder_level": 3,
    },
    {
        "part_id": "SP-003",
        "part_name": "Motor Cooling Fan Assembly",
        "compatible_machine_type": "Packaging",
        "stock_qty": 2,
        "reorder_level": 1,
    },
    {
        "part_id": "SP-004",
        "part_name": "Compressor Intake Filter",
        "compatible_machine_type": "Compressor",
        "stock_qty": 1,
        "reorder_level": 2,
    },
    {
        "part_id": "SP-005",
        "part_name": "Mixer Agitator Bearing",
        "compatible_machine_type": "Mixer",
        "stock_qty": 3,
        "reorder_level": 1,
    },
]

MACHINE_SPARE_MAPPING = [
    {"machine_id": "PKG-L3", "part_id": "SP-001", "critical_spare": 1},
    {"machine_id": "PKG-L3", "part_id": "SP-003", "critical_spare": 1},
    {"machine_id": "CNV-B2", "part_id": "SP-002", "critical_spare": 1},
    {"machine_id": "CMP-A1", "part_id": "SP-004", "critical_spare": 1},
    {"machine_id": "MIX-R1", "part_id": "SP-005", "critical_spare": 1},
]

MAINTENANCE_HISTORY_ROWS = [
    {
        "ticket_id": "WO-2026-001",
        "machine_id": "PKG-L3",
        "opened_at": "2026-05-18T09:12:00",
        "closed_at": "2026-05-18T11:40:00",
        "symptoms": "High vibration, motor current increase, repeated jam alarm.",
        "root_cause": "Belt misalignment caused increased motor load.",
        "action_taken": (
            "Applied lockout-tagout; "
            "Inspected conveyor alignment; "
            "Adjusted tracking roller; "
            "Verified belt tension; "
            "Removed debris near rollers; "
            "Restarted machine."
        ),
        "downtime_minutes": 95,
    },
    {
        "ticket_id": "WO-2026-002",
        "machine_id": "PKG-L3",
        "opened_at": "2026-04-29T15:20:00",
        "closed_at": "2026-04-29T17:05:00",
        "symptoms": "Motor overheating and thermal trip.",
        "root_cause": "Cooling fan blocked by packaging debris.",
        "action_taken": "Cleaned motor fan and vents.",
        "downtime_minutes": 75,
    },
    {
        "ticket_id": "WO-2026-003",
        "machine_id": "CMP-A1",
        "opened_at": "2026-05-22T13:10:00",
        "closed_at": "2026-05-22T15:00:00",
        "symptoms": "Low discharge pressure during high demand.",
        "root_cause": "Clogged intake filter.",
        "action_taken": "Replaced intake filter and verified pressure recovery.",
        "downtime_minutes": 60,
    },
    {
        "ticket_id": "WO-2026-004",
        "machine_id": "MIX-R1",
        "opened_at": "2026-06-02T10:30:00",
        "closed_at": "2026-06-02T13:20:00",
        "symptoms": "High current and abnormal agitator noise.",
        "root_cause": "Bearing wear in agitator drive assembly.",
        "action_taken": "Replaced bearing and lubricated drive assembly.",
        "downtime_minutes": 130,
    },
]

TICKET_DETAILS_ROWS = [
    {
        "ticket_id": "WO-2026-001",
        "root_cause_category": "Mechanical Alignment",
        "parts_used": "SP-002 | Conveyor Belt Tracking Roller",
        "skills_used": (
            "SK-001 | Mechanical Maintenance Technician; "
            "SK-003 | Lockout Tagout Certified; "
            "SK-004 | Conveyor Alignment Training"
        ),
        "verification_result": (
            "Vibration reduced from 7.2 mm/s to 4.3 mm/s; "
            "no jam alarms observed after restart."
        ),
        "work_outcome": "Resolved",
    },
    {
        "ticket_id": "WO-2026-002",
        "root_cause_category": "Cooling System Blockage",
        "parts_used": "SP-003 | Motor Cooling Fan Assembly",
        "skills_used": "SK-001 | Mechanical Maintenance Technician",
        "verification_result": (
            "Motor temperature returned below 78°C after a 5-minute run; "
            "no thermal trip alarm recurred."
        ),
        "work_outcome": "Resolved",
    },
    {
        "ticket_id": "WO-2026-003",
        "root_cause_category": "Filter Blockage",
        "parts_used": "SP-004 | Compressor Intake Filter",
        "skills_used": "SK-001 | Mechanical Maintenance Technician; SK-006 | Compressed Air System Technician",
        "verification_result": (
            "Discharge pressure recovered to 7.1 bar; "
            "no low-pressure alarm within 30 minutes of restart."
        ),
        "work_outcome": "Resolved",
    },
    {
        "ticket_id": "WO-2026-004",
        "root_cause_category": "Bearing Wear",
        "parts_used": "SP-005 | Mixer Agitator Bearing",
        "skills_used": (
            "SK-001 | Mechanical Maintenance Technician; "
            "SK-005 | Bearing Replacement Specialist"
        ),
        "verification_result": (
            "Motor current returned below 18A; "
            "vibration reduced to 4.8 mm/s; "
            "no overload alarm after restart."
        ),
        "work_outcome": "Resolved",
    },
]

TICKET_EXTRAS = {
    "WO-2026-001": {
        "tools_used": [
            "TL-001 | Belt tension gauge",
            "TL-003 | Alignment ruler",
            "TL-002 | Torque wrench",
            "TL-009 | Flashlight",
        ],
        "parts_used": ["SP-002 | Conveyor Belt Tracking Roller"],
        "skills_used": [
            "SK-001 | Mechanical Maintenance Technician",
            "SK-003 | Lockout Tagout Certified",
            "SK-004 | Conveyor Alignment Training",
        ],
        "verification": [
            "Vibration reduced from 7.2 mm/s to 4.3 mm/s.",
            "No jam alarms observed.",
        ],
        "work_outcome": "Resolved",
        "duration": "95 minutes",
    },
    "WO-2026-002": {
        "tools_used": [
            "TL-010 | Compressed air nozzle",
            "TL-009 | Flashlight",
        ],
        "parts_used": ["SP-003 | Motor Cooling Fan Assembly"],
        "skills_used": ["SK-001 | Mechanical Maintenance Technician"],
        "verification": [
            "Motor temperature returned below 78°C after a 5-minute run.",
            "No thermal trip alarm recurred.",
        ],
        "work_outcome": "Resolved",
        "duration": "75 minutes",
    },
    "WO-2026-003": {
        "tools_used": [
            "TL-006 | Pressure gauge",
            "TL-007 | Filter wrench",
        ],
        "parts_used": ["SP-004 | Compressor Intake Filter"],
        "skills_used": [
            "SK-001 | Mechanical Maintenance Technician",
            "SK-006 | Compressed Air System Technician",
        ],
        "verification": [
            "Discharge pressure recovered to 7.1 bar.",
            "No low-pressure alarm within 30 minutes of restart.",
        ],
        "work_outcome": "Resolved",
        "duration": "60 minutes",
    },
    "WO-2026-004": {
        "tools_used": [
            "TL-004 | Bearing puller",
            "TL-002 | Torque wrench",
            "TL-008 | Grease gun",
        ],
        "parts_used": ["SP-005 | Mixer Agitator Bearing"],
        "skills_used": [
            "SK-001 | Mechanical Maintenance Technician",
            "SK-005 | Bearing Replacement Specialist",
        ],
        "verification": [
            "Motor current returned below 18A.",
            "Vibration reduced to 4.8 mm/s.",
            "No overload alarm after restart.",
        ],
        "work_outcome": "Resolved",
        "duration": "130 minutes",
    },
}


def ensure_dirs() -> None:
    MANUALS_DIR.mkdir(parents=True, exist_ok=True)
    TICKETS_DIR.mkdir(parents=True, exist_ok=True)
    STRUCTURED_DIR.mkdir(parents=True, exist_ok=True)
    PROCESSED_DIR.mkdir(parents=True, exist_ok=True)


def write_text_file(path: Path, content: str) -> None:
    path.write_text(content.strip() + "\n", encoding="utf-8")


def format_bullets(items: list[str]) -> str:
    return "\n".join(f"- {item}" for item in items)


def generate_manuals() -> None:
    packaging_manual = """
    # Packaging Machine Maintenance Manual

    Machine Family: Automated Packaging Machines
    Applicable Machine: PKG-L3 Line 3 Packaging Machine

    ## 1. Normal Operating Range

    The packaging machine motor temperature should normally remain between 45°C and 78°C.
    Motor current should remain between 8A and 13A during steady load.
    Vibration should remain below 5.0 mm/s during normal operation.

    ## 2. Overheating Symptoms

    Possible symptoms of motor overheating include:
    - Motor temperature greater than 85°C
    - Motor current greater than 15A
    - Repeated jam alarms
    - Burning smell near the motor housing
    - Machine stoppage after short operating cycles

    ## 3. Likely Causes of Motor Overheating

    The most common causes are:
    1. Belt misalignment
    2. Excessive belt tension
    3. Bearing lubrication failure
    4. Blocked cooling fan
    5. Overloaded packaging feed

    When vibration is high and motor current rises together,
    belt misalignment or bearing wear should be inspected first.

    ## 4. Maintenance Procedure For Belt Misalignment

    Step 1: Stop the machine from the HMI.
    Step 2: Apply lockout-tagout procedure.
    Step 3: Inspect conveyor belt alignment.
    Step 4: Verify belt tension using approved belt tension gauge.
    Step 5: Adjust tracking rollers as required.
    Step 6: Inspect motor bearings.
    Step 7: Clean cooling fan and air vents.
    Step 8: Restart machine under observation.

    ### Required Tools

    - Belt tension gauge
    - Alignment ruler
    - Torque wrench
    - Flashlight

    ### Required Skills

    - Mechanical Maintenance Technician
    - Conveyor Alignment Training

    ### Verification Procedure

    - Run machine for 5 minutes.
    - Observe belt tracking.
    - Verify no jam alarm occurs.
    - Verify motor current returns below 13A.
    - Verify vibration remains below 5.0 mm/s.

    ### Acceptance Criteria

    - Belt tracks within roller centerline.
    - Motor temperature remains below 78°C.
    - Vibration remains below 5.0 mm/s.
    - No overload alarm occurs.

    ### Estimated Duration

    30-45 minutes

    ### Escalation Rule

    If motor temperature remains above 98°C for more than 10 minutes after inspection,
    escalate to the maintenance supervisor.
    """

    conveyor_sop = """
    # Conveyor Maintenance SOP

    Applicable Machines: CNV-B2 and packaging feed conveyors

    ## 1. Safety Requirement

    Before performing any conveyor inspection, technicians must:
    - Stop the conveyor from the control panel
    - Apply lockout-tagout
    - Confirm zero stored mechanical energy
    - Wear cut-resistant gloves
    - Wear safety glasses

    ## 2. Belt Misalignment

    Belt misalignment may cause:
    - Increased vibration
    - Higher motor load
    - Uneven belt wear
    - Repeated jam alarms
    - Product accumulation at transfer points

    ### Inspection Procedure

    1. Check belt tracking position.
    2. Inspect roller alignment.
    3. Inspect tension adjustment bolts.
    4. Inspect bearing condition.
    5. Remove foreign material.

    ### Corrective Procedure

    1. Adjust tracking rollers.
    2. Adjust belt tension gradually.
    3. Verify belt centering.
    4. Run conveyor at low speed.

    ### Required Tools

    - Belt tension gauge
    - Alignment ruler
    - Bearing inspection light

    ### Required Skills

    - Mechanical Maintenance Technician
    - Conveyor Alignment Training

    ### Verification Procedure

    - Conveyor runs continuously for 5 minutes.
    - Belt remains centered.
    - No abnormal vibration observed.

    ### Acceptance Criteria

    - Vibration remains below 6.0 mm/s.
    - No jam alarms occur.
    - Belt remains within tracking limits.

    ### Estimated Duration

    20-30 minutes
    """

    safety_sop = """
    # Lockout Tagout Safety SOP

    ## 1. Purpose

    This SOP prevents accidental machine startup during maintenance.

    ## 2. Required Before Maintenance

    Before opening guards, covers, or electrical panels:
    1. Notify affected operators.
    2. Stop the machine using the normal stop command.
    3. Isolate electrical energy.
    4. Apply lockout device.
    5. Apply visible tag.
    6. Verify zero energy state.
    7. Only then begin maintenance.

    ### Required PPE

    - Safety glasses
    - Cut resistant gloves
    - Safety shoes
    - Hearing protection

    ### Required Competency

    - Lockout Tagout Certification
    - Authorized Maintenance Personnel

    ## 3. Prohibited Actions

    Technicians must not:
    - Open motor panels while machine is energized.
    - Bypass safety guards.
    - Restart machine while another technician is inspecting moving parts.
    - Perform belt adjustment while the conveyor is running.

    ## 4. High Risk Actions

    The following require supervisor approval:
    - Motor replacement
    - Electrical panel modification
    - Safety interlock bypass
    - Restart after repeated thermal trip
    """

    compressor_manual = """
    # Air Compressor A1 Maintenance Guide

    Applicable Machine: CMP-A1

    ## 1. Normal Operating Range

    Discharge pressure should remain between 6.0 and 8.5 bar.
    Oil temperature should remain below 82°C.
    Vibration should remain below 4.5 mm/s.

    ## 2. Pressure Drop

    Possible causes of pressure drop:
    - Air leak in downstream line
    - Clogged intake filter
    - Worn compressor valve
    - Faulty pressure sensor
    - Excessive demand from connected equipment

    ## 3. Recommended Troubleshooting

    Inspect air leaks using ultrasonic leak detector.
    Check intake filter differential pressure.
    Verify pressure sensor calibration.
    Review demand pattern from connected production lines.

    ## 4. Escalation

    If pressure falls below 5.5 bar for more than 15 minutes,
    notify utility maintenance lead.
    """

    mixer_manual = """
    # Mixer Reactor R1 Operating and Maintenance Manual

    Applicable Machine: MIX-R1

    ## 1. Normal Range

    Mixer motor current should remain below 18A.
    Vibration should remain below 5.5 mm/s.
    Process temperature should remain within recipe limits.

    ## 2. Agitator Overload

    Agitator overload may happen due to:
    - Higher material viscosity
    - Foreign object in vessel
    - Bearing wear
    - Shaft misalignment
    - Incorrect batch loading

    ## 3. Symptoms

    Symptoms include:
    - Motor current above 22A
    - High vibration
    - Reduced mixing speed
    - Overload alarm
    - Abnormal noise from drive assembly

    ## 4. Action

    Stop mixer.
    Verify batch recipe.
    Inspect for mechanical obstruction.
    Check bearing housing.
    Escalate if overload repeats after restart.
    """

    write_text_file(MANUALS_DIR / "packing_machine_manual.md", packaging_manual)
    write_text_file(MANUALS_DIR / "conveyor_maintenance_sop.md", conveyor_sop)
    write_text_file(MANUALS_DIR / "lockout_tagout_safety_sop.md", safety_sop)
    write_text_file(MANUALS_DIR / "compressor_a1_maintenance_guide.md", compressor_manual)
    write_text_file(MANUALS_DIR / "mixer_reactor_r1_manual.md", mixer_manual)


def generate_machine_master() -> pd.DataFrame:
    df = pd.DataFrame(MACHINES)
    df.to_csv(STRUCTURED_DIR / "machine_master.csv", index=False)
    return df


def generate_sensor_logs() -> pd.DataFrame:
    rows = []

    start_time = datetime(2026, 6, 10, 8, 0, 0)
    intervals = 12 * 60  # 12 hours, 1-minute interval

    for machine in MACHINES:
        machine_id = machine["machine_id"]

        for i in range(intervals):
            ts = start_time + timedelta(minutes=i)

            temperature = np.random.normal(65, 4)
            vibration = np.random.normal(3.2, 0.6)
            current = np.random.normal(10.5, 1.0)
            pressure = np.random.normal(6.8, 0.3)

            status = "normal"

            # Inject incident pattern for PKG-L3 between 10:35 and 11:10
            if machine_id == "PKG-L3" and datetime(2026, 6, 10, 10, 35) <= ts <= datetime(2026, 6, 10, 11, 10):
                minutes_since_start = (ts - datetime(2026, 6, 10, 10, 35)).seconds / 60
                temperature = 78 + minutes_since_start * 0.45 + np.random.normal(0, 1.2)
                vibration = 5.2 + minutes_since_start * 0.08 + np.random.normal(0, 0.4)
                current = 13.5 + minutes_since_start * 0.12 + np.random.normal(0, 0.5)
                pressure = np.random.normal(6.7, 0.2)

                if temperature > 85 or vibration > 6.0 or current > 15:
                    status = "warning"

                if temperature > 90 or vibration > 7.5 or current > 17:
                    status = "critical"

            # Inject compressor pressure drop
            if machine_id == "CMP-A1" and datetime(2026, 6, 10, 14, 15) <= ts <= datetime(2026, 6, 10, 14, 50):
                pressure = 6.5 - ((ts - datetime(2026, 6, 10, 14, 15)).seconds / 60) * 0.04 + np.random.normal(0, 0.1)
                temperature = np.random.normal(75, 2)
                vibration = np.random.normal(4.0, 0.4)
                current = np.random.normal(12.0, 1.0)

                if pressure < 5.8:
                    status = "warning"
                if pressure < 5.3:
                    status = "critical"

            rows.append(
                {
                    "machine_id": machine_id,
                    "timestamp": ts.isoformat(),
                    "temperature_c": round(float(temperature), 2),
                    "vibration_mm_s": round(float(vibration), 2),
                    "current_a": round(float(current), 2),
                    "pressure_bar": round(float(pressure), 2),
                    "status": status,
                }
            )

    df = pd.DataFrame(rows)
    df.to_csv(STRUCTURED_DIR / "sensor_logs.csv", index=False)
    return df


def generate_alarm_events() -> pd.DataFrame:
    rows = [
        {
            "alarm_id": "ALM-1001",
            "machine_id": "PKG-L3",
            "timestamp": "2026-06-10T10:43:00",
            "severity": "warning",
            "alarm_code": "MOTOR_TEMP_HIGH",
            "message": "Motor temperature exceeded warning threshold.",
        },
        {
            "alarm_id": "ALM-1002",
            "machine_id": "PKG-L3",
            "timestamp": "2026-06-10T10:49:00",
            "severity": "warning",
            "alarm_code": "VIBRATION_HIGH",
            "message": "Vibration level exceeded normal operating range.",
        },
        {
            "alarm_id": "ALM-1003",
            "machine_id": "PKG-L3",
            "timestamp": "2026-06-10T10:56:00",
            "severity": "critical",
            "alarm_code": "MOTOR_OVERLOAD",
            "message": "Motor current exceeded overload threshold.",
        },
        {
            "alarm_id": "ALM-1004",
            "machine_id": "PKG-L3",
            "timestamp": "2026-06-10T11:02:00",
            "severity": "critical",
            "alarm_code": "MACHINE_STOPPED",
            "message": "Packaging machine stopped due to thermal protection trip.",
        },
        {
            "alarm_id": "ALM-2001",
            "machine_id": "CMP-A1",
            "timestamp": "2026-06-10T14:32:00",
            "severity": "warning",
            "alarm_code": "PRESSURE_LOW",
            "message": "Compressor discharge pressure below warning threshold.",
        },
        {
            "alarm_id": "ALM-2002",
            "machine_id": "CMP-A1",
            "timestamp": "2026-06-10T14:47:00",
            "severity": "critical",
            "alarm_code": "PRESSURE_CRITICAL",
            "message": "Compressor discharge pressure below critical threshold.",
        },
    ]

    df = pd.DataFrame(rows)
    df.to_csv(STRUCTURED_DIR / "alarm_events.csv", index=False)
    return df


def generate_maintenance_history() -> pd.DataFrame:
    df = pd.DataFrame(MAINTENANCE_HISTORY_ROWS)
    df.to_csv(STRUCTURED_DIR / "maintenance_history.csv", index=False)
    return df


def generate_maintenance_ticket_details() -> pd.DataFrame:
    df = pd.DataFrame(TICKET_DETAILS_ROWS)
    df.to_csv(STRUCTURED_DIR / "maintenance_ticket_details.csv", index=False)
    return df


def generate_spare_parts_inventory() -> pd.DataFrame:
    df = pd.DataFrame(SPARE_PARTS)
    df.to_csv(STRUCTURED_DIR / "spare_parts_inventory.csv", index=False)
    return df


def generate_technician_skills() -> pd.DataFrame:
    df = pd.DataFrame(SKILLS)
    df.to_csv(STRUCTURED_DIR / "technician_skills.csv", index=False)
    return df


def generate_technicians() -> pd.DataFrame:
    df = pd.DataFrame(TECHNICIANS)
    df.to_csv(STRUCTURED_DIR / "technicians.csv", index=False)
    return df


def generate_technician_skill_mapping() -> pd.DataFrame:
    df = pd.DataFrame(TECHNICIAN_SKILL_MAPPING)
    df.to_csv(STRUCTURED_DIR / "technician_skill_mapping.csv", index=False)
    return df


def generate_machine_spare_mapping() -> pd.DataFrame:
    df = pd.DataFrame(MACHINE_SPARE_MAPPING)
    df.to_csv(STRUCTURED_DIR / "machine_spare_mapping.csv", index=False)
    return df


def generate_tool_inventory() -> pd.DataFrame:
    df = pd.DataFrame(TOOLS)
    df.to_csv(STRUCTURED_DIR / "tool_inventory.csv", index=False)
    return df


def generate_ticket_text_files(maintenance_df: pd.DataFrame) -> None:
    details_df = pd.DataFrame(TICKET_DETAILS_ROWS).set_index("ticket_id")

    for _, row in maintenance_df.iterrows():
        tid = row["ticket_id"]
        extras = TICKET_EXTRAS.get(tid, {})
        details = details_df.loc[tid].to_dict() if tid in details_df.index else {}

        tools_section = format_bullets(extras.get("tools_used", ["- Not recorded"]))
        parts_section = format_bullets(extras.get("parts_used", ["- Not recorded"]))
        skills_section = format_bullets(extras.get("skills_used", ["- Not recorded"]))
        verification_section = format_bullets(extras.get("verification", ["- Not recorded"]))
        duration_section = extras.get("duration", f"{row['downtime_minutes']} minutes")
        work_outcome = extras.get("work_outcome", details.get("work_outcome", "Not recorded"))
        root_cause_category = details.get("root_cause_category", "Not recorded")

        content = f"""
        # Maintenance Ticket {row['ticket_id']}

        Machine ID: {row['machine_id']}
        Opened At: {row['opened_at']}
        Closed At: {row['closed_at']}

        ## Symptoms

        {row['symptoms']}

        ## Root Cause

        {row['root_cause']}

        ## Root Cause Category

        {root_cause_category}

        ## Action Taken

        {row['action_taken']}

        ## Parts Used

        {parts_section}

        ## Skills Used

        {skills_section}

        ## Tools Used

        {tools_section}

        ## Verification Result

        {verification_section}

        ## Work Outcome

        {work_outcome}

        ## Duration

        {duration_section}

        ## Downtime

        {row['downtime_minutes']} minutes
        """

        write_text_file(TICKETS_DIR / f"{row['ticket_id']}.md", content)


def create_sqlite_database(
    machine_df: pd.DataFrame,
    sensor_df: pd.DataFrame,
    alarm_df: pd.DataFrame,
    maintenance_df: pd.DataFrame,
    maintenance_ticket_details_df: pd.DataFrame,
    inventory_df: pd.DataFrame,
    skills_df: pd.DataFrame,
    technicians_df: pd.DataFrame,
    technician_skill_mapping_df: pd.DataFrame,
    machine_spare_mapping_df: pd.DataFrame,
    tools_df: pd.DataFrame,
) -> None:
    if DB_PATH.exists():
        DB_PATH.unlink()

    conn = sqlite3.connect(DB_PATH)

    machine_df.to_sql("machine_master", conn, index=False, if_exists="replace")
    sensor_df.to_sql("sensor_logs", conn, index=False, if_exists="replace")
    alarm_df.to_sql("alarm_events", conn, index=False, if_exists="replace")
    maintenance_df.to_sql("maintenance_history", conn, index=False, if_exists="replace")
    maintenance_ticket_details_df.to_sql("maintenance_ticket_details", conn, index=False, if_exists="replace")
    inventory_df.to_sql("spare_parts_inventory", conn, index=False, if_exists="replace")
    skills_df.to_sql("technician_skills", conn, index=False, if_exists="replace")
    technicians_df.to_sql("technicians", conn, index=False, if_exists="replace")
    technician_skill_mapping_df.to_sql("technician_skill_mapping", conn, index=False, if_exists="replace")
    machine_spare_mapping_df.to_sql("machine_spare_mapping", conn, index=False, if_exists="replace")
    tools_df.to_sql("tool_inventory", conn, index=False, if_exists="replace")

    conn.close()


def main() -> None:
    ensure_dirs()

    print("Generating manuals and SOPs...")
    generate_manuals()

    print("Generating machine master...")
    machine_df = generate_machine_master()

    print("Generating sensor logs...")
    sensor_df = generate_sensor_logs()

    print("Generating alarm events...")
    alarm_df = generate_alarm_events()

    print("Generating maintenance history...")
    maintenance_df = generate_maintenance_history()

    print("Generating maintenance ticket details...")
    maintenance_ticket_details_df = generate_maintenance_ticket_details()

    print("Generating spare parts inventory...")
    inventory_df = generate_spare_parts_inventory()

    print("Generating technician skills...")
    skills_df = generate_technician_skills()

    print("Generating technicians...")
    technicians_df = generate_technicians()

    print("Generating technician-skill mapping...")
    technician_skill_mapping_df = generate_technician_skill_mapping()

    print("Generating machine-spare mapping...")
    machine_spare_mapping_df = generate_machine_spare_mapping()

    print("Generating tool inventory...")
    tools_df = generate_tool_inventory()

    print("Generating ticket text files...")
    generate_ticket_text_files(maintenance_df)

    print("Creating SQLite database...")
    create_sqlite_database(
        machine_df=machine_df,
        sensor_df=sensor_df,
        alarm_df=alarm_df,
        maintenance_df=maintenance_df,
        maintenance_ticket_details_df=maintenance_ticket_details_df,
        inventory_df=inventory_df,
        skills_df=skills_df,
        technicians_df=technicians_df,
        technician_skill_mapping_df=technician_skill_mapping_df,
        machine_spare_mapping_df=machine_spare_mapping_df,
        tools_df=tools_df,
    )

    print("\nDataset generation complete.")
    print(f"Manuals: {MANUALS_DIR}")
    print(f"Tickets: {TICKETS_DIR}")
    print(f"Structured CSV files: {STRUCTURED_DIR}")
    print(f"SQLite DB: {DB_PATH}")


if __name__ == "__main__":
    main()
