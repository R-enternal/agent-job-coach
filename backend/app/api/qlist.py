"""题单 API：生成（JD + 素材 + 题库配额检索）/ 查看"""

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.database import get_db
from app.models import QuestionList
from app.schemas import QlistGenerateRequest
from app.services.qlist import generate_qlist, qlist_to_dict

router = APIRouter(prefix="/api/qlist", tags=["题单"])


@router.post("/generate")
def generate(req: QlistGenerateRequest, db: Session = Depends(get_db)):
    """生成定制题单：LLM 出题（source=llm）+ 缺额题库补齐（source=kb）"""
    try:
        qlist = generate_qlist(db, req.jd_id, req.quota)
    except ValueError as exc:
        return {"error": str(exc)}
    return qlist_to_dict(qlist)


@router.get("")
def qlist_list(status: str = "active", db: Session = Depends(get_db)):
    """题单列表（前端"按题单开考"下拉）：不含题目明细，仅摘要"""
    query = db.query(QuestionList).order_by(QuestionList.id.desc())
    if status:
        query = query.filter(QuestionList.status == status)
    return {
        "items": [
            {
                "id": q.id,
                "jd_id": q.jd_id,
                "status": q.status,
                "total": len(q.questions or []),
                "created_at": q.created_at.isoformat() if q.created_at else None,
            }
            for q in query.all()
        ]
    }


@router.get("/{qid}")
def detail(qid: int, db: Session = Depends(get_db)):
    qlist = db.get(QuestionList, qid)
    return qlist_to_dict(qlist) if qlist else {"error": f"题单不存在: id={qid}"}
