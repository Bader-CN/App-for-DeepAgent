import flet as ft

from src.utils.log import logger
from src.components.chat_with_user_input import UserInput
from src.components.chat_with_chat_list import ChatList
from src.components.chat_with_chat_details import ChatDetails

class ChatView:
    """
    负责聊天对话页面
    """
    def __init__(self):
        self.page = None
        self.right_view = None
        self.settings_lv1 = None
        self.settings_lv2 = None
        self.chat_details = None
        self.chat_input = None
    
    def full_update(self, e, right_view_container):
        """
        完整渲染聊天页面基础布局, 一般用于首次渲染
        """
        self.page = e.page
        self.right_view = right_view_container
        self.right_view.content = ft.Row(expand=True, spacing=0)

        # 该组件需要提前暴露锚点, 因此直接在此定义
        self.chat_details = ft.Container(
            ft.Stack(expand=True),
            expand=True, 
            # padding=5,
            # border=ft.Border.all(width=1, color=ft.Colors.BLUE),
        )
        # 暴露 chat_details/page 给 ChatDetails
        ChatDetails.chat_details = self.chat_details
        ChatDetails.page = self.page

        # 该组件需要提前暴露 (附件列表功能需要, 否则找不到控件)
        self.settings_lv2 = ft.Container(
            ft.Column(
                [
                    self.chat_details,
                    UserInput.create_user_input_component(self.page),
                ]
            ),
            expand=True,
            alignment=ft.Alignment.TOP_CENTER,
            padding=ft.Padding(left=20, right=20, top=5, bottom=10),
        )
        
        # 渲染界面
        self.update_lv1_chat_list()
        self.update_lv2_chat_details()

    def update_lv1_chat_list(self):
        """
        更新 Lv1 层级的对话列表
        """
        self.settings_lv1 = ft.Container(
            ft.Column(
                [
                    ft.Button(content="+ 新建对话", width=200, on_click=ChatList.chat_list_add),
                    ChatList.create_chat_list_component(),
                ],
                width=220,
                horizontal_alignment=ft.CrossAxisAlignment.CENTER,
            ),
            padding=ft.Padding.symmetric(vertical=10, horizontal=0),
        )
        # ft.Row Contorl 对象
        if self.settings_lv1 not in self.right_view.content.controls:
            self.right_view.content.controls.append(self.settings_lv1)
            self.right_view.content.controls.append(ft.VerticalDivider(width=1))
    
    def update_lv2_chat_details(self):
        """
        更新 Lv2 层级的对话详情
        """
        if self.settings_lv2 not in self.right_view.content.controls:
            self.right_view.content.controls.append(self.settings_lv2)
