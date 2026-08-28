"""JD 定制 API：文本/截图双通道解析（先落 draft）→ 回显编辑 → 确认"""

from pathlib import Path

from fastapi import APIRouter, Depends, UploadFile
from sqlalchemy.orm import Session

from app.database import get_db
from app.schemas import JdParseTextRequest, JdUpdateRequest
from app.services.jd import (
    jd_to_dict,
    get_jd,
    list_jds,
    parse_image_jd,
    parse_text_jd,
    update_jd,
)

router = APIRouter(prefix="/api/jd", tags=["JD 定制"])

_IMAGE_SUFFIX = (".png", ".jpg", ".jpeg", ".webp")


@router.post("/parse")
def parse_text(req: JdParseTextRequest, db: Session = Depends(get_db)):
    """文本 JD → glm-5.1 结构化解析 → draft 落库"""
    return jd_to_dict(parse_text_jd(db, req.raw_text))


@router.post("/parse_image")
def parse_image(file: UploadFile, db: Session = Depends(get_db)):
    """JD 截图 → glm-4v-plus 多模态识别 → draft 落库"""
    suffix = Path(file.filename or "").suffix.lower()
    if suffix not in _IMAGE_SUFFIX:
        return {"error": f"不支持的图片类型 {suffix}（支持 png/jpg/jpeg/webp）"}
    data = file.file.read()  # 同步端点走线程池，直接用底层文件对象
    if not data:
        return {"error": "空文件"}
    return jd_to_dict(parse_image_jd(db, file.filename or "jd.png", data))


@router.get("")
def jd_list(status: str = "", db: Session = Depends(get_db)):
    return {"items": [jd_to_dict(e) for e in list_jds(db, status)]}


@router.get("/{jid}")
def jd_detail(jid: int, db: Session = Depends(get_db)):
    entry = get_jd(db, jid)
    return jd_to_dict(entry) if entry else {"error": f"JD 不存在: id={jid}"}


@router.put("/{jid}")
def jd_update(jid: int, req: JdUpdateRequest, db: Session = Depends(get_db)):
    """回显确认：编辑解析结果或仅确认（status=confirmed）"""
    entry = update_jd(db, jid, req)
    return jd_to_dict(entry) if entry else {"error": f"JD 不存在: id={jid}"}
