import streamlit as st
import requests

# Streamlit页面配置
st.title("InsightScan智扫通系统")
st.write("输入一个句子，点击生成按钮进行问答及报告生成任务")

# 输入框
sentence = st.text_area("请输入句子：", height=100)

# 生成按钮
if st.button("生成"):
    if not sentence.strip():
        st.error("请输入有效的句子！")
    else:
        try:
            # 调用FLask API
            response = requests.post("http://127.0.0.1:8002/predict", json={"query": sentence, "uuid": 1001})
            response.raise_for_status()
            result = response.json()
            if 'answer' in result:
                st.success(f"生成结果：{result['answer']}")
            else:
                st.error(f"错误：{result.get('error', '未知错误')}")
        except requests.exceptions.RequestException as e:
            st.error(f'无法连接到API：{str(e)}')

# 添加说明
st.markdown("""
### 使用说明
1. 在文本框中输入一个句子。
2. 点击“生成”按钮，系统会调用模型进行问答及报告生成任务。
""")
