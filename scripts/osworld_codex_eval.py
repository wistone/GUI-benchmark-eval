#!/usr/bin/env python3
"""Run OSWorld tasks with the local Codex CLI as the agent.

The runner keeps OSWorld's environment/evaluator path intact:
task JSON -> DesktopEnv.reset -> Codex CLI predicts pyautogui -> env.step -> env.evaluate.
"""

from __future__ import annotations

import argparse
import json
import os
import re
import shutil
import subprocess
import sys
import tempfile
import time
from pathlib import Path
from typing import Any


DEFAULT_TASKS = {
    "chrome": "bb5e4c0d-f964-439c-97b6-bdb9747de3f4",
    "gimp": "7767eef2-56a3-4cea-8c9f-48c070c7d65b",
    "libreoffice_calc": "01b269ae-2111-4a07-81fd-3fcd711993b0",
    "libreoffice_impress": "2cd43775-7085-45d8-89fa-9e35c0a915cf",
    "libreoffice_writer": "0e47de2a-32e0-456c-a366-8c607ef7a9d2",
    "multi_apps": "937087b6-f668-4ba6-9110-60682ee33441",
    "os": "28cc3b7e-b194-4bc9-8353-d04c0f4d56d2",
    "thunderbird": "a10b69e1-6034-4a2b-93e1-571d45194f75",
    "vlc": "215dfd39-f493-4bc3-a027-8a97d72c61bf",
    "vs_code": "57242fad-77ca-454f-b71b-f187181a9f23",
}


SYSTEM_GUIDANCE = """You are controlling an Ubuntu desktop VM for OSWorld evaluation using Harness V3.19.
Return only JSON matching the provided schema.
Do not ask the user questions.
Do not use shell/tools to inspect the host. Decide the next VM GUI action from the screenshot and task state.

The action field must be one of:
- pyautogui Python code, for example: pyautogui.click(100, 200)
- WAIT
- DONE
- FAIL

Use pyautogui for GUI control. Keep each action small and executable.
For long text entry into the VM GUI, especially Terminal commands or JSON/config content, do not type hundreds of characters with pyautogui.write. Use a clipboard paste action such as `import pyperclip; pyperclip.copy(text); pyautogui.hotkey('ctrl','v')`, then press Enter if needed. Clipboard paste is allowed only for putting text into the VM GUI; do not use Python imports to inspect host files, call subprocess, or bypass the desktop/evaluator.
You may use the Ubuntu Terminal as a normal GUI application when it is the most reliable way to complete or verify a desktop task. If you use Terminal, open it through the VM GUI and type commands with pyautogui; do not call subprocess, os.system, host tools, OSWorld backend APIs, or evaluator files directly from the action code.

Every response must include a verification field. For normal actions, say what you will check next. For DONE or FAIL, provide concrete evidence for why that final action is justified.
If the prompt includes Harness state warnings or runner intervention notices, treat them as authoritative guardrails for the next action. They are generated from your recent action history and are meant to prevent repeated non-progress.

Core policy:
- Do exactly the requested task, not an adjacent or approximate task. Do not toggle unrelated settings, choose substitute app features, or create approximate files just because the exact route is hard.
- Treat the requested final artifact/state as the source of truth. Visual completion is not enough for files, settings, shortcuts, downloads, exports, or spreadsheets.
- Separate mutation from verification. After the requested state appears complete, only verify unless verification shows a specific mismatch.
- Avoid over-repair. Extra mutations can break a correct state. Do not broaden selected ranges, reapply formatting, or rewrite files after the target condition is satisfied.
- Respect scope exactly. If the instruction names a range, folder, slide, row, file name, or app, operate only on that scope unless the task explicitly asks otherwise.
- For editable documents, a visible change is not complete until it is saved to the requested file and the saved artifact is verified. Before DONE on Writer/Calc/Impress document tasks, save with the app or equivalent VM-visible file route, then verify the saved file's modified timestamp/content/format.
- If two consecutive attempts do not change the relevant UI/file/config state, switch strategy. If three recent actions are precision mouse-placement attempts on the same text/object, stop using mouse placement and switch to Find, keyboard selection, menus/dialogs, or a VM Terminal artifact route. If five recent actions make no measurable progress, use a lower-level route through the VM Terminal when allowed, or FAIL if the exact task is blocked.
- Do not repeat failed long command entry. If a command/script appears not to execute, first confirm whether the terminal is at a shell prompt, Python prompt, or an unfinished quote/here-doc. Exit/cancel back to a shell prompt once, then use clipboard paste with a shorter command. If an artifact-generation script is necessary, write one temporary script with a quoted here-doc and run it once; do not type into the Python REPL line by line. After two failed attempts to enter or run a long script, abandon that script route and choose a simpler route or FAIL with evidence. When pasting into Terminal, prefer ctrl+shift+v or the terminal menu paste; ctrl+v is often literal input rather than paste.
- For Terminal commands, treat command entry as a stateful operation: focus the terminal first, paste/type once, press Enter, then wait for visible output or a clean prompt. If two clipboard-pasted commands do not visibly run, stop using clipboard paste for Terminal and use a short directly typed command or a GUI route.
- Unless the task explicitly asks for a new subfolder, save generated output files in the requested folder, current opened folder, or Desktop alongside the source/template files. Do not create a new output subdirectory just to organize files; evaluators often check exact filenames in the requested location.

Typed playbooks:
- LibreOffice Calc exact range fill-down: if asked to fill blank cells in a named range/range with the value above, process every column in the requested range and only blank cells inside that range. Do not select the entire range and fill down because that overwrites nonblank cells and may touch irrelevant blanks. A reliable route is to use the VM Terminal with a spreadsheet library: load the workbook, for each blank cell in the requested range set it to the same-column value from the row above, save the same workbook path, then verify sample filled cells and that cells outside the requested range are unchanged.
- LibreOffice Calc chart/table tasks: prefer a deterministic artifact route before long GUI chart clicking. Compute requested rows/formulas, create the requested chart object with exact chart type/title/source ranges using a spreadsheet library or LibreOffice headless/UNO route when possible, save the workbook, then inspect workbook structure or reopen in Calc to verify the chart object and source range. Do not accept a visible spreadsheet with no verified chart object. If the task asks for sparklines, first verify whether LibreOffice Calc exposes native sparkline support; if it is unavailable, do not emulate sparklines with normal charts/shapes and return FAIL with evidence.
- LibreOffice Writer exact edits: first use Find/search, keyboard selection, Format dialogs, style controls, or document structure routes; avoid repeated pixel dragging for single characters or sentence boundaries. For paragraph formatting, verify the actual paragraph property and not only visual spacing. For DOCX line spacing tasks, a deterministic file-structure route is acceptable: set the exact requested paragraphs' `w:spacing` property (for double line spacing, line `480` with `auto` rule), save/reopen, and verify adjacent paragraphs were not changed. Always save and verify the saved document before DONE.
- LibreOffice Impress exact formatting: apply formatting only to the requested slide/object/textbox. For exact named colors, use the app's Basic/Standard values or an explicit file-structure/custom RGB route; common exact values are yellow `#FFFF00`, red `#FF0000`, blue `#0000FF`, and LibreOffice green `#00A933` / RGB `(0, 169, 51)`. Do not choose visually nearby swatches or pure web green `#00FF00` for LibreOffice green. For multiple textboxes/runs, a PPTX file-structure edit is often more reliable than coordinate palette clicks: set only the target text runs' `srgbClr`, save, and verify the saved file.
- LibreOffice Calc/Writer/Impress exact formatting: apply formatting only to the requested range/paragraph/slide/object. Before DONE, verify the selected target, saved state, and at least one negative condition: an adjacent unrelated cell/paragraph/slide/object remains unchanged.
- VS Code keybindings/settings: prefer the JSON settings/keybindings file when the task asks for a precise shortcut or preference. The reliable target is the current VM user's config path, written as `~/.config/Code/User/settings.json` or `~/.config/Code/User/keybindings.json`; do not hard-code another home directory. If a VM Terminal command writes and validates the minimal JSON file, do not reopen the same JSON file for manual GUI editing. Verify by reading the same file or testing behavior. For a terminal-to-editor shortcut, the expected command is normally `workbench.action.focusActiveEditorGroup` with condition `terminalFocus`.
- Browser/profile/settings tasks: verify the exact requested setting. If the requested feature is unavailable, do not change a nearby setting; return FAIL with direct evidence from the requested page/search plus one independent search route.
- Download set tasks: first infer the complete expected set from the instruction, opened folder, visible source page, and any already-seeded file in the target folder. If there are more than three expected files or the page is a repeated week/lecture/part sequence, switch to the VM Terminal by step 8 after identifying the site/pattern; do not keep manually opening PDFs one by one. Use Terminal either to enumerate exact PDF links from the source page(s) or to derive a numbered URL template from the visible page/seeded filename and verify every candidate URL with HEAD/spider before downloading. A verified template is acceptable; an unverified guessed template is not. If the task says "opened folder", "current folder", or shows a seeded file in a folder, that folder is the destination; use the VM user's `~` or `/home/user`, never `/home/oai`, and do not use the default Downloads folder or bare home directory unless it is the opened folder. For numbered week/lecture/part sets, include every intermediate number in the visible sequence except files already present; do not start from the first currently visible link if earlier numbers are also expected. Once exact links or verified template URLs are known, use one concise command in the target folder to download all missing files and then list/verify every expected PDF with nonzero sizes; do not alternate between browser navigation, URL scraping scripts, and near-duplicate download commands. Before DONE, verify the complete expected list, no numeric gaps, destination folder, extensions, and nonzero sizes. A browser download bubble is not enough.
- Repetitive form/PDF generation tasks: if the task asks to fill many similar files from a spreadsheet/template, do not spend the run manually editing one form at a time. Use the VM Terminal to inspect the spreadsheet and the existing PDF/form/template once, then fill or overlay that template to generate every requested output with deterministic filenames in the requested location. Preserve the template's layout; do not draw a new approximate form unless no template exists. Verify count, exact names, nonzero sizes, and representative field content/marks. Repeated package/probe commands without producing outputs are not progress.
- Media conversion/snapshot tasks: verify file path, type, nonzero size, and when relevant codec/duration/dimensions. If VLC GUI conversion fails or creates the wrong file, using Terminal from the VM to verify or repair with installed user-level tools is allowed unless the task forbids command-line use. The output must still satisfy the requested file name/location/format.
- Infeasible or unavailable tasks: use the direct requested route and one independent route such as menu search, app setting search, package/config check, or VM-visible docs. If the exact requested feature/source/app/package is unavailable, return FAIL with evidence; do not substitute a different feature or attempt long installs from unavailable sources. For installation requests, check whether the package/source exists before starting a long install path; if no supported source is available in the VM, FAIL with evidence.

Completion gate:
- Return DONE only after verifying the final state using concrete observable evidence.
- For file tasks, verify path, name, type/extension, size, content or codec when relevant, and saved/exported state.
- For settings/shortcuts/default apps/file associations, verify the underlying config or actual behavior, not only the UI label.
- For Office tasks, verify exact target content/format/scope and saved state. Screenshot evidence alone is weak when file structure or exact formatting matters.

If a task explicitly forbids terminal/command-line tools, follow that instruction and do not use Terminal.
If the task uses a specific app, complete the requested app workflow first. Terminal may be used for normal user-visible verification or config checks, but not to bypass an explicit requirement to use that app feature.
Before returning DONE, verify from the current screenshot, recent history, or VM-visible checks that the requested end state is actually complete. If the last action may still be loading or applying, return WAIT instead of DONE.
Return DONE only when the task's requested final state has been checked.
Return FAIL only when the exact task is impossible or blocked after reasonable alternate routes, and state the concrete evidence in verification.
"""


