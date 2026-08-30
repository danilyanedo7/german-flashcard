const UINT32_MAX_PLUS_ONE = 4294967296;

export const HISTORY_STORAGE_KEY = "german-typing-game.learning-history.v1";

function defaultStorage() {
  try {
    return typeof localStorage !== "undefined" ? localStorage : null;
  } catch {
    return null;
  }
}

export function createCryptoRandom(cryptoApi = (typeof crypto !== "undefined" ? crypto : null)) {
  if (!cryptoApi || typeof cryptoApi.getRandomValues !== "function") {
    throw new Error("A cryptographically secure random source is required.");
  }
  return () => {
    const values = new Uint32Array(1);
    cryptoApi.getRandomValues(values);
    return values[0] / UINT32_MAX_PLUS_ONE;
  };
}

export function normalizeAnswer(value) {
  if (typeof value !== "string") return "";
  return value
    .normalize("NFKC")
    .toLowerCase()
    .trim()
    .replace(/\s+/gu, " ")
    .replace(/[.!?,;:。！？]+$/gu, "")
    .trim();
}

function isNonEmptyString(value) {
  return typeof value === "string" && value.trim().length > 0;
}

export function validateDataset(rawDataset) {
  const errors = [];
  const entries = [];
  const seenIds = new Set();
  const seenGerman = new Set();

  if (!Array.isArray(rawDataset)) {
    return { entries, errors: ["A1 dataset must be a JSON array."] };
  }

  rawDataset.forEach((raw, index) => {
    const location = `A1 entry ${index + 1}`;
    if (!raw || typeof raw !== "object" || Array.isArray(raw)) {
      errors.push(`${location}: expected an object; skipped.`);
      return;
    }
    const missing = ["id", "german", "english"].filter((field) => !isNonEmptyString(raw[field]));
    if (missing.length) {
      errors.push(`${location}: missing or empty ${missing.join(", ")}; skipped.`);
      return;
    }
    if (seenIds.has(raw.id)) {
      errors.push(`${location}: duplicate id ${raw.id}; skipped.`);
      return;
    }
    if (seenGerman.has(raw.german)) {
      errors.push(`${location} (${raw.id}): duplicate German text “${raw.german}”; retained for review.`);
    }

    let acceptedAnswers;
    if (raw.accepted_answers === undefined) {
      acceptedAnswers = [raw.english];
    } else if (!Array.isArray(raw.accepted_answers)) {
      errors.push(`${location} (${raw.id}): accepted_answers must be an array; skipped.`);
      return;
    } else if (
      raw.accepted_answers.length === 0 ||
      raw.accepted_answers.some((answer) => !isNonEmptyString(answer))
    ) {
      errors.push(`${location} (${raw.id}): accepted_answers contains an empty or non-string value; skipped.`);
      return;
    } else {
      acceptedAnswers = raw.accepted_answers.slice();
    }

    const normalizedAnswers = new Set(acceptedAnswers.map(normalizeAnswer));
    if (normalizedAnswers.size !== acceptedAnswers.length) {
      errors.push(`${location} (${raw.id}): accepted_answers contains duplicate answers; skipped.`);
      return;
    }
    if (!normalizedAnswers.has(normalizeAnswer(raw.english))) {
      errors.push(`${location} (${raw.id}): primary English answer is not in accepted_answers; skipped.`);
      return;
    }

    seenIds.add(raw.id);
    seenGerman.add(raw.german);
    entries.push({ ...raw, accepted_answers: acceptedAnswers });
  });

  return { entries, errors };
}

export function filterAntonymEntries(entries) {
  if (!Array.isArray(entries)) return [];
  return entries.filter(
    (entry) =>
      entry &&
      ((typeof entry.antonym === "string" && entry.antonym.trim().length > 0) ||
        (Array.isArray(entry.accepted_antonyms) && entry.accepted_antonyms.length > 0))
  );
}

export function answerMatches(entry, answer) {
  if (!entry || typeof answer !== "string" || !normalizeAnswer(answer)) return false;
  const accepted = Array.isArray(entry.accepted_answers) ? entry.accepted_answers : [entry.english];
  const normalized = normalizeAnswer(answer);
  return accepted.some((candidate) => normalizeAnswer(candidate) === normalized);
}

