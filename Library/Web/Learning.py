from Library.Web.Launcher import LauncherPageAPI

class LearningPageAPI(LauncherPageAPI):

    def __init__(self, *, app) -> None:
        super().__init__(app=app, path="/learning", button="Learning", icon="bi bi-robot", step="Learning", action="Start Learning", description="Train deep reinforcement learning agents and review their performance")