def ensure_executable(name: str) -> str:
    path = shutil.which(name)
    if path:
        return path
    codex_app_path = "/Applications/Codex.app/Contents/Resources/codex"
    if name == "codex" and Path(codex_app_path).exists():
        return codex_app_path
    raise RuntimeError(f"{name} not found on PATH")


def ensure_vmrun_on_path() -> None:
    fusion_vmrun = Path("/Applications/VMware Fusion.app/Contents/Library/vmrun")
    if shutil.which("vmrun"):
        return
    if fusion_vmrun.exists():
        os.environ["PATH"] = f"{fusion_vmrun.parent}{os.pathsep}{os.environ['PATH']}"
        return
    raise RuntimeError("vmrun was not found. Install VMware Fusion first.")


def run_vmrun(*args: str) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        ["vmrun", "-T", "fusion", *args],
        text=True,
        capture_output=True,
        check=False,
    )


def ensure_snapshot(path_to_vm: str, snapshot_name: str) -> None:
    snapshots = run_vmrun("listSnapshots", path_to_vm)
    if snapshots.returncode == 0 and snapshot_name in snapshots.stdout.splitlines():
        return
    raise RuntimeError(f"VM snapshot '{snapshot_name}' is missing.")


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser()
    parser.add_argument("--osworld-dir", default="external/OSWorld")
    parser.add_argument(
        "--path-to-vm",
        default="external/OSWorld/vmware_vm_data/Ubuntu0/Ubuntu0.vmx",
    )
    parser.add_argument("--provider-name", default="vmware")
    parser.add_argument("--os-type", default="Ubuntu")
    parser.add_argument("--snapshot-name", default="init_state")
    parser.add_argument("--headless", action="store_true")
    parser.add_argument("--domains", default=",".join(DEFAULT_TASKS))
    parser.add_argument(
        "--task-mode",
        choices=["default", "all"],
        default="default",
        help="default runs one smoke task per domain; all runs every task JSON in the selected domains.",
    )
    parser.add_argument(
        "--task-file",
        default=None,
        help="JSON file with an ordered list of tasks. Each item must have domain and task_id.",
    )
    parser.add_argument(
        "--skip-completed",
        action="store_true",
        help="Skip tasks whose result.txt already exists in the result directory.",
    )
    parser.add_argument(
        "--start-index",
        type=int,
        default=1,
        help="1-based inclusive index into the discovered task list.",
    )
    parser.add_argument(
        "--end-index",
        type=int,
        default=None,
        help="1-based inclusive index into the discovered task list.",
    )
    parser.add_argument("--max-steps", type=int, default=50)
    parser.add_argument(
        "--retry-no-result",
        type=int,
        default=0,
        help="Retry a task this many times when it crashes before producing an evaluator score.",
    )
    parser.add_argument("--model", default="gpt-5.4")
    parser.add_argument("--codex-bin", default=None)
    parser.add_argument(
        "--schema",
        default="schemas/codex_osworld_action.schema.json",
    )
    parser.add_argument(
        "--result-dir",
        default="results/osworld_codex_eval",
    )
    parser.add_argument(
        "--summary-path",
        default=None,
        help="Where to write the incremental summary JSON. Defaults to RESULT_DIR/summary.json.",
    )
    parser.add_argument(
        "--metadata-path",
        default=None,
        help="Where to write run metadata. Defaults to RESULT_DIR/run_metadata.json.",
    )
    parser.add_argument(
        "--analysis-html",
        default=None,
        help="Where to write the HTML analysis report. Defaults to RESULT_DIR/analysis.html.",
    )
    parser.add_argument(
        "--no-analysis",
        action="store_true",
        help="Do not generate the HTML analysis report after the run.",
    )
    return parser.parse_args()


