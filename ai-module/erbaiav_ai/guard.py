# -*- coding: utf-8 -*-
"""数据修改拦截 (DataGuard) —— 二伯杀毒「发现修改电脑数据 → 直接拦截 → 可选信任」。

工作原理：
  1. 对受保护目录内的 写入/覆盖/删除/重命名 操作做前置检查；
  2. 未信任的修改操作被【直接拦截】，并把原文件自动备份到 .erbai-guard/backup/；
  3. 每次拦截生成一条 pending 事件，等待用户决策：
       - allow   ：把该路径加入信任区，并重放（放行）被拦截的操作；
       - block   ：拒绝该次修改，文件保持原样，备份保留；
       - restore ：从备份恢复原文件（撤销已被放行/部分写入的改动）。

状态与数据保存在受保护目录下的 .erbai-guard/ 中：
  config.json    保护开关与模式（block=直接拦截 / off=关闭）
  trusted.json   信任区（路径 -> {reason, time, by}）
  events.jsonl   拦截事件日志（含 pending 操作载荷，可重放）
  backup/        被拦截修改前的原文件备份

零依赖（仅 Python 标准库），可独立使用：
  python -m erbaiav_ai.guard --workspace <目录> status
  python -m erbaiav_ai.guard --workspace <目录> trust docs/计划.docx --reason 正常软件
  python -m erbaiav_ai.guard --workspace <目录> attempt-write notes.txt "hello" --source demo.exe
  python -m erbaiav_ai.guard --workspace <目录> decide <事件ID> allow|block|restore
"""
import argparse
import hashlib
import json
import os
import shutil
import sys
import time

from . import fsops

DEFAULT_MODE = "block"          # block=直接拦截 off=关闭
_ALLOWED_MODES = ("block", "off")
_ALLOWED_DECISIONS = ("allow", "block", "restore")


def _now():
    return time.strftime("%Y-%m-%d %H:%M:%S")


