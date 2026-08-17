from __future__ import annotations

import argparse
from pathlib import Path
from typing import Any

from config import config_hash, load_config, load_validated_config, validate_config
from agents.rl_training import train_tabular_agent
from engine.simulation_engine import compare_agents, run_config
from experiment_tracking.logger import ExperimentLogger
from research.reporting import write_comparison_report, write_result_artifacts
from research.data_loading import load_price_series
from research.monte_carlo import run_monte_carlo, summarize_monte_carlo, write_monte_carlo_artifacts
from research.optimization import run_grid_search, write_optimization_artifacts
from research.scenarios import run_scenario_matrix, write_scenario_artifacts
from research.stress import run_stress_replay, write_stress_artifacts
from research.synthetic_data import write_synthetic_l1_csv
from research.walk_forward import run_walk_forward_prices, write_walk_forward_artifacts
from order_flow.calibration import calibrate_order_flow_csv, write_order_flow_calibration


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Run market-making simulation experiments.")
    sub = parser.add_subparsers(dest="command", required=True)

    run = sub.add_parser("run", help="Run one YAML experiment.")
    run.add_argument("--config", default="configs/baseline_naive.yaml")
    run.add_argument("--run-name", default=None)
    run.add_argument("--artifacts-dir", default="runs/artifacts")

    compare = sub.add_parser("compare", help="Compare all configured agents on one shared path.")
    compare.add_argument("--base-config", default="configs/baseline_naive.yaml")
    compare.add_argument("--artifacts-dir", default="runs/comparison")

    sweep = sub.add_parser("sweep", help="Sweep risk aversion for Avellaneda-Stoikov.")
    sweep.add_argument("--base-config", default="configs/avellaneda_stoikov.yaml")
    sweep.add_argument("--values", default="0.02,0.05,0.08,0.12,0.2")
    sweep.add_argument("--artifacts-dir", default="runs/sweep")

    batch = sub.add_parser("batch", help="Run every config and write a research report.")
    batch.add_argument("--config-dir", default="configs")
    batch.add_argument("--base-config", default="configs/baseline_naive.yaml")
    batch.add_argument("--artifacts-dir", default="runs/batch")

    demo = sub.add_parser("demo-data", help="Generate synthetic L1 data for ingest/calibration demos.")
    demo.add_argument("--output", default="data/raw/synthetic_l1.csv")
    demo.add_argument("--steps", type=int, default=3600)
    demo.add_argument("--seed", type=int, default=42)

    train_rl = sub.add_parser("train-rl", help="Train the tabular RL quoting policy.")
    train_rl.add_argument("--config", default="configs/rl_agent.yaml")
    train_rl.add_argument("--episodes", type=int, default=25)
    train_rl.add_argument("--output", default="runs/policies/tabular_q_policy.json")
    train_rl.add_argument("--artifacts-dir", default="runs/rl_training")
    train_rl.add_argument("--epsilon-start", type=float, default=0.25)
    train_rl.add_argument("--epsilon-end", type=float, default=0.02)

    walk = sub.add_parser("walk-forward", help="Run calibrated walk-forward validation on a price file.")
    walk.add_argument("--config", default="configs/baseline_naive.yaml")
    walk.add_argument("--data", required=True)
    walk.add_argument("--price-col", default="price")
    walk.add_argument("--train-size", type=int, default=500)
    walk.add_argument("--test-size", type=int, default=200)
    walk.add_argument("--artifacts-dir", default="runs/walk_forward")

    mc = sub.add_parser("monte-carlo", help="Run seed-sweep Monte Carlo for one config.")
    mc.add_argument("--config", default="configs/baseline_naive.yaml")
    mc.add_argument("--runs", type=int, default=20)
    mc.add_argument("--seed-start", type=int, default=None)
    mc.add_argument("--artifacts-dir", default="runs/monte_carlo")

    stress = sub.add_parser("stress", help="Replay strategy through worst price windows.")
    stress.add_argument("--config", default="configs/baseline_naive.yaml")
    stress.add_argument("--data", required=True)
    stress.add_argument("--price-col", default="price")
    stress.add_argument("--window-size", type=int, default=300)
    stress.add_argument("--top-n", type=int, default=3)
    stress.add_argument("--artifacts-dir", default="runs/stress")

    flow_cal = sub.add_parser("calibrate-flow", help="Estimate order-flow parameters from trades.")
    flow_cal.add_argument("--data", required=True)
    flow_cal.add_argument("--output", default="data/processed/order_flow_calibration.csv")
    flow_cal.add_argument("--timestamp-col", default="timestamp")
    flow_cal.add_argument("--side-col", default="side")
    flow_cal.add_argument("--quantity-col", default="quantity")
    flow_cal.add_argument("--price-col", default="price")
    flow_cal.add_argument("--mid-col", default="mid")

    scenarios_cmd = sub.add_parser("scenario-matrix", help="Run named market-regime scenarios.")
    scenarios_cmd.add_argument("--config", default="configs/baseline_naive.yaml")
    scenarios_cmd.add_argument("--scenarios", default="configs/scenario_matrix.yaml")
    scenarios_cmd.add_argument("--artifacts-dir", default="runs/scenario_matrix")

    optimize = sub.add_parser("optimize", help="Run a YAML-defined parameter grid search.")
    optimize.add_argument("--spec", default="configs/optimization_avellaneda.yaml")
    optimize.add_argument("--artifacts-dir", default="runs/optimization")

    args = parser.parse_args(argv)
    logger = ExperimentLogger()
    if args.command == "run":
        config = load_validated_config(args.config)
        result = run_config(config)
        name = args.run_name or Path(args.config).stem
        logger.log(name, config, _numeric_summary(result.summary), run_hash=config_hash(config))
        write_result_artifacts(result, Path(args.artifacts_dir) / name)
        _print_summary(result.summary)
        return 0
    if args.command == "compare":
        base = load_validated_config(args.base_config)
        agent_configs = [
            cfg.get("agent", {})
            for cfg in _experiment_configs(Path("configs"))
        ]
        results = compare_agents(base, agent_configs)
        for result in results:
            run_cfg = base | {"agent": result.agent_id}
            logger.log(
                f"compare_{result.agent_id}",
                run_cfg,
                _numeric_summary(result.summary),
                run_hash=config_hash(run_cfg),
            )
            write_result_artifacts(result, Path(args.artifacts_dir) / result.agent_id)
            _print_summary(result.summary)
        report_path = write_comparison_report(results, args.artifacts_dir)
        print(f"report={report_path}")
        return 0
    if args.command == "sweep":
        base = load_validated_config(args.base_config)
        results = []
        for raw in args.values.split(","):
            gamma = float(raw)
            cfg = {**base, "agent": {**base.get("agent", {}), "gamma": gamma}}
            validate_config(cfg, source=f"{args.base_config}:gamma={gamma}")
            result = run_config(cfg)
            results.append(result)
            logger.log(
                f"gamma_{gamma:g}",
                cfg,
                _numeric_summary(result.summary),
                run_hash=config_hash(cfg),
            )
            write_result_artifacts(result, Path(args.artifacts_dir) / f"gamma_{gamma:g}")
            _print_summary(result.summary)
        report_path = write_comparison_report(results, args.artifacts_dir, title="Gamma Sweep")
        print(f"report={report_path}")
        return 0
    if args.command == "batch":
        base = load_validated_config(args.base_config)
        results = []
        for path, cfg in _experiment_config_paths(Path(args.config_dir)):
            result = run_config(cfg)
            results.append(result)
            logger.log(
                path.stem,
                cfg,
                _numeric_summary(result.summary),
                run_hash=config_hash(cfg),
            )
            write_result_artifacts(result, Path(args.artifacts_dir) / path.stem)
            _print_summary(result.summary)
        agent_configs = [cfg.get("agent", {}) for _, cfg in _experiment_config_paths(Path(args.config_dir))]
        paired = compare_agents(base, agent_configs)
        report_path = write_comparison_report(paired, args.artifacts_dir)
        print(f"report={report_path}")
        return 0
    if args.command == "demo-data":
        path = write_synthetic_l1_csv(args.output, steps=args.steps, seed=args.seed)
        print(f"wrote={path}")
        return 0
    if args.command == "train-rl":
        config = load_validated_config(args.config)
        agent, results = train_tabular_agent(
            config,
            episodes=args.episodes,
            output_path=args.output,
            epsilon_start=args.epsilon_start,
            epsilon_end=args.epsilon_end,
        )
        for idx, result in enumerate(results):
            run_cfg = config | {"seed": int(config.get("seed", 1)) + idx}
            logger.log(
                f"rl_train_episode_{idx + 1}",
                run_cfg,
                _numeric_summary(result.summary),
                run_hash=config_hash(run_cfg),
            )
        report_path = write_comparison_report(results, args.artifacts_dir, title="RL Training Episodes")
        print(f"policy={Path(args.output)} states={len(agent.q_values)} report={report_path}")
        return 0
    if args.command == "walk-forward":
        config = load_validated_config(args.config)
        prices = load_price_series(args.data, price_col=args.price_col)
        results = run_walk_forward_prices(
            config,
            prices,
            train_size=args.train_size,
            test_size=args.test_size,
        )
        report_path = write_walk_forward_artifacts(results, args.artifacts_dir)
        for idx, result in enumerate(results, start=1):
            run_cfg = config | {"walk_forward_split": idx}
            logger.log(
                f"walk_forward_{idx}_{result.simulation.agent_id}",
                run_cfg,
                _numeric_summary(result.simulation.summary),
                run_hash=config_hash(run_cfg),
            )
            _print_summary(result.simulation.summary)
        print(f"splits={len(results)} report={report_path}")
        return 0
    if args.command == "monte-carlo":
        config = load_validated_config(args.config)
        results = run_monte_carlo(config, runs=args.runs, seed_start=args.seed_start)
        report_path = write_monte_carlo_artifacts(results, args.artifacts_dir)
        aggregate = summarize_monte_carlo(results)
        logger.log(
            f"monte_carlo_{Path(args.config).stem}",
            config,
            aggregate,
            run_hash=config_hash(config),
        )
        print(
            "runs={runs:.0f} pnl_mean={pnl:.2f} sharpe_mean={sharpe:.2f} report={report}".format(
                runs=aggregate["runs"],
                pnl=aggregate["total_pnl_mean"],
                sharpe=aggregate["sharpe_mean"],
                report=report_path,
            )
        )
        return 0
    if args.command == "stress":
        config = load_validated_config(args.config)
        prices = load_price_series(args.data, price_col=args.price_col)
        results = run_stress_replay(
            config,
            prices,
            window_size=args.window_size,
            top_n=args.top_n,
        )
        report_path = write_stress_artifacts(results, args.artifacts_dir)
        for idx, result in enumerate(results, start=1):
            run_cfg = config | {"stress_window": idx}
            logger.log(
                f"stress_{idx}_{result.simulation.agent_id}",
                run_cfg,
                _numeric_summary(result.simulation.summary),
                run_hash=config_hash(run_cfg),
            )
            _print_summary(result.simulation.summary)
        print(f"windows={len(results)} report={report_path}")
        return 0
    if args.command == "calibrate-flow":
        calibration = calibrate_order_flow_csv(
            args.data,
            timestamp_col=args.timestamp_col,
            side_col=args.side_col,
            quantity_col=args.quantity_col,
            price_col=args.price_col,
            mid_col=args.mid_col,
        )
        write_order_flow_calibration(args.output, calibration)
        print(
            "observations={obs} intensity={intensity:.4f} imbalance={imbalance:.4f} output={output}".format(
                obs=calibration.observations,
                intensity=calibration.total_intensity,
                imbalance=calibration.buy_sell_imbalance,
                output=args.output,
            )
        )
        return 0
    if args.command == "scenario-matrix":
        config = load_validated_config(args.config)
        scenario_doc = load_config(args.scenarios)
        results = run_scenario_matrix(config, scenario_doc.get("scenarios", []))
        report_path = write_scenario_artifacts(results, args.artifacts_dir)
        for result in results:
            run_cfg = config | {"scenario": result.name}
            logger.log(
                f"scenario_{result.name}_{result.simulation.agent_id}",
                run_cfg,
                _numeric_summary(result.simulation.summary),
                run_hash=config_hash(run_cfg),
            )
            _print_summary(result.simulation.summary)
        print(f"scenarios={len(results)} report={report_path}")
        return 0
    if args.command == "optimize":
        spec = load_config(args.spec)
        config = load_validated_config(spec.get("base_config", "configs/baseline_naive.yaml"))
        results = run_grid_search(
            config,
            spec.get("grid", {}),
            objective=str(spec.get("objective", "sharpe")),
            maximize=bool(spec.get("maximize", True)),
        )
        report_path = write_optimization_artifacts(results, args.artifacts_dir)
        for result in results:
            run_cfg = config | {"optimization_rank": result.rank, "parameters": result.parameters}
            logger.log(
                f"opt_rank_{result.rank}_{result.simulation.agent_id}",
                run_cfg,
                _numeric_summary(result.simulation.summary),
                run_hash=config_hash(run_cfg),
            )
        best = results[0] if results else None
        if best is not None:
            print(
                "best_rank={rank} objective={objective} value={value:.4f} report={report}".format(
                    rank=best.rank,
                    objective=best.objective,
                    value=best.objective_value,
                    report=report_path,
                )
            )
        else:
            print(f"best_rank=none report={report_path}")
        return 0
    return 1


def _numeric_summary(summary: dict[str, Any]) -> dict[str, float]:
    return {key: float(value) for key, value in summary.items() if isinstance(value, (int, float))}


def _print_summary(summary: dict[str, Any]) -> None:
    agent = summary.get("agent", "unknown")
    pnl = float(summary.get("total_pnl", 0.0))
    sharpe = float(summary.get("sharpe", 0.0))
    drawdown = float(summary.get("max_drawdown", 0.0))
    fills = int(float(summary.get("fill_count", 0.0)))
    print(f"{agent}: pnl={pnl:.2f} sharpe={sharpe:.2f} drawdown={drawdown:.2f} fills={fills}")


def _experiment_configs(config_dir: Path) -> list[dict[str, Any]]:
    return [cfg for _, cfg in _experiment_config_paths(config_dir)]


def _experiment_config_paths(config_dir: Path) -> list[tuple[Path, dict[str, Any]]]:
    configs: list[tuple[Path, dict[str, Any]]] = []
    for path in sorted(config_dir.glob("*.yaml")):
        cfg = load_config(path)
        if "agent" not in cfg:
            continue
        validate_config(cfg, source=str(path))
        configs.append((path, cfg))
    return configs


if __name__ == "__main__":
    raise SystemExit(main())
