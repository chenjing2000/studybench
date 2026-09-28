let bridge = null;
let currentAccent = "uk";
let selectedText = "";
let vocabularyWords = [];
let vocabularyHighlightsVisible = false;
let genAudioEnabled = true;
let exerciseDirty = false;
let exerciseSaveAllowed = true;
let exerciseSaveTimer = null;
let currentAnswerNumbers = [];

const addButton = document.getElementById("selectionAddButton");
const passageTextElement = document.getElementById("passageText");
const passageControlsElement = document.getElementById("passageControls");
const exerciseSectionElement = document.getElementById("exerciseSection");

new QWebChannel(qt.webChannelTransport, function (channel) {
  bridge = channel.objects.bridge;
});

window.renderStudyView = function (viewModel) {
  currentAccent = "uk";
  hideSelectionButton();
  clearTimeout(exerciseSaveTimer);
  exerciseSaveTimer = null;
  currentAnswerNumbers = [];
  setExerciseDirty(false, false);

  document.getElementById("emptyState").classList.add("hidden");
  document.getElementById("passagePage").classList.remove("hidden");
  document.getElementById("passageTitle").textContent = "";
  passageTextElement.replaceChildren();
  passageControlsElement.replaceChildren();
  exerciseSectionElement.replaceChildren();
  passageControlsElement.classList.add("hidden");

  const components = Array.isArray(viewModel && viewModel.components)
    ? viewModel.components
    : [];
  components.forEach(renderTopLevelComponent);
  applyVocabularyHighlights();
  updateExerciseInputState();
};

window.clearStudyView = function () {
  hideSelectionButton();
  clearTextSelection();
  clearTimeout(exerciseSaveTimer);
  exerciseSaveTimer = null;
  currentAnswerNumbers = [];
  setExerciseDirty(false, false);
  document.getElementById("passageTitle").textContent = "";
  passageTextElement.replaceChildren();
  passageControlsElement.replaceChildren();
  exerciseSectionElement.replaceChildren();
  document.getElementById("passagePage").classList.add("hidden");
  document.getElementById("emptyState").classList.remove("hidden");
};

window.setVocabularyWords = function (words, visible) {
  vocabularyWords = normalizeVocabularyWords(words);
  vocabularyHighlightsVisible = Boolean(visible);
  applyVocabularyHighlights();
};

window.setVocabularyHighlightsVisible = function (visible) {
  vocabularyHighlightsVisible = Boolean(visible);
  applyVocabularyHighlights();
};

window.setGenAudioEnabled = function (enabled) {
  genAudioEnabled = Boolean(enabled);
  const button = document.getElementById("genAudioButton");
  if (button) button.disabled = !genAudioEnabled;
};

window.setExerciseSaveAllowed = function (allowed) {
  exerciseSaveAllowed = Boolean(allowed);
  updateExerciseInputState();
};

window.markExerciseSaved = function () {
  setExerciseDirty(false, true);
};

window.flushExerciseAnswers = function () {
  window.submitExerciseAnswers();
};

window.submitExerciseAnswers = function () {
  clearTimeout(exerciseSaveTimer);
  exerciseSaveTimer = null;
  if (!bridge || !exerciseDirty || !exerciseSaveAllowed || currentAnswerNumbers.length === 0) {
    return;
  }
  bridge.saveExerciseAnswers(JSON.stringify(collectExerciseAnswers()));
};

window.updateAudioState = function (state, owner) {
  document.querySelectorAll(".paragraph-play").forEach(function (button) {
    const paragraphIndex = button.dataset.paragraphIndex;
    if (state !== "stopped" && owner === "paragraph:" + paragraphIndex) {
      button.textContent = state === "playing" ? "⏸" : "▶";
    } else {
      button.textContent = "▶";
    }
  });
  const passageButton = document.getElementById("wholePassageButton");
  if (passageButton) {
    if (state !== "stopped" && owner === "passage") {
      passageButton.textContent = state === "playing" ? "⏸ Read All" : "▶ Read All";
    } else {
      passageButton.textContent = "▶ Read All";
    }
  }
};

function renderTopLevelComponent(component) {
  if (!component || typeof component !== "object") return;
  const type = component.type;
  if (type === "title") {
    document.getElementById("passageTitle").textContent = component.text || "";
    return;
  }
  if (type === "paragraph") {
    passageTextElement.appendChild(renderParagraph(component));
    return;
  }
  if (type === "passage_audio_controls") {
    renderPassageControls();
    return;
  }
  if (type === "exercise_title") {
    const title = document.createElement("h2");
    title.className = "exercise-title";
    title.textContent = component.text || "Exercises";
    exerciseSectionElement.appendChild(title);
    return;
  }
  const rendered = renderComponent(component);
  if (rendered) exerciseSectionElement.appendChild(rendered);
}

