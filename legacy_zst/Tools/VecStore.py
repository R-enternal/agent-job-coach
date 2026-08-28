from langchain.text_splitter import RecursiveCharacterTextSplitter
from langchain.schema import Document
from langchain_community.vectorstores import Chroma
import os
import sys

sys.path.append('../..')
sys.path.append('.')
sys.path.append('../')
from Utils.FileReader import FileReader, ConfigHandler
from Models.Factory import embed_model

reader = FileReader()
config_reader = ConfigHandler()
config_yaml = config_reader.read_yaml(os.path.join(os.getcwd(), "Configs/rag_config.yml"))
# config_yaml = config_reader.read_yaml("Configs/rag_config.yml")

class VecStore:
    def __init__(self, dir=config_yaml['DATA_PATH'], save_dir=config_yaml['CHROMA_PATH']) -> None:
        self.dir = dir
        self.save_dir = save_dir

    def get_db(self):
        documents = self.load_documents()
        chunks = self.split_text(documents)
        chroma_db = Chroma.from_documents(documents=chunks,embedding=embed_model,persist_directory=self.save_dir)
        return chroma_db

    def load_documents(self):
        files = os.listdir(self.dir)
        docs = []
        for file in files:
            file_path = os.path.join(self.dir, file)
            if file.endswith('.docx'):
                txts = reader.read_docx(file_path)
            elif file.endswith('.pdf'):
                txts = reader.read_pdf(file_path)
            elif file.endswith('.txt'):
                # 原代码漏掉了 txt 支持（read_md 已存在），补上使故障日志也能入库
                content = reader.read_md(file_path)
                txts = [Document(page_content=content, metadata={"source": file})] if content else []
            elif file.endswith('.csv'):
                df = reader.read_csvs(file_path)
                txts = df.values.tolist()
            else:
                txts = []
            docs.extend(txts)
        return docs

    def split_text(self, documents):
        text_splitter = RecursiveCharacterTextSplitter(
            chunk_size=300,
            chunk_overlap=100,
            length_function=len,
            add_start_index=True,
        )
        # print(f'documents:{documents}')
        chunks = text_splitter.split_documents(documents)
        print(f"Split {len(documents)} documents into {len(chunks)} chunks.")
        return chunks

    def save_to_chroma(self, db):
        db.persist()  # 持久化
        print(f"Saved chunks to {config_yaml['CHROMA_PATH']}.")

    def load_chroma(self):
        db = Chroma(persist_directory=self.save_dir, embedding_function=embed_model)
        return db


# db = vec.get_db()
if __name__ == "__main__":
    vec = VecStore()
    db = vec.get_db()
    vec.save_to_chroma(db)
