# StudyBench UI / Application Architecture — V0.8

## Boundaries

- Domain/Data: Article classes, Word/WordCell/Vocabulary and persistence/validation services.
- Feature UI: Article view-model builders and Vocabulary view-model/widget code.
- Application: Library, Account, Article and Vocabulary workflows. No PySide6 imports.
- Program UI: left/center/right shell, dialogs, tree, web bridge, resources and generic web runtime.
- WorkspaceCoordinator: only workflows that cross two or more application modules.

## State ownership

- `LibraryApplication`: current Library, Book and Passage path.
- `AccountApplication`: current user/account state.
- `ArticleApplication`: current Article, answers, dirty state and Passage-audio business state.
- `VocabularyApplication`: current Vocabulary and its synchronization lock.
- `WorkspaceCoordinator`: owns no duplicate current state.

## Dependency rules

1. Domain/Data does not import Application or UI.
2. Application does not import PySide6, Feature UI or Program UI.
3. Feature UI may read Domain objects and produce view models.
4. Program UI may use Feature UI and call Application workflows.
5. Article and Vocabulary do not directly depend on each other.
6. Cross-feature interactions (Passage selection → Vocabulary load, selected Passage text → Vocabulary add, Vocabulary show/hide → Passage highlighting) go through the application shell/coordinator.

## Article presentation

The seven Article UI builders produce a generic component tree. The web runtime renders component types rather than dispatching on `exercise.type`. `ArticleBlankUI` creates explicit `blank` components and never produces Passage-audio controls.

## Vocabulary presentation

`WordCell` is UI-free. `WordCellUI` owns word color/bold/layout/speaker presentation. `VocabularyPresenter` owns alternating row presentation. `VocabularyPanel` creates actual Qt widgets.

## Resources

All SVG/PNG resources are under `studybench/program/ui/resources/`. HTML/CSS/JS live separately under `studybench/program/ui/web/`. `resource_paths.py` is the single Python resource locator.
