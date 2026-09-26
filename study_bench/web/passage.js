let bridge = null;
let currentAccent = "uk";
let selectedText = "";
let vocabularyWords = [];
let vocabularyHighlightsVisible = false;
let genAudioEnabled = true;

const addButton = document.getElementById("selectionAddButton");

new QWebChannel(qt.webChannelTransport, function (channel) {
  bridge = channel.objects.bridge;
});

window.renderPassage = function (data) {
  currentAccent = "uk";
  hideSelectionButton();

  document.getElementById("emptyState").classList.add("hidden");
  document.getElementById("passagePage").classList.remove("hidden");

  const title = document.getElementById("passageTitle");
  title.textContent = data.title;

  renderParagraphs(data.paragraphs || []);
  renderPassageControls();
  renderExercises(data.questions || []);
};

window.clearPassage = function () {
  hideSelectionButton();
  clearTextSelection();
  document.getElementById("passageTitle").textContent = "";
  document.getElementById("passageText").replaceChildren();
  document.getElementById("passageControls").replaceChildren();
  document.getElementById("exerciseSection").replaceChildren();
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
  if (button) {
    button.disabled = !genAudioEnabled;
  }
};

window.updateAudioState = function (state, owner) {
  const paragraphButtons = document.querySelectorAll(".paragraph-play");
  paragraphButtons.forEach(function (button) {
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

function applyVocabularyHighlights() {
  clearTextSelection();
  const segments = document.querySelectorAll("#passageText .segment");
  segments.forEach(function (segment) {
    const originalText = segment.dataset.originalText || segment.textContent || "";
    segment.dataset.originalText = originalText;
    segment.replaceChildren();

    if (!vocabularyHighlightsVisible || vocabularyWords.length === 0) {
      segment.appendChild(document.createTextNode(originalText));
      return;
    }

    appendHighlightedText(segment, originalText, vocabularyWords);
  });
}

function normalizeVocabularyWords(words) {
  if (!Array.isArray(words)) {
    return [];
  }

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
  result.sort(function (a, b) {
    return b.length - a.length;
  });
  return result;
}

function appendHighlightedText(parent, text, words) {
  let position = 0;
  while (position < text.length) {
    let bestStart = -1;
    let bestEnd = -1;

    words.forEach(function (word) {
      const start = findWholeWord(text, word, position);
      if (start === -1) {
        return;
      }
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

    if (bestStart > position) {
      parent.appendChild(document.createTextNode(text.slice(position, bestStart)));
    }

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
    if (!isEnglishWordCharacter(before) && !isEnglishWordCharacter(after)) {
      return start;
    }
    start = lowerText.indexOf(lowerWord, start + 1);
  }

  return -1;
}

function isEnglishWordCharacter(character) {
  return /[A-Za-z'’-]/.test(character || "");
}

function renderParagraphs(paragraphs) {
  const container = document.getElementById("passageText");
  container.replaceChildren();

  paragraphs.forEach(function (paragraph, paragraphIndex) {
    const row = document.createElement("div");
    row.className = "paragraph-row";

    const playButton = document.createElement("button");
    playButton.className = "paragraph-play";
    playButton.type = "button";
    playButton.textContent = "▶";
    playButton.dataset.paragraphIndex = String(paragraphIndex);
    playButton.title = "朗读本段";
    playButton.addEventListener("click", function () {
      if (bridge) {
        bridge.playParagraph(paragraphIndex);
      }
    });
    row.appendChild(playButton);

    const text = document.createElement("p");
    text.className = "paragraph-text";

    paragraph.segments.forEach(function (segment, segmentIndex) {
      if (segmentIndex > 0) {
        text.appendChild(document.createTextNode(" "));
      }

      const span = document.createElement("span");
      span.className = "segment";
      span.dataset.sid = segment.sid;
      span.dataset.originalText = segment.text;
      span.textContent = segment.text;
      span.title = "右键朗读该句";
      span.addEventListener("contextmenu", function (event) {
        event.preventDefault();
        event.stopPropagation();
        clearTextSelection();
        if (bridge) {
          bridge.playSegment(segment.sid);
        }
      });
      text.appendChild(span);
    });

    row.appendChild(text);
    container.appendChild(row);
  });
}

function renderPassageControls() {
  const controls = document.getElementById("passageControls");
  controls.replaceChildren();

  const genAudioButton = document.createElement("button");
  genAudioButton.id = "genAudioButton";
  genAudioButton.type = "button";
  genAudioButton.className = "control-button";
  genAudioButton.textContent = "Gen Audio";
  genAudioButton.disabled = !genAudioEnabled;
  genAudioButton.addEventListener("click", function () {
    if (bridge && genAudioEnabled) {
      bridge.genAudio();
    }
  });

  const accentButton = document.createElement("button");
  accentButton.type = "button";
  accentButton.className = "accent-button";
  accentButton.textContent = "British";
  accentButton.title = "Switch British / American pronunciation";
  accentButton.addEventListener("click", function () {
    currentAccent = currentAccent === "uk" ? "us" : "uk";
    accentButton.textContent = currentAccent === "uk" ? "British" : "American";
    if (bridge) {
      bridge.setAccent(currentAccent);
    }
  });

  const playButton = document.createElement("button");
  playButton.id = "wholePassageButton";
  playButton.type = "button";
  playButton.className = "control-button";
  playButton.textContent = "▶ Read All";
  playButton.addEventListener("click", function () {
    if (bridge) {
      bridge.playPassage();
    }
  });

  const stopButton = document.createElement("button");
  stopButton.type = "button";
  stopButton.className = "control-button";
  stopButton.textContent = "■ Stop";
  stopButton.addEventListener("click", function () {
    if (bridge) {
      bridge.stopAudio();
    }
  });

  controls.appendChild(genAudioButton);
  controls.appendChild(accentButton);
  controls.appendChild(playButton);
  controls.appendChild(stopButton);
}

function renderExercises(questions) {
  const section = document.getElementById("exerciseSection");
  section.replaceChildren();

  if (!questions.length) {
    return;
  }

  const title = document.createElement("h2");
  title.className = "exercise-title";
  title.textContent = "Exercises";
  section.appendChild(title);

  questions.forEach(function (question, questionIndex) {
    const block = document.createElement("div");
    block.className = "question";
    block.dataset.questionIndex = String(questionIndex);

    if (question.type === "choice") {
      renderChoiceQuestion(block, question, questionIndex);
    } else if (question.type === "fill_blank") {
      renderFillBlankQuestion(block, question, questionIndex);
    }

    renderAnswerInfo(block, question);
    renderUserNote(block, question, questionIndex);
    section.appendChild(block);
  });
}

function renderChoiceQuestion(block, question, questionIndex) {
  const prompt = document.createElement("p");
  prompt.className = "question-prompt";
  prompt.textContent = String(questionIndex + 1) + ". " + question.prompt;
  block.appendChild(prompt);

  const options = document.createElement("div");
  options.className = "question-options";
  const savedAnswer = question.answer ? question.answer.user_answer || "" : "";

  question.options.forEach(function (option) {
    const row = document.createElement("label");
    row.className = "option-row";

    const radio = document.createElement("input");
    radio.type = "radio";
    radio.name = "question-" + questionIndex;
    radio.value = option.key;
    radio.checked = savedAnswer === option.key;
    radio.addEventListener("change", function () {
      if (radio.checked && bridge) {
        bridge.saveAnswer(questionIndex, option.key);
      }
    });

    const text = document.createElement("span");
    text.textContent = option.key + ". " + option.text;

    row.appendChild(radio);
    row.appendChild(text);
    options.appendChild(row);
  });

  block.appendChild(options);
}

function renderFillBlankQuestion(block, question, questionIndex) {
  const prompt = document.createElement("p");
  prompt.className = "question-prompt";

  const prefix = document.createTextNode(String(questionIndex + 1) + ". ");
  prompt.appendChild(prefix);

  const pieces = question.prompt.split("______");
  prompt.appendChild(document.createTextNode(pieces[0]));

  const input = document.createElement("input");
  input.className = "fill-input";
  input.type = "text";
  input.value = question.answer ? question.answer.user_answer || "" : "";
  input.addEventListener("keydown", function (event) {
    if (event.key === "Enter") {
      input.blur();
    }
  });
  input.addEventListener("blur", function () {
    if (bridge) {
      bridge.saveAnswer(questionIndex, input.value);
    }
  });
  prompt.appendChild(input);
  prompt.appendChild(document.createTextNode(pieces[1]));

  block.appendChild(prompt);
}

function renderAnswerInfo(block, question) {
  const info = document.createElement("div");
  info.className = "answer-info";

  const answer = document.createElement("p");
  answer.textContent = "Reference answer: " + question.reference_answer;
  info.appendChild(answer);

  if (question.explanation) {
    const explanation = document.createElement("p");
    explanation.textContent = "Explanation: " + question.explanation;
    info.appendChild(explanation);
  }

  block.appendChild(info);
}

function renderUserNote(block, question, questionIndex) {
  const label = document.createElement("label");
  label.className = "user-note-label";
  label.textContent = "Your note:";
  block.appendChild(label);

  const note = document.createElement("textarea");
  note.className = "user-note";
  note.value = question.answer ? question.answer.user_note || "" : "";
  note.addEventListener("blur", function () {
    if (bridge) {
      bridge.saveUserNote(questionIndex, note.value);
    }
  });
  block.appendChild(note);
}

const passageTextElement = document.getElementById("passageText");

passageTextElement.addEventListener("contextmenu", function (event) {
  event.preventDefault();
});

document.addEventListener("selectionchange", function () {
  updateSelectionButton();
});

addButton.addEventListener("mousedown", function (event) {
  // Keep the browser selection unchanged while the user clicks +.
  event.preventDefault();
});

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
  if (node && node.nodeType === Node.TEXT_NODE) {
    element = node.parentElement;
  }
  if (!element || !element.closest) {
    return null;
  }
  return element.closest(".segment");
}

function clearTextSelection() {
  const selection = window.getSelection();
  if (selection) {
    selection.removeAllRanges();
  }
  hideSelectionButton();
}

function hideSelectionButton() {
  selectedText = "";
  addButton.classList.add("hidden");
}

