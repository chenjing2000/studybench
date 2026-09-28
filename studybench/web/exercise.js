let exerciseDirty = false;
let exerciseSaveAllowed = true;
let currentExercise = null;
let currentAnswers = null;
let exerciseSaveTimer = null;

window.renderExercise = function (exercise, answers) {
  currentExercise = exercise || null;
  currentAnswers = answers || null;
  const section = document.getElementById("exerciseSection");
  section.replaceChildren();
  setExerciseDirty(false, false);

  if (!exercise) {
    return;
  }

  const title = document.createElement("h2");
  title.className = "exercise-title";
  title.textContent = "Exercises";
  section.appendChild(title);

  const type = exercise.type;
  if (type === "article_choice") {
    renderArticleChoiceExercise(section, exercise);
  } else if (type === "article_answer") {
    renderArticleAnswerExercise(section, exercise);
  } else if (type === "article_cloze") {
    renderArticleClozeExercise(section, exercise);
  } else if (type === "article_cloze_words") {
    renderArticleClozeWordsExercise(section, exercise);
  } else if (type === "article_cloze_sentences") {
    renderArticleClozeSentencesExercise(section, exercise);
  }

  applyExerciseAnswers(currentAnswers);
  updateExerciseInputState();
};

window.clearExercise = function () {
  clearTimeout(exerciseSaveTimer);
  exerciseSaveTimer = null;
  currentExercise = null;
  currentAnswers = null;
  setExerciseDirty(false, false);
  document.getElementById("exerciseSection").replaceChildren();
};

window.setExerciseSaveAllowed = function (allowed) {
  exerciseSaveAllowed = Boolean(allowed);
  updateExerciseInputState();
};

window.markExerciseSaved = function () {
  setExerciseDirty(false, true);
};

window.submitExerciseAnswers = function () {
  clearTimeout(exerciseSaveTimer);
  exerciseSaveTimer = null;
  if (!bridge || !exerciseDirty || !exerciseSaveAllowed || !currentExercise) {
    return;
  }
  bridge.saveExerciseAnswers(JSON.stringify(collectExerciseAnswers()));
};

window.flushExerciseAnswers = function () {
  window.submitExerciseAnswers();
};

function answerMap() {
  const result = new Map();
  const entries = currentAnswers && Array.isArray(currentAnswers.answers)
    ? currentAnswers.answers
    : [];
  entries.forEach(function (entry) {
    if (entry && Number.isInteger(entry.number)) {
      result.set(entry.number, String(entry.answer || ""));
    }
  });
  return result;
}

function renderArticleChoiceExercise(section, exercise) {
  exercise.questions.forEach(function (question) {
    const block = createQuestionBlock(question.number, "article_choice");
    const prompt = document.createElement("p");
    prompt.className = "question-prompt";
    prompt.textContent = question.number + ". " + question.prompt;
    block.appendChild(prompt);

    const options = document.createElement("div");
    options.className = "question-options";
    question.options.forEach(function (option) {
      options.appendChild(createRadioOption(question.number, option));
    });
    block.appendChild(options);
    section.appendChild(block);
  });
}

function renderArticleAnswerExercise(section, exercise) {
  exercise.questions.forEach(function (question) {
    const block = createQuestionBlock(question.number, "article_answer");
    const prompt = document.createElement("p");
    prompt.className = "question-prompt";
    prompt.textContent = question.number + ". " + question.prompt;
    block.appendChild(prompt);

    const input = document.createElement("textarea");
    input.className = "exercise-textbox answer-textbox";
    input.dataset.number = String(question.number);
    input.rows = 1;
    input.addEventListener("input", function () {
      autoGrow(input);
      answerChanged();
    });
    block.appendChild(input);
    section.appendChild(block);
  });
}

function renderArticleClozeExercise(section, exercise) {
  exercise.items.forEach(function (item) {
    const block = createQuestionBlock(item.number, "article_cloze");
    block.classList.add("cloze-row");
    const number = document.createElement("span");
    number.className = "exercise-number";
    number.textContent = item.number + ".";
    block.appendChild(number);

    const options = document.createElement("div");
    options.className = "cloze-options";
    item.options.forEach(function (option) {
      options.appendChild(createRadioOption(item.number, option));
    });
    block.appendChild(options);
    section.appendChild(block);
  });
}

