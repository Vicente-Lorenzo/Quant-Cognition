from Library.App.V2 import SectionPageAPI

class SchedulerPageAPI(SectionPageAPI):

    def __init__(self, *, app) -> None:
        super().__init__(app=app, path="/scheduler", button="Scheduler", icon="bi bi-calendar2-week", description="Create, schedule and monitor workflows, tasks and their runs")