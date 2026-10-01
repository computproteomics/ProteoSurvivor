import os
import html
from pathlib import Path
import tempfile

os.environ.setdefault("MPLCONFIGDIR", str(Path(tempfile.gettempdir()) / "matplotlib"))

import matplotlib

matplotlib.use("Agg")

import matplotlib.pyplot as plt
import pandas as pd
import seaborn as sns
from django.conf import settings
from django.core.management.base import BaseCommand, CommandError
from django.db import connection
from django.db.models import Q

from game.models import FinalStationResult, StationRun

STATION_ORDER = [
    "sample_prep",
    "mass_spec",
    "spectral_search",
    "data_review",
    "transform",
    "filtering",
    "normalize",
    "imputer",
    "statistical_analysis",
    "multiple_testing_corrector",
    "the_cutter",
    "final_report",
]


class Command(BaseCommand):
    help = "Generate game-run statistics and paper-ready visualization drafts."

    def add_arguments(self, parser):
        parser.add_argument(
            "--output-dir",
            default=Path(settings.BASE_DIR) / "reports" / "game_report",
            type=Path,
            help="Directory for summary.md, CSVs, and PNG figures.",
        )


    def handle(self, *args, **options):
        out = options["output_dir"]
        out.mkdir(parents=True, exist_ok=True)
        self._clean_old_outputs(out)
        sns.set_theme(style="whitegrid")

        runs = self._runs()
        if not runs.exists():
            raise CommandError("No non-seed station runs found.")

        run_df = pd.DataFrame(
            runs.values(
                "id",
                "player_id",
                "player__username",
                "station_id",
                "score",
                "created_at",
                "params",
            )
        ).rename(columns={"player__username": "username"})
        run_df["created_at"] = pd.to_datetime(run_df["created_at"])
        run_df["score"] = pd.to_numeric(run_df["score"])
        participant_key = self._participant_key(run_df)
        run_df = run_df.merge(
            participant_key[["player_id", "participant"]], on="player_id", how="left"
        )
        run_df.to_csv(out / "station_runs.csv", index=False)

        final_df = self._finals(run_df["id"].tolist())
        if not final_df.empty:
            final_df = final_df.merge(
                participant_key[["player_id", "participant"]],
                on="player_id",
                how="left",
            )
        if not final_df.empty:
            final_df.to_csv(out / "final_results.csv", index=False)

        station_order = self._station_order(run_df)
        station_summary = self._station_summary(run_df, station_order)
        station_summary.to_csv(out / "station_summary.csv", index=False)

        player_summary = self._player_summary(run_df, final_df)
        player_summary.to_csv(out / "player_summary.csv", index=False)
        participant_key = self._participant_counts(participant_key, run_df, final_df)
        participant_key.to_csv(out / "participant_key.csv", index=False)

        final_players = set(final_df["player_id"]) if not final_df.empty else set()
        param_df = self._parameter_summary(run_df, final_players)
        parameter_figures = []
        if not param_df.empty:
            param_df.to_csv(out / "parameter_summary.csv", index=False)

        self._plot_station_reach(station_summary, out)
        self._plot_station_runs_to_final(run_df, final_df, station_order, out)
        self._plot_retries(station_summary, out)
        self._plot_final_scores(final_df, out)
        self._plot_tp_fp(final_df, out)
        self._plot_effort_vs_score(run_df, final_df, out)
        parameter_figures = self._plot_parameter_bars(param_df, out)
        self._write_summary(
            out,
            run_df,
            station_summary,
            player_summary,
            final_df,
            parameter_figures,
            participant_key,
        )

        self.stdout.write(self.style.SUCCESS(f"Report written to {out}"))
        self.stdout.write(f"Database: {connection.settings_dict.get('NAME')}")

    def _runs(self):
        keep = Q(player__username__isnull=False) & ~Q(
            player__username__startswith="seed_player_"
        )
        return StationRun.objects.filter(keep).order_by("created_at", "id")

    def _clean_old_outputs(self, out):
        for pattern in (
            "parameter_choice_heatmap.png",
            "parameter_choice_heatmap.svg",
            "parameter_choices_*.png",
            "parameter_choices_*.svg",
        ):
            for path in out.glob(pattern):
                path.unlink()

    def _finals(self, run_ids):
        rows = FinalStationResult.objects.filter(station_run_id__in=run_ids).values(
            "station_run_id",
            "station_run__player_id",
            "station_run__player__username",
            "station_run__score",
            "station_run__created_at",
            "true_positives",
            "false_positives",
        )
        final_df = pd.DataFrame(rows)
        if final_df.empty:
            return final_df
        final_df = final_df.rename(
            columns={
                "station_run__player_id": "player_id",
                "station_run__player__username": "username",
                "station_run__score": "score",
                "station_run__created_at": "created_at",
            }
        )
        final_df["created_at"] = pd.to_datetime(final_df["created_at"])
        final_df["score"] = pd.to_numeric(final_df["score"])
        total = final_df["true_positives"] + final_df["false_positives"]
        final_df["fdr_like"] = final_df["false_positives"].div(total).fillna(0)
        return final_df.sort_values(["created_at", "station_run_id"])

    def _participant_key(self, run_df):
        users = (
            run_df.sort_values(["created_at", "player_id"])
            .drop_duplicates("player_id")[["player_id", "username"]]
            .reset_index(drop=True)
        )
        users["participant"] = [f"P{i:02d}" for i in range(1, len(users) + 1)]
        return users[["participant", "player_id", "username"]]

    def _participant_counts(self, participant_key, run_df, final_df):
        runs = run_df.groupby("player_id").size().rename("runs")
        df = participant_key.merge(runs, on="player_id", how="left")
        if final_df.empty:
            df["final_submissions"] = 0
        else:
            finals = final_df.groupby("player_id").size().rename("final_submissions")
            df = df.merge(finals, on="player_id", how="left")
        return df.fillna({"runs": 0, "final_submissions": 0})

    def _station_order(self, run_df):
        configured = list(getattr(settings, "STATIONS_CONFIG", {}).keys())
        seen = run_df["station_id"].drop_duplicates().tolist()
        ordered = [s for s in STATION_ORDER if s in seen]
        ordered += [s for s in configured if s in seen and s not in ordered]
        ordered += [s for s in seen if s not in ordered]
        return ordered

    def _station_summary(self, run_df, station_order):
        rows = []
        total_players = run_df["player_id"].nunique()
        for station in station_order:
            df = run_df[run_df["station_id"] == station]
            players = df["player_id"].nunique()
            attempts = df.groupby("player_id").size()
            rows.append(
                {
                    "station_id": station,
                    "runs": len(df),
                    "players": players,
                    "players_percent": 100 * players / total_players,
                    "mean_attempts_per_player": attempts.mean(),
                    "retried_players": int((attempts > 1).sum()),
                    "max_attempts": int(attempts.max()),
                    "mean_score": df["score"].mean(),
                    "median_score": df["score"].median(),
                    "min_score": df["score"].min(),
                    "max_score": df["score"].max(),
                }
            )
        return pd.DataFrame(rows)

    def _player_summary(self, run_df, final_df):
        final_latest = pd.DataFrame()
        if not final_df.empty:
            final_latest = final_df.sort_values(["player_id", "created_at"]).groupby(
                "player_id", as_index=False
            ).tail(1)

        rows = []
        final_by_player = {
            row.player_id: row
            for row in final_latest.itertuples()
        }
        for player_id, df in run_df.groupby("player_id"):
            start = df["created_at"].min()
            end = df["created_at"].max()
            final = final_by_player.get(player_id)
            rows.append(
                {
                    "participant": df["participant"].iloc[0],
                    "player_id": player_id,
                    "username": df["username"].iloc[0],
                    "runs": len(df),
                    "stations": df["station_id"].nunique(),
                    "duration_minutes": (end - start).total_seconds() / 60,
                    "submitted_final": final is not None,
                    "final_score": getattr(final, "score", pd.NA),
                    "true_positives": getattr(final, "true_positives", pd.NA),
                    "false_positives": getattr(final, "false_positives", pd.NA),
                    "fdr_like": getattr(final, "fdr_like", pd.NA),
                }
            )
        return pd.DataFrame(rows)

    def _parameter_summary(self, run_df, final_players):
        rows = []
        for run in run_df.itertuples():
            for key, value in (run.params or {}).items():
                rows.append(
                    {
                        "player_id": run.player_id,
                        "station_id": run.station_id,
                        "parameter": key,
                        "value": str(value),
                        "from_final_report_account": run.player_id in final_players,
                    }
                )
        if not rows:
            return pd.DataFrame()
        df = pd.DataFrame(rows)
        summary = df.groupby(["station_id", "parameter", "value"]).agg(
            runs=("player_id", "size"),
            runs_from_final_report_accounts=("from_final_report_account", "sum"),
        )
        return (
            summary.reset_index()
            .sort_values(
                ["station_id", "parameter", "runs"],
                ascending=[True, True, False],
            )
        )

    def _plot_station_reach(self, station_summary, out):
        fig, ax = plt.subplots(figsize=(8, 5))
        sns.barplot(
            data=station_summary,
            y="station_id",
            x="players_percent",
            color="#4C78A8",
            ax=ax,
        )
        ax.set(xlabel="Accounts reaching station (%)", ylabel="")
        ax.bar_label(ax.containers[0], fmt="%.0f%%", padding=3)
        fig.tight_layout()
        self._save_figure(fig, out, "station_reach.png")
        plt.close(fig)

    def _plot_station_runs_to_final(self, run_df, final_df, station_order, out):
        if final_df.empty:
            return
        final_players = set(final_df["player_id"])
        df = run_df[run_df["player_id"].isin(final_players)]
        counts = (
            df.groupby("station_id")
            .size()
            .reindex(station_order)
            .dropna()
            .reset_index(name="runs")
        )
        fig, ax = plt.subplots(figsize=(8, 5))
        sns.barplot(data=counts, y="station_id", x="runs", color="#B279A2", ax=ax)
        ax.set(xlabel="Runs from accounts with at least one final report", ylabel="")
        ax.bar_label(ax.containers[0], fmt="%.0f", padding=3)
        fig.tight_layout()
        self._save_figure(fig, out, "station_runs_to_final.png")
        plt.close(fig)

    def _plot_retries(self, station_summary, out):
        fig, ax = plt.subplots(figsize=(8, 5))
        sns.barplot(
            data=station_summary,
            y="station_id",
            x="mean_attempts_per_player",
            color="#F58518",
            ax=ax,
        )
        ax.set(xlabel="Mean attempts per account that reached station", ylabel="")
        fig.tight_layout()
        self._save_figure(fig, out, "retry_burden.png")
        plt.close(fig)

    def _plot_final_scores(self, final_df, out):
        if final_df.empty:
            return
        fig, ax = plt.subplots(figsize=(4.8, 4.8))
        sns.violinplot(y=final_df["score"], color="#72B7B2", inner=None, ax=ax)
        sns.stripplot(y=final_df["score"], color="#222222", size=4, jitter=0.15, ax=ax)
        ax.set(xlabel="", ylabel="Final-report score per submission", ylim=(0, 1.02))
        fig.tight_layout()
        self._save_figure(fig, out, "final_score_distribution.png")
        plt.close(fig)

    def _plot_tp_fp(self, final_df, out):
        if final_df.empty:
            return
        fig, ax = plt.subplots(figsize=(5.6, 4.8))
        sns.scatterplot(
            data=final_df,
            x="true_positives",
            y="false_positives",
            hue="score",
            palette="viridis",
            s=70,
            edgecolor="black",
            linewidth=0.3,
            ax=ax,
        )
        ax.set(xlabel="True positives", ylabel="False positives")
        for row in final_df.itertuples():
            ax.annotate(
                row.participant,
                (row.true_positives, row.false_positives),
                xytext=(4, 4),
                textcoords="offset points",
                fontsize=6,
            )
        fig.tight_layout()
        self._save_figure(fig, out, "true_vs_false_positives.png")
        plt.close(fig)

    def _plot_effort_vs_score(self, run_df, final_df, out):
        if final_df.empty:
            return
        efforts = []
        for final in final_df.itertuples():
            runs = run_df[
                (run_df["player_id"] == final.player_id)
                & (run_df["created_at"] <= final.created_at)
            ]
            efforts.append(
                {
                    "score": final.score,
                    "runs": len(runs),
                    "stations": runs["station_id"].nunique(),
                    "participant": final.participant,
                }
            )
        df = pd.DataFrame(efforts)
        if df.empty:
            return
        fig, ax = plt.subplots(figsize=(5.6, 4.8))
        sns.scatterplot(
            data=df,
            x="runs",
            y="score",
            size="stations",
            sizes=(35, 180),
            color="#54A24B",
            alpha=0.75,
            ax=ax,
            legend="brief",
        )
        for row in df.itertuples():
            ax.annotate(
                row.participant,
                (row.runs, row.score),
                xytext=(4, 4),
                textcoords="offset points",
                fontsize=6,
            )
        ax.set(
            xlabel="Station runs before final submission",
            ylabel="Final-report score",
            ylim=(-0.03, 1.08),
        )
        legend = ax.get_legend()
        if legend:
            legend.set_title("Stations reached")
        fig.tight_layout()
        self._save_figure(fig, out, "effort_vs_final_score.png")
        plt.close(fig)

    def _plot_parameter_bars(self, param_df, out):
        if param_df.empty:
            return []
        figures = []
        for station, df in param_df.groupby("station_id", sort=False):
            rows = df.copy()
            rows["choice"] = rows["parameter"] + "=" + rows["value"]
            rows = rows.sort_values(["parameter", "runs"], ascending=[True, False])
            rows = rows.rename(
                columns={
                    "runs": "All non-seed runs",
                    "runs_from_final_report_accounts": "Runs from final-report accounts",
                }
            )
            plot_rows = rows.melt(
                id_vars=["choice"],
                value_vars=["All non-seed runs", "Runs from final-report accounts"],
                var_name="run_group",
                value_name="count",
            )
            filename = f"parameter_choices_{station}.png"
            fig, ax = plt.subplots(figsize=(8, max(3.5, 0.32 * len(rows))))
            sns.barplot(
                data=plot_rows,
                y="choice",
                x="count",
                hue="run_group",
                palette=["#4C78A8", "#F58518"],
                ax=ax,
            )
            ax.set(xlabel="Runs", ylabel="")
            ax.legend(title="")
            fig.tight_layout()
            self._save_figure(fig, out, filename)
            plt.close(fig)
            figures.append(filename)
        return figures

    def _save_figure(self, fig, out, filename):
        fig.savefig(out / filename, dpi=300)
        fig.savefig((out / filename).with_suffix(".svg"))

    def _write_summary(
        self,
        out,
        run_df,
        station_summary,
        player_summary,
        final_df,
        parameter_figures,
        participant_key,
    ):
        players = run_df["player_id"].nunique()
        finals = player_summary[player_summary["submitted_final"]]
        final_scores = final_df["score"].astype(float) if not final_df.empty else pd.Series(dtype=float)
        lines = [
            "# ProteoSurvivor Game Report",
            "",
            f"- Database: `{connection.settings_dict.get('NAME')}`",
            f"- Non-seed accounts with runs: {players}",
            f"- Station runs, including duplicates: {len(run_df)}",
            f"- Final-report submissions, including duplicates: {len(final_df)}",
            f"- First run: {run_df['created_at'].min()}",
            f"- Last run: {run_df['created_at'].max()}",
            f"- Accounts with final report: {len(finals)} / {players} ({100 * len(finals) / players:.1f}%)",
        ]
        if not final_df.empty:
            fdr = final_df["fdr_like"].astype(float)
            lines += [
                f"- Median final-submission score: {final_scores.median():.3f}",
                f"- Mean final-submission score: {final_scores.mean():.3f}",
                f"- Final submissions with score >= 0.90: {(final_scores >= 0.90).sum()} / {len(final_scores)} ({100 * (final_scores >= 0.90).mean():.1f}%)",
                f"- Median true positives: {final_df['true_positives'].median():.1f}",
                f"- Median false positives: {final_df['false_positives'].median():.1f}",
                f"- Median FP / (TP + FP): {fdr.median():.3f}",
            ]
        figure_descriptions = [
            (
                "station_reach.png",
                "Station reach",
                "Percentage of non-seed accounts that reached each station at least once. Repeat submissions do not change this figure.",
            ),
            (
                "station_runs_to_final.png",
                "Station runs to final report",
                "Duplicate-inclusive station-run counts for accounts that submitted at least one final report.",
            ),
            (
                "retry_burden.png",
                "Retry burden",
                "Mean attempts per account among accounts that reached the station. A value of 1 means no retries; larger values mark repeated station runs.",
            ),
            (
                "final_score_distribution.png",
                "Final score distribution",
                "Score distribution for all final-report submissions, including repeated final reports.",
            ),
            (
                "true_vs_false_positives.png",
                "True versus false positives",
                "True positives versus false positives for each final-report submission. Point labels are generic participant IDs.",
            ),
            (
                "effort_vs_final_score.png",
                "Effort versus final score",
                "Final-report score versus station runs completed before that final submission. Circle size shows how many distinct stations had been reached; point labels are generic participant IDs.",
            ),
        ]
        figure_descriptions += [
            (
                figure,
                f"Parameter choices: {figure.removeprefix('parameter_choices_').removesuffix('.png')}",
                "Parameter-choice counts within one station. Blue bars count all non-seed runs; orange bars count the subset from accounts that submitted at least one final report.",
            )
            for figure in parameter_figures
        ]
        lines += [
            "",
            "## Generated Figures",
            "",
            "Each figure is written in both PNG and SVG format.",
            "",
        ]
        for filename, title, description in figure_descriptions:
            lines += [f"### {title}", "", f"![{title}]({filename})", "", description, ""]
        lines += [
            "",
            "## Station Summary",
            "",
            self._markdown_table(station_summary),
            "",
            "## Participant Key",
            "",
            self._markdown_table(participant_key),
            "",
            "Seeds are excluded by username prefix `seed_player_`. Duplicate/retry runs are retained.",
        ]
        (out / "summary.md").write_text("\n".join(lines), encoding="utf-8")
        self._write_html_summary(
            out,
            players,
            len(run_df),
            len(final_df),
            run_df,
            station_summary,
            finals,
            final_df,
            participant_key,
            figure_descriptions,
        )

    def _write_html_summary(
        self,
        out,
        players,
        run_count,
        final_count,
        run_df,
        station_summary,
        finals,
        final_df,
        participant_key,
        figure_descriptions,
    ):
        items = [
            f"Database: {connection.settings_dict.get('NAME')}",
            f"Non-seed accounts with runs: {players}",
            f"Station runs, including duplicates: {run_count}",
            f"Final-report submissions, including duplicates: {final_count}",
            f"First run: {run_df['created_at'].min()}",
            f"Last run: {run_df['created_at'].max()}",
            f"Accounts with final report: {len(finals)} / {players} ({100 * len(finals) / players:.1f}%)",
        ]
        if not final_df.empty:
            scores = final_df["score"].astype(float)
            fdr = final_df["fdr_like"].astype(float)
            items += [
                f"Median final-submission score: {scores.median():.3f}",
                f"Mean final-submission score: {scores.mean():.3f}",
                f"Final submissions with score >= 0.90: {(scores >= 0.90).sum()} / {len(scores)} ({100 * (scores >= 0.90).mean():.1f}%)",
                f"Median true positives: {final_df['true_positives'].median():.1f}",
                f"Median false positives: {final_df['false_positives'].median():.1f}",
                f"Median FP / (TP + FP): {fdr.median():.3f}",
            ]
        page = [
            "<!doctype html>",
            '<html lang="en"><head><meta charset="utf-8">',
            "<title>ProteoSurvivor Game Report</title>",
            "<style>body{font:16px system-ui,sans-serif;max-width:1100px;margin:2rem auto;padding:0 1rem;color:#222}img{max-width:100%;height:auto}figure{margin:1.5rem 0}table{border-collapse:collapse;width:100%;margin-bottom:2rem}th,td{border:1px solid #ccc;padding:.35rem;text-align:left}th{background:#eee}code{background:#f2f2f2;padding:.1rem .25rem}</style>",
            "</head><body><h1>ProteoSurvivor Game Report</h1>",
            "<ul>",
        ]
        page += [f"<li>{html.escape(item)}</li>" for item in items]
        page += [
            "</ul>",
            "<h2>Generated Figures</h2>",
            "<p>Each figure is written in both PNG and SVG format.</p>",
        ]
        for filename, title, description in figure_descriptions:
            page += [
                f"<figure><h3>{html.escape(title)}</h3><img src=\"{html.escape(filename)}\" alt=\"{html.escape(title)}\"><figcaption>{html.escape(description)}</figcaption></figure>"
            ]
        page += [
            "<h2>Station Summary</h2>",
            self._html_table(station_summary),
            "<h2>Participant Key</h2>",
            self._html_table(participant_key),
            "<p>Seeds are excluded by username prefix <code>seed_player_</code>. Duplicate/retry runs are retained.</p>",
            "</body></html>",
        ]
        (out / "summary.html").write_text("\n".join(page), encoding="utf-8")

    def _markdown_table(self, df):
        view = df.copy()
        for col in view.select_dtypes("number").columns:
            values = view[col].dropna()
            if not values.empty and (values % 1 == 0).all():
                view[col] = view[col].map(lambda value: f"{value:.0f}")
            else:
                view[col] = view[col].map(lambda value: f"{value:.2f}")
        rows = [list(view.columns), ["---"] * len(view.columns)]
        rows += view.astype(str).values.tolist()
        return "\n".join("| " + " | ".join(row) + " |" for row in rows)

    def _html_table(self, df):
        view = self._formatted_table(df)
        head = "".join(f"<th>{html.escape(str(col))}</th>" for col in view.columns)
        body = "".join(
            "<tr>" + "".join(f"<td>{html.escape(str(value))}</td>" for value in row) + "</tr>"
            for row in view.astype(str).values.tolist()
        )
        return f"<table><thead><tr>{head}</tr></thead><tbody>{body}</tbody></table>"

    def _formatted_table(self, df):
        view = df.copy()
        for col in view.select_dtypes("number").columns:
            values = view[col].dropna()
            if not values.empty and (values % 1 == 0).all():
                view[col] = view[col].map(lambda value: f"{value:.0f}")
            else:
                view[col] = view[col].map(lambda value: f"{value:.2f}")
        return view