def resolve_path(base: Path, value: str) -> Path:
    path = Path(value)
    if path.is_absolute():
        return path
    return base / path


def load_task(osworld_dir: Path, domain: str, task_id: str) -> dict[str, Any]:
    task_path = osworld_dir / "evaluation_examples" / "examples" / domain / f"{task_id}.json"
    with task_path.open("r", encoding="utf-8") as task_file:
        return json.load(task_file)


def discover_tasks(osworld_dir: Path, domains: list[str], task_mode: str) -> list[tuple[str, str]]:
    examples_dir = osworld_dir / "evaluation_examples" / "examples"
    tasks = []
    for domain in domains:
        domain_dir = examples_dir / domain
        if not domain_dir.is_dir():
            raise RuntimeError(f"Unknown domain or missing examples directory: {domain}")
        if task_mode == "default":
            if domain not in DEFAULT_TASKS:
                raise RuntimeError(f"No default smoke task configured for domain: {domain}")
            tasks.append((domain, DEFAULT_TASKS[domain]))
        else:
            tasks.extend((domain, task_path.stem) for task_path in sorted(domain_dir.glob("*.json")))
    return tasks


def load_task_file(path: Path) -> list[tuple[str, str]]:
    payload = json.loads(path.read_text(encoding="utf-8"))
    if isinstance(payload, dict):
        payload = payload.get("tasks", [])
    if not isinstance(payload, list):
        raise RuntimeError("--task-file must contain a list or an object with a tasks list")
    tasks = []
    for index, item in enumerate(payload, start=1):
        if not isinstance(item, dict) or "domain" not in item or "task_id" not in item:
            raise RuntimeError(f"Invalid task-file item at index {index}: {item!r}")
        tasks.append((str(item["domain"]), str(item["task_id"])))
    if not tasks:
        raise RuntimeError("--task-file contains no tasks")
    return tasks


def slice_tasks(
    tasks: list[tuple[str, str]],
    start_index: int,
    end_index: int | None,
) -> list[tuple[int, str, str]]:
    if start_index < 1:
        raise RuntimeError("--start-index must be >= 1")
    total = len(tasks)
    end_index = total if end_index is None else end_index
    if end_index < start_index:
        raise RuntimeError("--end-index must be >= --start-index")
    if start_index > total:
        raise RuntimeError(f"--start-index {start_index} exceeds task count {total}")
    end_index = min(end_index, total)
    return [
        (task_index, domain, task_id)
        for task_index, (domain, task_id) in enumerate(tasks, start=1)
        if start_index <= task_index <= end_index
    ]


def cleanup_task_artifacts(task_dir: Path) -> None:
    stale_paths = [
        task_dir / "traj.jsonl",
        task_dir / "result.txt",
        task_dir / "final.png",
        *task_dir.glob("step_*.png"),
    ]
    for stale_path in stale_paths:
        stale_path.unlink(missing_ok=True)


def extract_json_object(text: str) -> dict[str, Any]:
    text = text.strip()
    try:
        return json.loads(text)
    except json.JSONDecodeError:
        match = re.search(r"\{.*\}", text, flags=re.DOTALL)
        if not match:
            raise
        return json.loads(match.group(0))


def action_text(entry: dict[str, Any]) -> str:
    return str(entry.get("action", ""))


def is_text_entry_action(action: str) -> bool:
    return "pyperclip.copy" in action or "pyautogui.write" in action


def is_long_text_entry_action(action: str) -> bool:
    if "pyperclip.copy" in action:
        return True
    if "pyautogui.write" not in action:
        return False
    return len(action) > 160


def is_terminal_paste_action(action: str) -> bool:
    return "pyperclip.copy" in action and "ctrl','shift','v" in action.lower()


def executes_terminal_paste(action: str) -> bool:
    if not is_terminal_paste_action(action):
        return True
    normalized = action.lower().replace(" ", "")
    return (
        "press('enter')" in normalized
        or 'press("enter")' in normalized
        or "\\n" in action
    )


def is_terminal_like_action(action: str) -> bool:
    markers = [
        "python3",
        "wget",
        "curl",
        "ls ",
        "pwd",
        "stat ",
        "file ",
        "grep",
        "find ",
        "pdftotext",
        "soffice",
        "libreoffice",
        "openpyxl",
        "PyPDF2",
        "reportlab",
    ]
    return any(marker in action for marker in markers)


def terminal_command_family(action: str) -> str | None:
    families = [
        ("download", ["wget", "curl", "urlretrieve", "urllib.request"]),
        ("python_script", ["python3", "openpyxl", "PyPDF2", "reportlab"]),
        ("list_verify", ["ls ", "find ", "stat ", "file ", "pwd"]),
        ("text_extract", ["grep", "pdftotext"]),
        ("office_cli", ["soffice", "libreoffice"]),
    ]
    for family, markers in families:
        if any(marker in action for marker in markers):
            return family
    return None


