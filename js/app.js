import {
  createCryptoRandom,
  createSession,
  filterAntonymEntries,
  loadLearningHistory,
  mostFrequentlyMissed,
  recordShown,
  resetLearningHistory,
  saveLearningHistory,
  selectNextEntry,
  sessionAccuracy,
  submitAnswer,
  submitRetry,
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
  gamePrompt: document.querySelector("#game-prompt"),
  questionProgress: document.querySelector("#question-progress"),
  correctCount: document.querySelector("#correct-count"),
  streakCount: document.querySelector("#streak-count"),
  uniqueCount: document.querySelector("#unique-count"),
  word: document.querySelector("#german-word"),
  answerForm: document.querySelector("#answer-form"),
  answerLabel: document.querySelector("#answer-label"),
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
  datasets: {},
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

async function loadLevelDataset(levelKey) {
  if (state.datasets[levelKey]) return state.datasets[levelKey];
  const level = state.config?.levels?.[levelKey];
  if (!level?.enabled || !level.data) throw new Error(`The ${levelKey} level is not configured.`);
  const response = await fetch(level.data, { cache: "no-store" });
  if (!response.ok) throw new Error(`Could not load the ${levelKey} vocabulary (${response.status}).`);
  const result = validateDataset(await response.json());
  result.errors.forEach((message) => console.warn(`[${levelKey} data validation] ${message}`));
  if (!result.entries.length) throw new Error(`No valid ${levelKey} vocabulary entries remain after validation.`);
  state.datasets[levelKey] = result.entries;
  return result.entries;
}

async function loadLevelConfig() {
  try {
    const configResponse = await fetch("data/levels.json", { cache: "no-store" });
    if (!configResponse.ok) throw new Error(`Could not load level configuration (${configResponse.status}).`);
    state.config = await configResponse.json();
    renderLevels();

    state.levelKey = state.config.defaultLevel || "A1";
    state.entries = await loadLevelDataset(state.levelKey);
    updateSelectedLevelCount();
    clearDataError();
    updateHistoryNote();
  } catch (error) {
    console.error("Vocabulary loading failed.", error);
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

function updateSelectedLevelCount() {
  const mode = document.querySelector('input[name="practice-mode"]:checked')?.value || "translate";
  if (mode === "antonym") {
    const antonymCards = filterAntonymEntries(state.entries);
    ui.selectedLevelCount.textContent = `${antonymCards.length} antonym cards ready`;
  } else {
    ui.selectedLevelCount.textContent = `${state.entries.length} cards ready`;
  }
}

async function openSessionSelection(levelKey) {
  try {
    const entries = await loadLevelDataset(levelKey);
    state.levelKey = levelKey;
    state.entries = entries;
    ui.selectedLevel.textContent = levelKey;
    updateSelectedLevelCount();
    clearDataError();
    showView(ui.session);
    document.querySelector("#session-size-20").focus();
  } catch (error) {
    console.error(`${levelKey} vocabulary loading failed.`, error);
    showDataError(`${error.message} Try running the site through a local static server.`);
  }
}

function selectedSession() {
  const sizeValue = document.querySelector('input[name="session-size"]:checked')?.value || "20";
  const questionType = document.querySelector('input[name="practice-mode"]:checked')?.value || "translate";
  if (sizeValue === "endless") return { mode: "endless", totalQuestions: null, questionType };
  return { mode: "finite", totalQuestions: Number(sizeValue), questionType };
}

function startSession(
  entries = state.entries,
  { mode = "finite", totalQuestions = 20, questionType = "translate", review = false } = {}
) {
  if (!state.random) {
    showDataError("Secure randomization is unavailable in this browser. Please use a current browser.");
    showView(ui.home);
    return;
  }
  const sessionEntries = questionType === "antonym" ? filterAntonymEntries(entries) : entries;
  if (!sessionEntries.length) {
    showDataError(
      questionType === "antonym"
        ? "There are no antonym words available for this level."
        : "There are no valid words available for this session."
    );
    showView(ui.home);
    return;
  }
  state.session = createSession(sessionEntries, {
    mode: review ? "review" : mode,
    totalQuestions: review ? Math.max(20, sessionEntries.length) : totalQuestions,
    level: state.levelKey,
    history: state.history,
    questionType,
  });
  state.lastSessionBlueprint = {
    entries: sessionEntries,
    mode: state.session.mode,
    totalQuestions: state.session.totalQuestions,
    questionType: state.session.questionType,
  };
  showView(ui.game);
  nextCard();
}

function nextCard() {
  const session = state.session;
  if (!session) return;
  if (session.totalQuestions !== null && session.answered >= session.totalQuestions && session.currentChecked && !session.retryPending) {
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
  const isAntonym = state.session?.questionType === "antonym";
  ui.gameLevel.textContent = state.levelKey;
  ui.word.textContent = entry.german;
  ui.answerInput.value = "";
  ui.answerInput.disabled = false;
  ui.answerInput.placeholder = isAntonym ? "e.g. opposite word in German" : "";
  ui.actionButton.textContent = "Check";
  if (ui.gamePrompt) {
    ui.gamePrompt.textContent = isAntonym ? "Find the German antonym (opposite)" : "Translate this word";
  }
  if (ui.answerLabel) {
    ui.answerLabel.textContent = isAntonym ? "German antonym" : "English translation";
  }
  ui.feedback.className = "feedback feedback--empty";
  ui.feedbackHeading.textContent = "Your answer";
  ui.feedbackAnswer.textContent = isAntonym
    ? "Type the opposite German word, then press Enter or Check."
    : "Type the English translation, then press Enter or Check.";
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
  const isAntonym = result.questionType === "antonym";

  if (isAntonym) {
    if (result.isCorrect) {
      ui.feedback.className = "feedback feedback--correct";
      ui.feedbackHeading.textContent = "Correct!";
      ui.feedbackAnswer.textContent = `${entry.german} (${entry.english}) ↔ ${entry.antonym}`;
      revealDetails(entry);
    } else {
      ui.feedback.className = "feedback feedback--incorrect";
      ui.feedbackHeading.textContent = "Not quite";
      ui.feedbackAnswer.textContent = `Opposite: ${entry.antonym} · Word: “${entry.german}” (${entry.english}). Type the antonym below to continue:`;
    }
  } else {
    ui.feedback.className = `feedback feedback--${result.isCorrect ? "correct" : "incorrect"}`;
    ui.feedbackHeading.textContent = result.isCorrect ? "Correct" : "Not quite";
    ui.feedbackAnswer.textContent = result.isCorrect
      ? `${entry.german} = ${entry.english}`
      : `Correct answer: ${entry.english}`;
    revealDetails(entry);
  }
}

function showEmptyAnswer() {
  ui.feedback.className = "feedback feedback--notice";
  ui.feedbackHeading.textContent = "Please enter an answer";
  ui.feedbackAnswer.textContent = state.session?.questionType === "antonym"
    ? "Type the German antonym before checking."
    : "Type a translation before checking.";
}

function handleAnswerSubmit(event) {
  event.preventDefault();
  const session = state.session;
  if (!session) return;

  // Advance to next card if already checked and not waiting for retry
  if (session.currentChecked && !session.retryPending) {
    nextCard();
    return;
  }

  // Handle retry after incorrect answer
  if (session.retryPending) {
    const retryResult = submitRetry(session, ui.answerInput.value);
    if (retryResult.status === "empty") {
      showEmptyAnswer();
      ui.answerInput.focus();
      return;
    }
    if (retryResult.isCorrect) {
      ui.feedback.className = "feedback feedback--correct";
      ui.feedbackHeading.textContent = "Great! You got it right.";
      ui.feedbackAnswer.textContent = `${session.currentEntry.german} (${session.currentEntry.english}) ↔ ${session.currentEntry.antonym}`;
      revealDetails(session.currentEntry);
      ui.answerInput.disabled = true;
      ui.actionButton.textContent = "Next";
      ui.actionButton.focus();
    } else {
      ui.feedback.className = "feedback feedback--incorrect";
      ui.feedbackHeading.textContent = "Try again";
      ui.feedbackAnswer.textContent = `Type the correct antonym: ${session.currentEntry.antonym}`;
      ui.answerInput.value = "";
      ui.answerInput.focus();
    }
    return;
  }

  // Initial submission
  const result = submitAnswer(session, ui.answerInput.value);
  if (result.status === "empty") {
    showEmptyAnswer();
    ui.answerInput.focus();
    return;
  }
  if (result.status !== "correct" && result.status !== "incorrect") return;
  saveLearningHistory(state.history);

  if (result.isCorrect) {
    ui.answerInput.disabled = true;
    ui.actionButton.textContent = "Next";
    showFeedback(result);
    ui.actionButton.focus();
  } else {
    showFeedback(result);
    if (session.questionType === "antonym") {
      ui.answerInput.value = "";
      ui.answerInput.disabled = false;
      ui.answerInput.placeholder = `Type “${session.currentEntry.antonym}”`;
      ui.actionButton.textContent = "Verify";
      ui.answerInput.focus();
    } else {
      ui.answerInput.disabled = true;
      ui.actionButton.textContent = "Next";
      ui.actionButton.focus();
    }
  }
  syncStats();
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
    const label = session.questionType === "antonym" && entry.antonym
      ? `↔ ${entry.antonym} · ${misses} miss${misses === 1 ? "" : "es"}`
      : `${entry.english} · ${misses} miss${misses === 1 ? "" : "es"}`;
    count.textContent = label;
    item.append(word, count);
    ui.missedList.append(item);
  });
  showView(ui.summary);
}

function startReviewMistakes() {
  const session = state.lastCompletedSession;
  if (!session || !session.mistakes.size) return;
  const mistakeEntries = session.entries.filter((entry) => session.mistakes.has(entry.id));
  startSession(mistakeEntries, {
    review: true,
    questionType: session.questionType || "translate",
  });
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
  document.querySelectorAll('input[name="practice-mode"]').forEach((input) => {
    input.addEventListener("change", () => {
      document.querySelectorAll(".mode-option").forEach((option) => option.classList.remove("mode-option--selected"));
      input.closest(".mode-option")?.classList.add("mode-option--selected");
      updateSelectedLevelCount();
    });
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
