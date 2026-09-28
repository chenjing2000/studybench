let bridge = null;
let currentAccent = "uk";
let selectedText = "";
let vocabularyWords = [];
let vocabularyHighlightsVisible = false;
let genAudioEnabled = true;
let currentArticleFamily = "article";

const addButton = document.getElementById("selectionAddButton");
const passageTextElement = document.getElementById("passageText");

new QWebChannel(qt.webChannelTransport, function (channel) {
  bridge = channel.objects.bridge;
});

window.renderStudyPage = function (data) {
  currentAccent = "uk";
  currentArticleFamily = data.article_family === "article_blank" ? "article_blank" : "article";
  hideSelectionButton();

  document.getElementById("emptyState").classList.add("hidden");
  document.getElementById("passagePage").classList.remove("hidden");

  const passage = data.passage || {};
  document.getElementById("passageTitle").textContent = passage.title || "";

  if (currentArticleFamily === "article_blank") {
    renderArticleBlankPassage(passage);
  } else {
    renderArticlePassage(passage);
  }

  if (window.renderExercise) {
    window.renderExercise(data.exercise || null, data.answers || null);
  }
  applyVocabularyHighlights();
};

// Backward-compatible function name inside this package only; all Python calls use renderStudyPage.
window.renderPassage = window.renderStudyPage;

window.clearPassage = function () {
  hideSelectionButton();
  clearTextSelection();
  document.getElementById("passageTitle").textContent = "";
  document.getElementById("passageText").replaceChildren();
  document.getElementById("passageControls").replaceChildren();
  if (window.clearExercise) {
    window.clearExercise();
  } else {
    document.getElementById("exerciseSection").replaceChildren();
  }
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

function renderArticlePassage(passage) {
  renderParagraphs(passage.paragraphs || [], true);
  renderPassageControls(true);
}

function renderArticleBlankPassage(passage) {
  renderParagraphs(passage.paragraphs || [], false);
  renderPassageControls(false);
}

function renderParagraphs(paragraphs, audioEnabled) {
  const container = document.getElementById("passageText");
  container.replaceChildren();

  paragraphs.forEach(function (paragraph, paragraphIndex) {
    const row = document.createElement("div");
    row.className = audioEnabled ? "paragraph-row" : "paragraph-row paragraph-row-no-audio";

    if (audioEnabled) {
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
    }

    const text = document.createElement("p");
    text.className = "paragraph-text";
    const segments = Array.isArray(paragraph.segments) ? paragraph.segments : [];
    segments.forEach(function (segment, segmentIndex) {
      if (segmentIndex > 0) {
        text.appendChild(document.createTextNode(" "));
      }
      const span = document.createElement("span");
      span.className = audioEnabled ? "segment audio-enabled" : "segment";
      span.dataset.sid = segment.sid || "";
      span.dataset.originalText = segment.text || "";
      if (audioEnabled) {
        span.title = "右键朗读该句";
        span.addEventListener("contextmenu", function (event) {
          event.preventDefault();
          event.stopPropagation();
          clearTextSelection();
          if (bridge) {
            bridge.playSegment(segment.sid);
          }
        });
      }
      text.appendChild(span);
    });
    row.appendChild(text);
    container.appendChild(row);
  });
}

function renderPassageControls(audioEnabled) {
  const controls = document.getElementById("passageControls");
  controls.replaceChildren();
  controls.classList.toggle("hidden", !audioEnabled);
  if (!audioEnabled) {
    return;
  }

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

function applyVocabularyHighlights() {
  clearTextSelection();
  const segments = document.querySelectorAll("#passageText .segment");
  segments.forEach(function (segment) {
    const originalText = segment.dataset.originalText || "";
    segment.replaceChildren();
    appendSegmentText(segment, originalText);
  });
}

function appendSegmentText(parent, text) {
  if (currentArticleFamily !== "article_blank") {
    appendMaybeHighlighted(parent, text);
    return;
  }

  const pattern = /\[\[(\d+)\]\]/g;
  let cursor = 0;
  let match;
  while ((match = pattern.exec(text)) !== null) {
    appendMaybeHighlighted(parent, text.slice(cursor, match.index));
    const blank = document.createElement("span");
    blank.className = "blank-placeholder";
    blank.textContent = "____" + match[1] + "____";
    parent.appendChild(blank);
    cursor = match.index + match[0].length;
  }
  appendMaybeHighlighted(parent, text.slice(cursor));
}

function appendMaybeHighlighted(parent, text) {
  if (!text) {
    return;
  }
  if (!vocabularyHighlightsVisible || vocabularyWords.length === 0) {
    parent.appendChild(document.createTextNode(text));
    return;
  }
  appendHighlightedText(parent, text, vocabularyWords);
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

passageTextElement.addEventListener("contextmenu", function (event) {
  if (currentArticleFamily === "article_blank") {
    event.preventDefault();
  }
});

document.addEventListener("selectionchange", function () {
  updateSelectionButton();
});

addButton.addEventListener("mousedown", function (event) {
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
