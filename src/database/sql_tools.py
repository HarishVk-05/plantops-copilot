import argparse
import json
import sqlite3
from pathlib import Path
from typing import Any, Dict, List, Optional

import pandas as pd

BASE_DIR = Path(__file__).resolve().parents[2]
DB_PATH = BASE_DIR / "data" / "processed" / "plantops.db"
LIMITS_PATH = BASE_DIR / "data" / "config" / "operating_limits.json"


def load_operating_limits() -> Dict[str, Any]:
    if not LIMITS_PATH.exists():
        raise FileNotFoundError(
            f"Operating limits not found at {LIMITS_PATH}"
        )
    
    with LIMITS_PATH.open("r", encoding="utf-8") as file:
        return json.load(file)
    

class PlantOpsSQLTool:
    def __init__(self, db_path: Path = DB_PATH) -> None:
        self.db_path = db_path

        if not self.db_path.exists():
            raise FileNotFoundError(
                f"Database not found at {self.db_path}. "
                "Run src/data_generation/generate_factory_data.py first."
                )

    def get_tool_inventory(self) -> List[Dict[str, Any]]:
        query = """
        SELECT
            tool_id,
            tool_name,
            qty,
            CASE
                WHEN qty <= 0 THEN 'unavailable'
                ELSE 'available'
            END AS availability
        FROM tool_inventory
        ORDER BY tool_name ASC
        """

        df = self._query_df(query)

        return df.to_dict(orient="records")


    def get_skill_catalog(self) -> List[Dict[str, Any]]:
        query = """
        SELECT skill_id, skill_name
        FROM technician_skills
        ORDER BY skill_name ASC
        """

        df = self._query_df(query)

        return df.to_dict(orient="records")


    def get_technicians_with_skills(
        self
    ) -> List[Dict[str, Any]]:
        query = """
        SELECT
            technicians.tech_id,
            technicians.tech_name,
            technicians.shift,
            technicians.availability,
            skills.skill_id,
            skills.skill_name
        FROM technicians
        LEFT JOIN technician_skill_mapping AS mapping
            ON technicians.tech_id = mapping.tech_id
        LEFT JOIN technician_skills AS skills
            ON mapping.skill_id = skills.skill_id
        ORDER BY technicians.tech_id, skills.skill_name
        """

        df = self._query_df(query)

        technicians = {}

        for row in df.to_dict(orient="records"):
            tech_id = row["tech_id"]

            if tech_id not in technicians:
                technicians[tech_id] = {
                    "tech_id": tech_id,
                    "tech_name": row["tech_name"],
                    "shift": row["shift"],
                    "availability": row["availability"],
                    "skills": []
                }

            if row.get("skill_id"):
                technicians[tech_id]["skills"].append(
                    {
                        "skill_id": row["skill_id"],
                        "skill_name": row["skill_name"]
                    }
                )

        return list(technicians.values())

    def _connect(self):
        return sqlite3.connect(self.db_path)
    
    def _query_df(self, query: str, params: Optional[List[Any]] = None) -> pd.DataFrame:
        params = params or []

        with self._connect() as conn:
            return pd.read_sql_query(query, conn, params=params)
    
    def get_machine_info(self, machine_id: str) -> Dict[str, Any]:
        query = """
        SELECT machine_id, machine_name, machine_type, criticality, location
        FROM machine_master
        WHERE machine_id = ?
        """

        df = self._query_df(query, [machine_id])

        if df.empty:
            return {
                "found": False,
                "machine_id": machine_id,
                "message": "Machine not found."
            }
    

        return {
            "found": True,
            "machine": df.iloc[0].to_dict()
        }
    
    def get_alarms(
            self,
            machine_id: str,
            start_time: Optional[str] = None,
            end_time: Optional[str] = None,
            severity: Optional[str] = None
    ) -> List[Dict[str, Any]]:
        query=  """
        SELECT alarm_id, machine_id, timestamp, severity, alarm_code, message
        FROM alarm_events
        WHERE machine_id = ?
        """

        params: List[Any] = [machine_id]

        if start_time:
            query += " AND timestamp >= ?"
            params.append(start_time)
        
        if end_time:
            query += " AND timestamp <= ?"
            params.append(end_time)
        
        if severity:
            query += " AND severity = ?"
            params.append(severity)
        
        query += " ORDER BY timestamp ASC"

        df = self._query_df(query, params)
        return df.to_dict(orient="records")
    
    def get_sensor_window(
            self,
            machine_id: str,
            start_time: str,
            end_time: str
    ) -> List[Dict[str, Any]]:
        query = """
        SELECT machine_id, timestamp, temperature_c, vibration_mm_s,
        current_a, pressure_bar, status
        FROM sensor_logs
        WHERE machine_id = ?
        AND timestamp >= ?
        AND timestamp <= ?
        ORDER BY timestamp ASC
        """

        df = self._query_df(query, [machine_id, start_time, end_time])
        return df.to_dict(orient="records")
    
    def summarize_sensor_window(
            self,
            machine_id: str,
            start_time: str,
            end_time: str
    ) -> Dict[str, Any]:
        rows = self.get_sensor_window(
            machine_id=machine_id,
            start_time=start_time,
            end_time=end_time
        )

        if not rows:
            return {
                "machine_id": machine_id,
                "start_time": start_time,
                "end_time": end_time,
                "found": False,
                "message": "No sensor data found for this window."
            }
        
        df = pd.DataFrame(rows)

        numeric_cols = [
            "temperature_c",
            "vibration_mm_s",
            "current_a",
            "pressure_bar"
        ]

        stats: Dict[str, Any] = {}

        for col in numeric_cols:
            stats[col] = {
                "min": round(float(df[col].min()), 2),
                "max": round(float(df[col].max()), 2),
                "mean": round(float(df[col].mean()), 2),
                "first": round(float(df[col].iloc[0]), 2),
                "last": round(float(df[col].iloc[-1]), 2),
                "change": round(float(df[col].iloc[-1] - df[col].iloc[0]), 2),
            }

        status_counts = df["status"].value_counts().to_dict()

        all_limits = load_operating_limits()
        machine_limits = all_limits.get(machine_id, {})

        limit_violations = []

        for metric, metric_limits in machine_limits.items():
            if metric not in df.columns:
                continue

            for severity in ["warning", "critical"]:
                limit = metric_limits.get(severity)

                if not limit:
                    continue

                operator = limit["operator"]
                threshold = limit["value"]

                if operator == ">":
                    count = int((df[metric] > threshold).sum())
                elif operator == "<":
                    count = int((df[metric] < threshold).sum())
                else:
                    continue

                if count > 0:
                    limit_violations.append(
                         {
                            "metric": metric,
                            "label": metric_limits.get(
                                "label",
                                metric
                            ),
                            "unit": metric_limits.get(
                                "unit",
                                ""
                            ),
                            "severity": severity,
                            "operator": operator,
                            "threshold": threshold,
                            "violation_count": count
                        }
                    )

        timeline = []
        
        for _, row in df.iterrows():
            if row["status"] in {"warning", "critical"}:
                timeline.append(
                    {
                        "timestamp": row["timestamp"],
                        "status": row["status"],
                        "temperature_c": row["temperature_c"],
                        "vibration_mm_s": row["vibration_mm_s"],
                        "current_a": row["current_a"],
                        "pressure_bar": row["pressure_bar"]
                    }
                )
        
        return {
            "found": True,
            "machine_id": machine_id,
            "start_time": start_time,
            "end_time": end_time,
            "row_count": len(df),
            "status_counts": status_counts,
            "stats": stats,
            "limit_violations": limit_violations,
            "abnormal_timeline": timeline[:20]
        }
    
    def get_maintenance_history(
            self,
            machine_id: Optional[str] = None,
            limit: int = 10
    ) -> List[Dict[str, Any]]:
        query = """
        SELECT ticket_id, machine_id, opened_at, closed_at, symptoms,
        root_cause, action_taken, downtime_minutes
        FROM maintenance_history
        """

        params: List[Any] = []

        if machine_id:
            query += " WHERE machine_id = ?"
            params.append(machine_id)
        
        query += " ORDER BY opened_at DESC LIMIT ?"
        params.append(limit)

        df = self._query_df(query, params)
        return df.to_dict(orient="records")
    

    def search_similar_tickets(
            self,
            keywords: str,
            machine_id: Optional[str] = None,
            limit: int = 5
    ) -> List[Dict[str, Any]]:
        terms = [
            term.strip().lower()
            for term in keywords.replace(",", " ").split()
            if len(term.strip()) >= 4
        ]

        if not terms:
            terms = [keywords.lower()]
        
        query = """
        SELECT ticket_id, machine_id, opened_at, closed_at, symptoms,
        root_cause, action_taken, downtime_minutes
        FROM maintenance_history
        WHERE 1 = 1
        """

        params: List[Any] = []

        if machine_id:
            query += " AND machine_id = ?"
            params.append(machine_id)
        
        like_clauses = []

        for term in terms:
            like_pattern = f"%{term}%"
            like_clauses.append(
                """
                (
                    LOWER(symptoms) LIKE ?
                    OR LOWER(root_cause) LIKE ?
                    OR LOWER(action_taken) LIKE ?
                )
                """
            )
            params.extend([like_pattern, like_pattern, like_pattern])
        
        if like_clauses:
            query += " AND (" + " OR ".join(like_clauses) + ")"
        
        query += " ORDER BY opened_at DESC LIMIT ?"
        params.append(limit)

        df = self._query_df(query, params)
        return df.to_dict(orient="records")
    
    def get_spare_parts_for_machine(
        self,
        machine_id: str
    ) -> List[Dict[str, Any]]:
        query = """
        SELECT
            mapping.machine_id,
            inventory.part_id,
            inventory.part_name,
            inventory.compatible_machine_type,
            inventory.stock_qty,
            inventory.reorder_level,
            mapping.critical_spare,
            CASE
                WHEN inventory.stock_qty <= 0
                    THEN 'out_of_stock'
                WHEN inventory.stock_qty <= inventory.reorder_level
                    THEN 'low_stock'
                ELSE 'available'
            END AS stock_status
        FROM machine_spare_mapping AS mapping
        JOIN spare_parts_inventory AS inventory
            ON mapping.part_id = inventory.part_id
        WHERE mapping.machine_id = ?
        ORDER BY mapping.critical_spare DESC,
                inventory.part_name ASC
        """

        df = self._query_df(query, [machine_id])

        return df.to_dict(orient="records")
    
    def list_machines(self) -> List[Dict[str, Any]]:
        query = """
        SELECT
            machine_id,
            machine_name,
            machine_type,
            criticality,
            location
        FROM machine_master
        ORDER BY machine_id
        """

        df = self._query_df(query)

        return df.to_dict(orient="records")
    
    def get_machine_time_bounds(
            self,
            machine_id: str
    ) -> Dict[str, Any]:
        sensor_query = """
        SELECT
            MIN(timestamp) AS start_time,
            MAX(timestamp) AS end_time
        FROM sensor_logs
        WHERE machine_id = ?
        """

        alarm_query = """
        SELECT
            MIN(timestamp) AS start_time,
            MAX(timestamp) AS end_time
        FROM alarm_events
        WHERE machine_id = ?
        """

        sensor_df = self._query_df(
            sensor_query,
            [machine_id]
        )

        alarm_df = self._query_df(
            alarm_query,
            [machine_id]
        )
        sensor_row = sensor_df.iloc[0].to_dict()
        alarm_row = alarm_df.iloc[0].to_dict()

        return {
            "sensor_start": sensor_row.get("start_time"),
            "sensor_end": sensor_row.get("end_time"),
            "alarm_start": alarm_row.get("start_time"),
            "alarm_end": alarm_row.get("end_time")
        }

    def build_incident_context(
            self,
            machine_id: str,
            start_time: str,
            end_time: str
    ) -> Dict[str, Any]:
        
        machine_info = self.get_machine_info(machine_id)

        sensor_summary = self.summarize_sensor_window(
            machine_id=machine_id,
            start_time=start_time,
            end_time=end_time
        )

        alarms = self.get_alarms(
            machine_id=machine_id,
            start_time=start_time,
            end_time=end_time
        )

        maintenance_history = self.get_maintenance_history(
            machine_id = machine_id,
            limit = 5
        )

        spare_parts = self.get_spare_parts_for_machine(machine_id)

        return {
            "machine_info": machine_info,
            "sensor_summary": sensor_summary,
            "alarms": alarms,
            "maintenance_history": maintenance_history,
            "spare_parts": spare_parts
        }
    
