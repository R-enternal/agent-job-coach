import warnings
warnings.filterwarnings("ignore")

from langchain.tools import StructuredTool
from .RagQATool import rag_qa
from .ReportGenerationTool import generator

rag_qa_tool = StructuredTool.from_function(
    func=rag_qa,
    name="RagQA",
    description="使用RAG检索知识进行问答"
)

report_generation_tool = StructuredTool.from_function(
    func=generator,
    name="ReportGeneration",
    description="从第三方系统查询信息，完成报告"
)