def is_click_only_action(action: str) -> bool:
    if "pyautogui.click" not in action and "pyautogui.doubleClick" not in action:
        return False
    text_markers = ["pyperclip.copy", "pyautogui.write", "press('", "hotkey("]
    return not any(marker in action for marker in text_markers)


def is_right_palette_click(action: str) -> bool:
    if not is_click_only_action(action):
        return False
    numbers = [int(value) for value in re.findall(r"\b\d{3,4}\b", action)]
    return any(value >= 1450 for value in numbers)


def exact_color_instruction(task: dict[str, Any]) -> bool:
    instruction = str(task.get("instruction", "")).lower()
    return "exact" in instruction and any(
        color in instruction
        for color in ("yellow", "red", "green", "blue", "color", "colour")
    )


def exact_named_office_color_instruction(task: dict[str, Any], domain: str | None = None) -> bool:
    if not exact_color_instruction(task):
        return False
    if not is_office_task(task, domain):
        return False
    instruction = str(task.get("instruction", "")).lower()
    return any(color in instruction for color in ("yellow", "red", "green", "blue"))


def uses_pure_web_named_color(action: str, task: dict[str, Any], domain: str | None = None) -> bool:
    if not exact_named_office_color_instruction(task, domain):
        return False
    instruction = str(task.get("instruction", "")).lower()
    normalized = action.lower().replace(" ", "")
    risky_values = []
    if "green" in instruction:
        risky_values.extend(["00ff00", "#00ff00", "'0','255','0'", '"0","255","0"'])
    return any(value in normalized for value in risky_values)


def uses_green_value_for_non_green_task(action: str, task: dict[str, Any], domain: str | None = None) -> bool:
    if not exact_named_office_color_instruction(task, domain):
        return False
    instruction = str(task.get("instruction", "")).lower()
    if "green" in instruction:
        return False
    normalized = action.lower().replace(" ", "")
    return any(value in normalized for value in ("00a933", "#00a933", "0,169,51", "'0','169','51'"))


def is_repeated_numbered_download_task(task: dict[str, Any]) -> bool:
    instruction = str(task.get("instruction", "")).lower()
    if "download" not in instruction or "pdf" not in instruction:
        return False
    return any(
        marker in instruction
        for marker in ("week", "lecture", "slide", "slides", "part", "numbered")
    )


def is_guessed_numbered_download_template(action: str) -> bool:
    normalized = action.lower()
    if ".pdf" not in normalized or not any(marker in normalized for marker in ("wget", "curl", "urlretrieve")):
        return False
    has_template_loop = any(marker in normalized for marker in ("for i in", "{1..", "seq "))
    has_template_url = any(marker in normalized for marker in ("$i", "${i}", "lecture$i", "week$i", "part$i"))
    if not (has_template_loop or has_template_url):
        return False
    derives_hrefs = any(
        marker in normalized
        for marker in ("wget -qo-", "curl -l", "curl -s", "requests.get", "beautifulsoup", "grep -oe")
    )
    verifies_urls = any(marker in normalized for marker in ("--spider", "--head", "curl -i", "curl -f"))
    return not (derives_hrefs or verifies_urls)


def opened_folder_hints(task: dict[str, Any]) -> list[str]:
    hints: list[str] = []
    config = task.get("config", [])
    if not isinstance(config, list):
        return hints
    for item in config:
        if not isinstance(item, dict):
            continue
        parameters = item.get("parameters", {})
        if not isinstance(parameters, dict):
            continue
        command = parameters.get("command")
        if isinstance(command, list) and command:
            executable = str(command[0]).lower()
            if executable in {"nautilus", "xdg-open"}:
                for arg in command[1:]:
                    text = str(arg)
                    if text.startswith("/home/user/"):
                        hints.append(text.rstrip("/"))
        files = parameters.get("files")
        if isinstance(files, list):
            for file_item in files:
                if not isinstance(file_item, dict):
                    continue
                path = str(file_item.get("path", ""))
                if path.startswith("/home/user/"):
                    hints.append(str(Path(path).parent).rstrip("/"))
    deduped: list[str] = []
    for hint in hints:
        if hint and hint not in deduped:
            deduped.append(hint)
    return deduped


def shell_path_hint(path: str) -> str:
    if path == "/home/user":
        return "~"
    if path.startswith("/home/user/"):
        return "~/" + path[len("/home/user/") :]
    return path


def action_mentions_path_hint(action: str, hints: list[str]) -> bool:
    normalized = action.lower()
    compact = normalized.replace(" ", "")
    for hint in hints:
        shell_hint = shell_path_hint(hint).lower()
        basename = Path(hint).name.lower()
        variants = {
            hint.lower(),
            shell_hint,
            shell_hint.replace("~", "$home"),
            shell_hint.replace("~", "${home}"),
            basename,
        }
        if any(variant and variant in normalized for variant in variants):
            return True
        compact_variants = {variant.replace(" ", "") for variant in variants if variant}
        if any(variant and variant in compact for variant in compact_variants):
            return True
    return False


def uses_default_or_home_download_destination(action: str) -> bool:
    normalized = action.lower().replace(" ", "")
    destination_markers = [
        "~/downloads",
        "$home/downloads",
        "${home}/downloads",
        "/home/user/downloads",
        "cd~&&",
        "cd$home&&",
        "cd${home}&&",
        "cd/home/user&&",
    ]
    return any(marker in normalized for marker in destination_markers)


def should_reject_wrong_opened_folder_home(task: dict[str, Any], action: str) -> bool:
    if not is_repeated_numbered_download_task(task):
        return False
    if "/home/oai/" not in action.lower():
        return False
    return any(hint.startswith("/home/user/") for hint in opened_folder_hints(task))


def uses_wrong_vs_code_home(action: str, domain: str | None = None) -> bool:
    if domain != "vs_code":
        return False
    normalized = action.lower()
    if ".config/code/user" not in normalized:
        return False
    return "/home/oai/" in normalized or "/home/user/" in normalized


def is_vs_code_config_write_or_validation(action: str) -> bool:
    normalized = action.lower()
    if ".config/code/user" not in normalized:
        return False
    return any(
        marker in normalized
        for marker in (
            "keybindings.json",
            "settings.json",
            "json.tool",
            "printf",
            "cat ",
            "echo ",
            "workbench.action.focusactiveeditorgroup",
        )
    )


def should_reject_vs_code_gui_drift(domain: str | None, recent_actions: list[str], action: str) -> bool:
    if domain != "vs_code":
        return False
    if not any(is_vs_code_config_write_or_validation(old) for old in recent_actions):
        return False
    normalized = action.lower()
    gui_edit_markers = [
        "code ~/.config/code/user",
        "open keyboard shortcuts",
        "pyautogui.click",
        "pyautogui.write('[",
        "pyautogui.write(\"[",
        "hotkey('ctrl','a')",
        'hotkey("ctrl","a")',
        "press('backspace')",
        'press("backspace")',
    ]
    return any(marker in normalized for marker in gui_edit_markers)


