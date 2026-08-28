import sys
sys.path.append('../..')
sys.path.append('.')
sys.path.append('./')
from Tools.VecStore import VecStore

if __name__=="__main__":
    vec = VecStore()
    db = vec.get_db()
    vec.save_to_chroma(db)