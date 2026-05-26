#!/usr/bin/env python3
"""Generate an HTML analysis report for OSWorld Codex evaluation runs."""

from __future__ import annotations

import argparse
import html
import json
import os
from pathlib import Path
from typing import Any


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser()
    parser.add_argument("--result-dir", default="results/osworld_codex_eval")
    parser.add_argument("--osworld-dir", default="external/OSWorld")
    parser.add_argument("--output", default=None)
    return parser.parse_args()


def resolve_path(base: Path, value: str) -> Path:
    path = Path(value)
    if path.is_absolute():
        return path
    return base / path


def read_json(path: Path) -> Any:
    with path.open("r", encoding="utf-8") as json_file:
        return json.load(json_file)


def read_trajectory(path: Path) -> list[dict[str, Any]]:
    if not path.exists():
        return []
    rows = []
    with path.open("r", encoding="utf-8") as traj_file:
        for line in traj_file:
            line = line.strip()
            if line:
                rows.append(json.loads(line))
    return rows


def rel_image(output_path: Path, image_path: Path | None) -> str | None:
    if not image_path or not image_path.exists():
        return None
    return html.escape(os.path.relpath(image_path, output_path.parent))


def find_before_image(task_dir: Path, step: int) -> Path | None:
    candidates = [
        task_dir / f"step_{step:03d}_before.png",
        task_dir / f"step_{step}_before.png",
        task_dir / f"step_{step}.png",
    ]
    return next((candidate for candidate in candidates if candidate.exists()), None)


def find_after_image(task_dir: Path, step: int) -> Path | None:
    candidates = [
        task_dir / f"step_{step:03d}_after.png",
        task_dir / f"step_{step}_after.png",
        task_dir / f"step_{step + 1:03d}_before.png",
        task_dir / f"step_{step + 1}_before.png",
        task_dir / f"step_{step + 1}.png",
        task_dir / "final.png",
    ]
    return next((candidate for candidate in candidates if candidate.exists()), None)


def image_link(src: str | None, caption: str, css_class: str = "thumb") -> str:
    if not src:
        return '<span class="missing">未保存</span>'
    escaped_caption = html.escape(caption)
    return (
        f'<figure class="{css_class}-figure">'
        f'<a href="{src}"><img class="{css_class}" src="{src}" loading="lazy" alt="{escaped_caption}" /></a>'
        f"<figcaption>{escaped_caption}</figcaption>"
        "</figure>"
    )


def render_score(score: Any) -> str:
    if score is None:
        return "N/A"
    if isinstance(score, float):
        return f"{score:.3g}"
    return html.escape(str(score))


def score_value(row: dict[str, Any]) -> float | None:
    score = row.get("score")
    if isinstance(score, (int, float)):
        return float(score)
    return None


def outcome(row: dict[str, Any]) -> str:
    score = score_value(row)
    if row.get("status") != "ok":
        return "error"
    if score is None:
        return "error"
    if score >= 1.0:
        return "correct"
    if score > 0:
        return "partial"
    return "wrong"


def outcome_label(value: str) -> str:
    labels = {
        "correct": "正确",
        "partial": "部分得分",
        "wrong": "错误",
        "error": "运行错误",
    }
    return labels.get(value, value)


def compact_action(action: str, limit: int = 220) -> str:
    action = " ".join(action.split())
    return action if len(action) <= limit else action[: limit - 1] + "…"


