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
    error = row.get("error")
    trajectory = read_trajectory(task_dir / "traj.jsonl")

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
    table_html = "\n".join(rows) if rows else '<tr><td colspan="5">没有轨迹记录。</td></tr>'
    return f"""
<section class="task">
  <h2>{domain}</h2>
  <div class="meta">
    <span>task_id: <code>{task_id}</code></span>
    <span>status: <strong>{status}</strong></span>
    <span>score: <strong>{score}</strong></span>
    <span>steps: <strong>{len(trajectory)}</strong></span>
  </div>
  <p class="instruction">{instruction}</p>
  {error_html}
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
.meta {{ display:flex; flex-wrap:wrap; gap:10px 18px; color:var(--muted); margin-bottom:10px; }}
.instruction {{ font-size:16px; line-height:1.55; }}
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
  </div>
  <p>每一步都展示 Codex 的思路、执行的 pyautogui 动作、动作前截图和动作后状态。动作前截图是传给 Codex 决策的观测；动作后状态优先复用下一步的动作前截图，最后一步使用 <code>final.png</code>，避免重复保存同一帧。</p>
</section>
{''.join(sections)}
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
