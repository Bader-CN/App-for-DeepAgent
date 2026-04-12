import re
import json

import flet as ft

from src.utils.log import logger
from src.utils.globals import app_chat_utils
from src.components.chat_with_chat_details import ChatDetails
from src.components.chat_with_user_input import UserInput

class ChatList:
    # 类变量: 页面布局
    chat_listview = None

    @classmethod
    def create_chat_list_component(cls):
        """
        会话列表组件
        """
        # 获取当前会话列表(已排序)
        chat_list_ids = app_chat_utils.get_chat_list_with_sort()
        chat_list_files = app_chat_utils.chat_list_with_file

        # 对话列表
        chat_listview = ft.ReorderableListView(
            show_default_drag_handles=False,
            on_reorder=cls.chat_list_handle_reorder,
        )
        cls.chat_listview = chat_listview
        # 构建组件
        cls.create_chat_list_sub_component(chat_list_ids, chat_list_files)
        
        return cls.chat_listview
    
    @classmethod
    def create_chat_list_sub_component(cls, chat_list_ids, chat_list_files):
        """
        基于对话列表 "索引 & 文件" 创建每一个子控件
        """
        for id in chat_list_ids:
            # 获取完整的文件路径
            file = ""
            for file in chat_list_files:
                if re.findall(str(id), file):
                    filename = file
                    break
            # 基于完整的文件路径截取显示名
            # 基于 id 来切分, 并去掉文件尾部的 ".json"
            title = filename.split(str(id))[-1][1:-5]
            # 构建每一个子项
            cls.chat_listview.controls.append(
                ft.ListTile(
                    title=title,
                    title_text_style=ft.TextStyle(font_family="Microsoft YaHei", size=13, color=ft.Colors.BLACK),
                    leading=ft.ReorderableDragHandle(
                        content=ft.Icon(ft.Icons.DRAG_INDICATOR, color=ft.Colors.GREY_500),
                        mouse_cursor=ft.MouseCursor.GRAB,
                    ),
                    trailing=ft.IconButton(
                        ft.Icons.DELETE_FOREVER_OUTLINED, icon_color=ft.Colors.GREY_500, 
                        icon_size=18,
                        data=filename, 
                        # ListTile.trailing.data 用于删除
                        on_click=cls.chat_list_delete),
                    horizontal_spacing=5,
                    content_padding=5,
                    dense=True,
                    hover_color=ft.Colors.BLUE_GREY_50,
                    toggle_inputs=True,
                    # ListTile.data 用于加载指定文件
                    data=filename,
                    visual_density=ft.VisualDensity.COMPACT,
                    on_click=cls.render_chat_details,
                )
            )
            # 首次渲染一下 Chat Details
            cls.render_chat_details_by_init()

    @classmethod
    def chat_list_handle_reorder(cls, e):
        """
        基于视图来更新配置中 "对话列表" 的排序
        """
        chat_list_ids = app_chat_utils.chat_list_with_sort_ids
        chat_list_ids[e.old_index], chat_list_ids[e.new_index] = chat_list_ids[e.new_index], chat_list_ids[e.old_index]
        with open(app_chat_utils.sort_file, "w", encoding="utf-8") as f:
            json.dump(chat_list_ids, fp=f)
            f.flush()
        logger.debug("Flush chat_list_ids finish.")

    @classmethod
    def chat_list_get(cls):
        """
        获取当前所有的对话列表
        """
        return cls.chat_listview.controls
    
    @classmethod
    def chat_list_update(cls):
        """
        基于已有的数据进行刷新, 刷新阶段不需要从文件里读取
        """
        # 获取当前会话列表(已排序) & 带有完整路径的会话文件列表
        chat_list_ids = app_chat_utils.chat_list_with_sort_ids
        chat_list_files = app_chat_utils.chat_list_with_file
        # 清空布局
        cls.chat_listview.controls.clear()
        # 构建组件
        cls.create_chat_list_sub_component(chat_list_ids, chat_list_files)
    
    @classmethod
    def chat_list_add(cls, e):
        """
        添加一个聊天列表
        """
        # 新增一个对话列表
        app_chat_utils.generate_unique_chatfile()
        cls.chat_list_update()
        # 刷新对话详情 (显示当前最后一个)
        last_chat_list_control = cls.chat_listview.controls[-1]
        ChatDetails.create_chat_details_component(chat_list_control=last_chat_list_control)
    
    @classmethod
    def chat_list_delete(cls, e):
        # 必须大于等于2个的时候才能删除
        if len(cls.chat_listview.controls) >= 2:
            # 值可以通过 e.control.data 获取
            app_chat_utils.sync_chat_list_by_delete(filename=e.control.data)
            cls.chat_list_update()
            ChatDetails.clear_chat_details_component()
            # 刷新对话详情 (显示当前最后一个)
            last_chat_list_control = cls.chat_listview.controls[-1]
            ChatDetails.create_chat_details_component(chat_list_control=last_chat_list_control)
    
    @classmethod
    def render_chat_details(cls, e):
        """
        渲染聊天详情
        """
        ChatDetails.create_chat_details_component(e)
        UserInput.update_attachments(prefix=e.control.data[:32])

    @classmethod
    def render_chat_details_by_init(cls):
        """
        首次渲染聊天详情
        """
        # ChatList 的第一个对话控件
        first_chat_list_control = cls.chat_listview.controls[0]
        ChatDetails.create_chat_details_component(chat_list_control=first_chat_list_control)
        UserInput.update_attachments(prefix=first_chat_list_control.data[:32])