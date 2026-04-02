import sys
from pathlib import Path
# sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))
sys.path.append(str(Path(__file__).resolve().parent.parent))

import flet as ft

from views.main_view import MainView

def main(page: ft.Page):
    # Page 全局
    page.padding = 0
    page.spacing = 0
    # Page 全局主题
    # https://docs.flet.dev/types/theme/#flet.Theme
    # page.theme = ft.Theme(
    #     # 字体
    #     font_family="Consolas",
    # )

    # 组件对象
    main_view = MainView(page)

    # 基本布局
    page.add(
        ft.Column(
            [   
                ft.Divider(height=1),
                ft.Row(
                    [   # 导航栏
                        main_view.navigation_rail,
                        ft.VerticalDivider(width=1),
                        # 右侧区域基础视图
                        main_view.right_view,
                    ],
                    expand=True,
                    spacing=0,
                )
            ],
            expand=True,
            spacing=0,
        )
    )

    # 刷新界面
    page.update()

if __name__ == "__main__":
    ft.run(main)