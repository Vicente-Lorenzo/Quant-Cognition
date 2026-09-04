from typing import Generic

from Library.App.V2 import AppType
from Library.App.V2.Core.Callback import ComponentID
from Library.App.V2.Component.Component import Component, ButtonAPI, ContainerAPI, IconAPI, MarkdownAPI, PaginatorAPI, TextAPI
from Library.App.V2.Page.Page import PageAPI

class FormAPI(PageAPI, Generic[AppType]):

    FORM_BACK_PAGINATOR_ID: ComponentID | dict = ComponentID()
    FORM_BACK_INTERNAL_ID: ComponentID | dict = ComponentID()
    FORM_BACK_EXTERNAL_ID: ComponentID | dict = ComponentID()
    FORM_ACTION_BUTTON_ID: ComponentID | dict = ComponentID()
    FORM_NEXT_PAGINATOR_ID: ComponentID | dict = ComponentID()
    FORM_NEXT_INTERNAL_ID: ComponentID | dict = ComponentID()
    FORM_NEXT_EXTERNAL_ID: ComponentID | dict = ComponentID()

    def __init__(self, *,
                 app: AppType,
                 path: str,
                 button: str = None,
                 icon: str = None,
                 description: str = None,
                 step: str = None,
                 action: str = None,
                 back: str | bool = False,
                 forward: str | bool = False,
                 back_label: str = "Back",
                 forward_label: str = "Next",
                 add_backward_parent: bool = True,
                 add_backward_children: bool = False,
                 add_current_parent: bool = False,
                 add_current_children: bool = True,
                 add_forward_parent: bool = False,
                 add_forward_children: bool = True) -> None:
        super().__init__(app=app, path=path, button=button, icon=icon, description=description, add_backward_parent=add_backward_parent, add_backward_children=add_backward_children, add_current_parent=add_current_parent, add_current_children=add_current_children, add_forward_parent=add_forward_parent, add_forward_children=add_forward_children)
        self._step_ = step
        self._action_ = action
        self._back_ = back
        self._forward_ = forward
        self._back_label_ = back_label
        self._forward_label_ = forward_label

    def __init_ids__(self) -> None:
        self.FORM_ACTION_BUTTON_ID = self.register(type="button", name="action")
        self.FORM_BACK_PAGINATOR_ID = self.register(type="paginator", name="back")
        self.FORM_BACK_INTERNAL_ID = self.register(type="button", name="internal-back")
        self.FORM_BACK_EXTERNAL_ID = self.register(type="button", name="external-back")
        self.FORM_NEXT_PAGINATOR_ID = self.register(type="paginator", name="next")
        self.FORM_NEXT_INTERNAL_ID = self.register(type="button", name="internal-next")
        self.FORM_NEXT_EXTERNAL_ID = self.register(type="button", name="external-next")
        super().__init_ids__()

    def __init_step_layout__(self) -> list[Component]:
        if not self._step_: return []
        return [MarkdownAPI(text=self._step_, classname="form-step")]

    def __init_controls_layout__(self) -> list[Component]:
        buttons = []
        if self._back_:
            href = self.app.endpointize(path=self._back_, relative=True) if isinstance(self._back_, str) else None
            buttons.append(PaginatorAPI(id=self.FORM_BACK_PAGINATOR_ID, iid=self.FORM_BACK_INTERNAL_ID, eid=self.FORM_BACK_EXTERNAL_ID, label=[IconAPI(icon="bi bi-chevron-left"), TextAPI(text=f" {self._back_label_}")], invert=False, href=href, classname="form-back"))
        if self._action_:
            buttons.append(ButtonAPI(id=self.FORM_ACTION_BUTTON_ID, label=[TextAPI(text=self._action_)], background="primary", classname="form-action"))
        if self._forward_:
            href = self.app.endpointize(path=self._forward_, relative=True) if isinstance(self._forward_, str) else None
            buttons.append(PaginatorAPI(id=self.FORM_NEXT_PAGINATOR_ID, iid=self.FORM_NEXT_INTERNAL_ID, eid=self.FORM_NEXT_EXTERNAL_ID, label=[TextAPI(text=f"{self._forward_label_} "), IconAPI(icon="bi bi-chevron-right")], invert=True, href=href, classname="form-next"))
        return buttons

    def __init_content_layout__(self) -> list[Component]:
        hidden = self.__init_hidden_layout__()
        steps = self.__init_step_layout__()
        step = ContainerAPI(elements=steps, classname="form-header").build() if steps else []
        controls = self.__init_controls_layout__()
        controls = ContainerAPI(elements=controls, classname="form-controls").build() if controls else []
        content = self._content_ or self.normalize(self.content())
        wrapper = ContainerAPI(elements=content, classname="form-body").build()
        form = ContainerAPI(elements=[*step, *wrapper, *controls], classname="form").build()
        return [*form, *hidden]