def pretty_print_json(data: Any) -> None:
    print(json.dumps(data, indent = 2, ensure_ascii=False))
    
def main() -> None:
    parser = argparse.ArgumentParser(
        description="PlantOps SQL tool for machine telemetry, alarms, history, and spare parts."
    )

    parser.add_argument(
        "--machine-id",
        required = True,
        help = "Machine ID, for example PKG-L3."
    )

    parser.add_argument(
        "--start",
        default="2026-06-10T10:30:00",
        help="Start timestamp."
    )

    parser.add_argument(
        "--end",
        default="2026-06-10T11:10:00",
        help="End timestamp."
    )

    parser.add_argument(
        "--mode",
        choices=[
            "machine",
            "alarms",
            "sensors",
            "summary",
            "history",
            "parts",
            "incident"
        ],
        default="incident",
        help="Which tool output to show."
        )

    args = parser.parse_args()

    tool = PlantOpsSQLTool()

    if args.mode == "machine":
        output = tool.get_machine_info(args.machine_id)
        
    elif args.mode == "alarms":
        output = tool.get_alarms(
            machine_id=args.machine_id,
            start_time=args.start,
            end_time=args.end
        )
        
    elif args.mode == "sensors":
        output = tool.get_sensor_window(
            machine_id=args.machine_id,
            start_time=args.start,
            end_time=args.end
        )
        
    elif args.mode == "summary": 
        output = tool.summarize_sensor_window(
            machine_id=args.machine_id,
            start_time=args.start,
            end_time=args.end
        )
    elif args.mode == "history":
        output = tool.get_maintenance_history(
            machine_id=args.machine_id
        )
    elif args.mode == "parts":
        output = tool.get_spare_parts_for_machine(
            machine_id=args.machine_id
        )
    else:
        output = tool.build_incident_context(
            machine_id = args.machine_id,
            start_time=args.start,
            end_time=args.end
        )

    pretty_print_json(output)

if __name__ == "__main__":
    main()