def is_final_numbered_download_action(action: str) -> bool:
    normalized = action.lower()
    has_loop = "for i in" in normalized or "{1.." in normalized or "seq " in normalized
    has_download = "wget" in normalized or "curl" in normalized or "urlretrieve" in normalized
    has_pdf = ".pdf" in normalized
    has_verify = "ls " in normalized or "find " in normalized or "stat " in normalized
    return has_loop and has_download and has_pdf and has_verify


def should_reject_wrong_download_destination(task: dict[str, Any], action: str) -> bool:
    if not is_repeated_numbered_download_task(task):
        return False
    if not is_final_numbered_download_action(action):
        return False
    hints = opened_folder_hints(task)
    if not hints:
        return False
    if action_mentions_path_hint(action, hints):
        return False
    return uses_default_or_home_download_destination(action)


def should_reject_download_drift(
    task: dict[str, Any],
    step_index: int,
    recent_actions: list[str],
    action: str,
) -> bool:
    if not is_repeated_numbered_download_task(task) or step_index < 12:
        return False
    if action in {"DONE", "FAIL", "WAIT"}:
        return False
    if is_final_numbered_download_action(action):
        return False

    recent_downloads = [
        old for old in recent_actions if any(marker in old for marker in ("wget", "curl", "requests", "urlretrieve"))
    ]
    repeated_download_context = len(recent_downloads) >= 2
    exploratory_markers = [
        "requests",
        "urlparse",
        "grep",
        "ctrl','l",
        "ctrl\",\"l",
        "pyautogui.click",
        "alt','tab",
        "alt\",\"tab",
    ]
    if repeated_download_context and any(marker in action for marker in exploratory_markers):
        return True
    if repeated_download_context and any(marker in action for marker in ("wget", "curl")):
        return True
    return False


def should_reject_repeated_long_terminal_entry(
    step_index: int,
    recent_actions: list[str],
    action: str,
) -> bool:
    if step_index < 10:
        return False
    if not is_long_text_entry_action(action) or not is_terminal_like_action(action):
        return False
    long_terminal_entries = [
        old for old in recent_actions if is_long_text_entry_action(old) and is_terminal_like_action(old)
    ]
    if len(long_terminal_entries) < 2:
        return False
    short_verification_markers = ("ls ", "find ", "stat ", "file ", "wc -l", "grep -o")
    return not any(marker in action for marker in short_verification_markers) or len(action) > 900


def is_calc_chart_or_sparkline_task(task: dict[str, Any], domain: str | None = None) -> bool:
    if domain != "libreoffice_calc":
        return False
    instruction = str(task.get("instruction", "")).lower()
    return any(marker in instruction for marker in ("chart", "sparkline", "data range", "series"))


def is_calc_sparkline_task(task: dict[str, Any], domain: str | None = None) -> bool:
    if domain != "libreoffice_calc":
        return False
    instruction = str(task.get("instruction", "")).lower()
    return "sparkline" in instruction


def should_reject_late_calc_sparkline_nonfail(
    task: dict[str, Any],
    domain: str | None,
    step_index: int,
    recent_actions: list[str],
    action: str,
) -> bool:
    if not is_calc_sparkline_task(task, domain) or step_index < 12:
        return False
    if action in {"FAIL", "WAIT"}:
        return False
    evidence_actions = [old.lower() for old in recent_actions]
    attempted_feature_check = any(
        any(marker in old for marker in ("sparkline", "alt','i", 'alt","i', "insert", "find "))
        for old in evidence_actions
    )
    probing_actions = [
        old for old in evidence_actions
        if any(marker in old for marker in ("sparkline", "xlsxwriter", "openpyxl", "chart", "click(", "hotkey("))
    ]
    return attempted_feature_check and len(probing_actions) >= 3


def should_reject_late_calc_click_loop(
    task: dict[str, Any],
    domain: str | None,
    step_index: int,
    recent_actions: list[str],
    action: str,
) -> bool:
    if not is_calc_chart_or_sparkline_task(task, domain) or step_index < 28:
        return False
    if not is_click_only_action(action):
        return False
    calc_clicks = [old for old in recent_actions if is_click_only_action(old)]
    chart_markers = ["chart", "wizard", "click(969", "click(957", "hotkey('alt','i')", 'hotkey("alt","i")']
    chart_attempts = [old for old in recent_actions if any(marker in old.lower() for marker in chart_markers)]
    return len(calc_clicks) >= 3 or len(chart_attempts) >= 2


def is_office_task(task: dict[str, Any], domain: str | None = None) -> bool:
    if domain in {"libreoffice_writer", "libreoffice_calc", "libreoffice_impress"}:
        return True
    instruction = str(task.get("instruction", "")).lower()
    markers = [
        "writer",
        "calc",
        "impress",
        "spreadsheet",
        "workbook",
        "presentation",
        "slide",
        "document",
        "paragraph",
        "line spacing",
    ]
    return any(marker in instruction for marker in markers)


def is_save_action(action: str) -> bool:
    return bool(
        re.search(
            r"hotkey\(\s*['\"]ctrl['\"]\s*,\s*['\"]s['\"]\s*\)",
            action,
        )
    )


def is_office_verification_action(action: str) -> bool:
    markers = [
        "alt','o",
        "Format",
        "Properties",
        "spacing",
        "pdfinfo",
        "python3",
        "openpyxl",
        "python-pptx",
        "unzip",
        "grep",
        "stat ",
        "ls ",
    ]
    return any(marker in action for marker in markers)


