# Overview
App-for-DeepAgent 是一个基于 [LangChain/DeepAgents](https://docs.langchain.com/oss/python/deepagents/overview) + [Flet GUI 框架](https://flet.dev/) 开发的纯 Python 应用
- 支持多模态 (可以上传图片, 未来可以继续添加)
- 可以接入任意兼容 openai 和 ollama 类型的 API
- 高度可扩展性, Flet 框架原生为 Python 语言, 可以扩展和对接大量的第三方 Python 库
- 每个对话数据都单独保存为 `json` 文件, 方便转移和备份
- 对话数据均已 `<date>_<uuid[:16]>_<title>.json` 的形式来保存, 方便自行排序和查找

# Dependencies
```Shell
# Flet 框架
pip install -U 'flet[all]' -i https://pypi.tuna.tsinghua.edu.cn/simple
# LangChain 相关组件
pip install -U deepagents
pip install -U langchain-openai
pip install -U langchain-ollama
# 其余内容
pip install -U PyYAML
pip install -U pillow
```

# Running
```Shell
cd <App-for-DeepAgent>
flet run -r main.py
```

# Running effect
软件初始界面
![初始效果](./example/deep_agent_1.png)
支持多模态输入
![聊天对话](./example/deep_agent_2.png)
模型设置界面
![设置界面](./example/deep_agent_3.png)