function renderParagraph(component) {
  const audioEnabled = Boolean(component.audio_enabled);
  const row = document.createElement("div");
  row.className = audioEnabled ? "paragraph-row" : "paragraph-row paragraph-row-no-audio";
  if (audioEnabled) {
    const playButton = document.createElement("button");
    playButton.className = "paragraph-play";
    playButton.type = "button";
    playButton.textContent = "▶";
    playButton.dataset.paragraphIndex = String(component.paragraph_index || 0);
    playButton.title = "朗读本段";
    playButton.addEventListener("click", function () {
      if (bridge) bridge.playParagraph(Number(playButton.dataset.paragraphIndex));
    });
    row.appendChild(playButton);
  }
  const text = document.createElement("p");
  text.className = "paragraph-text";
  const children = Array.isArray(component.children) ? component.children : [];
  children.forEach(function (segment, index) {
    if (index > 0) text.appendChild(document.createTextNode(" "));
    text.appendChild(renderSegment(segment));
  });
  row.appendChild(text);
  return row;
}

function renderSegment(component) {
  const span = document.createElement("span");
  const audioEnabled = Boolean(component.audio_enabled);
  span.className = audioEnabled ? "segment audio-enabled" : "segment";
  span.dataset.sid = component.sid || "";
  span._parts = Array.isArray(component.children) ? component.children : [];
  if (audioEnabled) {
    span.title = "右键朗读该句";
    span.addEventListener("contextmenu", function (event) {
      event.preventDefault();
      event.stopPropagation();
      clearTextSelection();
      if (bridge) bridge.playSegment(component.sid || "");
    });
  }
  renderSegmentParts(span);
  return span;
}

function renderSegmentParts(segment) {
  segment.replaceChildren();
  const parts = Array.isArray(segment._parts) ? segment._parts : [];
  parts.forEach(function (part) {
    if (!part || typeof part !== "object") return;
    if (part.type === "blank") {
      const blank = document.createElement("span");
      blank.className = "blank-placeholder";
      blank.textContent = "____" + String(part.number || "") + "____";
      segment.appendChild(blank);
    } else if (part.type === "text") {
      appendMaybeHighlighted(segment, String(part.text || ""));
    }
  });
}

function renderComponent(component) {
  if (!component || typeof component !== "object") return null;
  const type = component.type;
  if (type === "question") return renderContainer(component, "question");
  if (type === "cloze_row") return renderContainer(component, "question cloze-row");
  if (type === "fill_row") return renderContainer(component, "question fill-row");
  if (type === "sentence_answer_row") return renderContainer(component, "question sentence-answer-row");
  if (type === "sentence_answer_list") return renderContainer(component, "sentence-answer-list");
  if (type === "prompt") {
    const p = document.createElement("p");
    p.className = "question-prompt";
    p.textContent = component.text || "";
    return p;
  }
  if (type === "number") {
    const span = document.createElement("span");
    span.className = "exercise-number";
    span.textContent = component.text || "";
    return span;
  }
  if (type === "cue") {
    const span = document.createElement("span");
    span.className = "exercise-cue";
    span.textContent = component.text || "";
    return span;
  }
  if (type === "radio_group") return renderRadioGroup(component);
  if (type === "textbox") return renderTextbox(component);
  if (type === "option_pool") return renderOptionPool(component);
  return null;
}

function renderContainer(component, className) {
  const block = document.createElement("div");
  block.className = className;
  if (Number.isInteger(component.number)) block.dataset.number = String(component.number);
  (Array.isArray(component.children) ? component.children : []).forEach(function (child) {
    const rendered = renderComponent(child);
    if (rendered) block.appendChild(rendered);
  });
  return block;
}

function registerAnswerNumber(number) {
  if (!Number.isInteger(number) || number < 1) return;
  if (!currentAnswerNumbers.includes(number)) currentAnswerNumbers.push(number);
}

