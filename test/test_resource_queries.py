from src.database.sql_tools import PlantOpsSQLTool


def test_tool_inventory():
    tool = PlantOpsSQLTool()

    inventory = tool.get_tool_inventory()

    assert len(inventory) == 10
    assert all("availability" in item for item in inventory)


def test_skill_catalog():
    tool = PlantOpsSQLTool()

    skills = tool.get_skill_catalog()

    assert len(skills) == 6


def test_technicians_include_skills():
    tool = PlantOpsSQLTool()

    technicians = tool.get_technicians_with_skills()

    assert len(technicians) == 4
    assert all("skills" in technician for technician in technicians)


def test_pkg_l3_spare_mapping():
    tool = PlantOpsSQLTool()

    spare_parts = tool.get_spare_parts_for_machine(
        "PKG-L3"
    )

    part_ids = {
        part["part_id"]
        for part in spare_parts
    }

    assert part_ids == {"SP-001", "SP-003"}