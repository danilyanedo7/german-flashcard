import {
  createCryptoRandom,
  createSession,
  loadLearningHistory,
  mostFrequentlyMissed,
  recordShown,
  resetLearningHistory,
  saveLearningHistory,
  selectNextEntry,
  sessionAccuracy,
  submitAnswer,
  validateDataset,
} from "./game-logic.js";

const ui = {
  home: document.querySelector("#home-view"),
  session: document.querySelector("#session-view"),
  game: document.querySelector("#game-view"),
  summary: document.querySelector("#summary-view"),
  levelGrid: document.querySelector("#level-grid"),
  dataError: document.querySelector("#data-error"),
  historyNote: document.querySelector("#history-note"),
  sessionForm: document.querySelector("#session-form"),
  selectedLevel: document.querySelector("#selected-level"),
  selectedLevelCount: document.querySelector("#selected-level-count"),
  gameLevel: document.querySelector("#game-level"),
  questionProgress: document.querySelector("#question-progress"),
  correctCount: document.querySelector("#correct-count"),
  streakCount: document.querySelector("#streak-count"),
  uniqueCount: document.querySelector("#unique-count"),
  word: document.querySelector("#german-word"),
  answerForm: document.querySelector("#answer-form"),
  answerInput: document.querySelector("#answer-input"),
  actionButton: document.querySelector("#answer-action"),
  feedback: document.querySelector("#feedback"),
  feedbackHeading: document.querySelector("#feedback-heading"),
  feedbackAnswer: document.querySelector("#feedback-answer"),
  answerDetails: document.querySelector("#answer-details"),
  detailType: document.querySelector("#detail-type"),
  detailGender: document.querySelector("#detail-gender"),
  detailPlural: document.querySelector("#detail-plural"),
  detailExample: document.querySelector("#detail-example"),
  endSession: document.querySelector("#end-session"),
  summaryTitle: document.querySelector("#summary-title"),
  summaryQuestions: document.querySelector("#summary-questions"),
  summaryCorrect: document.querySelector("#summary-correct"),
  summaryIncorrect: document.querySelector("#summary-incorrect"),
  summaryAccuracy: document.querySelector("#summary-accuracy"),
  summaryUnique: document.querySelector("#summary-unique"),
  summaryLongest: document.querySelector("#summary-longest"),
  missedList: document.querySelector("#missed-list"),
  missedEmpty: document.querySelector("#missed-empty"),
  reviewMistakes: document.querySelector("#review-mistakes"),
  resetHistory: document.querySelector("#reset-history"),
};

const state = {
  config: null,
  levelKey: "A1",
  entries: [],
  history: loadLearningHistory(),
  session: null,
  lastSessionBlueprint: null,
  lastCompletedSession: null,
  random: null,
};

try {
  state.random = createCryptoRandom(window.crypto);
} catch (error) {
  console.error(error);
  showDataError("Secure randomization is unavailable in this browser. Please use a current browser.");
}

function showView(view) {
  [ui.home, ui.session, ui.game, ui.summary].forEach((section) => {
    section.hidden = section !== view;
  });
  window.scrollTo({ top: 0, behavior: "smooth" });
}

function showDataError(message) {
  ui.dataError.hidden = false;
  ui.dataError.textContent = message;
}

function clearDataError() {
  ui.dataError.hidden = true;
  ui.dataError.textContent = "";
}

function sessionLabel(mode, totalQuestions) {
  if (mode === "endless") return "Endless practice";
  if (mode === "review") return "Review mistakes";
  return `${totalQuestions} questions`;
}

async function loadLevelConfig() {
  try {
    const configResponse = await fetch("data/levels.json", { cache: "no-store" });
    if (!configResponse.ok) throw new Error(`Could not load level configuration (${configResponse.status}).`);
    state.config = await configResponse.json();
    renderLevels();

    const level = state.config.levels?.[state.levelKey];
    if (!level?.enabled || !level.data) throw new Error("The enabled A1 level is not configured.");
    const dataResponse = await fetch(level.data, { cache: "no-store" });
    if (!dataResponse.ok) throw new Error(`Could not load the A1 vocabulary (${dataResponse.status}).`);
    const rawDataset = await dataResponse.json();
    const result = validateDataset(rawDataset);
    result.errors.forEach((message) => console.warn(`[A1 data validation] ${message}`));
    state.entries = result.entries;
    if (!state.entries.length) throw new Error("No valid A1 vocabulary entries remain after validation.");
    ui.selectedLevelCount.textContent = `${state.entries.length} cards ready`;
    clearDataError();
    updateHistoryNote();
  } catch (error) {
    console.error("A1 vocabulary loading failed.", error);
    showDataError(`${error.message} Try running the site through a local static server.`);
  }
}

