import flet as ft

class guiEndPoints:
    """
    Flet GUI 暴露的端点类, 用于保存需要跨通信的组件对象
    """
    # 对话界面
    chat = {}
    # 设置界面
    settings = {
        # src.settings_view.SettingsView
        "settings_view_lv1": ft.Ref[ft.Container](),
        "settings_view_lv2": ft.Ref[ft.Container](),
        "settings_view_lv3": ft.Ref[ft.Container](),
    }