function renderRadioGroup(component) {
  const number = Number(component.number);
  registerAnswerNumber(number);
  const wrapper = document.createElement("div");
  wrapper.className = component.class_name || "question-options";
  (Array.isArray(component.options) ? component.options : []).forEach(function (option) {
    const row = document.createElement("label");
    row.className = "option-row";
    const radio = document.createElement("input");
    radio.type = "radio";
    radio.name = "answer-" + number;
    radio.value = option.key || "";
    radio.dataset.number = String(number);
    radio.className = "answer-control";
    radio.checked = String(component.value || "") === radio.value;
    radio.addEventListener("change", answerChanged);
    const text = document.createElement("span");
    text.className = "option-text";
    text.textContent = String(option.key || "") + ". " + String(option.text || "");
    row.appendChild(radio);
    row.appendChild(text);
    wrapper.appendChild(row);
  });
  if (wrapper.closest && component._cloze) wrapper.classList.add("cloze-options");
  return wrapper;
}

function renderTextbox(component) {
  const number = Number(component.number);
  registerAnswerNumber(number);
  let input;
  if (component.multiline) {
    input = document.createElement("textarea");
    input.rows = 1;
    input.className = "exercise-textbox answer-textbox answer-control";
  } else {
    input = document.createElement("input");
    input.type = "text";
    input.className = "exercise-textbox answer-control" + (component.class_name ? " " + component.class_name : "");
    if (Number(component.max_length) > 0) input.maxLength = Number(component.max_length);
  }
  input.dataset.number = String(number);
  input.value = String(component.value || "");
  input.addEventListener("input", function () {
    if (component.uppercase) input.value = input.value.toUpperCase();
    if (input.tagName === "TEXTAREA") autoGrow(input);
    answerChanged();
  });
  if (input.tagName === "TEXTAREA") autoGrow(input);
  return input;
}

function renderOptionPool(component) {
  const pool = document.createElement("div");
  pool.className = "sentence-option-pool";
  (Array.isArray(component.options) ? component.options : []).forEach(function (option) {
    const row = document.createElement("div");
    row.className = "sentence-option";
    row.textContent = String(option.key || "") + ". " + String(option.text || "");
    pool.appendChild(row);
  });
  return pool;
}

function renderPassageControls() {
  passageControlsElement.replaceChildren();
  passageControlsElement.classList.remove("hidden");
  const genAudioButton = document.createElement("button");
  genAudioButton.id = "genAudioButton";
  genAudioButton.type = "button";
  genAudioButton.className = "control-button";
  genAudioButton.textContent = "Gen Audio";
  genAudioButton.disabled = !genAudioEnabled;
  genAudioButton.addEventListener("click", function () {
    if (bridge && genAudioEnabled) bridge.genAudio();
  });

  const accentButton = document.createElement("button");
  accentButton.type = "button";
  accentButton.className = "accent-button";
  accentButton.textContent = "British";
  accentButton.title = "Switch British / American pronunciation";
  accentButton.addEventListener("click", function () {
    currentAccent = currentAccent === "uk" ? "us" : "uk";
    accentButton.textContent = currentAccent === "uk" ? "British" : "American";
    if (bridge) bridge.setAccent(currentAccent);
  });

  const playButton = document.createElement("button");
  playButton.id = "wholePassageButton";
  playButton.type = "button";
  playButton.className = "control-button";
  playButton.textContent = "▶ Read All";
  playButton.addEventListener("click", function () { if (bridge) bridge.playPassage(); });

  const stopButton = document.createElement("button");
  stopButton.type = "button";
  stopButton.className = "control-button";
  stopButton.textContent = "■ Stop";
  stopButton.addEventListener("click", function () { if (bridge) bridge.stopAudio(); });

  passageControlsElement.appendChild(genAudioButton);
  passageControlsElement.appendChild(accentButton);
  passageControlsElement.appendChild(playButton);
  passageControlsElement.appendChild(stopButton);
}

function collectExerciseAnswers() {
  return currentAnswerNumbers.map(function (number) {
    const checked = document.querySelector('input[type="radio"][name="answer-' + number + '"]:checked');
    if (checked) return {number: number, answer: checked.value};
    const input = document.querySelector('.exercise-textbox[data-number="' + number + '"]');
    return {number: number, answer: input ? input.value : ""};
  });
}

function answerChanged() {
  setExerciseDirty(true, true);
  scheduleAutoSave();
}

function setExerciseDirty(dirty, notifyBridge) {
  exerciseDirty = Boolean(dirty);
  if (notifyBridge !== false && bridge) bridge.setExerciseDirty(exerciseDirty);
}

function scheduleAutoSave() {
  clearTimeout(exerciseSaveTimer);
  if (!exerciseSaveAllowed || !exerciseDirty) return;
  exerciseSaveTimer = setTimeout(function () { window.submitExerciseAnswers(); }, 600);
}