function renderLevels() {
  ui.levelGrid.replaceChildren();
  Object.entries(state.config?.levels || {}).forEach(([key, level]) => {
    const card = document.createElement("article");
    card.className = `level-card${level.enabled ? " level-card--enabled" : " level-card--disabled"}`;
    const title = document.createElement("h3");
    title.textContent = key;
    const description = document.createElement("p");
    description.textContent = level.enabled ? "Start with practical everyday words." : "Coming soon.";
    card.append(title, description);
    const button = document.createElement("button");
    button.type = "button";
    button.className = "button button--secondary level-card__button";
    button.textContent = level.enabled ? `Practice ${key}` : "Coming soon";
    button.disabled = !level.enabled;
    if (level.enabled) button.addEventListener("click", () => openSessionSelection(key));
    card.append(button);
    ui.levelGrid.append(card);
  });
}

function updateHistoryNote() {
  const practiced = Object.values(state.history).filter((record) => Number(record?.timesShown) > 0).length;
  ui.historyNote.textContent = practiced
    ? `Learning history is saved on this device for ${practiced} word${practiced === 1 ? "" : "s"}.`
    : "Learning history is saved on this device.";
}

function openSessionSelection(levelKey) {
  if (levelKey !== "A1" || !state.entries.length) return;
  state.levelKey = levelKey;
  ui.selectedLevel.textContent = levelKey;
  ui.selectedLevelCount.textContent = `${state.entries.length} cards ready`;
  showView(ui.session);
  document.querySelector("#session-size-20").focus();
}

function selectedSession() {
  const value = document.querySelector('input[name="session-size"]:checked')?.value || "20";
  if (value === "endless") return { mode: "endless", totalQuestions: null };
  return { mode: "finite", totalQuestions: Number(value) };
}

function startSession(entries = state.entries, { mode = "finite", totalQuestions = 20, review = false } = {}) {
  if (!state.random) {
    showDataError("Secure randomization is unavailable in this browser. Please use a current browser.");
    showView(ui.home);
    return;
  }
  if (!entries.length) {
    showDataError("There are no valid words available for this session.");
    showView(ui.home);
    return;
  }
  state.session = createSession(entries, {
    mode: review ? "review" : mode,
    totalQuestions: review ? Math.max(20, entries.length) : totalQuestions,
    level: state.levelKey,
    history: state.history,
  });
  state.lastSessionBlueprint = {
    entries,
    mode: state.session.mode,
    totalQuestions: state.session.totalQuestions,
  };
  showView(ui.game);
  nextCard();
}

function nextCard() {
  const session = state.session;
  if (!session) return;
  if (session.totalQuestions !== null && session.answered >= session.totalQuestions && session.currentChecked) {
    showSummary();
    return;
  }
  const entry = selectNextEntry(session, state.random);
  if (!entry) {
    showSummary();
    return;
  }
  recordShown(state.history, entry);
  saveLearningHistory(state.history);
  renderCurrentCard(entry);
  window.requestAnimationFrame(() => ui.answerInput.focus());
}

function renderCurrentCard(entry) {
  ui.gameLevel.textContent = state.levelKey;
  ui.word.textContent = entry.german;
  ui.answerInput.value = "";
  ui.answerInput.disabled = false;
  ui.actionButton.textContent = "Check";
  ui.feedback.className = "feedback feedback--empty";
  ui.feedbackHeading.textContent = "Your answer";
  ui.feedbackAnswer.textContent = "Type the English translation, then press Enter or Check.";
  ui.answerDetails.hidden = true;
  ui.endSession.hidden = state.session.mode !== "endless";
  syncStats();
}

function syncStats() {
  const session = state.session;
  ui.questionProgress.textContent = session.totalQuestions === null
    ? `${session.questionNumber}`
    : `${session.questionNumber} / ${session.totalQuestions}`;
  ui.correctCount.textContent = String(session.correctCount);
  ui.streakCount.textContent = String(session.streak);
  ui.uniqueCount.textContent = String(session.shownIds.size);
}