function renderArticleClozeWordsExercise(section, exercise) {
  exercise.items.forEach(function (item) {
    const block = createQuestionBlock(item.number, "article_cloze_words");
    block.classList.add("fill-row");

    const number = document.createElement("span");
    number.className = "exercise-number";
    number.textContent = item.number + ".";
    block.appendChild(number);

    const cue = document.createElement("span");
    cue.className = "exercise-cue";
    cue.textContent = item.cue ? "(" + item.cue + ")" : "";
    block.appendChild(cue);

    const input = document.createElement("input");
    input.type = "text";
    input.className = "exercise-textbox word-textbox";
    input.dataset.number = String(item.number);
    input.addEventListener("input", answerChanged);
    block.appendChild(input);
    section.appendChild(block);
  });
}

function renderArticleClozeSentencesExercise(section, exercise) {
  const pool = document.createElement("div");
  pool.className = "sentence-option-pool";
  exercise.options.forEach(function (option) {
    const row = document.createElement("div");
    row.className = "sentence-option";
    row.textContent = option.key + ". " + option.text;
    pool.appendChild(row);
  });
  section.appendChild(pool);

  const answers = document.createElement("div");
  answers.className = "sentence-answer-list";
  exercise.items.forEach(function (item) {
    const row = createQuestionBlock(item.number, "article_cloze_sentences");
    row.classList.add("sentence-answer-row");
    const number = document.createElement("span");
    number.className = "exercise-number";
    number.textContent = item.number + ".";
    row.appendChild(number);

    const input = document.createElement("input");
    input.type = "text";
    input.maxLength = 1;
    input.className = "exercise-textbox sentence-key-textbox";
    input.dataset.number = String(item.number);
    input.addEventListener("input", function () {
      input.value = input.value.toUpperCase();
      answerChanged();
    });
    row.appendChild(input);
    answers.appendChild(row);
  });
  section.appendChild(answers);
}

function createQuestionBlock(number, type) {
  const block = document.createElement("div");
  block.className = "question";
  block.dataset.number = String(number);
  block.dataset.exerciseType = type;
  return block;
}

function createRadioOption(number, option) {
  const row = document.createElement("label");
  row.className = "option-row";

  const radio = document.createElement("input");
  radio.type = "radio";
  radio.name = "answer-" + number;
  radio.value = option.key;
  radio.dataset.number = String(number);
  radio.addEventListener("change", answerChanged);

  const text = document.createElement("span");
  text.className = "option-text";
  text.textContent = option.key + ". " + option.text;

  row.appendChild(radio);
  row.appendChild(text);
  return row;
}

function applyExerciseAnswers(answersPayload) {
  const map = answerMap();
  const radios = document.querySelectorAll('#exerciseSection input[type="radio"]');
  radios.forEach(function (radio) {
    const number = Number(radio.dataset.number);
    radio.checked = map.get(number) === radio.value;
  });

  const textboxes = document.querySelectorAll("#exerciseSection .exercise-textbox");
  textboxes.forEach(function (input) {
    const number = Number(input.dataset.number);
    input.value = map.get(number) || "";
    if (input.tagName === "TEXTAREA") {
      autoGrow(input);
    }
  });
  setExerciseDirty(false, false);
}

function collectExerciseAnswers() {
  if (!currentExercise) {
    return [];
  }
  const type = currentExercise.type;
  const source = Array.isArray(currentExercise.questions)
    ? currentExercise.questions
    : currentExercise.items;
  const result = [];

  source.forEach(function (item) {
    const number = item.number;
    let answer = "";
    if (type === "article_choice" || type === "article_cloze") {
      const checked = document.querySelector(
        '#exerciseSection input[type="radio"][name="answer-' + number + '"]:checked'
      );
      answer = checked ? checked.value : "";
    } else {
      const input = document.querySelector(
        '#exerciseSection .exercise-textbox[data-number="' + number + '"]'
      );
      answer = input ? input.value : "";
    }
    result.push({number: number, answer: answer});
  });
  return result;
}

function answerChanged() {
  setExerciseDirty(true, true);
  scheduleAutoSave();
}

function setExerciseDirty(dirty, notifyBridge) {
  exerciseDirty = Boolean(dirty);
  if (notifyBridge !== false && bridge) {
    bridge.setExerciseDirty(exerciseDirty);
  }
}

function scheduleAutoSave() {
  clearTimeout(exerciseSaveTimer);
  if (!exerciseSaveAllowed || !exerciseDirty) {
    return;
  }
  exerciseSaveTimer = setTimeout(function () {
    window.submitExerciseAnswers();
  }, 600);
}

function updateExerciseInputState() {
  const controls = document.querySelectorAll(
    "#exerciseSection input, #exerciseSection textarea"
  );
  controls.forEach(function (control) {
    control.disabled = !exerciseSaveAllowed;
  });
}

function autoGrow(textarea) {
  textarea.style.height = "auto";
  textarea.style.height = Math.max(34, textarea.scrollHeight) + "px";
}
