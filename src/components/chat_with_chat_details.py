import os
import ast
import uuid
import base64

import flet as ft
from langchain.messages import AIMessageChunk, ToolMessage

from copy import deepcopy
from src.utils.log import logger
from src.utils.globals import app_config
from src.utils.globals import app_agent
from src.utils.globals import app_chat_utils

class ChatDetails:
    # 类变量: ChatView 中的聊天详情
    page = None                 # 获取 page 对象, 用于创建异步任务
    chat_details = None
    chat_list_control = None    # 当前选中的 chat_list 控件
    chat_details_data = None    # 对应会话的数据, 字典类型
    chat_details_title = ft.Ref[ft.TextField]()
    chat_details_messages = ft.Ref[ft.Column]()
    current_chat_data_filename = None   # 当前 chat_data 的文件名
    need_stop_response = False  # 是否需要停止输出

    @classmethod
    def clear_chat_details_component(cls):
        """
        清空聊天详情, 用于相应会话被删除的时候
        """
        if cls.chat_details is not None:
            cls.chat_details.content.controls.clear()
    
    @classmethod
    def create_chat_details_component(cls, e=None, chat_list_control=None):
        """
        创建聊天详情的基本组件
        """
        if e is not None:
            # 映射 page 对象
            cls.page = e.page
            # 设置操作的锚点: 对应 chatlist 里的 ft.ListTile 控件对象
            cls.chat_list_control = e.control
            cls.current_chat_data_filename = e.control.data
        elif chat_list_control is not None:
            cls.chat_list_control = chat_list_control
            cls.current_chat_data_filename = chat_list_control.data
        # 构建组件
        cls.chat_details.content = ft.Stack(
            [
                ft.Column(
                    [
                        ft.Container(height=32),    # 用于占位
                    ], 
                    ref=cls.chat_details_messages,
                    spacing=5,
                    scroll=ft.ScrollMode.AUTO,
                    auto_scroll=True,
                ),
                cls.create_chat_details_sub_info_panel(cls.current_chat_data_filename),
            ],
        )
        # 加载对应会话的聊天数据
        cls.chat_details_data = app_chat_utils.get_chat_details_data_with_filename(cls.current_chat_data_filename)
        # 渲染聊天内容
        cls.render_chat_details_data()
    
    @classmethod
    def create_chat_details_sub_info_panel(cls, filename):
        """
        聊天基础详情的信息组件
        """
        chat_detail_info_panel = ft.Container(
            ft.Row(
                [
                    ft.TextField(
                        value=filename[33:-5], 
                        expand=True, 
                        height=32,
                        text_size=14,
                        content_padding=ft.Padding(left=5, top=0, right=5, bottom=0),
                        border=ft.InputBorder.OUTLINE,
                        border_color=ft.Colors.TRANSPARENT,
                        # Flet 默认主题的容器背景色 ft.Colors.SURFACE
                        bgcolor=ft.Colors.SURFACE,
                        ref=cls.chat_details_title,
                        on_focus=cls.chat_details_title_boder_enable,
                        on_blur=cls.chat_details_title_boder_disable,
                        data=filename,
                    ),
                    # ft.Button(content="重命名"),
                ],
            ),
            # border_radius=5,
            # border=ft.Border.all(width=1),
            # padding=ft.Padding.symmetric(vertical=2, horizontal=5),
            margin=ft.Margin.symmetric(vertical=0, horizontal=10),
        )
        return chat_detail_info_panel
        
    @classmethod
    def chat_details_title_boder_enable(cls, e):
        """
        显示边框
        """
        cls.chat_details_title.current.border_color = ft.Colors.BLACK
    
    @classmethod
    def chat_details_title_boder_disable(cls, e):
        """
        隐藏边框并决定同步修改信息

        Notes:
        - e.control / cls.chat_details_title 都是 ft.TextField 对象
        - cls.chat_list_control 是 ft.ListTile 对象
        - cls.chat_list_control 有两个 data, 一个是 cls.chat_list_control.data; 另一个是 cls.chat_list_control.trailing.data (用于指定删除的文件)
        """
        cls.chat_details_title.current.border_color = ft.Colors.TRANSPARENT
        # 获取新标题名 & 构建文件名
        new_summary_title = e.control.value
        # 安全处理新标题名
        new_summary_title = app_chat_utils.generate_safe_filename(original_string=new_summary_title)
        new_filename = f"{cls.current_chat_data_filename[:32]}_{new_summary_title}.json"
        old_filename = deepcopy(cls.current_chat_data_filename)
        # 更新 chat_details_title
        cls.chat_details_title.current.value = new_summary_title    # 更新标题
        cls.chat_details_title.current.data = new_filename          # 更新组件的 data 为新的文件名
        # 更新 cls.chat_list_control
        cls.chat_list_control.title = new_summary_title             # 界面显示
        cls.chat_list_control.data = new_filename                   # 用于加载文件
        cls.chat_list_control.trailing.data = new_filename          # 用于删除文件
        # 重命名文件 & 同步信息
        app_chat_utils.sync_chat_list_by_rename(old_filename, new_filename)
        cls.current_chat_data_filename = new_filename

    @classmethod
    async def chat_details_title_summary(cls, old_summary_filename, chat_details_data, force=False):
        """
        基于当前会话内容来总结标题

        Args:
        - old_summary_filename: 总结的标题是基于哪个对话文件的
        - chat_details_data:    总结的标题是基于哪个对话数据
        - force:                是否强制执行
        """
        chat_details_msg = chat_details_data["messages"]
        chat_data_id = old_summary_filename[:32]
        # 利用 messages 中 role 中的 user 数量来决定是否启动总结
        role_user = 0
        if force is False:
            for msg in chat_details_msg:
                if msg.get("role") == "user":
                    role_user += 1
                if role_user >= 2:
                    # 只要超过2个就可以直接退出了
                    break
        # 判断是否执行标题总结 - 只有首次对话或触发强制执行时才会执行标题总结
        if role_user <=1 or force is True:
            # 总结标题
            summary_prompt = {"role": "user", "content":[{"type": "text", "text": "用最精简的语言总结对话内容并作为标题, 字数尽可能压缩在15个字以内, 不要包含任何标点符号"}]}
            summary_for_messages = chat_details_msg + [summary_prompt]      # 不用再次 deepcopy, 追加就行
            logger.debug("Summarizing the chat title...")
            summary_response = await app_agent.agent_summary.ainvoke(summary_for_messages)
            summary_title = summary_response.content
            # 安全处理标题
            summary_title = app_chat_utils.generate_safe_filename(original_string=summary_title)
            new_summary_filename = f"{chat_data_id}_{summary_title}.json"
            logger.debug(f"Summary title is {summary_title}")
            # 重命名文件
            app_chat_utils.sync_chat_list_by_rename(old_summary_filename, new_summary_filename)
            # 基于实际情况来刷新数据
            if cls.chat_details_title.current.data == old_summary_filename:
                # 如果用户没切换会话, 则更新标题名
                cls.chat_details_title.current.value = summary_title        # 界面显示
                cls.chat_details_title.current.data = new_summary_filename  # 维护信息
                cls.current_chat_data_filename = new_summary_filename       # 维护信息
            if cls.chat_list_control.data[:32] == chat_data_id:
                # 如果用户没切换会话, 则更新标题和内部指向数据
                cls.chat_list_control.title = summary_title                 # 界面显示
                cls.chat_list_control.data = new_summary_filename           # 用于加载文件
                cls.chat_list_control.trailing.data = new_summary_filename  # 用于删除文件
            else:
                # 如果用户切换了会话, 则找到改组件并修改对应的值
                from src.components.chat_with_chat_list import ChatList
                all_chat_list = ChatList.chat_list_get()
                for chat_list in all_chat_list:
                    if chat_list.data[:32] == chat_data_id:
                        chat_list.title = summary_title                     # 界面显示
                        chat_list.data = new_summary_filename               # 用于加载文件
                        chat_list.trailing.data = new_summary_filename      # 用于删除文件
            # 刷新界面
            cls.page.update()
    
    @classmethod
    def render_chat_details_data(cls):
        """
        针对已有的 chat_ddetails_data 数据来渲染内容
        """
        if len(cls.chat_details_data["messages"]) != 0:
            for msg_dict in cls.chat_details_data["messages"]:
                # User Message
                if msg_dict.get("role") == "user":
                    user_blk = cls.add_blk_with_user(user_message=msg_dict)
                    cls.add_blk_with_sub_tools(data=user_blk.data, type="user_message", flet_blk=user_blk)
                # AI Thinking Message
                if msg_dict.get("role") == "assistant" and msg_dict.get("additional_kwargs").get("reasoning_content") is not None:
                    lc_run_id = msg_dict.get("additional_kwargs").get("id")
                    content=msg_dict.get("additional_kwargs").get("reasoning_content")
                    cls.add_blk_with_think(lc_run_id=lc_run_id, content=content)
                # AI Tool Calls
                if msg_dict.get("role") == "assistant" and msg_dict.get("tool_calls") not in ["", [], None]:
                    tool_calls = msg_dict.get("tool_calls")
                    additional_kwargs = msg_dict.get("additional_kwargs")
                    cls.add_blk_with_tool_calls(tool_calls=tool_calls, additional_kwargs=additional_kwargs)
                # Tool Message
                if msg_dict.get("role") == "tool":
                    cls.update_blk_with_tool_calls(tool_message=msg_dict)
                # AI Message
                if msg_dict.get("role") == "assistant" and msg_dict.get("content").strip() not in ["", None]:
                    lc_run_id = msg_dict.get("additional_kwargs").get("id")
                    content = msg_dict.get("content")
                    ai_message_blk = cls.add_blk_with_agent(lc_run_id=lc_run_id, content=content)
                    cls.add_blk_with_sub_tools(data=ai_message_blk.data, type="ai_message", flet_blk=ai_message_blk)
    
    @classmethod
    def add_blk_with_user(cls, user_message: dict):
        """
        创建一个 user message 消息块

        Args:
        - user_message
        """
        # 多模态/抽取内容
        render_md_text = ""
        lc_run_id = user_message.get("additional_kwargs").get("id")
        user_message_content = user_message.get("content")
        images_list = []

        for data in user_message_content:
            # 文本内容
            if data.get("type") == "text":
                render_md_text += data.get("text")
            # 图片数据
            if data.get("type") == "image":
                images_list.append(data.get("url"))
        # 创建组件
        user_msg_blk = ft.Container(
            ft.Column(
                [
                    ft.Container(         
                        ft.Markdown(
                            value=render_md_text,
                            selectable=True,
                            extension_set=ft.MarkdownExtensionSet.GITHUB_WEB,
                            code_theme=ft.MarkdownCodeTheme.GITHUB,
                            code_style_sheet=ft.MarkdownStyleSheet(
                                code_text_style=ft.TextStyle(font_family="Consolas")
                            ),
                        ),
                        bgcolor=ft.Colors.GREEN_100,
                        border_radius=5,
                        padding=ft.Padding.symmetric(vertical=3, horizontal=3),
                    ),
                ],
                alignment=ft.MainAxisAlignment.END,
                horizontal_alignment=ft.CrossAxisAlignment.END,
                spacing=3,
            ),
            data={"lc_run_id": lc_run_id, "type": "user_message"},
            margin=ft.Margin.symmetric(vertical=0, horizontal=20),
            border_radius=5,
            # border=ft.Border.all(width=1, color=ft.Colors.RED),
        )
        # 添加图片信息
        if len(images_list) > 0:
            for image in images_list:
                bytes_src = base64.b64decode(image.split("base64,")[-1])
                user_msg_blk.content.controls.append(
                    ft.Container(
                        ft.Row(
                            [
                                # 图片内容
                                ft.Container(
                                    ft.Image(
                                        src=bytes_src,
                                        fit=ft.BoxFit.SCALE_DOWN,
                                    ),
                                    expand=True,
                                    expand_loose=True,
                                    alignment=ft.Alignment.CENTER_RIGHT,
                                ),
                            ],
                        ),
                    )
                )
        # 添加列表
        cls.chat_details_messages.current.controls.append(user_msg_blk)
        # 返回消息块    
        return user_msg_blk     

    @classmethod
    def add_blk_with_think(cls, lc_run_id, content=""):
        """
        添加一个 think 消息块

        Args:
        - lc_run_id:    LangChain 流式结果的 id, 格式为 "lc_run--****"
        - content:      文本内容
        """
        # 字体风格
        style_sheet = ft.MarkdownStyleSheet(p_text_style=ft.TextStyle(size=12, font_family="Consolas", color=ft.Colors.GREY_700))
        # 消息块
        agent_think_msg_blk = ft.Container(
            ft.ExpansionTile(
                title="Thinking",
                controls=[
                    ft.Container(
                        ft.Markdown(
                            value=content,
                            extension_set=ft.MarkdownExtensionSet.GITHUB_WEB,
                            md_style_sheet=style_sheet,
                        ),
                        alignment=ft.Alignment.TOP_LEFT,
                        padding=ft.Padding.symmetric(vertical=4, horizontal=10),
                    ),
                ],
                tile_padding=5,
                dense=True,
            ),
            margin=ft.Margin.symmetric(vertical=0, horizontal=20),
            data={"lc_run_id": lc_run_id, "type": "ai_think"}
        )
        # 添加列表
        cls.chat_details_messages.current.controls.append(agent_think_msg_blk)
        # 返回消息块
        return agent_think_msg_blk

    @classmethod
    def add_blk_with_agent(cls, lc_run_id, content=""):
        """
        添加一个 agent message 消息块

        Args:
        - lc_run_id:    LangChain 流式结果的 id, 格式为 "lc_run--****"
        - content:      文本内容
        """
        agent_msg_blk = ft.Container(
            ft.Column(
                [
                    ft.Container(
                        ft.Markdown(
                            value=content,
                            selectable=True,
                            extension_set=ft.MarkdownExtensionSet.GITHUB_WEB,
                            code_theme=ft.MarkdownCodeTheme.GITHUB,
                            code_style_sheet=ft.MarkdownStyleSheet(
                                code_text_style=ft.TextStyle(font_family="Consolas")
                            ),
                        ),
                        bgcolor=ft.Colors.GREY_200,
                        expand=True,
                        alignment=ft.Alignment.TOP_LEFT,
                        padding=ft.Padding.symmetric(vertical=3, horizontal=3),
                        border_radius=5,
                    ),
                ],
                spacing=3,
            ),
            data={"lc_run_id": lc_run_id, "type": "ai_message"},
            margin=ft.Margin.symmetric(vertical=0, horizontal=20),
            # border=ft.Border.all(width=1, color=ft.Colors.RED),
        )
        # 添加列表
        cls.chat_details_messages.current.controls.append(agent_msg_blk)
        # 返回消息块
        return agent_msg_blk
    
    @classmethod
    def add_blk_with_tool_calls(cls, tool_calls:list, additional_kwargs:dict):
        """
        创建并添加一个 "工具调用" 消息块

        Args:
        - tool_calls:           AIMessage 中的 tool_calls 列表
        - additional_kwargs:    AIMessage 中的 additional_kwargs 字典
        """
        for tool_call in tool_calls:
            # 调试日志
            logger.trace(tool_call)
            # 抽取数据
            lc_run_id = additional_kwargs.get("id")
            tool_call_id = tool_call.get("id")
            tool_call_name = tool_call.get("name")
            tool_call_args = tool_call.get("args")
            # 实际内容
            tool_call_title = ft.Row([], spacing=5)
            for idx, call_value in enumerate([tool_call_id, tool_call_name, tool_call_args]):
                if idx == 0:
                    bgcolor = ft.Colors.GREY
                elif idx == 1:
                    bgcolor = ft.Colors.GREEN
                elif idx == 2:
                    bgcolor = ft.Colors.BLUE
                tool_call_text = ft.Container(
                    ft.Text(
                        value=call_value,
                        color=ft.Colors.WHITE,
                        font_family="Consolas",
                    ),
                    border_radius=5,
                    bgcolor=bgcolor,
                    padding=ft.Padding.symmetric(horizontal=4, vertical=2),
                )
                tool_call_title.controls.append(tool_call_text)
            # 组合控件
            tool_call_blk = ft.Container(
                ft.ExpansionTile(
                    title=tool_call_title,
                    # 空着占位
                    controls=[],
                    # https://flet.dev/docs/controls/expansiontile/#flet.ExpansionTile.tile_padding
                    # 不设置默认为 ft.Padding.symmetric(horizontal=16.0)
                    tile_padding=5,
                    dense=True,
                ),
                # 对该组件做标记, 用于未来的定位和回滚
                data={"tool_call_id":tool_call_id, "lc_run_id": lc_run_id, "type": "ai_tool_call"},
                margin=ft.Margin.symmetric(vertical=0, horizontal=20),
                # padding=ft.Padding.symmetric(vertical=2, horizontal=5),
            )
            # 添加进 chat_details_messages 中
            cls.chat_details_messages.current.controls.append(tool_call_blk)
    
    @classmethod
    def add_blk_with_error(cls, content):
        """
        添加一个 error 消息块
        """
        # 生成一个 uuid
        id = str(uuid.uuid4())
        # 错误消息块
        error_blk = ft.Container(
            ft.ListTile(
                title="Error",
                subtitle=content,
                bgcolor=ft.Colors.RED_50,
                # trailing=ft.Icon(ft.Icons.CANCEL),
                is_three_line=True,
                content_padding=5,
            ),
            data={"lc_run_id": id, "type": "error"},
            margin=ft.Margin.symmetric(vertical=0, horizontal=20),
            # border=ft.Border.all(width=1),
            border_radius=5,
        )
        # 添加进 chat_details_messages 中
        cls.chat_details_messages.current.controls.append(error_blk)
    
    @classmethod
    def add_blk_with_sub_tools(cls, data, type, flet_blk=None):
        """
        为每个消息块中添加一个控制条
        如果提供了对应的控件(flet_blk), 则添加到指定控件中, 否则默认添加到最后

        Args:
        - data:     需要传递的字典数据
        - type:     控件类型, 可以是 "ai_message" 或 "user_message"
        - flet_blk: 对应的 flet container 控件对象, 需要是消息块
        """
        tool_copy = ft.IconButton(
            icon=ft.Icon(ft.Icons.COPY, size=16),
            data=data, 
            icon_size=18,
            padding=0,
            height=26,  # 强制压缩高度
            width=26,   # 强制压缩宽度   
            on_click=cls.blk_sub_tools_by_copy,
        )
        tool_retry = ft.IconButton(
            icon=ft.Icon(ft.Icons.AUTORENEW, size=16),
            data=data, 
            icon_size=18,
            padding=0,
            height=26,  # 强制压缩高度
            width=26,   # 强制压缩宽度
            on_click=cls.blk_sub_tools_by_retry,
        )
        tool_edit = ft.IconButton(
            icon=ft.Icon(ft.Icons.EDIT_OUTLINED, size=16),
            data=data, 
            icon_size=18,
            padding=0,
            height=26,  # 强制压缩高度
            width=26,   # 强制压缩宽度
            on_click=cls.blk_sub_tools_by_edit,
        )
        # 生成对应的工具栏组件
        if type == "ai_message":
            blk_sub_tools = ft.Container(
                ft.Row(
                    [tool_copy, tool_retry],
                    spacing=0,
                ),
                # border=ft.Border.all(width=1),
            )
        elif type == "user_message":
            blk_sub_tools = ft.Container(
                ft.Row(
                    [tool_copy, tool_retry, tool_edit],
                    spacing=0,
                    alignment=ft.MainAxisAlignment.END,
                ),
                # border=ft.Border.all(width=1),
            )
        # 如果提供了对应的控件, 则添加到指定控件中, 否则默认添加到最后
        if flet_blk:
            flet_blk.content.controls.append(blk_sub_tools)
        else:
            cls.chat_details_messages.current.controls[-1].content.controls.append(blk_sub_tools)

    @classmethod
    def update_blk_with_think(cls, think_msg_blk, content):
        """
        基于已有的 think message 消息块 更新内容

        Args:
        - think_msg_blk: Flet think message 的消息控件
        - content:       最新的流式内容
        """
        think_msg_blk.content.controls[0].content.value += content

    @classmethod
    def update_blk_with_agent(cls, agent_msg_blk, content):
        """
        基于已有的 agent message 消息块 更新内容

        Args:
        - agent_msg_blk: Flet agent message 的消息控件
        - content:       最新的流式内容
        """
        agent_msg_blk.content.controls[0].content.value += content

    @classmethod
    def update_blk_with_tool_calls(cls, tool_message:dict):
        """
        基于 tool_message 显示更新内容
        """
        logger.trace(tool_message)
        # 抽取数据
        tool_call_id = tool_message.get("tool_call_id")
        tool_call_name = tool_message.get("name")
        tool_call_content = tool_message.get("content")
        tool_call_status = tool_message.get("status")
        # 处理数据
        if tool_call_content in ["", "[]", None]:
            tool_call_content = ""
        # 优化显示内容
        render_markdown = ""
        # 文件操作相关
        if tool_call_name in ["ls", "glob"] and tool_call_content != "":
            # 转换成列表, 比 eval() 安全
            # https://docs.python.org/zh-cn/3.14/library/ast.html#ast.literal_eval
            tool_call_content = ast.literal_eval(tool_call_content)
            for item_content in tool_call_content:
                render_markdown += item_content + "\n\n"
        # 最后兜底, 原样显示
        else:
            render_markdown = tool_call_content
        # 组装控件
        style_sheet = ft.MarkdownStyleSheet(
            p_text_style=ft.TextStyle(size=12, font_family="Consolas", color=ft.Colors.GREY_700),
        )
        tool_call_response = ft.Container(
            ft.Markdown(
                value=render_markdown,
                extension_set=ft.MarkdownExtensionSet.GITHUB_WEB,
                md_style_sheet=style_sheet,
            ),
            alignment=ft.Alignment.TOP_LEFT,
            padding=ft.Padding.symmetric(vertical=4, horizontal=10),
        )
        # 刷新 Tool Calls 内容
        controls = cls.chat_details_messages.current.controls
        tool_call_container = next((x for x in reversed(controls) if x.data.get("tool_call_id") == tool_call_id), None)
        if tool_call_container is not None:
            tool_call_container.content.controls.append(tool_call_response)

    @classmethod
    async def blk_sub_tools_by_copy(cls, e):
        """
        复制内容到剪贴板
        """
        data = e.control.data
        controls = cls.chat_details_messages.current.controls
        # 寻找当前控件
        # 原则上通过 e.control.parent.parent.parent.parent 应该也可以拿到该组件, 但如果 UI 布局发生变化, 这个方法需要调整更多内容
        copy_container = next((x for x in reversed(controls) if x.data is not None and x.data.get("lc_run_id") == data.get("lc_run_id")), None)
        if copy_container is not None:
            if data.get("type") == "ai_message":
                content = copy_container.content.controls[0].content.value
            elif data.get("type") == "user_message":
                content = copy_container.content.controls[0].content.value
            await ft.Clipboard().set(value=content)
    
    @classmethod
    def blk_sub_tools_by_retry(cls, e):
        """
        让模型重新回复
        """
        data = e.control.data
        controls = cls.chat_details_messages.current.controls
        # 如果当前控件类型是 AI Message, 则向上寻找距离最近的 User Message
        if data.get("type") == "ai_message":
            # 原则上通过 e.control.parent.parent.parent.parent 应该也可以拿到该组件, 但如果 UI 布局发生变化, 这个方法需要调整更多内容
            retry_container = next((x for x in reversed(controls) if x.data is not None and x.data.get("lc_run_id") == data.get("lc_run_id")), None)
            retry_idx = controls.index(retry_container)
            controls = controls[:retry_idx + 1]
            user_message_container = next((x for x in reversed(controls) if x.data is not None and x.data.get("type") == "user_message"), None)
        # 如果当前控件类型是 User Message, 则直接使用此控件
        elif data.get("type") == "user_message":
            # 原则上通过 e.control.parent.parent.parent.parent 应该也可以拿到该组件, 但如果 UI 布局发生变化, 这个方法需要调整更多内容
            user_message_container = next((x for x in reversed(controls) if x.data is not None and x.data.get("lc_run_id") == data.get("lc_run_id")), None)
        # 如果 User Message 非空
        if user_message_container:
            user_message_data = user_message_container.data
            # 更新界面
            end_idx = cls.chat_details_messages.current.controls.index(user_message_container) + 1
            cls.chat_details_messages.current.controls = cls.chat_details_messages.current.controls[:end_idx]
            # 更新数据
            new_messages = []
            for message in cls.chat_details_data["messages"]:
                new_messages.append(message)
                if message.get("additional_kwargs").get("id") == user_message_data.get("lc_run_id"):
                    break
            cls.chat_details_data["messages"] = new_messages
            # 发送请求
            cls.send_user_message(retry=True)

    @classmethod
    def blk_sub_tools_by_edit(cls, e):
        """
        Message 修改按钮
        """
        data = e.control.data
        controls = cls.chat_details_messages.current.controls
        edit_column = e.control.parent.parent.parent
        old_message_text = deepcopy(edit_column.controls[0])
        old_message_tool = deepcopy(edit_column.controls[1])
        # 可修改的内容区域
        new_message_text = ft.Container(
            ft.TextField(
                value=old_message_text.content.value,
                multiline=True,
                max_lines=3,
                expand=True,
            ),
        )
        # 内嵌函数
        def click_cancel(e):
            edit_column.controls[0] = old_message_text
            edit_column.controls[1] = old_message_tool
        def click_save(e):
            new_content = new_message_text.content.value
            old_message_text.content.value = new_content
            edit_column.controls[0] = old_message_text
            edit_column.controls[1] = old_message_tool
            # 修改数据
            for message in cls.chat_details_data["messages"]:
                if message.get("role") == "user" and message.get("additional_kwargs").get("id") == data.get("lc_run_id"):
                    for msg in message["content"]:
                        if msg.get("type") == "text":
                            msg["text"] = new_content
                            break
                    break
            # 保存数据
            app_chat_utils.save_chat_details_data_with_filename(cls.current_chat_data_filename, cls.chat_details_data)

        # 工具栏
        new_message_tool = ft.Container(
            ft.Row(
                [
                    ft.IconButton(
                        icon=ft.Icon(ft.Icons.CLOSE, size=16),
                        data=data, 
                        icon_size=18,
                        padding=0,
                        height=26,  # 强制压缩高度
                        width=26,   # 强制压缩宽度   
                        on_click=click_cancel,
                    ),
                    ft.IconButton(
                        icon=ft.Icon(ft.Icons.CHECK, size=16),
                        data=data, 
                        icon_size=18,
                        padding=0,
                        height=26,  # 强制压缩高度
                        width=26,   # 强制压缩宽度   
                        on_click=click_save,
                    ),
                ],
                spacing=0,
                alignment=ft.MainAxisAlignment.END,
            ),
        )
        # 刷新替换
        edit_column.controls[0] = new_message_text
        edit_column.controls[1] = new_message_tool
    
    @classmethod
    def send_user_message(cls, user_message_by_text=None, retry=False):
        """
        发送用户内容
        """
        # 用户输入的消息不能为空, 并且不是重新发送
        if user_message_by_text and retry is False:
            # 构建完整的用户消息数据
            id = str(uuid.uuid4())
            user_message = {"role": "user", "content":[{"type": "text", "text": user_message_by_text}], "additional_kwargs": {"id": id}}
            prefix = cls.chat_list_control.data[:32]
            images = app_chat_utils.get_images_with_temp(session_prefix=prefix)
            # 处理图片
            if images is not None:
                for image in images:
                    image_path = os.path.abspath(os.path.join(app_chat_utils.temp_dir, image))
                    # https://docs.langchain.com/oss/python/langchain/messages#multimodal
                    user_message.get("content").append({"type": "image", "url": app_chat_utils.file_to_base64_uri(image_path)})
            # UI 部分: 更新前会检查最后一个消息组件是否为错误消息块, 如果是则会删掉
            last_control = cls.chat_details_messages.current.controls[-1]
            if last_control.data is not None and last_control.data.get("type") == "error":
                del cls.chat_details_messages.current.controls[-1]
            # UI 部分: 添加新的消息块
            user_blk = cls.add_blk_with_user(user_message=user_message)
            cls.add_blk_with_sub_tools(data=user_blk.data, type="user_message", flet_blk=user_blk)
            # 添加到 chat_details_data["messages"] 中
            cls.chat_details_data["messages"].append(user_message)

        # 更新界面
        cls.page.update()
        # 发送 API 请求
        # https://docs.flet.dev/controls/page/?h=run_ta#flet.Page.render_views
        cls.page.run_task(cls.response_agent_message)

    @classmethod
    async def response_agent_message(cls):
        """
        接收从 LangChain DeepAgents 传回的内容 
        """
        # AI Message 相关
        new_agent_message_blk = None    # 最新的 AI Message 消息块
        new_think_message_blk = None    # 最新的 AI Thinking Message 消息块
        need_create_agent_blk = True    # 标记位
        need_create_think_blk = True    # 标记位: 思考内容
        # 所有待保存的消息 & 初始消息计数
        all_tmp_messages = []
        
        try:
            # 注意 v2 版本: version="v2"
            # https://docs.langchain.com/oss/python/deepagents/streaming#v2-streaming-format
            # v2 版本的 chunk: {"type":<stream_mode>, 'ns':(), "data":(<token>, <metadata>)}
            async for chunk in app_agent.agent_main.astream(input={"messages": cls.chat_details_data["messages"]}, stream_mode=["messages", "updates"], version="v2"):
                # 此标记位为 True 时停止输出
                if cls.need_stop_response:
                    logger.warning(f"AI response was manually interrupted.")
                    from src.components.chat_with_user_input import UserInput
                    UserInput.switch_button_to_send()
                    break
                
                # Main Agent Message
                elif chunk.get("ns") == ():
                    # 每个步骤完成时: 消息类型为 updates
                    if chunk["type"] == "updates":
                        # 重置标记位
                        need_create_agent_blk = True
                        need_create_think_blk = True
                        # 检查 AI Message 是否为全空
                        controls = cls.chat_details_messages.current.controls
                        ai_message_container = next((x for x in reversed(controls) if x.data is not None and x.data.get("type") == "ai_message"), None)
                        if ai_message_container is not None and ai_message_container.content.controls[0].content.value.strip() == "":
                            controls.remove(ai_message_container)
                            cls.page.update()
                            logger.warning("all empty content detected; removing AI Message block.")
                        # AIMessage
                        if chunk["data"].get("model") is not None:
                            # 保存到 all_tmp_messages
                            messages = chunk["data"].get("model").get("messages")
                            for ai_msg in messages:
                                additional_kwargs = ai_msg.additional_kwargs
                                additional_kwargs["id"] = ai_msg.id
                                additional_kwargs["ns"] = ()
                                all_tmp_messages.append({
                                    # AI Response Message
                                    "role": "assistant", "content": ai_msg.content, 
                                    # AI Tool Calls
                                    "tool_calls": ai_msg.tool_calls, "invalid_tool_calls":ai_msg.invalid_tool_calls, 
                                    # AI Thinking & ID & NS
                                    "additional_kwargs": additional_kwargs,
                                })
                            # 渲染界面: Tool_Calls
                            if ai_msg.tool_calls:
                                cls.add_blk_with_tool_calls(tool_calls=ai_msg.tool_calls, additional_kwargs=ai_msg.additional_kwargs)
                            # 渲染界面: AI Message
                            if ai_msg.content.strip() != "":
                                # 将当前最后一个消息块的 data 传给 sub_tools 消息块
                                cls.add_blk_with_sub_tools(
                                    data=cls.chat_details_messages.current.controls[-1].data, 
                                    type="ai_message", 
                                    flet_blk=cls.chat_details_messages.current.controls[-1],
                                )
                                # 刷新界面
                                await cls.chat_details_messages.current.scroll_to(offset=-1, duration=0)
                                cls.page.update()

                        # ToolMessage
                        elif chunk["data"].get("tools") is not None:
                            # 保存到 all_tmp_messages
                            messages = chunk["data"].get("tools").get("messages")
                            for tool_msg in messages:
                                additional_kwargs = tool_msg.additional_kwargs
                                additional_kwargs["id"] = tool_msg.id
                                additional_kwargs["ns"] = ()
                                tool_message = {
                                    "role": "tool", "type": "tool",
                                    "content": tool_msg.content,
                                    "name": tool_msg.name,
                                    "tool_call_id": tool_msg.tool_call_id,
                                    # 'success', 'error'
                                    "status": "success",
                                    "additional_kwargs": additional_kwargs,
                                }
                                all_tmp_messages.append(tool_message)
                            # 渲染界面: Tool_Calls
                            cls.update_blk_with_tool_calls(tool_message=tool_message)

                    # 流式输出: 消息类型为 messages
                    else:
                        if isinstance(chunk.get("data")[0], AIMessageChunk):
                            # 思考文本
                            if chunk.get("data")[0].additional_kwargs.get("reasoning_content"):
                                if need_create_think_blk:
                                    new_think_message_blk = cls.add_blk_with_think(lc_run_id=chunk.get("data")[0].id, content=chunk.get("data")[0].additional_kwargs.get("reasoning_content"))
                                    need_create_agent_blk = True
                                    need_create_think_blk = False
                                cls.update_blk_with_think(think_msg_blk=new_think_message_blk, content=chunk.get("data")[0].additional_kwargs.get("reasoning_content"))
                            # 普通文本
                            elif chunk.get("data")[0].content:
                                if need_create_agent_blk:
                                    new_agent_message_blk = cls.add_blk_with_agent(lc_run_id=chunk.get("data")[0].id, content=chunk.get("data")[0].content)
                                    need_create_agent_blk = False
                                    need_create_think_blk = True
                                cls.update_blk_with_agent(agent_msg_blk=new_agent_message_blk, content=chunk.get("data")[0].content)
                            # 其余内容
                            else:
                                pass
                # Sub Agent Message
                else:
                    pass
                    
                # 渲染/滚动界面
                await cls.chat_details_messages.current.scroll_to(offset=-1, duration=0)
                cls.page.update()

        except Exception as e:
            # 添加一个错误的消息块, 并终止消息产生
            cls.add_blk_with_error(content=str(e))
            await cls.chat_details_messages.current.scroll_to(offset=-1, duration=0)
            cls.page.update()
            logger.error(e)
        
        # 1.复制一份数据, 防止用户此刻点击别的会话
        cp_current_chat_data_filename = deepcopy(cls.current_chat_data_filename)
        cp_chat_details_data = deepcopy(cls.chat_details_data)
        cp_all_tmp_messages = deepcopy(all_tmp_messages)
        # 2.整合数据
        cp_chat_details_data["messages"].extend(cp_all_tmp_messages)
        # 3.保持到 ChatData 中 (这里需要保存复制后的)
        app_chat_utils.save_chat_details_data_with_filename(cp_current_chat_data_filename, cp_chat_details_data)
        # 4.删除 & 刷新 附件列表
        from src.components.chat_with_user_input import UserInput
        app_chat_utils.delete_tempfiles_with_prefix(prefix=cls.chat_list_control.data[:32])
        UserInput.update_attachments(prefix=cls.chat_list_control.data[:32])
        UserInput.switch_button_to_send()
        cls.page.update()
        # 5.重新赋值 (如果此刻用户没有切换对话列表)
        if cls.chat_list_control.data == cp_current_chat_data_filename:
            cls.chat_details_data = cp_chat_details_data
            logger.debug(f"chat history has been saved: {cp_current_chat_data_filename}")
        else:
            logger.warning(f"switch to view chatlist, Skip updating <cls.chat_details_data>")
        # 6.总结标题
        cls.page.run_task(cls.chat_details_title_summary, cp_current_chat_data_filename, cp_chat_details_data)        