function updateExerciseInputState() {
  document.querySelectorAll("#exerciseSection input, #exerciseSection textarea").forEach(function (control) {
    control.disabled = !exerciseSaveAllowed;
  });
}

function autoGrow(textarea) {
  textarea.style.height = "auto";
  textarea.style.height = Math.max(34, textarea.scrollHeight) + "px";
}

function applyVocabularyHighlights() {
  clearTextSelection();
  document.querySelectorAll("#passageText .segment").forEach(renderSegmentParts);
}

function appendMaybeHighlighted(parent, text) {
  if (!text) return;
  if (!vocabularyHighlightsVisible || vocabularyWords.length === 0) {
    parent.appendChild(document.createTextNode(text));
    return;
  }
  appendHighlightedText(parent, text, vocabularyWords);
}

function normalizeVocabularyWords(words) {
  if (!Array.isArray(words)) return [];
  const result = [];
  const seen = new Set();
  words.forEach(function (word) {
    const value = String(word || "").trim();
    const key = value.toLocaleLowerCase();
    if (value && !seen.has(key)) {
      seen.add(key);
      result.push(value);
    }
  });
  result.sort(function (a, b) { return b.length - a.length; });
  return result;
}

function appendHighlightedText(parent, text, words) {
  let position = 0;
  while (position < text.length) {
    let bestStart = -1;
    let bestEnd = -1;
    words.forEach(function (word) {
      const start = findWholeWord(text, word, position);
      if (start === -1) return;
      const end = start + word.length;
      if (bestStart === -1 || start < bestStart || (start === bestStart && end > bestEnd)) {
        bestStart = start;
        bestEnd = end;
      }
    });
    if (bestStart === -1) {
      parent.appendChild(document.createTextNode(text.slice(position)));
      break;
    }
    if (bestStart > position) parent.appendChild(document.createTextNode(text.slice(position, bestStart)));
    const mark = document.createElement("span");
    mark.className = "vocabulary-match";
    mark.textContent = text.slice(bestStart, bestEnd);
    parent.appendChild(mark);
    position = bestEnd;
  }
}

function findWholeWord(text, word, fromIndex) {
  const lowerText = text.toLocaleLowerCase();
  const lowerWord = word.toLocaleLowerCase();
  let start = lowerText.indexOf(lowerWord, fromIndex);
  while (start !== -1) {
    const end = start + word.length;
    const before = start > 0 ? text[start - 1] : "";
    const after = end < text.length ? text[end] : "";
    if (!isEnglishWordCharacter(before) && !isEnglishWordCharacter(after)) return start;
    start = lowerText.indexOf(lowerWord, start + 1);
  }
  return -1;
}

function isEnglishWordCharacter(character) {
  return /[A-Za-z'’-]/.test(character || "");
}

document.addEventListener("selectionchange", updateSelectionButton);
addButton.addEventListener("mousedown", function (event) { event.preventDefault(); });
addButton.addEventListener("click", function () {
  if (!bridge || !selectedText) {
    hideSelectionButton();
    return;
  }
  bridge.addWord(selectedText);
  clearTextSelection();
});

function updateSelectionButton() {
  const selection = window.getSelection();
  if (!selection || selection.rangeCount === 0 || selection.isCollapsed) {
    hideSelectionButton();
    return;
  }
  const range = selection.getRangeAt(0);
  if (!passageTextElement.contains(range.commonAncestorContainer)) {
    hideSelectionButton();
    return;
  }
  const startSegment = closestSegment(range.startContainer);
  const endSegment = closestSegment(range.endContainer);
  if (!startSegment || startSegment !== endSegment) {
    hideSelectionButton();
    return;
  }
  const text = selection.toString().replace(/\s+/g, " ").trim();
  if (!text) {
    hideSelectionButton();
    return;
  }
  const rect = range.getBoundingClientRect();
  if (rect.width === 0 && rect.height === 0) {
    hideSelectionButton();
    return;
  }
  selectedText = text;
  addButton.style.left = window.scrollX + rect.right - 4 + "px";
  addButton.style.top = window.scrollY + rect.bottom - 6 + "px";
  addButton.classList.remove("hidden");
}

function closestSegment(node) {
  let element = node;
  if (node && node.nodeType === Node.TEXT_NODE) element = node.parentElement;
  if (!element || !element.closest) return null;
  return element.closest(".segment");
}

function clearTextSelection() {
  const selection = window.getSelection();
  if (selection) selection.removeAllRanges();
  hideSelectionButton();
}

function hideSelectionButton() {
  selectedText = "";
  addButton.classList.add("hidden");
}