class DataGuard:
    """受保护目录的数据修改拦截器。"""

    def __init__(self, workspace=None, mode=None):
        self.workspace = os.path.abspath(os.path.expanduser(str(workspace or os.getcwd())))
        os.makedirs(self.workspace, exist_ok=True)
        self.dir = os.path.join(self.workspace, ".erbai-guard")
        os.makedirs(self.dir, exist_ok=True)
        self._config_path = os.path.join(self.dir, "config.json")
        self._trust_path = os.path.join(self.dir, "trusted.json")
        self._events_path = os.path.join(self.dir, "events.jsonl")
        self._backup_dir = os.path.join(self.dir, "backup")
        self._config = {"enabled": True, "mode": DEFAULT_MODE}
        self._trusted = {}
        if mode is not None:
            self.set_mode(mode)
        self._load()

    # ---------- 内部状态 ----------
    def _load(self):
        try:
            if os.path.isfile(self._config_path):
                with open(self._config_path, "r", encoding="utf-8") as f:
                    self._config.update(json.load(f))
        except Exception:
            pass
        try:
            if os.path.isfile(self._trust_path):
                with open(self._trust_path, "r", encoding="utf-8") as f:
                    data = json.load(f)
                if isinstance(data, dict):
                    self._trusted = data
                elif isinstance(data, list):
                    self._trusted = {p: {"reason": "", "time": "", "by": "user"} for p in data}
        except Exception:
            pass

    def _save_config(self):
        with open(self._config_path, "w", encoding="utf-8") as f:
            json.dump(self._config, f, ensure_ascii=False, indent=2)

    def _save_trusted(self):
        with open(self._trust_path, "w", encoding="utf-8") as f:
            json.dump(self._trusted, f, ensure_ascii=False, indent=2)

    def _load_events(self):
        events = []
        try:
            if os.path.isfile(self._events_path):
                with open(self._events_path, "r", encoding="utf-8") as f:
                    for line in f:
                        line = line.strip()
                        if line:
                            try:
                                events.append(json.loads(line))
                            except Exception:
                                pass
        except Exception:
            pass
        return events

    def _save_events(self, events):
        with open(self._events_path, "w", encoding="utf-8") as f:
            for evt in events:
                f.write(json.dumps(evt, ensure_ascii=False) + "\n")

    def _append_event(self, evt):
        events = self._load_events()
        events.append(evt)
        if len(events) > 500:
            events = events[-500:]
        self._save_events(events)

    # ---------- 路径 ----------
    def _norm_rel(self, rel):
        """校验并把路径规范化为工作区相对路径（防路径穿越）。"""
        full = fsops.safe_join(self.workspace, rel)
        return os.path.relpath(full, self.workspace).replace("\\", "/")

    def _full(self, rel):
        return fsops.safe_join(self.workspace, rel)

    # ---------- 开关与状态 ----------
    def set_mode(self, mode):
        mode = (mode or DEFAULT_MODE).lower()
        if mode not in _ALLOWED_MODES:
            raise ValueError("未知模式: %s（可选 %s）" % (mode, "/".join(_ALLOWED_MODES)))
        self._config["mode"] = mode
        self._config["enabled"] = mode != "off"
        self._save_config()
        return self.status()

    def enable(self, mode=DEFAULT_MODE):
        return self.set_mode(mode)

    def disable(self):
        return self.set_mode("off")

    def status(self):
        events = self._load_events()
        pending = sum(1 for e in events if e.get("status") == "pending")
        blocked = sum(1 for e in events if e.get("status") != "allowed")
        return {
            "enabled": bool(self._config.get("enabled", True)),
            "mode": self._config.get("mode", DEFAULT_MODE),
            "workspace": self.workspace,
            "guard_dir": self.dir,
            "trusted_count": len(self._trusted),
            "pending_events": pending,
            "blocked_events": blocked,
            "trusted": [{"path": p, "reason": v.get("reason", ""),
                         "time": v.get("time", ""), "by": v.get("by", "user")}
                        for p, v in sorted(self._trusted.items())],
            "recent_events": events[-10:][::-1],
        }

    # ---------- 信任区 ----------
    def is_trusted(self, rel):
        rel = self._norm_rel(rel)
        for t in self._trusted:
            t = t.replace("\\", "/").rstrip("/")
            if t == rel or rel.startswith(t + "/"):
                return True
        return False

    def trust(self, rel, reason="", by="user"):
        rel = self._norm_rel(rel)
        self._trusted[rel] = {
            "reason": reason or "",
            "time": _now(),
            "by": by or "user",
        }
        self._save_trusted()
        return {"path": rel, "reason": reason or "", "by": by or "user"}

    def untrust(self, rel):
        rel = self._norm_rel(rel)
        removed = self._trusted.pop(rel, None)
        self._save_trusted()
        return {"path": rel, "removed": bool(removed)}

    def list_trusted(self):
        return self.status()["trusted"]

    # ---------- 拦截核心 ----------
    def _block(self, kind, rel, source, payload):
        """未信任的修改 -> 备份原文件并记录 pending 事件（不执行修改）。"""
        evt_id = "evt_" + hashlib.md5(
            ("%s|%s|%s" % (time.time_ns(), kind, rel)).encode("utf-8")).hexdigest()[:12]
        full = self._full(rel)
        backup = None
        had_original = bool(os.path.exists(full))
        if had_original:
            bfull = os.path.join(self._backup_dir, evt_id)
            os.makedirs(bfull, exist_ok=True)
            try:
                if os.path.isdir(full):
                    shutil.copytree(full, os.path.join(bfull, os.path.basename(rel) or "dir"),
                                    dirs_exist_ok=True)
                else:
                    shutil.copy2(full, os.path.join(bfull, os.path.basename(rel) or "file"))
                backup = os.path.relpath(os.path.join(bfull, os.path.basename(rel) or "file"),
                                         self.dir).replace("\\", "/")
            except Exception:
                backup = None
        evt = {
            "id": evt_id,
            "time": _now(),
            "status": "pending",
            "kind": kind,
            "rel": rel,
            "source": source or "未知程序",
            "payload": payload or {},
            "backup": backup,
            "had_original": had_original,
        }
        self._append_event(evt)
        return {
            "blocked": True,
            "action": kind,
            "path": rel,
            "source": evt["source"],
            "event_id": evt_id,
            "reason": "未信任的程序尝试修改数据，已被二伯杀毒拦截",
            "backup": backup,
            "next": "调用 decide(event_id, allow|block|restore) 处理",
        }

    def _perform(self, kind, rel, payload):
        """实际执行操作（信任路径直接放行，或 allow 后重放）。"""
        if kind == "write":
            r = fsops.write_file(self.workspace, rel, payload.get("content", ""))
            return {"action": "write", "path": r["path"], "op": r["action"],
                    "bytes": r["bytes"]}
        if kind == "delete":
            full = self._full(rel)
            if os.path.isfile(full):
                os.remove(full)
            elif os.path.isdir(full):
                shutil.rmtree(full)
            return {"action": "delete", "path": rel}
        if kind == "rename":
            full = self._full(rel)
            new_rel = self._norm_rel(payload.get("new_rel"))
            new_full = self._full(new_rel)
            os.makedirs(os.path.dirname(new_full), exist_ok=True)
            os.rename(full, new_full)
            return {"action": "rename", "path": rel, "new_path": new_rel}
        raise ValueError("未知操作类型: %s" % kind)

    def attempt_write(self, rel, content="", source="未知程序"):
        """程序尝试写入/覆盖文件。受保护且未信任 -> 拦截并返回 pending。"""
        rel = self._norm_rel(rel)
        if not self._config.get("enabled", True) or self.is_trusted(rel):
            return {"blocked": False, **self._perform("write", rel, {"content": content})}
        return self._block("write", rel, source, {"content": content})

    def attempt_delete(self, rel, source="未知程序"):
        """程序尝试删除文件。受保护且未信任 -> 拦截并返回 pending。"""
        rel = self._norm_rel(rel)
        if not self._config.get("enabled", True) or self.is_trusted(rel):
            return {"blocked": False, **self._perform("delete", rel, {})}
        return self._block("delete", rel, source, {})

    def attempt_rename(self, rel, new_rel, source="未知程序"):
        """程序尝试重命名/移动文件。受保护且未信任 -> 拦截并返回 pending。"""
        rel = self._norm_rel(rel)
        new_rel = self._norm_rel(new_rel)
        if not self._config.get("enabled", True) or self.is_trusted(rel):
            return {"blocked": False,
                    **self._perform("rename", rel, {"new_rel": new_rel})}
        return self._block("rename", rel, source, {"new_rel": new_rel})

    # ---------- 拦截后决策 ----------
    def decide(self, event_id, action, by="user"):
        """处理一条被拦截的事件：allow=信任并放行 / block=继续拦截 / restore=回滚恢复。"""
        events = self._load_events()
        evt = next((e for e in events if e.get("id") == event_id), None)
        if not evt:
            raise ValueError("事件不存在: %s" % event_id)
        if evt.get("status") != "pending":
            raise ValueError("该事件已处理（当前状态: %s）" % evt.get("status"))
        action = (action or "").lower()
        if action not in _ALLOWED_DECISIONS:
            raise ValueError("未知决策: %s（可选 %s）" % (action, "/".join(_ALLOWED_DECISIONS)))

        rel = evt.get("rel")
        if action == "allow":
            self.trust(rel, reason="拦截后选择信任放行", by=by)
            replay = self._perform(evt.get("kind"), rel, evt.get("payload") or {})
            evt["status"] = "allowed"
            evt["decided_at"] = _now()
            evt["decided_by"] = by
            self._save_events(events)
            return {"event_id": event_id, "action": "allow", "path": rel,
                    "trusted": True, "replay": replay,
                    "message": "已将 %s 加入信任区，本次修改已放行" % rel}
        if action == "block":
            evt["status"] = "blocked"
            evt["decided_at"] = _now()
            evt["decided_by"] = by
            self._save_events(events)
            return {"event_id": event_id, "action": "block", "path": rel,
                    "message": "已拒绝该修改，文件保持原样（备份已保留）"}
        # restore
        restored = False
        if evt.get("backup"):
            bfull = os.path.join(self.dir, evt["backup"])
            full = self._full(rel)
            if os.path.exists(bfull):
                os.makedirs(os.path.dirname(full), exist_ok=True)
                if os.path.isdir(bfull):
                    if os.path.isdir(full):
                        shutil.rmtree(full)
                    shutil.copytree(bfull, full, dirs_exist_ok=True)
                else:
                    shutil.copy2(bfull, full)
                restored = True
        evt["status"] = "restored"
        evt["decided_at"] = _now()
        evt["decided_by"] = by
        self._save_events(events)
        return {"event_id": event_id, "action": "restore", "path": rel,
                "restored": restored,
                "message": "已从备份恢复原文件（%s）" % (rel if restored else "备份不存在")}

    def events(self, limit=20):
        events = self._load_events()
        return events[-int(limit):][::-1]


