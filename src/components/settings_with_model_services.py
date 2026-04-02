import flet as ft

from src.utils.globals import app_config
from src.utils.log import logger

class ModelServices:
    # 类变量: 页面布局
    settings_lv2 = None
    settings_lv3 = None
    # 类变量: Model_Services 列表
    model_services_listview = None
    # 类变量: Model_Services 详情
    old_display_name = None
    cfg_display_name = ft.Ref[ft.TextField]()
    cfg_provider = ft.Ref[ft.Dropdown]()
    cfg_enable = ft.Ref[ft.Switch]()
    cfg_base_url = ft.Ref[ft.TextField]()
    cfg_model_name = ft.Ref[ft.TextField]()
    cfg_max_tokens = ft.Ref[ft.TextField]()
    cfg_api_key = ft.Ref[ft.TextField]()

    @classmethod
    def create_model_services_component(cls):
        """
        模型列表组件
        """
        # 模型列表
        model_services_listview = ft.ReorderableListView(
            show_default_drag_handles=False,
            on_reorder=cls.model_services_listview_handle_reorder,
        )
        cls.model_services_listview = model_services_listview
        
        # 构建组件
        model_services_display_name = app_config.get_all_model_services_display_name()
        for display_name in model_services_display_name:
            model_service = app_config.get_model_service_by_display_name(display_name=display_name)
            if model_service.get("enable") is True:
                is_enable = "ON"
                txt_color = ft.Colors.GREEN
            else:
                is_enable = "OFF"
                txt_color = ft.Colors.RED
            
            model_services_listview.controls.append(
                ft.ListTile(
                    title=ft.Text(value=display_name, expand=True, expand_loose=True),
                    leading=ft.ReorderableDragHandle(
                        content=ft.Icon(ft.Icons.DRAG_INDICATOR, color=ft.Colors.GREY_500),
                        mouse_cursor=ft.MouseCursor.GRAB,
                    ),
                    trailing=ft.Text(value=is_enable, color=txt_color),
                    horizontal_spacing=10,
                    dense=True,
                    hover_color=ft.Colors.BLUE_GREY_50,
                    toggle_inputs=True,
                    on_click=cls.model_services_update,
                )
            )
        return model_services_listview

    @classmethod
    def model_services_listview_handle_reorder(cls, e):
        """
        基于视图来更新配置中 "模型服务" 的排序
        """
        display_names = app_config.get_all_model_services_display_name()
        display_names[e.old_index], display_names[e.new_index] = display_names[e.new_index], display_names[e.old_index]
        new_model_services = []
        for display_name in display_names:
            model_service = app_config.get_model_service_by_display_name(display_name)
            new_model_services.append(model_service)
        app_config.set_all_model_services(model_services=new_model_services)

    @classmethod
    def model_services_update(cls, e):
        """
        渲染 "模型服务" 详情
        """
        # 后续会用 "old_display_name" 追踪当前选择的 model_service
        display_name = e.control.title.value
        cls.old_display_name = display_name
        model_service = app_config.get_model_service_by_display_name(display_name=display_name)
        model_service_page = ft.Column(
            [   
                ft.TextField(value=model_service.get("display_name"), label="Display_Name", expand=True, expand_loose=True, ref=cls.cfg_display_name),
                ft.Row(
                    [
                        ft.Dropdown(
                            value=model_service.get("config").get("model_provider"),
                            label="Model_Provider", 
                            options=[ft.DropdownOption(key="ollama", text="ollama"), ft.DropdownOption(key="openai", text="openai")],
                            expand=True, expand_loose=True,
                            ref=cls.cfg_provider,
                        ),
                        ft.Switch(value=model_service.get("enable"), ref=cls.cfg_enable, on_change=cls.model_services_switch_button),
                    ],
                    alignment=ft.MainAxisAlignment.CENTER,
                ),
                ft.TextField(value=model_service.get("config").get("base_url"), label="Base_URL", expand=True, expand_loose=True, ref=cls.cfg_base_url),
                ft.TextField(value=model_service.get("config").get("model_name"), label="Model_Name", expand=True, expand_loose=True, ref=cls.cfg_model_name),
                ft.TextField(value=model_service.get("config").get("api_key"), label="API_Key", expand=True, expand_loose=True, password=True, ref=cls.cfg_api_key),
                ft.TextField(value=model_service.get("config").get("max_tokens"), label="Max_Tokens", expand=True, expand_loose=True, ref=cls.cfg_max_tokens),
                ft.Row(
                    [
                        ft.Button(content="保存", on_click=cls.model_services_save),
                        ft.Button(content="删除", on_click=cls.model_services_delete),
                    ]
                ),
            ],
            horizontal_alignment=ft.CrossAxisAlignment.CENTER,
        )
        cls.settings_lv3.content = model_service_page

    @classmethod
    def model_services_save(cls, e):
        """
        "模型服务" 保存按钮
        """
        # 获取当前模型服务
        from src.utils.globals import app_config
        cfg_model = app_config.get_model_service_by_display_name(display_name=cls.old_display_name)
        # 更新模型服务配置
        cfg_model["display_name"] = cls.cfg_display_name.current.value
        cfg_model["enable"] = cls.cfg_enable.current.value
        cfg_model["config"]["model_provider"] = cls.cfg_provider.current.value
        cfg_model["config"]["model_name"] = cls.cfg_model_name.current.value
        cfg_model["config"]["base_url"] = cls.cfg_base_url.current.value
        cfg_model["config"]["api_key"] = cls.cfg_api_key.current.value
        cfg_model["config"]["max_tokens"] = cls.cfg_max_tokens.current.value
        # 保存配置
        app_config.write_yaml()
        # 更新标记位
        # - 用来解决 display_name 变更 & 保存
        # - 如果不更新此标记位, 会导致 cfg_enable 切换失效
        cls.old_display_name = cls.cfg_display_name.current.value
        # 重新渲染: 保留 "添加按钮", 但重新渲染 "模型服务" 列表
        cls.settings_lv2.content.controls = cls.settings_lv2.content.controls[0:1]
        cls.settings_lv2.content.controls.append(cls.create_model_services_component())
    
    @classmethod
    def model_services_add(cls, e):
        """
        "模型服务" 添加按钮
        """
        # 追加一个新的配置项
        new_cfg_id = 1
        while f"new_config_{new_cfg_id}" in app_config.get_all_model_services_display_name():
            new_cfg_id += 1
        new_cfg = {
            'display_name': f"new_config_{new_cfg_id}", 
            'enable': False, 
            'config': {'model_provider': 'ollama', 'base_url': 'http://localhost:11434', 'model_name': '<model_name>', 'api_key': '<api_key>', 'max_tokens': 4096}
        }
        all_models = app_config.get_all_model_services()
        all_models.append(new_cfg)
        app_config.write_yaml()
        # 重新渲染: 保留 "添加按钮", 但重新渲染 "模型服务" 列表
        cls.settings_lv2.content.controls = cls.settings_lv2.content.controls[0:1]
        cls.settings_lv2.content.controls.append(cls.create_model_services_component())

    @classmethod
    def model_services_delete(cls, e):
        """
        删除一个指定的 "模型服务"
        """
        # 删掉指定 "模型配置"
        app_config.del_model_service_by_display_name(cls.old_display_name)
        app_config.write_yaml()
        # 重新渲染
        # - 保留 "添加按钮", 但重新渲染 "模型服务" 列表
        # - 清空 "模型详情"
        cls.settings_lv2.content.controls = cls.settings_lv2.content.controls[0:1]
        cls.settings_lv2.content.controls.append(cls.create_model_services_component())
        cls.settings_lv3.content.controls.clear()
        # 清空标记位
        cls.old_display_name = None

    @classmethod
    def model_services_switch_button(cls, e):
        """
        "模型服务" 切换按钮 (enable/disable)
        """
        # 取反 "模型服务" 中的 enable 项
        model_cfg = app_config.get_model_service_by_display_name(cls.old_display_name)
        model_cfg["enable"] = not model_cfg.get("enable")
        app_config.write_yaml()
        # 重新渲染: 保留 "添加按钮", 但重新渲染 "模型服务" 列表
        cls.settings_lv2.content.controls = cls.settings_lv2.content.controls[0:1]
        cls.settings_lv2.content.controls.append(cls.create_model_services_component())