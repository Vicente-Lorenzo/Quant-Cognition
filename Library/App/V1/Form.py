from typing import Union
from Library.App.V1 import AppType
from Library.App.V1.Page import PageAPI
from Library.App.V1.Callback import ComponentID
from Library.App.V1.Component import Component, IconAPI, TextAPI, MarkdownAPI, ButtonAPI, PaginatorAPI, ContainerAPI

class FormAPI(PageAPI[AppType]):

    FORM_BACK_PAGINATOR_ID: Union[ComponentID, dict] = ComponentID()
    FORM_BACK_INTERNAL_ID: Union[ComponentID, dict] = ComponentID()
    FORM_BACK_EXTERNAL_ID: Union[ComponentID, dict] = ComponentID()
    FORM_ACTION_BUTTON_ID: Union[ComponentID, dict] = ComponentID()
    FORM_NEXT_PAGINATOR_ID: Union[ComponentID, dict] = ComponentID()
    FORM_NEXT_INTERNAL_ID: Union[ComponentID, dict] = ComponentID()
    FORM_NEXT_EXTERNAL_ID: Union[ComponentID, dict] = ComponentID()

    def __init__(self, *,
                 app: AppType,
                 path: str,
                 anchor: str = None,
                 endpoint: str = None,
                 redirect: str = None,
                 button: str = None,
                 description: str = None,
                 content: Union[Component, list[Component]] = None,
                 sidebar: Union[Component, list[Component]] = None,
                 navigation: Union[Component, list[Component]] = None,
                 add_backward_parent: bool = True,
                 add_backward_children: bool = False,
                 add_current_parent: bool = False,
                 add_current_children: bool = True,
                 add_forward_parent: bool = False,
                 add_forward_children: bool = True,
                 add_step_label: str = None,
                 add_back_button: Union[bool, str] = False,
                 add_action_button: str = None,
                 add_next_button: Union[bool, str] = False,
                 back_button_label: str = "Back",
                 next_button_label: str = "Next") -> None:

        super().__init__(
            app=app,
            path=path,
            anchor=anchor,
            endpoint=endpoint,
            redirect=redirect,
            button=button,
            description=description,
            content=content,
            sidebar=sidebar,
            navigation=navigation,
            add_backward_parent=add_backward_parent,
            add_backward_children=add_backward_children,
            add_current_parent=add_current_parent,
            add_current_children=add_current_children,
            add_forward_parent=add_forward_parent,
            add_forward_children=add_forward_children
        )

        self._add_step_label_: str = add_step_label
        self._add_back_button_: Union[str, bool] = add_back_button
        self._add_action_button_: str = add_action_button
        self._add_next_button_: Union[str, bool] = add_next_button
        self._back_button_label_: str = back_button_label
        self._next_button_label_: str = next_button_label

    def __init_ids__(self) -> None:
        self.FORM_ACTION_BUTTON_ID: dict = self.register(type="button", name="action")
        self.FORM_BACK_PAGINATOR_ID: dict = self.register(type="paginator", name="back")
        self.FORM_BACK_INTERNAL_ID: dict = self.register(type="button", name="internal-back")
        self.FORM_BACK_EXTERNAL_ID: dict = self.register(type="button", name="external-back")
        self.FORM_NEXT_PAGINATOR_ID: dict = self.register(type="paginator", name="next")
        self.FORM_NEXT_INTERNAL_ID: dict = self.register(type="button", name="internal-next")
        self.FORM_NEXT_EXTERNAL_ID: dict = self.register(type="button", name="external-next")
        super().__init_ids__()

    def __init_step_layout__(self) -> list[Component]:
        steps = []
        if self._add_step_label_:
            steps.append(MarkdownAPI(text=self._add_step_label_, font_size="30px", font_weight="bold", font_color="var(--bs-primary)"))
        return self.normalize(steps)

    def __init_controls_layout__(self) -> list[Component]:
        buttons = []
        if self._add_back_button_:
            target: str = self.app.endpointize(path=self._add_back_button_, relative=True) if isinstance(self._add_back_button_, str) else None
            buttons.append(PaginatorAPI(
                id=self.FORM_BACK_PAGINATOR_ID,
                iid=self.FORM_BACK_INTERNAL_ID,
                eid=self.FORM_BACK_EXTERNAL_ID,
                label=[IconAPI(icon="bi bi-chevron-left"), TextAPI(text=f"  {self._back_button_label_}")],
                invert=False,
                href=target,
                background="white",
                outline_color="black",
                outline_style="solid",
                outline_width="1px",
                stylename="button"
            ))
        if self._add_action_button_:
            buttons.append(ButtonAPI(
                id=self.FORM_ACTION_BUTTON_ID,
                label=[TextAPI(text=self._add_action_button_)],
                background="white",
                outline_color="black",
                outline_style="solid",
                outline_width="1px",
                stylename="button"
            ))
        if self._add_next_button_:
            target: str = self.app.endpointize(path=self._add_next_button_, relative=True) if isinstance(self._add_next_button_, str) else None
            buttons.append(PaginatorAPI(
                id=self.FORM_NEXT_PAGINATOR_ID,
                iid=self.FORM_NEXT_INTERNAL_ID,
                eid=self.FORM_NEXT_EXTERNAL_ID,
                label=[TextAPI(text=f"{self._next_button_label_}  "), IconAPI(icon="bi bi-chevron-right")],
                invert=True,
                href=target,
                background="white",
                outline_color="black",
                outline_style="solid",
                outline_width="1px",
                stylename="button"
            ))
        return self.normalize([*buttons])

    def __init_content_layout__(self) -> list[Component]:
        hidden = self.__init_hidden_layout__()
        self._log_.debug(lambda: f"Loaded Hidden Layout")

        steps = self.__init_step_layout__()
        step = ContainerAPI(elements=steps, classname="step").build() if steps else []
        self._log_.debug(lambda: f"Loaded Step Layout")

        controls = self.__init_controls_layout__()
        controls = ContainerAPI(elements=controls, classname="controls").build() if controls else []
        self._log_.debug(lambda: f"Loaded Controls Layout")

        content = self.normalize(self._content_ or self.content())
        wrapper = ContainerAPI(elements=content, classname="wrapper").build()
        self._log_.debug(lambda: f"Loaded Content Wrapper Layout")

        form = ContainerAPI(elements=[*step, *wrapper, *controls], classname="form").build()
        return self.normalize([*form, *hidden])

    def __init_sidebar_layout__(self) -> list[Component]:
        sidebar = self.normalize(self._sidebar_ or self.sidebar())
        wrapper = ContainerAPI(elements=[*sidebar], classname="wrapper").build()
        form = ContainerAPI(elements=[*wrapper], classname="form").build()
        return self.normalize([*form])