export function antonymMatches(entry, answer) {
  if (!entry || typeof answer !== "string" || !normalizeAnswer(answer)) return false;
  let accepted = [];
  if (Array.isArray(entry.accepted_antonyms) && entry.accepted_antonyms.length > 0) {
    accepted = entry.accepted_antonyms;
  } else if (typeof entry.antonym === "string" && entry.antonym.trim().length > 0) {
    accepted = [entry.antonym];
  }
  if (!accepted.length) return false;
  const normalized = normalizeAnswer(answer);
  return accepted.some((candidate) => normalizeAnswer(candidate) === normalized);
}

function freshHistoryRecord() {
  return {
    timesShown: 0,
    correctAnswers: 0,
    incorrectAnswers: 0,
    consecutiveCorrectAnswers: 0,
    mostRecentResult: null,
    lastStudiedTimestamp: null,
  };
}

export function loadLearningHistory(storage = defaultStorage()) {
  if (!storage) return {};
  try {
    const raw = storage.getItem(HISTORY_STORAGE_KEY);
    if (!raw) return {};
    const parsed = JSON.parse(raw);
    if (!parsed || typeof parsed !== "object" || Array.isArray(parsed)) return {};
    return parsed;
  } catch (error) {
    console.warn("Could not restore learning history; starting with an empty history.", error);
    return {};
  }
}

export function saveLearningHistory(history, storage = defaultStorage()) {
  if (!storage) return;
  try {
    storage.setItem(HISTORY_STORAGE_KEY, JSON.stringify(history));
  } catch (error) {
    console.warn("Could not save learning history.", error);
  }
}

export function resetLearningHistory(storage = defaultStorage()) {
  if (!storage) return;
  try {
    storage.removeItem(HISTORY_STORAGE_KEY);
  } catch (error) {
    console.warn("Could not reset learning history.", error);
  }
}

function historyFor(history, entryId) {
  if (!history[entryId] || typeof history[entryId] !== "object") {
    history[entryId] = freshHistoryRecord();
  }
  const record = history[entryId];
  record.timesShown = Number.isFinite(record.timesShown) ? record.timesShown : 0;
  record.correctAnswers = Number.isFinite(record.correctAnswers) ? record.correctAnswers : 0;
  record.incorrectAnswers = Number.isFinite(record.incorrectAnswers) ? record.incorrectAnswers : 0;
  record.consecutiveCorrectAnswers = Number.isFinite(record.consecutiveCorrectAnswers)
    ? record.consecutiveCorrectAnswers
    : 0;
  return record;
}

export function recordShown(history, entry, timestamp = Date.now()) {
  const record = historyFor(history, entry.id);
  record.timesShown += 1;
  record.lastStudiedTimestamp = timestamp;
  return record;
}

export function recordAnswer(history, entry, isCorrect, timestamp = Date.now()) {
  const record = historyFor(history, entry.id);
  record.lastStudiedTimestamp = timestamp;
  record.mostRecentResult = isCorrect ? "correct" : "incorrect";
  if (isCorrect) {
    record.correctAnswers += 1;
    record.consecutiveCorrectAnswers += 1;
  } else {
    record.incorrectAnswers += 1;
    record.consecutiveCorrectAnswers = 0;
  }
  return record;
}

export function reviewWeight(record) {
  if (!record) return 1;
  if (record.mostRecentResult === "incorrect") return 6;
  if (record.consecutiveCorrectAnswers === 1) return 3;
  if (record.consecutiveCorrectAnswers === 2) return 2;
  return 1;
}

function safeRandom(randomFn) {
  const value = Number(randomFn());
  if (!Number.isFinite(value)) return 0;
  return Math.max(0, Math.min(0.9999999999, value));
}

function pickIndex(length, randomFn) {
  if (length <= 1) return 0;
  return Math.min(length - 1, Math.floor(safeRandom(randomFn) * length));
}

export function weightedPick(entries, history, randomFn) {
  if (!entries.length) return null;
  const weights = entries.map((entry) => reviewWeight(history[entry.id]));
  const total = weights.reduce((sum, weight) => sum + weight, 0);
  let cursor = safeRandom(randomFn) * total;
  for (let index = 0; index < entries.length; index += 1) {
    cursor -= weights[index];
    if (cursor < 0) return entries[index];
  }
  return entries[entries.length - 1];
}

