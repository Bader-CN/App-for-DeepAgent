import flet as ft

from src.utils.log import logger
from src.utils.globals import app_chat_utils
from src.views.chat_view import ChatView
from src.views.settings_view import SettingsView
from src.components.chat_with_user_input import UserInput
from src.components.chat_with_chat_details import ChatDetails

class MainView:
    """
    Flet 的一级布局
    """
    def __init__(self, page):
        # 从 Flet 主进程中获取 page 对象
        self.page = page
        # 绑定键盘事件
        self.page.on_keyboard_event = self.on_keyboard
        # 定义导航栏按钮
        self.chat = ft.IconButton(ft.Icons.CHAT, tooltip="对话", on_click=lambda e, selected_tag="Chat":self.callback_render_right_view(e, selected_tag))
        self.docs = ft.IconButton(ft.Icons.SNIPPET_FOLDER, tooltip="文档", on_click=lambda e, selected_tag="Docs":self.callback_render_right_view(e, selected_tag))
        self.settings = ft.IconButton(ft.Icons.SETTINGS, tooltip="设置", on_click=lambda e, selected_tag="Settings":self.callback_render_right_view(e, selected_tag))
        # 完整的导航栏
        self.navigation_rail = ft.Container(
            ft.Column(
                controls=[self.chat, self.docs, ft.Container(expand=True), self.settings],
                spacing=0,
                horizontal_alignment=ft.CrossAxisAlignment.CENTER,
            ),
            width=40,
            bgcolor="#E8E8E8",
        )
        # 记录上一次导航栏点击的按钮, 用于减少刷新次数
        self.last_navigation_rail_click = None

        # 对应页面的实例化对象
        self.chat_view = ChatView()
        self.settings_view = SettingsView()

        # 右侧区域视图
        self.right_view = ft.Container(
            expand=True,
            # border=ft.Border.all(width=1, color=ft.Colors.GREY),
        )

    def callback_render_right_view(self, e, selected_tag: str):
        """
        用于决定如何渲染右侧内容的回调函数
        """
        if self.last_navigation_rail_click != selected_tag:
            # 记录上一次点击的内容 & 清空 right_view 里的内容
            self.last_navigation_rail_click = selected_tag
            if self.right_view.content is not None:
                self.right_view.content.controls.clear()
            # 根据导航栏来选择实际渲染的画面
            if selected_tag == "Chat":
                self.chat_view.full_update(e, right_view_container=self.right_view)
            elif selected_tag == "Docs":
                pass
            elif selected_tag == "Settings":
                self.settings_view.full_update(e, right_view_container=self.right_view)
    
    def on_keyboard(self, e: ft.KeyboardEvent):
        """
        键盘事件
        """
        # Shift + Enter 且 UserInput.user_input_component 必须获得焦点
        if e.shift and e.key == "Enter" and UserInput.user_input_tag:
            UserInput.send_user_input_message()
        # Ctrl + V
        elif e.ctrl and e.key == "V" and UserInput.user_input_tag:
            # 异步执行 (获取剪贴板里的图片内容)
            # https://docs.flet.dev/services/clipboard/?h=clipboard
            self.page.run_task(self.get_image_from_clipboard)
    
    async def get_image_from_clipboard(self):
        """
        获取剪贴板里的图片内容
        """
        chat_session_filename = ChatDetails.chat_list_control.data
        image_prefix = chat_session_filename[:32]
        image_data = await ft.Clipboard().get_image()
        # 如果数据非空, 则添加一个图片
        if image_data is not None:
            app_chat_utils.add_image_with_temp(session_prefix=image_prefix, data=image_data)
        # 执行刷新
        UserInput.update_attachments(prefix=image_prefix)
        self.page.update()