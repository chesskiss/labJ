"""DB consistency checks for journal sessions/revisions/entries/events."""

from __future__ import annotations

import os
from dataclasses import dataclass, field
from datetime import datetime

from sqlalchemy import select
from sqlalchemy.orm import Session

from db.connection import create_db_engine
from db.models import Base, Event, JournalEntry, JournalRevision, JournalSession

DEFAULT_SQLITE_URL = "sqlite+pysqlite:///data/journal.sqlite"


@dataclass(frozen=True)
class SanityIssue:
    code: str
    message: str
    severity: str  # error | warning


@dataclass(frozen=True)
class SanityStats:
    sessions: int
    revisions: int
    entries: int
    events: int


@dataclass
class SanityReport:
    errors: list[SanityIssue] = field(default_factory=list)
    warnings: list[SanityIssue] = field(default_factory=list)
    stats: SanityStats | None = None

    @property
    def ok(self) -> bool:
        return not self.errors


def resolve_database_url() -> str:
    return os.getenv("DATABASE_URL", DEFAULT_SQLITE_URL)


def _sort_key(created_at: datetime, obj_id) -> tuple[datetime, str]:
    return created_at, str(obj_id)


def run_sanity_check(database_url: str | None = None) -> SanityReport:
    report = SanityReport()
    engine = create_db_engine(database_url or resolve_database_url())
    Base.metadata.create_all(engine, checkfirst=True)

    with Session(engine) as session:
        sessions = session.execute(select(JournalSession)).scalars().all()
        revisions = session.execute(select(JournalRevision)).scalars().all()
        entries = session.execute(select(JournalEntry)).scalars().all()
        events = (
            session.execute(
                select(Event).where(Event.event_type == "journal_entry_created")
            )
            .scalars()
            .all()
        )

        report.stats = SanityStats(
            sessions=len(sessions),
            revisions=len(revisions),
            entries=len(entries),
            events=len(events),
        )

        revisions_by_id = {row.id: row for row in revisions}
        revisions_by_session: dict = {}
        for revision in revisions:
            revisions_by_session.setdefault(revision.session_id, []).append(revision)

        for session_row in sessions:
            session_revisions = revisions_by_session.get(session_row.id, [])
            if session_row.head_revision_id is None:
                report.warnings.append(
                    SanityIssue(
                        code="session_head_missing",
                        severity="warning",
                        message=f"Session {session_row.id} has null head_revision_id.",
                    )
                )
                continue

            head = revisions_by_id.get(session_row.head_revision_id)
            if head is None:
                report.errors.append(
                    SanityIssue(
                        code="session_head_not_found",
                        severity="error",
                        message=(
                            f"Session {session_row.id} head_revision_id "
                            f"{session_row.head_revision_id} does not exist in journal_revisions."
                        ),
                    )
                )
                continue

            if head.session_id != session_row.id:
                report.errors.append(
                    SanityIssue(
                        code="session_head_session_mismatch",
                        severity="error",
                        message=(
                            f"Session {session_row.id} head_revision_id {head.id} belongs to "
                            f"session {head.session_id}."
                        ),
                    )
                )
                continue

            if session_revisions:
                expected_head = max(
                    session_revisions, key=lambda row: _sort_key(row.created_at, row.id)
                )
                if expected_head.id != head.id:
                    report.errors.append(
                        SanityIssue(
                            code="session_head_not_latest",
                            severity="error",
                            message=(
                                f"Session {session_row.id} head_revision_id {head.id} is not latest. "
                                f"Expected {expected_head.id}."
                            ),
                        )
                    )

        entry_by_id = {entry.id: entry for entry in entries}
        for revision in revisions:
            if revision.id not in entry_by_id:
                report.warnings.append(
                    SanityIssue(
                        code="revision_without_entry_row",
                        severity="warning",
                        message=(
                            f"Revision {revision.id} has no matching journal_entries row "
                            "(transitional data may be expected)."
                        ),
                    )
                )

        events_by_aggregate = {event.aggregate_id: event for event in events}
        for entry in entries:
            if entry.session_id is None:
                continue

            event = events_by_aggregate.get(entry.id)
            if event is None:
                report.warnings.append(
                    SanityIssue(
                        code="entry_missing_event",
                        severity="warning",
                        message=(
                            f"Entry {entry.id} (session {entry.session_id}) has no "
                            "journal_entry_created event."
                        ),
                    )
                )
                continue

            metadata = event.metadata_json or {}
            if "source" not in metadata:
                report.warnings.append(
                    SanityIssue(
                        code="event_missing_source_metadata",
                        severity="warning",
                        message=f"Event for entry {entry.id} is missing metadata.source.",
                    )
                )
            if "title" not in metadata:
                report.warnings.append(
                    SanityIssue(
                        code="event_missing_title_metadata",
                        severity="warning",
                        message=f"Event for entry {entry.id} is missing metadata.title.",
                    )
                )

    return report


def _print_report(report: SanityReport, database_url: str) -> None:
    print(f"[DB-SANITY] database_url={database_url}")
    if report.stats is not None:
        print(
            "[DB-SANITY] stats "
            f"sessions={report.stats.sessions} "
            f"revisions={report.stats.revisions} "
            f"entries={report.stats.entries} "
            f"events={report.stats.events}"
        )

    if report.ok:
        print("[DB-SANITY] status=PASS")
    else:
        print("[DB-SANITY] status=FAIL")

    for issue in report.errors:
        print(f"[DB-SANITY][ERROR] {issue.code}: {issue.message}")
    for issue in report.warnings:
        print(f"[DB-SANITY][WARN] {issue.code}: {issue.message}")


if __name__ == "__main__":
    db_url = resolve_database_url()
    sanity_report = run_sanity_check(db_url)
    _print_report(sanity_report, db_url)
    raise SystemExit(0 if sanity_report.ok else 1)