function revealDetails(entry) {
  ui.detailType.textContent = entry.word_type || "—";
  ui.detailGender.textContent = entry.gender || "—";
  ui.detailPlural.textContent = entry.plural || "—";
  const exampleDe = entry.example_de || "";
  const exampleEn = entry.example_en || "";
  ui.detailExample.textContent = exampleDe && exampleEn ? `${exampleDe} — ${exampleEn}` : "—";
  ui.answerDetails.hidden = false;
}

function showFeedback(result) {
  const entry = result.entry;
  ui.feedback.className = `feedback feedback--${result.isCorrect ? "correct" : "incorrect"}`;
  ui.feedbackHeading.textContent = result.isCorrect ? "Correct" : "Not quite";
  ui.feedbackAnswer.textContent = result.isCorrect
    ? `${entry.german} = ${entry.english}`
    : `Correct answer: ${entry.english}`;
  revealDetails(entry);
}

function showEmptyAnswer() {
  ui.feedback.className = "feedback feedback--notice";
  ui.feedbackHeading.textContent = "Please enter an answer";
  ui.feedbackAnswer.textContent = "Type a translation before checking.";
}

function handleAnswerSubmit(event) {
  event.preventDefault();
  const session = state.session;
  if (!session) return;
  if (session.currentChecked) {
    nextCard();
    return;
  }
  const result = submitAnswer(session, ui.answerInput.value);
  if (result.status === "empty") {
    showEmptyAnswer();
    ui.answerInput.focus();
    return;
  }
  if (result.status !== "correct" && result.status !== "incorrect") return;
  saveLearningHistory(state.history);
  ui.answerInput.disabled = true;
  ui.actionButton.textContent = "Next";
  showFeedback(result);
  syncStats();
  // Keep keyboard users on the logical next action after disabling the field.
  ui.actionButton.focus();
}

function showSummary() {
  const session = state.session;
  if (!session) return;
  state.lastCompletedSession = session;
  ui.summaryTitle.textContent = session.mode === "endless" ? "Endless practice complete" : "Session complete";
  ui.summaryQuestions.textContent = String(session.answered);
  ui.summaryCorrect.textContent = String(session.correctCount);
  ui.summaryIncorrect.textContent = String(session.incorrectCount);
  ui.summaryAccuracy.textContent = `${sessionAccuracy(session)}%`;
  ui.summaryUnique.textContent = String(session.shownIds.size);
  ui.summaryLongest.textContent = String(session.longestStreak);

  const missed = mostFrequentlyMissed(session);
  ui.missedList.replaceChildren();
  ui.missedEmpty.hidden = missed.length > 0;
  ui.reviewMistakes.hidden = missed.length === 0;
  missed.slice(0, 8).forEach(({ entry, misses }) => {
    const item = document.createElement("li");
    const word = document.createElement("strong");
    word.textContent = entry.german;
    const count = document.createElement("span");
    count.textContent = `${entry.english} · ${misses} miss${misses === 1 ? "" : "es"}`;
    item.append(word, count);
    ui.missedList.append(item);
  });
  showView(ui.summary);
}

function startReviewMistakes() {
  const session = state.lastCompletedSession;
  if (!session || !session.mistakes.size) return;
  const mistakeEntries = session.entries.filter((entry) => session.mistakes.has(entry.id));
  startSession(mistakeEntries, { review: true });
}

function resetHistoryFromInterface() {
  if (!window.confirm("Reset all learning history? This cannot be undone.")) return;
  resetLearningHistory();
  state.history = {};
  updateHistoryNote();
}

function bindEvents() {
  ui.sessionForm.addEventListener("submit", (event) => {
    event.preventDefault();
    const choice = selectedSession();
    startSession(state.entries, choice);
  });
  ui.answerForm.addEventListener("submit", handleAnswerSubmit);
  ui.endSession.addEventListener("click", showSummary);
  ui.reviewMistakes.addEventListener("click", startReviewMistakes);
  ui.resetHistory.addEventListener("click", resetHistoryFromInterface);
  document.querySelectorAll("[data-action='home']").forEach((button) => {
    button.addEventListener("click", () => showView(ui.home));
  });
  document.querySelector("#play-again").addEventListener("click", () => {
    const blueprint = state.lastSessionBlueprint;
    if (blueprint) startSession(blueprint.entries, blueprint);
  });
  document.querySelectorAll('input[name="session-size"]').forEach((input) => {
    input.addEventListener("change", () => {
      document.querySelectorAll(".session-option").forEach((option) => option.classList.remove("session-option--selected"));
      input.closest(".session-option")?.classList.add("session-option--selected");
    });
  });
}

bindEvents();
updateHistoryNote();
loadLevelConfig();
