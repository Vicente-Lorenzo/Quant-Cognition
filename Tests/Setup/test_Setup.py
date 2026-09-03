import pytest

from Library.Scheduler import WorkflowAPI, TaskAPI, DependencyAPI, CycleAPI, RunAPI, CoordinatorAPI, ManagerAPI
from Library.Auth import UserAPI
from Library.Database.Postgres.Postgres import PostgresDatabaseAPI
from Library.Utility.Path import traceback_root
from Setup.Install import bootstrap, register, WORKFLOWS

DATABASE = "Tests"
ROOT = traceback_root()

def test_definitions_are_acyclic_dags():
    uids = [task["uid"] for workflow in WORKFLOWS for task in workflow["tasks"]]
    assert len(uids) == len(set(uids))
    for workflow in WORKFLOWS:
        members = [task["uid"] for task in workflow["tasks"]]
        for predecessor, successor in workflow["edges"]:
            assert predecessor in members and successor in members
        assert CoordinatorAPI.acyclic(members, workflow["edges"])

def test_task_artifacts_exist_and_are_runnable():
    for workflow in WORKFLOWS:
        for task in workflow["tasks"]:
            source = ROOT / task["path"]
            assert source.is_file()
            text = source.read_text(encoding="utf-8")
            assert "def main(" in text and "__main__" in text

@pytest.fixture(scope="module")
def prepared():
    for cls in (UserAPI, WorkflowAPI, TaskAPI, DependencyAPI, CycleAPI, RunAPI):
        cls.Database = DATABASE
    admin = PostgresDatabaseAPI(admin=True)
    try:
        admin.connect()
        if not admin.exists(database=DATABASE): admin.create(database=DATABASE)
    finally:
        admin.disconnect()
    bootstrap(DATABASE)
    return DATABASE

def test_register_is_idempotent(prepared):
    register(ManagerAPI(database=DATABASE))
    register(ManagerAPI(database=DATABASE))
    manager = ManagerAPI(database=DATABASE)
    for workflow in WORKFLOWS:
        assert manager.workflow(workflow["uid"]) is not None
        assert len(manager.tasks(workflow=workflow["uid"])) == len(workflow["tasks"])
        assert len(manager.dependencies(workflow["uid"])) == len(workflow["edges"])
    for workflow in WORKFLOWS:
        for task in workflow["tasks"]: manager.delete_task(task["uid"])
        manager.delete_workflow(workflow["uid"])