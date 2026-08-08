"""
Cybernetic Evolver — 工作空间初始化加载器

在 SOUL.md 或其他 agent 配置中引用：
    import sys, os
    WORKSPACE = "<USER_WORKSPACE>"
    EVOLVER_DIR = os.path.join(WORKSPACE, "evolver")
    sys.path.insert(0, EVOLVER_DIR)
    from init_evolver import load_evolver_for_agent
    evolver = load_evolver_for_agent(WORKSPACE)
"""

import sys
import os
import json
from pathlib import Path

SKILL_DIR = os.path.join(os.path.dirname(__file__), "..",
    "skills", "@ywewanhuang", "cybernetic-evolver", "CODE")
if SKILL_DIR not in sys.path:
    sys.path.insert(0, os.path.abspath(SKILL_DIR))


def load_evolver_for_agent(workspace_path, config_override=None):
    """
    从工作空间加载/初始化进化器

    Args:
        workspace_path: 工作空间目录路径
        config_override: 可选配置覆盖参数
    """
    from evolver import CyberneticEvolver

    evolver_dir = Path(workspace_path) / "evolver"
    config_file = evolver_dir / "config.json"
    state_file = evolver_dir / "state.json"

    # 加载配置
    config = {}
    if config_file.exists():
        with open(config_file, "r", encoding="utf-8") as f:
            config = json.load(f)
    if config_override:
        config.update(config_override)

    evolver = CyberneticEvolver(
        target=config.get("target", 1.0),
        state_dim=config.get("state_dim", 5),
        action_dim=config.get("action_dim", 4),
        epsilon_start=config.get("epsilon_start", 1.0),
        epsilon_end=config.get("epsilon_end", 0.01),
        epsilon_decay=config.get("epsilon_decay", 0.995),
        learning_rate=config.get("learning_rate", 0.02),
        adaptation_threshold=config.get("adaptation_threshold", 1.0),
        adaptation_interval=config.get("adaptation_interval", 1),
        mutation_trigger=config.get("mutation_trigger", 10),
        lyapunov_lambda=config.get("lyapunov_lambda", 0.1),
        buffer_capacity=config.get("buffer_capacity", 10000),
    )

    # 尝试加载已保存的状态
    if state_file.exists():
        try:
            evolver.load(str(state_file))
        except Exception as e:
            print(f"Warning: Failed to load evolver state: {e}")

    # 注入默认触发条件
    trigger_config = config.get("trigger", {})
    min_history = trigger_config.get("min_history", 3)
    consecutive_decline = trigger_config.get("consecutive_decline", 3)
    suggested_iterations = trigger_config.get("suggested_iterations", 20)

    def default_trigger(perf_history):
        if len(perf_history) < min_history:
            return {"should_optimize": False, "reason": "数据不足",
                    "suggested_iterations": 0}
        recent = perf_history[-consecutive_decline:]
        if len(recent) >= consecutive_decline and \
           all(recent[i] > recent[i+1] for i in range(len(recent)-1)):
            return {"should_optimize": True,
                    "reason": f"性能连续{consecutive_decline}次下降",
                    "suggested_iterations": suggested_iterations}
        return {"should_optimize": False, "reason": "性能稳定",
                "suggested_iterations": 0}

    evolver.set_trigger_condition(default_trigger)

    return evolver


def save_evolver_state(evolver, workspace_path):
    """
    保存进化器状态到工作空间

    Args:
        evolver: CyberneticEvolver 实例
        workspace_path: 工作空间目录路径
    """
    state_file = Path(workspace_path) / "evolver" / "state.json"
    state_file.parent.mkdir(parents=True, exist_ok=True)
    evolver.save(str(state_file))


def record_performance(workspace_path, score):
    """
    记录性能分数到日志

    Args:
        workspace_path: 工作空间目录路径
        score: 性能分数 (0-1)
    """
    log_file = Path(workspace_path) / "evolver" / "performance_log.json"
    if log_file.exists():
        with open(log_file, "r", encoding="utf-8") as f:
            data = json.load(f)
    else:
        data = {"history": []}
    data["history"].append(score)
    with open(log_file, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2, ensure_ascii=False)
    return data["history"]