export function createSession(
  entries,
  {
    mode = "finite",
    totalQuestions = 20,
    level = "A1",
    history = {},
    questionType = "translate",
  } = {}
) {
  const sessionEntries =
    questionType === "antonym"
      ? filterAntonymEntries(entries)
      : entries.slice();

  return {
    entries: sessionEntries,
    mode,
    totalQuestions: mode === "endless" ? null : totalQuestions,
    level,
    questionType: questionType === "antonym" ? "antonym" : "translate",
    questionNumber: 0,
    answered: 0,
    correctCount: 0,
    incorrectCount: 0,
    streak: 0,
    longestStreak: 0,
    shownIds: new Set(),
    mistakes: new Set(),
    answerRecords: [],
    currentEntry: null,
    currentChecked: false,
    retryPending: false,
    history,
  };
}

export function selectNextEntry(session, randomFn = createCryptoRandom(), history = session?.history || {}) {
  if (!session || !session.entries.length) return null;
  if (session.totalQuestions !== null && session.questionNumber >= session.totalQuestions) return null;

  const newEntries = session.entries.filter((entry) => !session.shownIds.has(entry.id));
  const reviewEntries = session.entries.filter((entry) => session.shownIds.has(entry.id));
  let pool;
  if (!newEntries.length) {
    pool = reviewEntries;
  } else if (!reviewEntries.length) {
    pool = newEntries;
  } else {
    pool = safeRandom(randomFn) < 0.6 ? newEntries : reviewEntries;
  }

  const entry = pool === newEntries
    ? pool[pickIndex(pool.length, randomFn)]
    : weightedPick(pool, history, randomFn);
  session.shownIds.add(entry.id);
  session.currentEntry = entry;
  session.currentChecked = false;
  session.retryPending = false;
  session.questionNumber += 1;
  return entry;
}

export function submitAnswer(session, answer, timestamp = Date.now()) {
  if (!session || !session.currentEntry) return { status: "no_card" };
  if (session.currentChecked) return { status: "already_checked" };
  if (!normalizeAnswer(answer)) return { status: "empty" };

  const isAntonymMode = session.questionType === "antonym";
  const isCorrect = isAntonymMode
    ? antonymMatches(session.currentEntry, answer)
    : answerMatches(session.currentEntry, answer);

  session.currentChecked = true;
  session.retryPending = isAntonymMode && !isCorrect;
  session.answered += 1;
  if (isCorrect) {
    session.correctCount += 1;
    session.streak += 1;
    session.longestStreak = Math.max(session.longestStreak, session.streak);
  } else {
    session.incorrectCount += 1;
    session.streak = 0;
    session.mistakes.add(session.currentEntry.id);
  }
  recordAnswer(session.history, session.currentEntry, isCorrect, timestamp);
  session.answerRecords.push({
    entryId: session.currentEntry.id,
    answer: answer.trim(),
    isCorrect,
    questionType: session.questionType,
  });
  return {
    status: isCorrect ? "correct" : "incorrect",
    isCorrect,
    entry: session.currentEntry,
    questionType: session.questionType,
  };
}

export function submitRetry(session, answer) {
  if (!session || !session.currentEntry) return { status: "no_card" };
  if (!session.currentChecked || !session.retryPending) return { status: "not_pending" };
  if (!normalizeAnswer(answer)) return { status: "empty" };

  const isAntonymMode = session.questionType === "antonym";
  const isCorrect = isAntonymMode
    ? antonymMatches(session.currentEntry, answer)
    : answerMatches(session.currentEntry, answer);

  if (isCorrect) {
    session.retryPending = false;
  }
  return {
    status: isCorrect ? "retry_correct" : "retry_incorrect",
    isCorrect,
    entry: session.currentEntry,
    questionType: session.questionType,
  };
}

export function mostFrequentlyMissed(session) {
  if (!session) return [];
  const missed = new Map();
  session.answerRecords.forEach((record) => {
    if (!record.isCorrect) missed.set(record.entryId, (missed.get(record.entryId) || 0) + 1);
  });
  return session.entries
    .filter((entry) => missed.has(entry.id))
    .map((entry) => ({ entry, misses: missed.get(entry.id) }))
    .sort((a, b) => b.misses - a.misses || a.entry.german.localeCompare(b.entry.german));
}

export function sessionAccuracy(session) {
  if (!session || !session.answered) return 0;
  return Math.round((session.correctCount / session.answered) * 100);
}