def analyze_failure(
    row: dict[str, Any],
    task: dict[str, Any],
    trajectory: list[dict[str, Any]],
) -> list[str]:
    if outcome(row) == "correct":
        return []
    reasons: list[str] = []
    error = str(row.get("error") or "")
    if error:
        if "client_secrets.json" in error or "googledrive" in error.lower():
            reasons.append("环境 setup 失败：Google Drive 凭据缺失，不是 Agent 操作路径本身失败。")
        elif "NoneType" in error:
            reasons.append("评测或环境返回了空对象，属于运行时异常；需要单独 replay 该样本确认是否为环境不稳定。")
        else:
            reasons.append(f"运行时错误：{error}")
    score = score_value(row)
    if score == 0:
        reasons.append("Evaluator 返回 0，说明最终状态没有命中该任务的 Ground Truth。")
    elif score is not None and score < 1:
        reasons.append("Evaluator 返回部分得分，说明任务中有一部分检查项命中，但最终状态不完全匹配。")
    if trajectory:
        last_action = str(trajectory[-1].get("action", ""))
        if last_action == "FAIL":
            reasons.append("Agent 主动返回 FAIL，表示在允许步数内没有找到可行路径。")
        elif last_action == "DONE" and score != 1.0:
            reasons.append("Agent 返回 DONE 过早或自检不足，最终状态与评测条件不一致。")
        elif trajectory[-1].get("step", 0) >= 50:
            reasons.append("达到 max steps 上限，通常是导航反复尝试、控件定位不稳定或任务路径过长。")
        actions = [str(item.get("action", "")) for item in trajectory]
        waits = sum(1 for action in actions if action == "WAIT")
        terminals = sum(1 for action in actions if "ctrl', 'alt', 't" in action or 'ctrl", "alt", "t' in action)
        if waits >= 3:
            reasons.append(f"轨迹中 WAIT 较多（{waits} 次），可能存在页面/应用加载慢或状态未稳定的问题。")
        if terminals:
            reasons.append("轨迹使用了 VM 内 Terminal；如果任务要求应用内操作，可能需要检查是否偏离预期交互路径。")
        repeated = {}
        for action in actions:
            key = compact_action(action, 120)
            repeated[key] = repeated.get(key, 0) + 1
        repeats = [(action, count) for action, count in repeated.items() if count >= 4]
        if repeats:
            action, count = sorted(repeats, key=lambda item: item[1], reverse=True)[0]
            reasons.append(f"存在重复动作（{count} 次）：{action}")
        reasons.append(f"最后动作：{compact_action(last_action)}")
    evaluator = task.get("evaluator", {})
    if evaluator:
        reasons.append(
            "评测函数："
            + html.escape(str(evaluator.get("func", "unknown")))
            + "；建议对照 result/expected 配置复核最终截图。"
        )
    return reasons


def render_evaluator(task: dict[str, Any]) -> str:
    evaluator = task.get("evaluator", {})
    func = evaluator.get("func", "unknown")
    result = evaluator.get("result", {})
    expected = evaluator.get("expected", {})
    options = evaluator.get("options", {})
    brief = html.escape(json.dumps({"func": func}, ensure_ascii=False))
    details = html.escape(
        json.dumps(
            {
                "result": result,
                "expected": expected,
                "options": options,
            },
            ensure_ascii=False,
            indent=2,
        )
    )
    return f"<p><strong>Evaluator:</strong> <code>{brief}</code></p><pre>{details}</pre>"


def render_task_section(
    row: dict[str, Any],
    task: dict[str, Any],
    task_dir: Path,
    output_path: Path,
) -> str:
    domain = html.escape(str(row["domain"]))
    task_id = html.escape(str(row["task_id"]))
    instruction = html.escape(str(task.get("instruction", "")))
    score = render_score(row.get("score"))
    status = html.escape(str(row.get("status", "")))
    result_outcome = outcome(row)
    error = row.get("error")
    trajectory = read_trajectory(task_dir / "traj.jsonl")
    analysis = analyze_failure(row, task, trajectory)

    first_before = rel_image(output_path, find_before_image(task_dir, 1))
    last_step = trajectory[-1]["step"] if trajectory else 1
    last_after = rel_image(output_path, find_after_image(task_dir, int(last_step)))

    rows = []
    for item in trajectory:
        step = int(item.get("step", 0))
        thought = html.escape(str(item.get("thought", "")))
        action = html.escape(str(item.get("action", "")))
        before_src = rel_image(output_path, find_before_image(task_dir, step))
        after_src = rel_image(output_path, find_after_image(task_dir, step))
        rows.append(
            "<tr>"
            f'<td class="num">{step}</td>'
            f"<td>{thought}</td>"
            f"<td><code>{action}</code></td>"
            f"<td>{image_link(before_src, f'Step {step} 执行前')}</td>"
            f"<td>{image_link(after_src, f'Step {step} 执行后')}</td>"
            "</tr>"
        )

    error_html = f'<p class="error">Error: {html.escape(str(error))}</p>' if error else ""
    analysis_html = ""
    if analysis:
        items = "".join(f"<li>{item}</li>" for item in analysis)
        analysis_html = f"""
  <div class="failure-analysis">
    <strong>失败/部分得分原因分析</strong>
    <ul>{items}</ul>
  </div>
"""
    table_html = "\n".join(rows) if rows else '<tr><td colspan="5">没有轨迹记录。</td></tr>'
    return f"""
<section class="task" data-domain="{domain}" data-outcome="{result_outcome}">
  <h2>{domain}</h2>
  <div class="meta">
    <span>task_id: <code>{task_id}</code></span>
    <span>status: <strong>{status}</strong></span>
    <span>score: <strong>{score}</strong></span>
    <span>result: <strong>{outcome_label(result_outcome)}</strong></span>
    <span>steps: <strong>{len(trajectory)}</strong></span>
  </div>
  <p class="instruction">{instruction}</p>
  {error_html}
  {analysis_html}
  <div class="screens">
    {image_link(first_before, "初始状态", "preview")}
    {image_link(last_after, "最终状态", "preview")}
  </div>
  <details>
    <summary>评测器配置与 Ground Truth 来源</summary>
    {render_evaluator(task)}
  </details>
  <table class="steps">
    <thead>
      <tr><th>Step</th><th>Codex thought</th><th>执行 action</th><th>执行前截图</th><th>执行后截图</th></tr>
    </thead>
    <tbody>{table_html}</tbody>
  </table>
</section>
"""