def action_rejection_reason(
    task: dict[str, Any],
    step_index: int,
    history: list[dict[str, Any]],
    action: str,
    domain: str | None = None,
) -> str | None:
    recent_actions = [action_text(entry) for entry in history[-8:]]

    if action in {"FAIL", "WAIT"}:
        return None

    if should_reject_wrong_opened_folder_home(task, action):
        hints = ", ".join(shell_path_hint(hint) for hint in opened_folder_hints(task))
        return (
            "Rejected wrong VM user home for the opened target folder. This OSWorld VM uses `/home/user` for task files, "
            f"and the opened/seeded destination appears to be {hints}. Use that target folder via `~` or `/home/user/...`, "
            "not `/home/oai/...`; then download and verify the complete PDF set there."
        )

    if should_reject_wrong_download_destination(task, action):
        hints = ", ".join(shell_path_hint(hint) for hint in opened_folder_hints(task))
        return (
            "Rejected wrong destination for a repeated download-set task. The task asks for the opened/current target folder, "
            f"and the visible/opened folder appears to be {hints}. Use that folder, not ~/Downloads or bare ~; "
            "download the complete numbered PDF set there, then verify names, no gaps, and nonzero sizes before DONE."
        )

    if uses_pure_web_named_color(action, task, domain):
        return (
            "Rejected invented web/CSS RGB value for an exact named Office color. "
            "For LibreOffice named green, use the Basic/Standard palette value or custom `#00A933` / RGB `(0, 169, 51)`; "
            "do not type pure `#00FF00` unless the task explicitly provides that code."
        )

    if uses_green_value_for_non_green_task(action, task, domain):
        return (
            "Rejected green-specific LibreOffice color value on a non-green exact-color task. "
            "Use the exact color named in the task, such as the Basic/Standard yellow/red/blue value or the task-provided RGB."
        )

    if uses_wrong_vs_code_home(action, domain):
        return (
            "Rejected hard-coded VS Code user config home. Use the current VM user's path with "
            "`~/.config/Code/User/...` or `$HOME/.config/Code/User/...`, write the minimal JSON, validate it, "
            "and then verify in VS Code or by reading the same file."
        )

    if should_reject_vs_code_gui_drift(domain, recent_actions, action):
        return (
            "Rejected VS Code config GUI drift after the keybindings/settings JSON was already written or validated. "
            "Do not reopen and manually edit the same JSON. Verify the current user's `~/.config/Code/User/...` file "
            "with a short read/json validation command, test the shortcut if useful, then DONE if it matches."
        )

    if should_reject_download_drift(task, step_index, recent_actions, action):
        return (
            "Rejected repeated download-set drift. Stop browser navigation, scraping scripts, and near-duplicate downloads. "
            "Use one concise VM Terminal action in the target folder: download the full numbered PDF set in a loop, "
            "then list or stat every expected PDF to verify names, no numeric gaps, and nonzero sizes before DONE."
        )

    if is_repeated_numbered_download_task(task) and is_guessed_numbered_download_template(action):
        return (
            "Rejected guessed numbered PDF URL template. For repeated download-set tasks, first enumerate exact PDF hrefs "
            "from the source page or verify the proposed template URLs with a HEAD/spider check, then download the verified "
            "links into the opened destination folder and list nonzero PDF sizes."
        )

    if is_terminal_paste_action(action) and not executes_terminal_paste(action):
        return (
            "Rejected Terminal clipboard paste without an execution step. Focus the VM Terminal, paste or type the command, "
            "press Enter in the same action, then wait for visible output or a returned prompt before issuing another command."
        )

    if should_reject_repeated_long_terminal_entry(step_index, recent_actions, action):
        return (
            "Rejected another long Terminal script after repeated long command-entry attempts. Use a short directly typed "
            "verification or artifact-producing command, switch to a GUI/dialog route, or FAIL with evidence; do not paste "
            "another large script."
        )

    if should_reject_late_calc_click_loop(task, domain, step_index, recent_actions, action):
        return (
            "Rejected late Calc chart/sparkline click loop. Stop precision GUI chart clicking. Save if needed, then use a "
            "file-structure inspection/creation route that verifies the chart or sparkline object and source range, or FAIL "
            "with evidence if the exact artifact route is blocked."
        )

    if should_reject_late_calc_sparkline_nonfail(task, domain, step_index, recent_actions, action):
        return (
            "Rejected continued Calc sparkline work after feature/probe attempts. LibreOffice Calc does not expose reliable "
            "native Excel-style sparklines in this environment. Do not emulate sparklines with ordinary charts/shapes; return "
            "FAIL with the menu/search or package evidence that the exact requested feature is unavailable."
        )

    if exact_color_instruction(task) and step_index >= 6 and is_right_palette_click(action):
        palette_clicks = [old for old in recent_actions if is_right_palette_click(old)]
        if len(palette_clicks) >= 3:
            return (
                "Rejected repeated coordinate palette click on an exact-color task. "
                "Use a named basic color, explicit RGB/custom color dialog, file-structure edit, or FAIL with evidence."
            )

    if action == "DONE" and is_office_task(task, domain):
        saved_recently = any(is_save_action(old) for old in recent_actions)
        verified_after_save = False
        if saved_recently:
            last_save_index = max(
                index for index, old in enumerate(recent_actions) if is_save_action(old)
            )
            verified_after_save = any(
                is_office_verification_action(old)
                for old in recent_actions[last_save_index + 1 :]
            )
        if saved_recently and not verified_after_save:
            return (
                "Rejected early DONE on an Office task: the file was saved but no post-save verification action is visible. "
                "Verify the exact requested property/scope using a dialog, menu/property check, or file-structure check, then DONE if it matches."
            )

    return None


