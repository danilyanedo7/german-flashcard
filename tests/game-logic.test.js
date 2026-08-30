import test from "node:test";
import assert from "node:assert/strict";
import {
  HISTORY_STORAGE_KEY,
  answerMatches,
  createSession,
  loadLearningHistory,
  mostFrequentlyMissed,
  normalizeAnswer,
  recordAnswer,
  recordShown,
  resetLearningHistory,
  reviewWeight,
  saveLearningHistory,
  selectNextEntry,
  sessionAccuracy,
  submitAnswer,
  validateDataset,
} from "../js/game-logic.js";

const entry = (id, english = id) => ({
  id,
  german: `das ${id}`,
  english,
  accepted_answers: [english],
});

function sequence(values) {
  let index = 0;
  return () => values[Math.min(index++, values.length - 1)];
}

function memoryStorage() {
  const values = new Map();
  return {
    getItem: (key) => values.get(key) ?? null,
    setItem: (key, value) => values.set(key, String(value)),
    removeItem: (key) => values.delete(key),
  };
}

test("normalizes Unicode, case, whitespace, and harmless final punctuation", () => {
  assert.equal(normalizeAnswer("  APPLE.  "), "apple");
  assert.equal(normalizeAnswer("Straße!!!"), "straße");
  assert.equal(normalizeAnswer(" café  "), "café");
});

test("matches primary and explicit alternative answers without fuzzy matching", () => {
  const card = { ...entry("apple"), accepted_answers: ["apple", "pippin"] };
  assert.equal(answerMatches(card, "Apple."), true);
  assert.equal(answerMatches(card, "pippin"), true);
  assert.equal(answerMatches(card, "appl"), false);
  assert.equal(answerMatches(card, ""), false);
});

test("validates entries, defaults missing optional accepted answers, and skips malformed data", () => {
  const result = validateDataset([
    entry("one", "one"),
    { id: "two", german: "zwei", english: "two" },
    { id: "bad", german: "", english: "empty" },
    { id: "two", german: "another", english: "two", accepted_answers: ["two"] },
    { id: "invalid-alternatives", german: "x", english: "x", accepted_answers: "x" },
    { id: "missing-primary", german: "x", english: "x", accepted_answers: ["y"] },
  ]);
  assert.equal(result.entries.length, 2);
  assert.deepEqual(result.entries[1].accepted_answers, ["two"]);
  assert.equal(result.errors.length, 4);
});

test("empty submissions do not score and only the first checked answer counts", () => {
  const history = {};
  const session = createSession([entry("apple")], { mode: "endless", history });
  selectNextEntry(session, () => 0);
  assert.equal(submitAnswer(session, "").status, "empty");
  assert.equal(session.answered, 0);
  assert.equal(submitAnswer(session, "apple.").status, "correct");
  assert.equal(submitAnswer(session, "wrong").status, "already_checked");
  assert.equal(session.answered, 1);
  assert.equal(history.apple.correctAnswers, 1);
});

test("scoring, streaks, resets, per-word history, and accuracy update correctly", () => {
  const history = {};
  const cards = [entry("one", "one"), entry("two", "two")];
  const session = createSession(cards, { mode: "endless", history });
  selectNextEntry(session, () => 0);
  recordShown(history, session.currentEntry, 100);
  submitAnswer(session, "one", 200);
  assert.equal(session.streak, 1);
  selectNextEntry(session, () => 0);
  recordShown(history, session.currentEntry, 300);
  submitAnswer(session, "wrong", 400);
  assert.equal(session.streak, 0);
  assert.equal(session.longestStreak, 1);
  assert.equal(sessionAccuracy(session), 50);
  assert.equal(history.one.correctAnswers, 1);
  assert.equal(history.two.incorrectAnswers, 1);
  assert.equal(history.two.consecutiveCorrectAnswers, 0);
  assert.equal(history.two.lastStudiedTimestamp, 400);
  assert.equal(mostFrequentlyMissed(session)[0].entry.id, "two");
});

test("history persists and reset removes saved data", () => {
  const storage = memoryStorage();
  const history = {};
  recordShown(history, entry("apple"), 123);
  saveLearningHistory(history, storage);
  assert.deepEqual(loadLearningHistory(storage), history);
  assert.ok(storage.getItem(HISTORY_STORAGE_KEY));
  resetLearningHistory(storage);
  assert.deepEqual(loadLearningHistory(storage), {});
});

test("adaptive selection uses a 60/40 new/review route and permits immediate repetition", () => {
  const history = {};
  const cards = [entry("a"), entry("b"), entry("c")];
  const session = createSession(cards, { mode: "endless", history });
  const first = selectNextEntry(session, sequence([0, 0]), history);
  assert.equal(first.id, "a");
  const newRoute = selectNextEntry(session, sequence([0.59, 0]), history);
  assert.equal(newRoute.id, "b");
  const reviewRoute = selectNextEntry(session, sequence([0.6, 0]), history);
  assert.equal(reviewRoute.id, "a");

  const one = createSession([entry("only")], { mode: "endless", history: {} });
  assert.equal(selectNextEntry(one, () => 0).id, "only");
  assert.equal(selectNextEntry(one, () => 0).id, "only");
});

test("incorrect words have greater review weight than mastered words", () => {
  const history = {};
  recordAnswer(history, entry("missed"), false, 1);
  history.mastered = { consecutiveCorrectAnswers: 4, mostRecentResult: "correct" };
  assert.equal(reviewWeight(history.missed), 6);
  assert.equal(reviewWeight(history.mastered), 1);
  const cards = [entry("missed"), entry("mastered")];
  const session = createSession(cards, { mode: "endless", history });
  session.shownIds.add("missed");
  session.shownIds.add("mastered");
  assert.equal(selectNextEntry(session, () => 0.5, history).id, "missed");
  assert.equal(selectNextEntry(session, () => 0.99, history).id, "mastered");
});

test("finite sessions stop at their question count and one-word/empty datasets are safe", () => {
  const session = createSession([entry("one")], { totalQuestions: 1, history: {} });
  assert.equal(selectNextEntry(session, () => 0).id, "one");
  submitAnswer(session, "one");
  assert.equal(selectNextEntry(session, () => 0), null);
  assert.equal(createSession([], { mode: "endless" }).entries.length, 0);
  assert.equal(selectNextEntry(createSession([], { mode: "endless" }), () => 0), null);
});
