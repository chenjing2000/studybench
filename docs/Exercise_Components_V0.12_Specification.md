# Exercise Components V0.12 Specification

## Scope

Every recognized extended Article renders one shared action row at the end of its Exercise:

```text
[hints]   [ref ans]   [reset]
```

Pure `Article` and `ArticleBlank` pages do not render the action row.

## Layout

`extended_article_classes/exercise_components/exercise_components_ui.py` is the shared UI description for the action row.

- one horizontal row
- centered
- button width: 70 px
- button height: 30 px
- adjacent gap: 15 px
- `hints` and `ref ans` are toggle actions when the exercise type supports the action
- `reset` is not a toggle

There is intentionally no `common.py`. Each extended Article owns its complete response rules in its own `*_components.py` module.

## Type-specific behavior

### ArticleChoice

- `hints`: for answered questions only. If the selected key differs from `reference_answer`, the selected option text becomes `#c8161d`. It does not reveal the reference answer or explanation. Toggling off restores the original text color.
- `ref ans`: for answered questions only. Shows `Reference answer: <key>. <option text>` and the question explanation below that question. It does not change option color.
- `reset`: clears every selected radio option, restores colors, hides reference/explanation feedback, switches both toggles off, and enters the existing answer autosave flow.

### ArticleAnswer

- `hints`: no-op.
- `ref ans`: for answered questions only. Shows the complete reference answer and explanation below that question.
- `reset`: clears every answer textbox, hides feedback, switches toggles off, and autosaves the empty answers.

### ArticleCloze

- `hints`: same wrong-selection behavior as `ArticleChoice`.
- `ref ans`: for answered blanks only. Shows `<key>. <option text>` and explanation below that blank.
- `reset`: complete Exercise reset.

### ArticleClozeWords

- `hints`: no-op.
- `ref ans`: for answered blanks only. Shows the reference word/phrase and explanation below that blank.
- `reset`: clears every textbox and completely resets the Exercise action state.

### ArticleClozeSentences

- `hints`: no-op.
- `ref ans`: for answered blanks only. Shows `<key>. <shared option sentence>` and explanation below that blank.
- `reset`: clears every one-character answer textbox and completely resets the Exercise action state.

## Runtime behavior

The Python component modules provide static action metadata. The generic web runtime owns live DOM state.

- Whether an item is answered is determined from the current control value at the moment of refresh.
- If a toggle is already on, newly answered items immediately receive the corresponding behavior.
- If an answer is cleared, its hint/reference feedback immediately disappears.
- Reference/explanation feedback is inserted below the matching question row, never as one combined block after the whole Exercise.
- `hints` and `ref ans` state reset to off on every new render.
- Toggle state is temporary UI state and is not persisted in `answer_sheet.json`.
- `reset` reuses the existing dirty/autosave lifecycle; no second answer-save path is introduced.

## Separation of responsibilities

```text
Extended Article domain
        ↓
exercise_components/<type>_components.py
        ↓
exercise_components/exercise_components_ui.py
        ↓
Extended Article Feature UI
        ↓
Generic Web Runtime
```

The generic runtime does not dispatch on `ArticleChoice`, `ArticleAnswer`, or other Python Article class names.
