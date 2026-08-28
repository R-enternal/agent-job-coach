"""评分金标集评测：judge 机器分 vs 人工基线

用法：uv run python scripts/eval_judge.py [--tag 迭代标签，默认 baseline]

输入：../data/evals/judge_golden.jsonl（# 开头为注释行）
输出：控制台三指标 + 逐条明细；追加落盘 ../data/evals/judge_eval_result.json
  （iterations 数组，每次跑一个迭代标签，单变量调 prompt 的回归过程可追溯）

三指标：
- 一致率：|机器分-人工分| ≤ 1 的占比（主指标）
- MAE：平均绝对误差
- Pearson 相关：排序一致性（样本量小，仅供参考趋势）
"""

import argparse
import json
import math
import sys
from datetime import datetime
from pathlib import Path

sys.path.append(str(Path(__file__).resolve().parents[1]))

from app.agent.interview_agent import _judge_answer  # noqa: E402

EVALS_DIR = Path(__file__).resolve().parents[2] / "data" / "evals"
GOLDEN_PATH = EVALS_DIR / "judge_golden.jsonl"
RESULT_PATH = EVALS_DIR / "judge_eval_result.json"


def _pearson(xs: list[float], ys: list[float]) -> float:
    n = len(xs)
    if n < 2:
        return 0.0
    mx, my = sum(xs) / n, sum(ys) / n
    cov = sum((x - mx) * (y - my) for x, y in zip(xs, ys))
    sx = math.sqrt(sum((x - mx) ** 2 for x in xs))
    sy = math.sqrt(sum((y - my) ** 2 for y in ys))
    return round(cov / (sx * sy), 4) if sx and sy else 0.0


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--tag", default="baseline", help="迭代标签（回归对比用）")
    args = parser.parse_args()

    if not GOLDEN_PATH.exists():
        print(f"金标集不存在：{GOLDEN_PATH}（先把草稿锁定为正式文件）")
        sys.exit(1)

    items = []
    for line in GOLDEN_PATH.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if line and not line.startswith("#"):
            items.append(json.loads(line))
    print(f"金标集 {len(items)} 条，逐条过 judge（每条一次 LLM 评分调用）...\n")

    details: list[dict] = []
    for i, item in enumerate(items, 1):
        state = {
            "current_question": item["question"],
            "answer": item["answer"],
            "current_reference": item.get("reference", ""),
        }
        result, degraded = _judge_answer(state)  # type: ignore[arg-type]
        delta = round(result.score - float(item["human_score"]), 2)
        details.append({
            "idx": i,
            "question": item["question"][:80],
            "answer": item["answer"][:120],
            "human": item["human_score"],
            "machine": result.score,
            "delta": delta,
            "degraded": degraded,
            "note": item.get("note", ""),
        })
        print(f"[{i:02d}] human={item['human_score']} machine={result.score} "
              f"Δ={delta:+.2f}{'（降级）' if degraded else ''} | {item['question'][:40]}")

    humans = [float(d["human"]) for d in details]
    machines = [float(d["machine"]) for d in details]
    n = len(details)
    consistency = round(sum(1 for d in details if abs(d["delta"]) <= 1) / n, 4)
    mae = round(sum(abs(d["delta"]) for d in details) / n, 4)
    pearson = _pearson(humans, machines)

    print(f"\n=== [{args.tag}] 一致率(|Δ|≤1)={consistency:.0%}  MAE={mae}  Pearson={pearson} ===")

    record = {
        "tag": args.tag,
        "at": datetime.now().isoformat(timespec="seconds"),
        "n": n,
        "consistency": consistency,
        "mae": mae,
        "pearson": pearson,
        "details": details,
    }
    existing = {"iterations": []}
    if RESULT_PATH.exists():
        existing = json.loads(RESULT_PATH.read_text(encoding="utf-8"))
    existing["iterations"] = [it for it in existing.get("iterations", [])
                              if it.get("tag") != args.tag]  # 同标签覆盖
    existing["iterations"].append(record)
    RESULT_PATH.write_text(
        json.dumps(existing, ensure_ascii=False, indent=2), encoding="utf-8"
    )
    print(f"结果已追加落盘：{RESULT_PATH}")


if __name__ == "__main__":
    main()
