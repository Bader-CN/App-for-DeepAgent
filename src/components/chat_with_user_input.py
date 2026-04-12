import flet as ft

from src.utils.log import logger
from src.utils.globals import app_config
from src.utils.globals import app_chat_utils
from src.utils.globals import app_agent
from src.components.chat_with_chat_details import ChatDetails

class UserInput:
    """
    用户输入组件
    """
    user_attachments = ft.Ref[ft.Row]()
    user_input = ft.Ref[ft.TextField]()
    user_input_tag = False              # 记录输入框是否被选中 (用于监听键盘事件)
    user_input_panel = ft.Ref[ft.Row]() # 输入框底部的功能栏

    @classmethod
    def create_user_input_component(cls, page):
        """
        创建用户输入组件

        Args:
        - page: 用于执行异步函数
        """
        # 附件栏
        attachments = ft.Container(
            ft.Row(),
            ref=cls.user_attachments,
            # border=ft.Border.all(width=1, color=ft.Colors.BLUE),
        )
        # 输入的文本框
        input_textfield = ft.TextField(
            border=ft.InputBorder.NONE,
            multiline=True,
            max_lines=3,
            expand=True,
            dense=True,
            content_padding=ft.Padding(left=0, top=10, right=0, bottom=20),
            hint_text="按 Shift + Enter 发送",
            text_style=ft.TextStyle(font_family="Microsoft YaHei", size=14),
            ref=cls.user_input,
            on_focus=cls.switch_user_input_tag,
            on_blur=cls.switch_user_input_tag,
        )
        # 模型选择
        model_select = ft.Dropdown(
            label="模型服务",
            value=app_config.get_default_model_with_agent(),
            options=[
                ft.DropdownOption(key=i, text=i) for i in app_config.get_all_model_services_display_name_with_enable()
            ],
            dense=True,
            on_select=cls.reload_agent_main,
        )
        # 组装 user_input_component
        user_input_component = ft.Container(
            ft.Column(
                [   
                    attachments,
                    input_textfield,
                    ft.Row(
                        [
                            model_select,
                            ft.Container(expand=True),
                            ft.IconButton(ft.Icons.SEND, tooltip="发送", data="Send", on_click=cls.send_user_input_message),
                        ],
                        ref=cls.user_input_panel,
                    ),
                ],
                spacing=0,
            ),
            border=ft.Border.all(width=1, color=ft.Colors.GREY),
            border_radius=10,
            padding=ft.Padding(left=15, right=15, top=5, bottom=10),
        )
        # 异步加载 "主智能体" 和 "总结模型"
        # https://docs.flet.dev/controls/page/?h=run_ta#flet.Page.render_views
        page.run_task(cls.load_agent_main)
        page.run_task(cls.load_agent_summary)

        return user_input_component
    
    @classmethod
    def send_user_input_message(cls, e=None, page=None):
        """
        将用户输入的 message 发送给 LLM
        """
        # 如果输入内容为非空 / 或按钮为 Send 
        if cls.user_input.current.value not in ["", None] and cls.user_input_panel.current.controls[-1].data == "Send":
            ChatDetails.need_stop_response = False
            ChatDetails.send_user_message(user_message_by_text=cls.user_input.current.value)
            cls.user_input.current.value = ""
            cls.switch_button_to_cancel()
        else:
            if cls.user_input.current.value in ["", None]:
                logger.warning("user input is empty, will be ignore it.")
            if cls.user_input_panel.current.controls[-1].data == "Cancel":
                logger.warning("duplicate message detected, will be ignore it.")
        # 刷新界面
        if page:
            page.update()
        else:
            e.page.update()

    @classmethod
    def switch_user_input_tag(cls, e):
        """
        切换键盘标记位
        """
        # 触发直接取反
        cls.user_input_tag = not cls.user_input_tag
    
    @classmethod
    def switch_button_to_send(cls):
        """
        将 "发送" 切换为 "取消"
        """
        cls.user_input_panel.current.controls[-1] = ft.IconButton(ft.Icons.SEND, tooltip="发送", data="Send", on_click=cls.send_user_input_message)

    @classmethod
    def switch_button_to_cancel(cls):
        """
        将 "取消" 切换为 "发送"
        """
        cls.user_input_panel.current.controls[-1] = ft.IconButton(ft.Icons.CANCEL, tooltip="取消", data="Cancel", on_click=cls.stop_response_message)
    
    @classmethod
    def stop_response_message(cls, e):
        """
        设置消息停止输出的标记位
        """
        ChatDetails.need_stop_response = True
        cls.switch_button_to_send()
        e.page.update()
    
    @classmethod
    def reload_agent_main(cls, e):
        """
        重新加载 "模型服务" 时触发
        """
        display_name=e.data
        app_agent.get_agent_main(display_name=display_name)
        app_config.set_default_model_with_agent(display_name=display_name)
        logger.debug(f"Model for Agent Main loading complete: {display_name}")
    
    @classmethod
    async def load_agent_main(cls):
        """
        异步加载 "模型服务"
        """
        display_name = app_config.get_default_model_with_agent()
        app_agent.get_agent_main(display_name=display_name)
        logger.debug(f"Model for Agent Main loading complete: {display_name}")
    
    @classmethod
    async def load_agent_summary(cls):
        """
        异步加载 "总结模型"
        """
        app_agent.get_agent_summary()

    @classmethod
    def update_attachments(cls, prefix=None):
        """
        基于 prefix 来刷新附件列表
        """
        # 情况原始内容
        cls.user_attachments.current.content.controls.clear()
        # 检索图片
        images = app_chat_utils.get_images_with_temp(session_prefix=prefix)
        if images is not None:
            for image in images:
                attachment = ft.Container(
                    ft.Row(
                        [
                            ft.Text(image[33:], size=14),
                            ft.IconButton(
                                icon=ft.Icon(ft.Icons.CANCEL, size=14), 
                                height=28, width=28,
                                data=image,  # 记录对应文件绝对路径, 为删除该文件做准备
                                on_click=cls.delete_attachment,
                                ),
                        ],
                        alignment=ft.MainAxisAlignment.CENTER,
                        spacing=0,
                    ),
                    padding=ft.Padding(left=5, right=0, top=0, bottom=0),
                    border_radius=10,
                    bgcolor=ft.Colors.BLUE_100,
                )
                # 添加至附件列表
                cls.user_attachments.current.content.controls.append(attachment)
    
    @classmethod
    def delete_attachment(cls, e):
        """
        删除指定附件
        """
        filename = e.control.data
        # 删除指定文件
        app_chat_utils.delete_tempfile_with_filename(filename=filename)
        # 刷新列表
        cls.update_attachments(prefix=filename[:32])