def build_harness_warnings(
    task: dict[str, Any],
    step_index: int,
    history: list[dict[str, Any]],
) -> str:
    instruction = str(task.get("instruction", "")).lower()
    actions = [action_text(entry) for entry in history]
    recent_actions = actions[-8:]
    warnings: list[str] = []

    long_entries = [action for action in recent_actions if is_long_text_entry_action(action)]
    terminal_actions = [action for action in recent_actions if is_terminal_like_action(action)]
    text_entries = [action for action in recent_actions if is_text_entry_action(action)]
    done_or_fail = any(action in {"DONE", "FAIL"} for action in recent_actions)

    if len(long_entries) >= 3 and not done_or_fail:
        warnings.append(
            "Recent history shows repeated long text/script entry. Do not enter another long command now. "
            "First recover to a clean shell/input state if needed, then either run one short decisive command, "
            "verify an already-created artifact, switch to a GUI/dialog route, or FAIL with evidence."
        )

    terminal_pastes = [action for action in recent_actions if is_terminal_paste_action(action)]
    if len(terminal_pastes) >= 2 and not done_or_fail:
        warnings.append(
            "Recent Terminal clipboard-paste commands may not have executed. Do not paste another long Terminal script. "
            "Click/focus Terminal, use one short typed command with Enter, or switch routes."
        )

    if len(terminal_actions) >= 5 and step_index >= 12:
        warnings.append(
            "Recent history is dominated by Terminal probes. More probing is not progress. "
            "The next action should produce the requested final artifact/state, verify a concrete output, or abandon this route."
        )

    if len(text_entries) >= 5 and step_index >= 18:
        warnings.append(
            "Many recent actions are text-entry attempts. Avoid another near-duplicate paste/type action. "
            "Use the current screen state to decide whether the command ran, whether files exist, or whether the route is blocked."
        )

    if "pdf" in instruction and ("spreadsheet" in instruction or "excel" in instruction or "form" in instruction):
        if step_index >= 10 and len(terminal_actions) >= 3:
            warnings.append(
                "This is a repetitive PDF/form generation task. By now the route should be: inspect schema once, generate all PDFs "
                "with deterministic employee filenames in the evaluator-expected location, then verify count/names/sizes/content. "
                "Do not keep issuing package or template probes without producing the PDFs."
            )

    if "download" in instruction and ("week" in instruction or "pdf" in instruction):
        if step_index >= 5:
            warnings.append(
                "For repeated PDF downloads, do not guess numbered PDF URLs. First print exact `.pdf` hrefs from the source "
                "page(s), or derive a candidate numbered template from the visible page/seeded filename and verify every "
                "candidate with HEAD/spider before using it. Use `~` or `/home/user/...`, not `/home/oai/...`, and verify names/sizes."
            )
        if step_index >= 12 and len(terminal_actions) >= 3:
            hints = opened_folder_hints(task)
            target_clause = ""
            if hints:
                target_clause = (
                    " The opened/seeded destination folder appears to be "
                    + ", ".join(shell_path_hint(hint) for hint in hints)
                    + "; use that folder, not ~/Downloads or bare ~."
                )
            warnings.append(
                "This is a repeated download-set task. Preserve original filenames in the opened destination folder, verify no gaps "
                "and nonzero PDF sizes, then DONE. Do not keep re-downloading or re-listing once the expected set is present. "
                "If this is a numbered week/lecture/part set, use one short loop in the target folder and then verify all expected numbers."
                + target_clause
            )

    if "exact" in instruction and any(color in instruction for color in ("yellow", "red", "green", "blue", "color", "colour")):
        warnings.append(
            "Exact color task detected. Use named basic colors or an explicit RGB/custom color dialog, one target object at a time. "
            "Do not choose visually similar swatches. Only use green-specific values such as `#00A933` when the instruction "
            "explicitly asks for green. Verify saved state before DONE."
        )

    if "shortcut" in instruction or "keybinding" in instruction or "keyboard shortcut" in instruction:
        if "code" in instruction or "vs code" in instruction or "terminal" in instruction:
            warnings.append(
                "For VS Code shortcut/settings tasks, write the current user's `~/.config/Code/User/keybindings.json` or "
                "`settings.json` with minimal valid JSON. Avoid opening hard-coded `/home/oai` or `/home/user` paths through "
                "the GUI. Once the file is written and validated, do not manually reopen and edit it; verify the same file "
                "or test the requested shortcut/setting."
            )

    if any(marker in instruction for marker in ("line spacing", "tab stop", "tab-stop", "paragraph")):
        if is_office_task(task):
            warnings.append(
                "Writer paragraph/layout task detected. Use one deterministic selection and property route, then verify the "
                "saved paragraph property and that adjacent unrelated content is unchanged. Do not keep alternating GUI clicks "
                "with unverified UNO/Terminal scripts."
            )

    if any(marker in instruction for marker in ("chart", "sparkline", "data range", "series")):
        if is_office_task(task):
            warnings.append(
                "Calc chart/sparkline task detected. Before DONE, verify the saved workbook contains the requested chart or "
                "sparkline object with the exact source range/series. If the GUI route is still unresolved after several "
                "chart wizard/click attempts, stop clicking and use a file-structure route or FAIL with evidence."
            )
    if "sparkline" in instruction and is_office_task(task):
        warnings.append(
            "Sparkline task detected. First verify whether the app has native sparkline support. If the exact sparkline "
            "feature is unavailable, do not emulate it with regular charts or shapes; return FAIL with evidence."
        )

    if not warnings:
        return "None."
    return "\n".join(f"- {warning}" for warning in warnings)


def build_prompt(
    task: dict[str, Any],
    step_index: int,
    history: list[dict[str, Any]],
    runner_notice: str | None = None,
) -> str:
    history_text = json.dumps(history[-5:], ensure_ascii=False, indent=2)
    harness_warnings = build_harness_warnings(task, step_index, history)
    runner_notice_text = runner_notice or "None."
    return f"""{SYSTEM_GUIDANCE}

Task instruction:
{task["instruction"]}

Current step: {step_index}

Harness state warnings:
{harness_warnings}

Runner intervention notice:
{runner_notice_text}

Recent action history:
{history_text}

Return exactly one next action as JSON.
"""


def save_observation_screenshot(observation: dict[str, Any], path: Path, label: str) -> Path:
    screenshot = observation.get("screenshot")
    if not screenshot:
        raise RuntimeError(f"empty screenshot for {label}")
    path.write_bytes(screenshot)
    return path


def call_codex(
    codex_bin: str,
    model: str | None,
    schema_path: Path,
    screenshot_path: Path,
    prompt: str,
    workdir: Path,
) -> dict[str, Any]:
    with tempfile.TemporaryDirectory(prefix="osworld-codex-") as tmpdir:
        response_path = Path(tmpdir) / "response.json"
        command = [
            codex_bin,
            "exec",
            "--skip-git-repo-check",
            "--ephemeral",
            "--sandbox",
            "read-only",
            "--output-schema",
            str(schema_path),
            "--output-last-message",
            str(response_path),
            "-C",
            str(workdir),
            "-i",
            str(screenshot_path),
        ]
        if model:
            command.extend(["--model", model])
        result = subprocess.run(
            command,
            input=prompt,
            text=True,
            capture_output=True,
            check=False,
            timeout=600,
        )
        if result.returncode != 0:
            raise RuntimeError(
                "codex exec failed: "
                + (result.stderr.strip() or result.stdout.strip() or str(result.returncode))
            )
        return extract_json_object(response_path.read_text(encoding="utf-8"))


