import flet as ft

from src.endpoints import guiEndPoints
from src.components.settings_with_model_services import ModelServices
from src.utils.log import logger

class SettingsView:
    """
    负责设置页面的渲染
    """
    def __init__(self):
        self.page = None
        self.right_view = None
        self.settings_lv1 = None
        self.settings_lv2 = None
        self.settings_lv3 = None

    def full_update(self, e, right_view_container):
        """
        完整渲染设置页面, 一般用于首次渲染
        """
        self.page = e.page
        self.right_view = right_view_container
        self.right_view.content = ft.Row(expand=True, spacing=0)

        self.update_lv1()

    def update_lv1(self):
        """
        只更新设置界面的 lv1 层级
        """
        self.settings_lv1 = ft.Container(
            ft.Column(
                [
                    ft.Button(content="常用设置", on_click=lambda e, tag="common_settings":self.update_lv2(e, tag)),
                    ft.Button(content="模型服务", on_click=lambda e, tag="model_services":self.update_lv2(e, tag)),
                ],
                width=130,
                horizontal_alignment=ft.CrossAxisAlignment.CENTER,
            ),
            padding=ft.Padding.symmetric(vertical=10, horizontal=0),
            # 暴露 settings_lv1
            ref=guiEndPoints.settings["settings_view_lv1"],
        )
        # ft.Row Contorl 对象
        if self.settings_lv1 not in self.right_view.content.controls:
            self.right_view.content.controls.append(self.settings_lv1)
            self.right_view.content.controls.append(ft.VerticalDivider(width=1))
    
    def update_lv2(self, e, tag):
        """
        只更新设置界面的 lv2 层级
        """
        # 对 right_view 进行截取, 仅保留 Lv1 层级
        self.right_view.content.controls = self.right_view.content.controls[0:2]

        # 常规设置
        if tag == "common_settings":
            self.settings_lv2 = ft.Container(
                ft.Text(value="这是 common_settings 界面"),
                expand=True,
                alignment=ft.Alignment.CENTER,
                ref=guiEndPoints.settings["settings_view_lv2"],
            )
            # 追加组件
            self.right_view.content.controls.append(self.settings_lv2)

        # 模型服务
        elif tag == "model_services":
            self.settings_lv3 = ft.Container(
                expand=True, 
                padding=ft.Padding(left=20, top=15, right=20, bottom=15), 
                # 暴露 settings_lv3 给 ModelServices
                ref=guiEndPoints.settings["settings_view_lv3"],
            )
            self.settings_lv2 = ft.Container(
                ft.Column(
                    [
                        ft.Button(content="+ 添加", width=200, on_click=ModelServices.model_services_add),
                        ModelServices.create_model_services_component(),
                    ],
                    width=240,
                    horizontal_alignment=ft.CrossAxisAlignment.CENTER,
                ),
                padding=ft.Padding.symmetric(vertical=10, horizontal=0),
                # 暴露 settings_lv2 给 ModelServices
                ref=guiEndPoints.settings["settings_view_lv2"],
            )
            # 追加组件
            self.right_view.content.controls.append(self.settings_lv2)
            self.right_view.content.controls.append(ft.VerticalDivider(width=1))
            self.right_view.content.controls.append(self.settings_lv3)