def write_report(result_dir: Path, osworld_dir: Path, output_path: Path) -> Path:
    summary_path = result_dir / "summary.json"
    summary = read_json(summary_path)
    output_path.parent.mkdir(parents=True, exist_ok=True)

    ok_count = sum(row.get("status") == "ok" for row in summary)
    scored_rows = [row for row in summary if isinstance(row.get("score"), (int, float))]
    total_score = sum(float(row["score"]) for row in scored_rows)
    domains = sorted({str(row["domain"]) for row in summary})
    outcome_counts = {key: sum(outcome(row) == key for row in summary) for key in ["correct", "partial", "wrong", "error"]}

    domain_rows = []
    for domain in domains:
        rows = [row for row in summary if str(row["domain"]) == domain]
        score = sum(float(row.get("score") or 0) for row in rows if isinstance(row.get("score"), (int, float)))
        domain_rows.append(
            "<tr>"
            f"<td>{html.escape(domain)}</td>"
            f"<td>{len(rows)}</td>"
            f"<td>{sum(outcome(row) == 'correct' for row in rows)}</td>"
            f"<td>{sum(outcome(row) == 'partial' for row in rows)}</td>"
            f"<td>{sum(outcome(row) == 'wrong' for row in rows)}</td>"
            f"<td>{sum(outcome(row) == 'error' for row in rows)}</td>"
            f"<td>{score:.3g}</td>"
            f"<td>{(score / len(rows)):.1%}</td>"
            "</tr>"
        )

    sections = []
    for row in summary:
        domain = str(row["domain"])
        task_id = str(row["task_id"])
        task_path = osworld_dir / "evaluation_examples" / "examples" / domain / f"{task_id}.json"
        task = read_json(task_path)
        task_dir = result_dir / domain / task_id
        sections.append(render_task_section(row, task, task_dir, output_path))

    document = f"""<!doctype html>
<html lang="zh-CN">
<head>
<meta charset="utf-8" />
<meta name="viewport" content="width=device-width, initial-scale=1" />
<title>OSWorld Codex Eval Analysis</title>
<style>
:root {{ --bg:#f7f7f8; --card:#fff; --text:#1f2328; --muted:#656d76; --line:#d0d7de; --ok:#1a7f37; --bad:#d1242f; }}
body {{ margin:0; padding:28px; background:var(--bg); color:var(--text); font-family:-apple-system,BlinkMacSystemFont,"Segoe UI",sans-serif; }}
h1 {{ margin:0 0 8px; }}
h2 {{ margin:0 0 10px; }}
code, pre {{ font-family:ui-monospace,SFMono-Regular,Menlo,Consolas,monospace; }}
pre {{ overflow:auto; padding:12px; background:#f6f8fa; border:1px solid var(--line); border-radius:10px; }}
.summary, .task {{ background:var(--card); border:1px solid var(--line); border-radius:14px; padding:18px; margin:0 0 18px; box-shadow:0 1px 2px rgba(0,0,0,.04); }}
.controls {{ display:flex; flex-wrap:wrap; gap:10px; align-items:center; margin:14px 0; }}
.controls select, .controls button {{ padding:7px 10px; border:1px solid var(--line); border-radius:8px; background:#fff; }}
.domain-summary {{ width:100%; border-collapse:collapse; margin-top:12px; }}
.domain-summary th, .domain-summary td {{ border-top:1px solid var(--line); padding:8px; text-align:left; }}
.meta {{ display:flex; flex-wrap:wrap; gap:10px 18px; color:var(--muted); margin-bottom:10px; }}
.instruction {{ font-size:16px; line-height:1.55; }}
.failure-analysis {{ border:1px solid #f0d98c; background:#fff8dc; border-radius:10px; padding:12px; margin:12px 0; }}
.failure-analysis ul {{ margin:8px 0 0 20px; padding:0; }}
.screens {{ display:grid; grid-template-columns:repeat(auto-fit,minmax(320px,1fr)); gap:14px; margin:14px 0; }}
figure {{ margin:0; }}
figcaption {{ color:var(--muted); font-size:13px; margin-top:6px; }}
.preview {{ width:100%; max-height:360px; object-fit:contain; border:1px solid var(--line); border-radius:10px; background:#eee; }}
.thumb {{ width:220px; max-height:140px; object-fit:contain; border:1px solid var(--line); border-radius:8px; background:#eee; }}
.steps {{ width:100%; border-collapse:collapse; table-layout:fixed; margin-top:14px; }}
.steps th, .steps td {{ border-top:1px solid var(--line); padding:10px; vertical-align:top; text-align:left; }}
.steps th:nth-child(1) {{ width:54px; }}
.steps th:nth-child(2) {{ width:24%; }}
.steps th:nth-child(3) {{ width:30%; }}
.num {{ text-align:right; color:var(--muted); }}
.missing {{ color:var(--muted); }}
.error {{ color:var(--bad); }}
</style>
</head>
<body>
<section class="summary">
  <h1>OSWorld Codex Eval Analysis</h1>
  <div class="meta">
    <span>tasks: <strong>{len(summary)}</strong></span>
    <span>status_ok: <strong>{ok_count}/{len(summary)}</strong></span>
    <span>score_sum: <strong>{total_score:.3g}/{len(scored_rows)}</strong></span>
    <span>accuracy: <strong>{(total_score / len(summary)):.1%}</strong></span>
    <span>correct/partial/wrong/error: <strong>{outcome_counts['correct']}/{outcome_counts['partial']}/{outcome_counts['wrong']}/{outcome_counts['error']}</strong></span>
  </div>
  <p>每一步都展示 Codex 的思路、执行的 pyautogui 动作、动作前截图和动作后状态。动作前截图是传给 Codex 决策的观测；动作后状态优先复用下一步的动作前截图，最后一步使用 <code>final.png</code>，避免重复保存同一帧。</p>
  <div class="controls">
    <label>Domain <select id="domainFilter"><option value="all">全部</option>{''.join(f'<option value="{html.escape(domain)}">{html.escape(domain)}</option>' for domain in domains)}</select></label>
    <label>Result <select id="outcomeFilter"><option value="all">全部</option><option value="correct">正确</option><option value="partial">部分得分</option><option value="wrong">错误</option><option value="error">运行错误</option><option value="incorrect">非满分</option></select></label>
    <button id="resetFilters">重置筛选</button>
    <span id="visibleCount"></span>
  </div>
  <table class="domain-summary">
    <thead><tr><th>Domain</th><th>完成</th><th>正确</th><th>部分得分</th><th>错误</th><th>运行错误</th><th>得分</th><th>Accuracy</th></tr></thead>
    <tbody>{''.join(domain_rows)}</tbody>
  </table>
</section>
{''.join(sections)}
<script>
const domainFilter = document.getElementById('domainFilter');
const outcomeFilter = document.getElementById('outcomeFilter');
const visibleCount = document.getElementById('visibleCount');
const tasks = Array.from(document.querySelectorAll('.task'));
function applyFilters() {{
  const domain = domainFilter.value;
  const result = outcomeFilter.value;
  let shown = 0;
  for (const task of tasks) {{
    const domainOk = domain === 'all' || task.dataset.domain === domain;
    const outcome = task.dataset.outcome;
    const resultOk = result === 'all' || outcome === result || (result === 'incorrect' && outcome !== 'correct');
    const visible = domainOk && resultOk;
    task.style.display = visible ? '' : 'none';
    if (visible) shown++;
  }}
  visibleCount.textContent = `显示 ${{shown}} / ${{tasks.length}} 个样本`;
}}
domainFilter.addEventListener('change', applyFilters);
outcomeFilter.addEventListener('change', applyFilters);
document.getElementById('resetFilters').addEventListener('click', () => {{
  domainFilter.value = 'all';
  outcomeFilter.value = 'all';
  applyFilters();
}});
applyFilters();
</script>
</body>
</html>
"""
    output_path.write_text(document, encoding="utf-8")
    return output_path


def main() -> int:
    base = Path.cwd()
    args = parse_args()
    result_dir = resolve_path(base, args.result_dir)
    osworld_dir = resolve_path(base, args.osworld_dir)
    output_path = resolve_path(base, args.output) if args.output else result_dir / "analysis.html"
    report_path = write_report(
        result_dir=result_dir,
        osworld_dir=osworld_dir,
        output_path=output_path,
    )
    print(f"analysis={report_path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