# ---------------- 命令行 ----------------
def _cmd(args):
    g = DataGuard(args.workspace)
    if args.cmd == "status":
        return g.status()
    if args.cmd == "enable":
        return g.enable(args.mode or DEFAULT_MODE)
    if args.cmd == "disable":
        return g.disable()
    if args.cmd == "trust":
        return g.trust(args.path, args.reason or "", args.by or "user")
    if args.cmd == "untrust":
        return g.untrust(args.path)
    if args.cmd == "trusted":
        return {"trusted": g.list_trusted()}
    if args.cmd == "events":
        return {"events": g.events(args.limit or 20)}
    if args.cmd == "attempt-write":
        return g.attempt_write(args.path, args.content or "", args.source or "未知程序")
    if args.cmd == "attempt-delete":
        return g.attempt_delete(args.path, args.source or "未知程序")
    if args.cmd == "attempt-rename":
        return g.attempt_rename(args.path, args.new_path, args.source or "未知程序")
    if args.cmd == "decide":
        return g.decide(args.event_id, args.decision, args.by or "user")
    raise ValueError("未知命令: %s" % args.cmd)


def main(argv=None):
    p = argparse.ArgumentParser(prog="erbai-guard",
                                description="二伯杀毒 数据修改拦截（直接拦截 + 可选信任）")
    p.add_argument("--workspace", default=None, help="受保护目录（默认当前目录）")
    sub = p.add_subparsers(dest="cmd", required=True)
    sub.add_parser("status", help="查看保护状态与信任区")
    sub.add_parser("disable", help="关闭数据修改拦截")
    p_enable = sub.add_parser("enable", help="开启数据修改拦截")
    p_enable.add_argument("--mode", default="block", choices=_ALLOWED_MODES)
    p_trust = sub.add_parser("trust", help="信任某路径（放行后续修改）")
    p_trust.add_argument("path")
    p_trust.add_argument("--reason", default="")
    p_trust.add_argument("--by", default="user")
    p_untrust = sub.add_parser("untrust", help="取消信任某路径")
    p_untrust.add_argument("path")
    sub.add_parser("trusted", help="列出信任区")
    p_events = sub.add_parser("events", help="查看拦截事件")
    p_events.add_argument("--limit", type=int, default=20)
    p_w = sub.add_parser("attempt-write", help="模拟程序尝试写入/覆盖")
    p_w.add_argument("path")
    p_w.add_argument("content", nargs="?", default="")
    p_w.add_argument("--source", default="未知程序")
    p_d = sub.add_parser("attempt-delete", help="模拟程序尝试删除")
    p_d.add_argument("path")
    p_d.add_argument("--source", default="未知程序")
    p_r = sub.add_parser("attempt-rename", help="模拟程序尝试重命名/移动")
    p_r.add_argument("path")
    p_r.add_argument("new_path")
    p_r.add_argument("--source", default="未知程序")
    p_dec = sub.add_parser("decide", help="处理被拦截的事件")
    p_dec.add_argument("event_id")
    p_dec.add_argument("decision", choices=_ALLOWED_DECISIONS)
    p_dec.add_argument("--by", default="user")

    args = p.parse_args(argv)
    try:
        result = _cmd(args)
        print(json.dumps(result, ensure_ascii=False, indent=2))
    except Exception as e:
        print("错误: %s" % e, file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
