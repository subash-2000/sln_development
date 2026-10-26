import os
import sys

from alembic import command
from alembic.config import Config

# Add project root to sys.path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))


def run_migration():
    os.environ["ALEMBIC_DATABASE_URL"] = (
        "postgresql+asyncpg://odoo:odoo@localhost:5433/sln_warehouse_test"
    )
    alembic_cfg = Config("alembic.ini")
    command.upgrade(alembic_cfg, "head")
    print("Successfully ran alembic upgrade head on sln_warehouse_test!")


if __name__ == "__main__":
    run_migration()
