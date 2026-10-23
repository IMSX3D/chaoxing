# -*- coding: utf-8 -*-
"""
只读查看学习通各课程进度（章节完成情况）。

严格只读：只调用登录、课程列表、章节列表三个查询接口。
**绝不调用 `get_job_list()`** —— 它内部在"解析不到任何任务点"时会调 `study_emptypage()`，
那是 `studentstudyAjax`，会把章节标记成已访问/已完成。

用法：
    .venv\\Scripts\\python.exe progress.py
    .venv\\Scripts\\python.exe progress.py --md
    .venv\\Scripts\\python.exe progress.py --course 265830212

报告存档：
    带 --md 运行时，除了写 进度报告.md（最新一份），还会在 进度存档\\ 下
    另存一份 进度报告_YYYYMMDD_HHMMSS.md —— 每次运行一份，不覆盖旧存档。
    存档可用 清理存档.cmd 一键清理 7 天前的旧报告。
"""
import argparse
import configparser
import sys
import time
import unicodedata
from pathlib import Path

from api.base import Chaoxing, Account

HERE = Path(__file__).resolve().parent
DEFAULT_CONFIG = HERE / "config.ini"
DEFAULT_REPORT = HERE / "进度报告.md"
# 每次运行都会在这里留一份带时间戳的存档，和日志的轮转模式类似
ARCHIVE_DIR = HERE / "进度存档"

# 某些课程名里混了不间断空格(\xa0)等 GBK 编不出来的字符，直接 print 会在
# cp936 终端里抛 UnicodeEncodeError；这里让编码错误降级成 "?"，不中断输出。
for _stream in (sys.stdout, sys.stderr):
    try:
        _stream.reconfigure(errors="replace")
    except (AttributeError, ValueError):
        pass


def norm(text) -> str:
    """把标题里的不间断空格/全角空格/零宽字符统一成普通空格。"""
    text = str(text if text is not None else "").replace("\xa0", " ").replace("\u3000", " ")
    text = "".join(ch for ch in text if unicodedata.category(ch) != "Cf")
    return " ".join(text.split())


def dwidth(text: str) -> int:
    """终端显示宽度（中文算 2 列）。"""
    return sum(2 if unicodedata.east_asian_width(ch) in ("W", "F") else 1 for ch in text)


def truncate_display(text: str, width: int) -> str:
    out, used = "", 0
    for ch in text:
        cw = 2 if unicodedata.east_asian_width(ch) in ("W", "F") else 1
        if used + cw > width:
            return (out[:-1] + "…") if out else out
        out += ch
        used += cw
    return out


def pad(text: str, width: int, right: bool = False) -> str:
    text = truncate_display(str(text), width)
    gap = max(0, width - dwidth(text))
    return (" " * gap + text) if right else (text + " " * gap)


def parse_args():
    p = argparse.ArgumentParser(description="只读查看学习通课程进度")
    p.add_argument("-c", "--config", default=str(DEFAULT_CONFIG), help="配置文件路径")
    p.add_argument("--course", default=None, help="只看某门课（课程 ID）")
    p.add_argument("--md", nargs="?", const=str(HERE / "进度报告.md"), default=None,
                   help="把结果写成 Markdown 报告（不给路径则写到 进度报告.md）")
    p.add_argument("--no-archive", action="store_true",
                   help="只写 --md 指定的报告，不生成 进度存档 下的带时间戳副本")
    p.add_argument("--sleep", type=float, default=0.5, help="课程之间的间隔秒数（默认 0.5）")
    p.add_argument("--limit", type=int, default=0, help="最多查看前 N 门课（0 = 全部）")
    p.add_argument("--todo", action="store_true", help="额外列出每门课未完成的章节名")
    return p.parse_args()


def load_common(path: Path) -> dict:
    if not path.exists():
        sys.exit(f"找不到配置文件: {path}")
    cp = configparser.ConfigParser()
    cp.read(path, encoding="utf8")
    if not cp.has_section("common"):
        sys.exit(f"配置文件缺少 [common] 段: {path}")
    conf = dict(cp.items("common"))
    conf["use_cookies"] = str(conf.get("use_cookies", "false")).strip().lower() in ("true", "1", "yes", "on")
    return conf


def to_int(value, default=0):
    try:
        return int(str(value).strip())
    except (TypeError, ValueError):
        return default


def fmt_pct(done, total):
    return f"{done / total * 100:5.1f}%" if total else "  --  "


def study_course(cx: Chaoxing, course: dict) -> dict:
    """只读：拉一门课的章节列表，统计完成情况。"""
    result = cx.get_course_point(course["courseId"], course["clazzId"], course["cpi"])
    points = result.get("points", []) or []
    for p in points:
        p["title"] = norm(p.get("title"))
    done = [p for p in points if p.get("has_finished")]
    todo = [p for p in points if not p.get("has_finished")]
    return {
        "course": course,
        "points": points,
        "done": len(done),
        "todo": len(todo),
        "total": len(points),
        "job_total": sum(to_int(p.get("jobCount"), 0) for p in points),
        "locked": sum(1 for p in points if p.get("need_unlock")),
    }


