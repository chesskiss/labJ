import { cleanup, fireEvent, render, screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import {
  appendJournalEntry,
  fetchLatestSessionEntry,
  fetchSessionHistory,
  fetchSessionSummaries,
  type JournalEntryRecord,
  type JournalSessionSummary,
} from "../api/journalApi";
import { AppShell } from "./AppShell";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";

vi.mock("../api/journalApi", () => ({
  appendJournalEntry: vi.fn(),
  fetchLatestSessionEntry: vi.fn(),
  fetchSessionHistory: vi.fn(),
  fetchSessionSummaries: vi.fn(),
}));

const mockFetchSessionSummaries = vi.mocked(fetchSessionSummaries);
const mockFetchLatestSessionEntry = vi.mocked(fetchLatestSessionEntry);
const mockFetchSessionHistory = vi.mocked(fetchSessionHistory);
const mockAppendJournalEntry = vi.mocked(appendJournalEntry);

function makeRevision(
  entryId: string,
  content: string,
  createdAt: string,
  parentRevisionId: string | null = null
): JournalEntryRecord {
  return {
    entry_id: entryId,
    session_id: "session-1",
    parent_revision_id: parentRevisionId,
    title: "Session One",
    content,
    entry_type: "general",
    revision_kind: "manual_edit",
    created_by: "ui_manual",
    created_at: createdAt,
    metadata: {},
  };
}

function seedApiMocks(options?: { latestHeadId?: string }) {
  const latestHeadId = options?.latestHeadId ?? "rev-head-1";
  const summary: JournalSessionSummary = {
    session_id: "session-1",
    title: "Session One",
    head_revision_id: latestHeadId,
    latest_created_at: "2026-03-22T10:00:00.000Z",
    latest_entry_id: latestHeadId,
    latest_entry_type: "general",
    latest_created_by: "ui_manual",
    latest_revision_kind: "manual_edit",
  };
  const latest = makeRevision(
    latestHeadId,
    "<p>Head content</p>",
    "2026-03-22T10:00:00.000Z",
    "rev-old-1"
  );
  const older = makeRevision("rev-old-1", "<p>Older content</p>", "2026-03-22T09:00:00.000Z");

  mockFetchSessionSummaries.mockResolvedValue([summary]);
  mockFetchLatestSessionEntry.mockResolvedValue(latest);
  mockFetchSessionHistory.mockResolvedValue([latest, older]);
  mockAppendJournalEntry.mockResolvedValue({
    ...latest,
    entry_id: "rev-head-2",
    parent_revision_id: latestHeadId,
    content: "<p>Edited content</p>",
    created_at: "2026-03-22T10:05:00.000Z",
  });

  return { latest, older };
}

describe("AppShell revision flow", () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  afterEach(() => {
    cleanup();
    vi.useRealTimers();
  });

  it("shows historical-revision banner and allows loading latest", async () => {
    const { older } = seedApiMocks();
    const user = userEvent.setup();

    render(<AppShell />);

    await screen.findByDisplayValue("Session One");
    const loadButtons = await screen.findAllByRole("button", { name: "Load" });
    await user.click(loadButtons[1]);

    expect(
      await screen.findByText("You are editing an older revision, not the current head.")
    ).toBeInTheDocument();

    const loadLatestButtons = screen.getAllByRole("button", { name: "Load latest" });
    const enabledLoadLatest = loadLatestButtons.find((button) => !button.hasAttribute("disabled"));
    expect(enabledLoadLatest).toBeTruthy();
    await user.click(enabledLoadLatest!);

    await waitFor(() => {
      expect(
        screen.queryByText("You are editing an older revision, not the current head.")
      ).not.toBeInTheDocument();
    });

    expect(screen.getByText("Head")).toBeInTheDocument();
    expect(screen.queryByText("Viewing")).toBeInTheDocument();
    expect(older.entry_id).toBe("rev-old-1");
  });

  it("blocks autosave when session head moved and does not append", async () => {
    const { older } = seedApiMocks();
    mockFetchLatestSessionEntry
      .mockResolvedValueOnce(makeRevision("rev-head-1", "<p>Head content</p>", "2026-03-22T10:00:00.000Z"))
      .mockResolvedValueOnce(makeRevision("rev-head-2", "<p>Newer head</p>", "2026-03-22T10:06:00.000Z"));

    const user = userEvent.setup();
    render(<AppShell />);

    await screen.findByDisplayValue("Session One");
    const loadButtons = await screen.findAllByRole("button", { name: "Load" });
    await user.click(loadButtons[1]);

    const editor = screen.getByLabelText("Journal editor");
    (editor as HTMLElement).innerHTML = "<p>Edited from old revision</p>";
    fireEvent.input(editor);
    fireEvent.blur(editor);

    await waitFor(() => {
      expect(
        screen.getByText(
          "Save paused. A newer revision was created in this session. Reload latest before saving."
        )
      ).toBeInTheDocument();
    });

    expect(mockAppendJournalEntry).not.toHaveBeenCalled();
    expect(older.entry_id).toBe("rev-old-1");
  });

  it("appends with base_revision_id when editing loaded historical revision", async () => {
    const { older } = seedApiMocks();
    const user = userEvent.setup();
    render(<AppShell />);

    await screen.findByDisplayValue("Session One");
    const loadButtons = await screen.findAllByRole("button", { name: "Load" });
    await user.click(loadButtons[1]);

    const editor = screen.getByLabelText("Journal editor");
    (editor as HTMLElement).innerHTML = "<p>Edited and saved</p>";
    fireEvent.input(editor);
    fireEvent.blur(editor);

    await waitFor(() => {
      expect(mockAppendJournalEntry).toHaveBeenCalledTimes(1);
    });

    expect(mockAppendJournalEntry).toHaveBeenCalledWith(
      expect.objectContaining({
        session_id: "session-1",
        base_revision_id: older.entry_id,
        source: "ui_manual",
      }),
      expect.objectContaining({
        keepalive: undefined,
      })
    );
  });
});