def main() -> int:
    args = parse_args()
    original_cwd = Path.cwd()
    osworld_dir = resolve_path(original_cwd, args.osworld_dir)
    path_to_vm = resolve_path(original_cwd, args.path_to_vm)
    schema_path = resolve_path(original_cwd, args.schema)
    result_dir = resolve_path(original_cwd, args.result_dir)
    summary_path = (
        resolve_path(original_cwd, args.summary_path)
        if args.summary_path
        else result_dir / "summary.json"
    )
    metadata_path = (
        resolve_path(original_cwd, args.metadata_path)
        if args.metadata_path
        else result_dir / "run_metadata.json"
    )
    domains = [domain.strip() for domain in args.domains.split(",") if domain.strip()]

    all_tasks = (
        load_task_file(resolve_path(original_cwd, args.task_file))
        if args.task_file
        else discover_tasks(osworld_dir, domains, args.task_mode)
    )
    tasks = slice_tasks(all_tasks, args.start_index, args.end_index)

    codex_bin = args.codex_bin or ensure_executable("codex")
    ensure_vmrun_on_path()
    ensure_snapshot(str(path_to_vm), args.snapshot_name)

    os.chdir(osworld_dir)
    from desktop_env.desktop_env import DesktopEnv

    env = DesktopEnv(
        provider_name=args.provider_name,
        path_to_vm=str(path_to_vm),
        snapshot_name=args.snapshot_name,
        os_type=args.os_type,
        action_space="pyautogui",
        headless=args.headless,
        require_a11y_tree=False,
    )

    summary = []
    result_dir.mkdir(parents=True, exist_ok=True)
    summary_path.parent.mkdir(parents=True, exist_ok=True)
    metadata_path.parent.mkdir(parents=True, exist_ok=True)
    metadata_path.write_text(
        json.dumps(
            {
                "started_at": time.strftime("%Y-%m-%dT%H:%M:%S%z"),
                "task_mode": args.task_mode,
                "domains": domains,
                "start_index": args.start_index,
                "end_index": args.end_index,
                "selected_tasks": len(tasks),
                "total_discovered_tasks": len(all_tasks),
                "result_dir": str(result_dir),
                "summary_path": str(summary_path),
                "path_to_vm": str(path_to_vm),
                "model": args.model,
                "max_steps": args.max_steps,
                "retry_no_result": args.retry_no_result,
                "harness": "v3.18",
            },
            ensure_ascii=False,
            indent=2,
        ),
        encoding="utf-8",
    )
    try:
        for position, (task_number, domain, task_id) in enumerate(tasks, start=1):
            task = load_task(osworld_dir, domain, task_id)
            task_dir = result_dir / domain / task_id
            task_dir.mkdir(parents=True, exist_ok=True)
            if args.skip_completed and (task_dir / "result.txt").exists():
                try:
                    score = float((task_dir / "result.txt").read_text(encoding="utf-8").strip())
                except ValueError:
                    score = None
                row = {
                    "domain": domain,
                    "task_id": task_id,
                    "status": "ok",
                    "score": score,
                    "error": None,
                    "skipped": True,
                }
                summary.append(row)
                summary_path.write_text(
                    json.dumps(summary, ensure_ascii=False, indent=2),
                    encoding="utf-8",
                )
                if summary_path != result_dir / "summary.json":
                    (result_dir / "summary.json").write_text(
                        json.dumps(summary, ensure_ascii=False, indent=2),
                        encoding="utf-8",
                    )
                print(
                    f"codex_eval_skip task={task_number}/{len(all_tasks)} "
                    f"slice={position}/{len(tasks)} "
                    f"domain={domain} task={task_id} score={score}",
                    flush=True,
                )
                continue
            row = {
                "domain": domain,
                "task_id": task_id,
                "status": "error",
                "score": None,
                "error": None,
                "attempts": 0,
                "retried_no_result": False,
            }
            for attempt in range(1, args.retry_no_result + 2):
                cleanup_task_artifacts(task_dir)
                history: list[dict[str, Any]] = []
                row["attempts"] = attempt
                print(
                    f"codex_eval_start task={task_number}/{len(all_tasks)} "
                    f"slice={position}/{len(tasks)} "
                    f"attempt={attempt}/{args.retry_no_result + 1} "
                    f"domain={domain} task={task_id}",
                    flush=True,
                )
                try:
                    observation = env.reset(task_config=task)
                    for step_index in range(1, args.max_steps + 1):
                        before_screenshot_path = task_dir / f"step_{step_index:03d}_before.png"
                        save_observation_screenshot(
                            observation,
                            before_screenshot_path,
                            f"step {step_index} before action",
                        )
                        response = call_codex(
                            codex_bin=codex_bin,
                            model=args.model,
                            schema_path=schema_path,
                            screenshot_path=before_screenshot_path,
                            prompt=build_prompt(task, step_index, history),
                            workdir=original_cwd,
                        )
                        rejection_reason = action_rejection_reason(
                            task,
                            step_index,
                            history,
                            response["action"].strip(),
                            domain,
                        )
                        if rejection_reason:
                            print(
                                f"codex_eval_reject step={step_index} reason={rejection_reason} "
                                f"action={response['action'].strip()}",
                                flush=True,
                            )
                            response = call_codex(
                                codex_bin=codex_bin,
                                model=args.model,
                                schema_path=schema_path,
                                screenshot_path=before_screenshot_path,
                                prompt=build_prompt(
                                    task,
                                    step_index,
                                    history,
                                    runner_notice=(
                                        rejection_reason
                                        + " The rejected action was: "
                                        + response["action"].strip()
                                    ),
                                ),
                                workdir=original_cwd,
                            )
                        action = response["action"].strip()
                        print(f"codex_eval_action step={step_index} action={action}", flush=True)
                        with (task_dir / "traj.jsonl").open("a", encoding="utf-8") as traj_file:
                            if action in {"DONE", "FAIL"}:
                                next_observation, _, _, _ = env.step(action, pause=0.5)
                            else:
                                next_observation, _, _, _ = env.step(action, pause=1.0)
                            if action in {"DONE", "FAIL"} or step_index == args.max_steps:
                                save_observation_screenshot(
                                    next_observation,
                                    task_dir / "final.png",
                                    "final state",
                                )
                            history.append(
                                {
                                    "step": step_index,
                                    "before_screenshot": before_screenshot_path.name,
                                    **response,
                                }
                            )
                            traj_file.write(json.dumps(history[-1], ensure_ascii=False) + "\n")
                        if action in {"DONE", "FAIL"}:
                            break
                        observation = next_observation
                    score = env.evaluate()
                    row["status"] = "ok"
                    row["score"] = float(score)
                    row["error"] = None
                    (task_dir / "result.txt").write_text(f"{score}\n", encoding="utf-8")
                    print(
                        f"codex_eval_ok domain={domain} task={task_id} "
                        f"attempt={attempt} score={score}",
                        flush=True,
                    )
                    break
                except Exception as exc:
                    row["status"] = "error"
                    row["score"] = None
                    row["error"] = repr(exc)
                    print(
                        f"codex_eval_error domain={domain} task={task_id} "
                        f"attempt={attempt} error={exc!r}",
                        flush=True,
                    )
                    if attempt <= args.retry_no_result:
                        row["retried_no_result"] = True
                        print(
                            f"codex_eval_retry_no_result domain={domain} "
                            f"task={task_id} next_attempt={attempt + 1}",
                            flush=True,
                        )
                        time.sleep(10)

            summary.append(row)
            summary_path.write_text(
                json.dumps(summary, ensure_ascii=False, indent=2),
                encoding="utf-8",
            )
            if summary_path != result_dir / "summary.json":
                (result_dir / "summary.json").write_text(
                    json.dumps(summary, ensure_ascii=False, indent=2),
                    encoding="utf-8",
                )
    finally:
        env.close()

    ok_count = sum(row["status"] == "ok" for row in summary)
    if not args.no_analysis:
        from osworld_codex_report import write_report

        analysis_path = (
            resolve_path(original_cwd, args.analysis_html)
            if args.analysis_html
            else result_dir / "analysis.html"
        )
        write_report(
            result_dir=result_dir,
            osworld_dir=osworld_dir,
            output_path=analysis_path,
        )
        print(f"analysis={analysis_path}")
    print(f"codex_eval_summary ok={ok_count} total={len(summary)}")
    print(f"summary={summary_path}")
    return 0 if ok_count == len(summary) else 1


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except Exception as exc:
        print(f"codex_eval_failed: {exc}", file=sys.stderr)
        raise SystemExit(1)