def build_markdown(rows, show_todo=False) -> str:
    total_points = sum(r["total"] for r in rows)
    total_done = sum(r["done"] for r in rows)
    lines = [
        "# 学习通进度报告",
        "",
        f"生成时间：{time.strftime('%Y-%m-%d %H:%M:%S')}",
        "",
        f"课程数：{len(rows)}　章节总数：{total_points}　已完成：{total_done}　"
        f"总完成率：{fmt_pct(total_done, total_points).strip()}",
        "",
        "| 课程 | 课程ID | 章节 | 已完成 | 未完成 | 完成率 | 任务点数 | 未解锁章节 |",
        "|---|---|---|---|---|---|---|---|",
    ]
    for r in rows:
        c = r["course"]
        lines.append(
            f"| {c['title']} | {c['courseId']} | {r['total']} | {r['done']} | {r['todo']} | "
            f"{fmt_pct(r['done'], r['total']).strip()} | {r['job_total']} | {r['locked']} |"
        )

    if show_todo:
        lines += ["", "## 未完成章节", ""]
        for r in rows:
            todo = [p for p in r["points"] if not p.get("has_finished")]
            if not todo:
                continue
            lines.append(f"### {r['course']['title']}（剩余 {len(todo)}/{r['total']}）")
            lines.append("")
            for p in todo:
                flag = "（未解锁）" if p.get("need_unlock") else ""
                lines.append(f"- {p.get('title')}{flag}")
            lines.append("")

    return "\n".join(lines) + "\n"


def write_markdown(path: Path, text: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text, encoding="utf8")
    print(f"\nMarkdown 报告已写入: {path}")


def archive_markdown(text: str) -> Path:
    """把本次报告另存一份带时间戳的存档，不覆盖旧存档。"""
    ARCHIVE_DIR.mkdir(parents=True, exist_ok=True)
    stamp = time.strftime("%Y%m%d_%H%M%S")
    target = ARCHIVE_DIR / f"进度报告_{stamp}.md"
    n = 1
    while target.exists():
        target = ARCHIVE_DIR / f"进度报告_{stamp}_{n}.md"
        n += 1
    target.write_text(text, encoding="utf8")
    return target


def main():
    args = parse_args()
    conf = load_common(Path(args.config))

    username = conf.get("username", "").strip()
    password = conf.get("password", "").strip()
    use_cookies = conf.get("use_cookies", False)

    if not use_cookies and (not username or not password):
        username = input("手机号: ").strip()
        password = input("密码: ").strip()

    cx = Chaoxing(account=Account(username, password), tiku=None)
    print("正在登录...")
    result = cx.login(login_with_cookies=use_cookies)
    if not isinstance(result, dict) or not result.get("status"):
        sys.exit(f"登录失败: {result}")

    print("正在读取课程列表...")
    courses = cx.get_course_list()
    if not courses:
        sys.exit("课程列表为空")
    for c in courses:
        c["title"] = norm(c.get("title"))
    if args.course:
        courses = [c for c in courses if str(c["courseId"]) == str(args.course)]
        if not courses:
            sys.exit(f"没找到课程 ID: {args.course}")
    if args.limit > 0:
        courses = courses[: args.limit]

    print(f"共 {len(courses)} 门课，开始逐个读取章节...\n")
    print(
        pad("课程", 26) + " " + pad("课程ID", 12) + " " + pad("章节", 4, True) + " "
        + pad("已完成", 6, True) + " " + pad("完成率", 7, True) + " "
        + pad("任务点数", 9, True) + " " + pad("未解锁", 6, True)
    )
    print("-" * 90)

    rows = []
    for course in courses:
        try:
            row = study_course(cx, course)
        except Exception as exc:
            print(f"{pad(course['title'], 26)} 读取失败: {type(exc).__name__}: {exc}")
            time.sleep(args.sleep)
            continue
        rows.append(row)
        print(
            pad(course["title"], 26) + " " + pad(course["courseId"], 12) + " "
            + pad(row["total"], 4, True) + " " + pad(row["done"], 6, True) + " "
            + pad(fmt_pct(row["done"], row["total"]), 7, True) + " "
            + pad(row["job_total"], 9, True) + " " + pad(row["locked"], 6, True)
        )
        time.sleep(args.sleep)

    total_points = sum(r["total"] for r in rows)
    total_done = sum(r["done"] for r in rows)
    print("-" * 90)
    print(
        f"合计: {len(rows)} 门课, {total_points} 个章节, 已完成 {total_done}, "
        f"总完成率 {fmt_pct(total_done, total_points).strip()}"
    )

    locked_courses = [r for r in rows if r["locked"]]
    if locked_courses:
        print("有未解锁章节的课程: " + ", ".join(
            f"{r['course']['title']}({r['locked']} 章)" for r in locked_courses))

    if args.todo:
        print()
        for r in rows:
            todo = [p for p in r["points"] if not p.get("has_finished")]
            if not todo:
                continue
            print(f"== {r['course']['title']} 未完成 {len(todo)}/{r['total']} ==")
            for p in todo:
                flag = "  [未解锁]" if p.get("need_unlock") else ""
                print(f"   - {p.get('title')}{flag}")
            print()

    if args.md:
        if not rows:
            print("没有可写的课程数据")
        else:
            latest = Path(args.md)
            if not latest.is_absolute():
                latest = HERE / latest
            text = build_markdown(rows, show_todo=args.todo)
            write_markdown(latest, text)
            if not args.no_archive:
                saved = archive_markdown(text)
                print(f"存档副本已写入: {saved}")


if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print("\n已中断")
