"""TranscriptRecorder 단위테스트 — 오디오·SDK 없이 캡처/직렬화/렌더만 검증.

실행: uv run python -m pytest skills/distillery/tests -q
  또는: uv run python skills/distillery/tests/test_transcript.py
"""
import json
import sys
import tempfile
import unittest
from pathlib import Path

_SCRIPTS = Path(__file__).resolve().parent.parent / "scripts"
sys.path.insert(0, str(_SCRIPTS))

from run_interview import TranscriptRecorder, run_text_only  # noqa: E402


class TestTranscriptRecorder(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.mkdtemp()
        clock = iter([f"2026-06-26T00:00:{i:02d}Z" for i in range(60)])
        self.rec = TranscriptRecorder(self.tmp, clock=lambda: next(clock))

    def _jsonl(self):
        return [json.loads(x) for x in
                (Path(self.tmp) / "transcript.jsonl").read_text(encoding="utf-8").splitlines()]

    def _notes(self):
        return (Path(self.tmp) / "interview-notes.md").read_text(encoding="utf-8")

    def test_agent_and_user_turns_written_to_jsonl(self):
        self.rec.record_agent("어떤 RA를 원하세요?")
        self.rec.record_user("분석이 빠른 사람이요")
        rows = self._jsonl()
        self.assertEqual(len(rows), 2)
        self.assertEqual(rows[0]["role"], "agent")
        self.assertEqual(rows[0]["text"], "어떤 RA를 원하세요?")
        self.assertEqual(rows[1]["role"], "user")
        self.assertIn("ts", rows[0])

    def test_jsonl_appends_each_turn(self):
        for i in range(4):
            self.rec.record_user(f"답변{i}")
        self.assertEqual(len(self._jsonl()), 4)

    def test_correction_event_shape(self):
        self.rec.record_correction("서른", "서론")
        row = self._jsonl()[0]
        self.assertEqual(row["role"], "correction")
        self.assertEqual(row["from"], "서른")
        self.assertEqual(row["to"], "서론")

    def test_notes_render_korean_speaker_labels(self):
        self.rec.record_agent("질문입니다")
        self.rec.record_user("답변입니다")
        notes = self._notes()
        self.assertIn("**면접관:** 질문입니다", notes)
        self.assertIn("**나(PM):** 답변입니다", notes)

    def test_notes_include_conversation_id_when_set(self):
        self.rec.record_agent("끝")
        self.rec.set_conversation_id("conv_abc123")
        self.assertIn("conv_abc123", self._notes())

    def test_summary_counts_only_spoken_turns(self):
        self.rec.record_agent("a")
        self.rec.record_user("b")
        self.rec.record_correction("x", "y")  # not counted as spoken turn
        self.assertEqual(self.rec.summary()["turns"], 2)

    def test_text_strip(self):
        self.rec.record_user("  공백 포함  ")
        self.assertEqual(self._jsonl()[0]["text"], "공백 포함")


class TestTextOnlyDryRun(unittest.TestCase):
    def test_dry_run_produces_transcript_files(self):
        tmp = tempfile.mkdtemp()
        rec = TranscriptRecorder(tmp)
        cid = run_text_only(rec)
        self.assertEqual(cid, "dryrun-local")
        self.assertTrue((Path(tmp) / "transcript.jsonl").exists())
        self.assertTrue((Path(tmp) / "interview-notes.md").exists())
        self.assertGreaterEqual(rec.summary()["turns"], 4)


if __name__ == "__main__":
    unittest.main(verbosity=2)
