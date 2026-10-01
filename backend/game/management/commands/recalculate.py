"""Recalculate stored StationRun scores and FinalStationResult TP/FP counts.

Replays each user's station history (in the order it was originally run) through
the current station simulators, threading the resulting dataset from one station
into the next, and compares the recalculated values against what is stored in the
database. Differences are presented for confirmation before anything is written.
"""

import math

from django.contrib.auth.models import User
from django.core.management.base import BaseCommand
from django.db import transaction

from game.models import StationRun
from game.services import STATION_SIMULATORS


class Command(BaseCommand):
    help = (
        "Re-run every user's recorded station history through the current station "
        "simulators, show any score/TP/FP differences, and optionally overwrite "
        "the database with the recalculated values."
    )

    def add_arguments(self, parser):
        parser.add_argument(
            "--yes",
            action="store_true",
            help="Apply changes without an interactive confirmation prompt.",
        )
        parser.add_argument(
            "--skip-repeated-runs",
            action="store_true",
            help=(
                "Do not apply changes to the dataset from repeated runs of the same "
                "station by the same user, assuming repeats were parameter "
                "adjustments on the same dataset."
            ),
        )

    def handle(self, *args, **options):
        score_changes, final_changes, unchanged_runs, unchanged_finals, errors, skipped, failures = (
            self._recalculate_all(skip_repeated_runs=options["skip_repeated_runs"])
        )

        if skipped:
            self.stdout.write(
                f"Skipped {skipped} repeated station run(s) (only the last run of "
                "each station per user is applied)."
            )

        for error in errors:
            self.stderr.write(self.style.WARNING(error))

        if failures:
            self.stdout.write(
                self.style.WARNING(
                    f"\n{len(failures)} station run(s) reported success=False "
                    "during recalculation:"
                )
            )
            for failure in failures:
                self.stdout.write(f"  - {failure}")

        self.stdout.write(
            f"\nRecalculated {len(score_changes) + unchanged_runs} station run(s): "
            f"{len(score_changes)} changed, {unchanged_runs} unchanged."
        )
        self.stdout.write(
            f"Recalculated {len(final_changes) + unchanged_finals} final result(s): "
            f"{len(final_changes)} changed, {unchanged_finals} unchanged."
        )

        if not score_changes and not final_changes:
            self.stdout.write(self.style.SUCCESS("No differences found. Nothing to update."))
            return

        self._print_summary(score_changes, final_changes)

        if errors:
            self.stdout.write(
                self.style.ERROR(
                    f"\nNot committing changes: {len(errors)} error(s) occurred during "
                    "recalculation. Resolve these and re-run the command."
                )
            )
            return

        if not options["yes"]:
            answer = input(
                f"\nOverwrite {len(score_changes)} score(s) and "
                f"{len(final_changes)} final result(s) in the database? [y/N] "
            )
            if answer.strip().lower() not in ("y", "yes"):
                self.stdout.write("Aborted. No changes were made.")
                return

        self._apply_changes(score_changes, final_changes)
        self.stdout.write(
            self.style.SUCCESS(
                f"Updated {len(score_changes)} station run score(s) and "
                f"{len(final_changes)} final result(s)."
            )
        )

    def _recalculate_all(self, skip_repeated_runs=False):
        score_changes = []
        final_changes = []
        unchanged_runs = 0
        unchanged_finals = 0
        errors = []
        failures = []
        skipped = 0

        for user in User.objects.order_by("id"):
            runs = list(
                StationRun.objects.filter(player=user)
                .select_related("final_result")
                .order_by("created_at", "id")
            )

            dataset = None
            for run_index, run in enumerate(runs):
                next_station_id = (
                    runs[run_index + 1].station_id if run_index + 1 < len(runs) else None
                )
                simulator = STATION_SIMULATORS.get(run.station_id)
                if simulator is None:
                    errors.append(
                        f"Skipping StationRun {run.pk} ({user.username}): "
                        f"unknown station '{run.station_id}'."
                    )
                    continue

                try:
                    result = simulator(dataset, run.params or {})
                except Exception as exc:
                    errors.append(
                        f"Skipping StationRun {run.pk} ({user.username}, "
                        f"station '{run.station_id}'): recalculation raised {exc!r}."
                    )
                    continue

                if result.get("success") is False:
                    failures.append(
                        f"StationRun {run.pk} ({user.username}, "
                        f"station '{run.station_id}'): simulator reported "
                        f"success=False with feedback: {result.get('feedback')!r}"
                    )

                # With --skip-repeated-runs, only the LAST run of a consecutive
                # same-station group applies its dataset; earlier repeats are
                # recalculated on the pre-group dataset but their output is
                # discarded.
                if not skip_repeated_runs or next_station_id != run.station_id:
                    dataset = result.get("dataset", dataset)
                else:
                    skipped += 1

                old_score = float(run.score)
                new_score = float(result.get("score", 0) or 0)
                if math.isclose(old_score, new_score, rel_tol=1e-9, abs_tol=1e-9):
                    unchanged_runs += 1
                else:
                    score_changes.append(
                        {
                            "user": user,
                            "run": run,
                            "old_score": old_score,
                            "new_score": new_score,
                        }
                    )

                final_result = getattr(run, "final_result", None)
                if final_result is not None:
                    new_tp = int(result.get("true_positives", 0) or 0)
                    new_fp = int(result.get("false_positives", 0) or 0)
                    if (
                        new_tp == final_result.true_positives
                        and new_fp == final_result.false_positives
                    ):
                        unchanged_finals += 1
                    else:
                        final_changes.append(
                            {
                                "user": user,
                                "run": run,
                                "final_result": final_result,
                                "old_tp": final_result.true_positives,
                                "old_fp": final_result.false_positives,
                                "new_tp": new_tp,
                                "new_fp": new_fp,
                            }
                        )

        return (
            score_changes,
            final_changes,
            unchanged_runs,
            unchanged_finals,
            errors,
            skipped,
            failures,
        )

    def _print_summary(self, score_changes, final_changes):
        if score_changes:
            self.stdout.write("\nStation run score changes:")
            header = (
                f"{'User':<20}{'Run ID':<10}{'Station':<28}"
                f"{'Old score':<14}{'New score':<14}"
            )
            self.stdout.write(header)
            self.stdout.write("-" * len(header))
            for change in score_changes:
                self.stdout.write(
                    f"{change['user'].username:<20}"
                    f"{change['run'].pk:<10}"
                    f"{change['run'].station_id:<28}"
                    f"{change['old_score']:<14.4f}"
                    f"{change['new_score']:<14.4f}"
                )

        if final_changes:
            self.stdout.write("\nFinal result changes:")
            header = (
                f"{'User':<20}{'Run ID':<10}{'Old TP':<10}{'New TP':<10}"
                f"{'Old FP':<10}{'New FP':<10}"
            )
            self.stdout.write(header)
            self.stdout.write("-" * len(header))
            for change in final_changes:
                self.stdout.write(
                    f"{change['user'].username:<20}"
                    f"{change['run'].pk:<10}"
                    f"{change['old_tp']:<10}"
                    f"{change['new_tp']:<10}"
                    f"{change['old_fp']:<10}"
                    f"{change['new_fp']:<10}"
                )

    @transaction.atomic
    def _apply_changes(self, score_changes, final_changes):
        for change in score_changes:
            change["run"].score = change["new_score"]
            change["run"].save(update_fields=["score"])

        for change in final_changes:
            change["final_result"].true_positives = change["new_tp"]
            change["final_result"].false_positives = change["new_fp"]
            change["final_result"].save(update_fields=["true_positives", "false_positives"])
