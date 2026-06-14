from src.database.sql_tools import PlantOpsSQLTool

sql_tool = PlantOpsSQLTool()

def investigate_incident(
        machine_id,
        start_time,
        end_time
):
    return sql_tool.build_incident_context(
        machine_id,
        start_time,
        end_time
    )