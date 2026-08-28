import re
import gradio as gr
from Agent.ReAct import ReActAgent
from Models.Factory import ChatModelFactory
from Tools.Tools import *
from langchain_community.chat_message_histories.in_memory import ChatMessageHistory


# 复用 app.py 中的核心启动逻辑
def launch_agent(query, agent, uuid=1001):
    chat_history = ChatMessageHistory()
    # 注意：verbose=True 会在控制台打印详细思考过程，Gradio 中可根据需要调整
    reply = agent.execute(query, uuid, chat_history=chat_history, verbose=True)
    return reply


def predict(query, uuid):
    if not query:
        return "请输入文本"

    try:
        # 初始化模型和工具 (与 app.py 保持一致)
        llm = ChatModelFactory().get_model()
        tools = [
            rag_qa_tool,
            report_generation_tool,
        ]

        # 初始化 Agent
        agent = ReActAgent(
            llm=llm,
            tools=tools,
            main_prompt_file_path="prompts/main.txt"
        )

        # 执行代理逻辑
        response = launch_agent(query, agent, uuid)

        # 复用原有的正则清洗逻辑，去除思维链标签
        answer = response
        if '<think>' in response and "</think>" in response:
            # 匹配 <think>...</think> 并移除
            answer = re.sub(r"<think>.*?</think>", "", response, flags=re.DOTALL)
        elif '<think>' in response and "</think>\n\n答：" in response:
            # 匹配特定格式 <think>...</think>\n\n 答：并移除
            answer = re.sub(r"<think>.*?</think>\n\n答：", "", response, flags=re.DOTALL)

        # 清理可能残留的首尾空白
        answer = answer.strip()

        return answer

    except Exception as e:
        return f"发生错误：{str(e)}"


# 构建 Gradio 界面
with gr.Blocks(title="InsightScan 智扫通系统") as demo:
    gr.Markdown("# InsightScan智扫通Agent系统")
    gr.Markdown("请输入您的问题，系统将调用AI Agent 进行扫地机器人产品的智能分析与回答。")

    with gr.Row():
        with gr.Column(scale=4):
            input_box = gr.Textbox(
                label="用户提问",
                placeholder="请输入您需要查询或生成报告的内容...",
                lines=4
            )
            uuid_box = gr.Number(label="用户 UUID", value=1001, visible=False)  # 默认隐藏，保持后端兼容

            submit_btn = gr.Button("开始分析", variant="primary")
            example_list = ["这个扫地机器人能扫哪些地面？", "app里面清洁记录作用是什么",
                            "根据我的扫地机器人的使用情况，生成一份使用报告,要2025年6月份的"]
            gr.Examples(examples=example_list, inputs=input_box)


        with gr.Column(scale=6):
            output_box = gr.Markdown(label="系统回答", line_breaks=True)

    # 绑定事件
    submit_btn.click(
        fn=predict,
        inputs=[input_box, uuid_box],
        outputs=output_box
    )

    # 支持按 Enter 键提交
    input_box.submit(
        fn=predict,
        inputs=[input_box, uuid_box],
        outputs=output_box
    )

if __name__ == "__main__":
    # 启动服务，允许局域网访问
    demo.launch(server_name="0.0.0.0", server_port=8004)
