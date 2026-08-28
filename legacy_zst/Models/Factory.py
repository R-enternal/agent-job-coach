import os
import sys
from langchain_openai import ChatOpenAI, OpenAIEmbeddings
from Utils.FileReader import ConfigHandler

sys.path.append(os.path.dirname(os.getcwd()))


# 初始化配置处理器实例
config_reader = ConfigHandler()
# 读取模型配置文件，解析 YAML 格式的配置内容
model_conf = config_reader.read_yaml(os.path.join(os.getcwd(), "Configs/config.yml"))


def _get_api_key(*names) -> str:
    """按优先级从环境变量读取 API Key"""
    for name in names:
        value = os.environ.get(name)
        if value:
            return value
    return ""


class ChatModelFactory:
    """
    聊天模型工厂类，用于创建和管理聊天模型实例
    """
    def __init__(self) -> None:
        """
        初始化聊天模型工厂
        """
        self.base_url = model_conf['server_url']

    def get_model(self):
        """
        获取聊天模型实例
        Returns:
            ChatOpenAI: 配置好的 DeepSeek 聊天模型实例（OpenAI 兼容接口）
        """
        api_key = _get_api_key('DEEPSEEK_API_KEY', 'LLM_API_KEY')
        if not api_key:
            raise RuntimeError("未找到 DEEPSEEK_API_KEY / LLM_API_KEY 环境变量，请先配置")
        llm = ChatOpenAI(
            model=model_conf['model_name'],
            api_key=api_key,
            base_url=self.base_url,
            temperature=0,
        )
        return llm


class EmbeddingModelFactory:
    """
    嵌入模型工厂类，用于创建和管理嵌入模型实例
    """
    def __init__(self) -> None:
        """
        初始化嵌入模型工厂
        """
        self.base_url = model_conf['embedding_server_url']

    def get_model(self):
        """
        获取嵌入模型实例
        Returns:
            OpenAIEmbeddings: 配置好的智谱 embedding 实例（OpenAI 兼容接口）
        """
        api_key = _get_api_key('ZHIPU_API_KEY', 'EMBEDDING_API_KEY')
        if not api_key:
            raise RuntimeError("未找到 ZHIPU_API_KEY / EMBEDDING_API_KEY 环境变量，请先配置")
        embeddings = OpenAIEmbeddings(
            model=model_conf['embedding_name'],
            api_key=api_key,
            base_url=self.base_url,
            # 智谱 embedding 不接受 tiktoken 编码后的 token id 数组，
            # 关闭长度检查以原始文本直传（chunk 均较短，无需截断）
            check_embedding_ctx_length=False,
            # 智谱单次 embedding 请求有条数/token 上限，16 条一批稳妥
            chunk_size=16,
        )
        return embeddings


llm = ChatModelFactory().get_model()
embed_model = EmbeddingModelFactory().get_model()
