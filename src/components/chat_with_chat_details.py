import os
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
            # padding=ft.Padding.symmetric(vertical=2, horizontal=5),
            margin=ft.Margin.symmetric(vertical=0, horizontal=20),
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
            chat_details_msg.append(summary_prompt)
            logger.debug("Summarizing the chat title...")
            summary_response = await app_agent.agent_summary.ainvoke(chat_details_msg)
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
                    cls.chat_details_messages.current.controls.append(cls.add_user_message_blk(msg_dict.get("content")))
                # AI Message
                elif msg_dict.get("role") == "assistant" and msg_dict.get("content") != "":
                    cls.chat_details_messages.current.controls.append(cls.add_agent_message_blk(msg_dict.get("content")))
                # AI Tool Calls
                elif msg_dict.get("role") == "assistant" and msg_dict.get("tool_calls") is not None:
                    for tool_call in msg_dict.get("tool_calls"):
                        new_tool_calls_message_blk = cls.add_tool_calls_message_blk(tool_call_id=tool_call.get("id"))
                        new_tool_calls_message_blk.content.title = cls.render_tool_calls_title(tool_call=tool_call)
                        cls.chat_details_messages.current.controls.append(new_tool_calls_message_blk)
                # Tools Message
                elif msg_dict.get("role") == "tool":
                    tool_call_id = msg_dict.get("tool_call_id")
                    for blk in cls.chat_details_messages.current.controls:
                        if isinstance(blk.content, ft.ExpansionTile):
                            if blk.content.data == tool_call_id:
                                # blk.content.controls.clear()
                                blk.content.controls.append(cls.render_tool_calls_content(tool_message_or_dict=msg_dict))

    
    @classmethod
    def add_user_message_blk(cls, user_message_content):
        """
        创建一个 user message 消息块

        Args:
        - user_message_content: 列表类型, 是完整用户消息的一部分内容 [{"type": "text", "text":user_message_by_test}]
        """
        # 需要考虑多模态
        render_md_text = ""
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
                    ft.Row(
                        [
                            # 左侧占位
                            ft.Container(expand=True, expand_loose=True),
                            # 右侧内容
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
                                padding=ft.Padding.symmetric(vertical=2, horizontal=5),
                                margin=ft.Margin.symmetric(vertical=0, horizontal=20),
                            ),
                        ],
                    ),
                ],

            )
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
                                    margin=ft.Margin.symmetric(vertical=0, horizontal=20),
                                    expand=True,
                                    expand_loose=True,
                                    alignment=ft.Alignment.CENTER_RIGHT,
                                ),
                            ],
                        ),
                    )
                )
        return user_msg_blk
    
    @classmethod
    def add_agent_message_blk(cls, ai_message=""):
        """
        创建一个 agent message 消息块
        """
        agent_msg_blk = ft.Container(
            ft.Markdown(
                value=ai_message,
                selectable=True,
                extension_set=ft.MarkdownExtensionSet.GITHUB_WEB,
                code_theme=ft.MarkdownCodeTheme.GITHUB,
                code_style_sheet=ft.MarkdownStyleSheet(
                    code_text_style=ft.TextStyle(font_family="Consolas")
                ),
            ),
            bgcolor=ft.Colors.GREY_100,
            alignment=ft.Alignment.TOP_LEFT,
            border_radius=5,
            padding=ft.Padding.symmetric(vertical=2, horizontal=5),
            margin=ft.Margin.symmetric(vertical=0, horizontal=20),
        )
        return agent_msg_blk
    
    @classmethod
    def add_tool_calls_message_blk(cls, tool_call_id=None):
        """
        创建一个 tool calls 消息块

        Args:
        - tool_call_id:     会基于 Tool Message 的 tool_call_id 来渲染内容
        """
        tool_calls_blk = ft.Container(
            ft.ExpansionTile(
                # 这两项为空, 先占位, 后续在添加和调整
                title="",
                controls=[],
                # https://flet.dev/docs/controls/expansiontile/#flet.ExpansionTile.tile_padding
                # 不设置默认为 ft.Padding.symmetric(horizontal=16.0)
                tile_padding=5,
                dense=True,
                data=tool_call_id,
            ),
            # padding=ft.Padding.symmetric(vertical=2, horizontal=5),
            margin=ft.Margin.symmetric(vertical=0, horizontal=20),
        )
        return tool_calls_blk
    
    @classmethod
    def send_user_message(cls, user_message_by_test):
        """
        发送用户内容
        """
        # 构建完整的用户消息数据
        user_message = {"role": "user", "content":[{"type": "text", "text": user_message_by_test}]}
        prefix = cls.chat_list_control.data[:32]
        images = app_chat_utils.get_images_with_temp(session_prefix=prefix)
        # 处理图片
        if images is not None:
            for image in images:
                image_path = os.path.abspath(os.path.join(app_chat_utils.temp_dir, image))
                # https://docs.langchain.com/oss/python/langchain/messages#multimodal
                user_message.get("content").append({"type": "image", "url": app_chat_utils.file_to_base64_uri(image_path)})
        # UI 部分: 只传递 content 部分内容
        cls.chat_details_messages.current.controls.append(cls.add_user_message_blk(user_message.get("content")))
        # 添加到 chat_details_data["messages"] 中
        cls.chat_details_data["messages"].append(user_message)
        # 更新界面
        # cls.page.update()
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
        need_create_agent_blk = True    # 标记位
        # Tool Calls 相关
        tool_calls_blk = {}             # 记录消息块对象
        tool_calls_data = {}            # 保存工具调用数据
        # 临时数据
        ai_text_message = {"role": "assistant", "content": ""}
        tool_messages = []
        
        # 注意 v2 版本: version="v2"
        # https://docs.langchain.com/oss/python/deepagents/streaming#v2-streaming-format
        async for chunk in app_agent.agent_main.astream(input={"messages": cls.chat_details_data["messages"]}, stream_mode=["messages"], version="v2"):
            # v2 版本的 chunk: {"type":<stream_mode>, "data":(<token>, <metadata>)}
            token = chunk["data"][0]
            metadata = chunk["data"][1]

            # 此标记位为 True 时停止输出
            if cls.need_stop_response:
                logger.warning(f"AI response was manually interrupted.")
                from src.components.chat_with_user_input import UserInput
                UserInput.switch_button_to_send()
                break
            
            # AIMessage
            if isinstance(token, AIMessageChunk):
                # 工具调用
                if token.tool_call_chunks:
                    # 循环遍历每一个 tool_call 字典
                    for tool_call in token.tool_call_chunks:
                        # 情况1: 去掉没有 index 的特殊情况
                        index = tool_call.get("index")
                        if not isinstance(index, int):
                            logger.warning(f"tool_call index not int: {index}")
                            continue
                        # 情况2: index 没有在 tool_calls_blk 里
                        if index not in tool_calls_blk:
                            # 创建一个新的 tool_calls 消息块
                            new_tool_calls_blk = cls.add_tool_calls_message_blk()
                            new_tool_calls_blk.content.title =  cls.render_tool_calls_title(tool_call=tool_call)
                            # 使用字典记录该 tool_calls 消息块
                            tool_calls_blk[index] = new_tool_calls_blk
                            # 使用字典记录该 tool_calls 的数据
                            tool_calls_data[index] = {}
                            cls.merge_tool_calls_data(tool_calls_data[index], tool_call)
                            # 添加进 chat_details_messages 的 ft.Column 中
                            cls.chat_details_messages.current.controls.append(new_tool_calls_blk)
                        # 情况3: index 在 tool_calls_blk 里
                        else:
                            cls.merge_tool_calls_data(tool_calls_data[index], tool_call)
                            tool_calls_blk[index].content.title = cls.render_tool_calls_title(tool_call=tool_calls_data[index])
                        # 调试日志
                        logger.debug(f"token.tool_call_chunks: {tool_call}")

                # 普通文本
                elif token.content:
                    # 首次出现
                    if need_create_agent_blk:
                        # 处理消息块
                        new_agent_message_blk = cls.add_agent_message_blk()
                        cls.chat_details_messages.current.controls.append(new_agent_message_blk)
                        need_create_agent_blk = False
                    # UI 渲染
                    new_agent_message_blk.content.value += token.content
                    # 消息存储
                    ai_text_message["content"] += token.content
                    
            # ToolMessage
            elif isinstance(token, ToolMessage):
                # 工具结果
                for idx, tool_call in tool_calls_data.items():
                    if tool_call.get("id") == token.tool_call_id:
                        # UI 渲染
                        # tool_calls_blk[idx].content.controls.clear()
                        tool_calls_blk[idx].content.controls.append(cls.render_tool_calls_content(tool_message_or_dict=token))
                        # 消息存储
                        tool_messages.append({
                            "role": "tool",
                            "name": token.name,
                            "tool_call_id": token.tool_call_id,
                            "content": token.content
                        })
                        # 调试日志
                        logger.debug(f"ToolMessage_{idx}: {tool_call}")
                        break
            
            # 渲染/滚动界面
            await cls.chat_details_messages.current.scroll_to(offset=-1, duration=0)
            cls.page.update()
        
        # 流式对话后统一处理 messages
        # 1.复制一份数据, 防止用户此刻点击别的会话
        current_chat_data_filename = deepcopy(cls.current_chat_data_filename)
        chat_details_data = deepcopy(cls.chat_details_data)
        cp_tool_calls_data = deepcopy(tool_calls_data)
        cp_ai_text_message = deepcopy(ai_text_message)
        cp_tool_messages = deepcopy(tool_messages)
        # 2.如果 AI 尝试 tool_calls, 则创建对应的 {"role": "assistant", "content": "", "tool_calls": []} message
        if cp_tool_calls_data:
            # 建立一个空的 AI ToolCalls Message
            ai_tool_calls_message = {"role": "assistant", "content": "", "tool_calls": []}
            # 补全该 AI ToolCalls Message
            for index in sorted(cp_tool_calls_data.keys()):
                tc = cp_tool_calls_data[index]
                ai_tool_calls_message["tool_calls"].append({
                    "id": tc.get("id"),
                    "type": "function",
                    "function": {"name": tc.get("name", ""), "arguments": tc.get("args", "")},
                })
            # 添加到历史信息里
            chat_details_data["messages"].append(ai_tool_calls_message)
        # 3.Tool Messages
        if len(cp_tool_messages) > 0:
            chat_details_data["messages"].extend(cp_tool_messages)
        # 4.AI 最终文本
        if cp_ai_text_message["content"] != "":
            chat_details_data["messages"].append(cp_ai_text_message)
        # 5.保持到 ChatData 中
        app_chat_utils.save_chat_details_data_with_filename(current_chat_data_filename, chat_details_data)
        # 6.删除 & 刷新 附件列表
        from src.components.chat_with_user_input import UserInput
        app_chat_utils.delete_tempfiles_with_prefix(prefix=cls.chat_list_control.data[:32])
        UserInput.update_attachments(prefix=cls.chat_list_control.data[:32])
        UserInput.switch_button_to_send()
        cls.page.update()
        # 7.重新赋值 (如果此刻用户没有切换对话列表)
        if cls.chat_list_control.data == current_chat_data_filename:
            cls.chat_details_data = chat_details_data
            logger.debug(f"Continue saving chat data; file is: {current_chat_data_filename}")
        else:
            logger.warning(f"User has switch chat list, Skip updating cls.chat_details_data")
        # 8.总结标题
        cls.page.run_task(cls.chat_details_title_summary, current_chat_data_filename, chat_details_data)
        
    @classmethod
    def merge_tool_calls_data(cls, main_data: dict, chunk_data: dict):
        """
        合并流式返回的 tool_call chunk

        Args:
        - main_data:    完整的数据字典
        - chunk_daya:   数据片段
        """
        for k, v in chunk_data.items():
            if v in [None, "", [], {}]:
                continue

            # 如果 args 是分片字符串, 做拼接
            if k == "args" and isinstance(v, str) and isinstance(main_data.get("args"), str):
                main_data["args"] += v
            else:
                main_data[k] = v

    @classmethod
    def render_tool_calls_title(cls, tool_call: dict):
        """
        基于 Tool Calls 字典来渲染显示内容
        """
        logger.debug(f"Tool Call by Title: {tool_call}")
        # 抽取数据: 运行期间
        if tool_call.get("function") is None:
            tool_call_id = tool_call.get("id")
            tool_call_name = tool_call.get("name")
            tool_call_args = tool_call.get("args")
        # 抽取数据: 从文件里读取数据
        else:
            tool_call_id = tool_call.get("id")
            tool_call_name = tool_call.get("function").get("name")
            tool_call_args = tool_call.get("function").get("arguments")            
        # 组装显示内容
        tool_call_title = ft.Row([], spacing=5)
        for idx, call_value in enumerate([tool_call_id, tool_call_name, tool_call_args]):
            if call_value is not None:
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
                    bgcolor=bgcolor,
                    padding=ft.Padding.symmetric(horizontal=4, vertical=2),
                    border_radius=5,
                )
                tool_call_title.controls.append(tool_call_text)
        # 返回 tool_call_title 对象
        return tool_call_title

    @classmethod
    def render_tool_calls_content(cls, tool_message_or_dict):
        """
        基于 ToolMessage 或 Dict 渲染显示内容
        """
        logger.debug(f"Tool Call by Content: {type(tool_message_or_dict)} | {tool_message_or_dict}")
        # 抽取数据: 运行期间
        if isinstance(tool_message_or_dict, ToolMessage):
            tool_call_id = tool_message_or_dict.tool_call_id
            tool_call_name = tool_message_or_dict.name
            too_call_content = tool_message_or_dict.content
            logger.warning(f"id: {tool_call_id}")
            logger.warning(f"name: {tool_call_name}")
            logger.warning(f"content: {too_call_content}")
        # 抽取数据: 从文件里读取数据
        elif isinstance(tool_message_or_dict, dict):
            tool_call_id = tool_message_or_dict.get("tool_call_id")
            tool_call_name = tool_message_or_dict.get("name")
            too_call_content = tool_message_or_dict.get("content")
            logger.warning(f"id: {tool_call_id}")
            logger.warning(f"name: {tool_call_name}")
            logger.warning(f"content: {too_call_content}")
        # 渲染数据
        tool_call_response = ft.Container(
            ft.Markdown(value=too_call_content)
        )

        return tool_call_response