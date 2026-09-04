from Library.App.V2 import SectionPageAPI

class FrameworkPageAPI(SectionPageAPI):

    def __init__(self, *, app) -> None:
        super().__init__(app=app, path="/framework", button="Framework", icon="bi bi-boxes", description="Inspect the database and the module hierarchy behind the framework")