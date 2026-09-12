// Three states, not two. "System" is the absence of a choice, so it is stored
// as the absence of a key: nothing here ever writes the resolved value back,
// which is what used to pin a reader to light or dark the first time their OS
// switched over.

const THEME = "theme";

type Choice = "light" | "dark" | "system";
type Resolved = "light" | "dark";

const media = window.matchMedia("(prefers-color-scheme: dark)");

function storedChoice(): Choice {
  const raw = localStorage.getItem(THEME);
  return raw === "light" || raw === "dark" ? raw : "system";
}

function resolve(choice: Choice): Resolved {
  if (choice !== "system") return choice;
  return media.matches ? "dark" : "light";
}

function reflect(choice: Choice = storedChoice()): void {
  document.firstElementChild?.setAttribute("data-theme", resolve(choice));

  for (const option of document.querySelectorAll<HTMLElement>(
    "[data-theme-choice]"
  )) {
    option.setAttribute(
      "aria-checked",
      String(option.dataset.themeChoice === choice)
    );
  }

  // Android colours its navigation bar from this, so it tracks the pane.
  if (document.body) {
    document
      .querySelector("meta[name='theme-color']")
      ?.setAttribute(
        "content",
        getComputedStyle(document.body).backgroundColor
      );
  }
}

function choose(choice: Choice): void {
  if (choice === "system") localStorage.removeItem(THEME);
  else localStorage.setItem(THEME, choice);
  reflect(choice);
}

window.theme = {
  get choice() {
    return storedChoice();
  },
  resolved: () => resolve(storedChoice()),
  choose,
  reflect,
};

function bindControls(): void {
  reflect();

  for (const option of document.querySelectorAll<HTMLElement>(
    "[data-theme-choice]"
  )) {
    option.addEventListener("click", () => {
      const choice = option.dataset.themeChoice;
      if (choice === "light" || choice === "dark" || choice === "system") {
        choose(choice);
      }
    });
  }
}

bindControls();

// Re-bind after a view transition: the buttons are new elements, the listeners
// on them are not.
document.addEventListener("astro:after-swap", bindControls);

// Carry the resolved colour across a transition so Android's navigation bar
// does not flash.
document.addEventListener("astro:before-swap", event => {
  const colour = document
    .querySelector("meta[name='theme-color']")
    ?.getAttribute("content");
  if (colour) {
    (event as unknown as { newDocument: Document }).newDocument
      .querySelector("meta[name='theme-color']")
      ?.setAttribute("content", colour);
  }
});

// Follow the system only while the reader has not chosen. This listener must
// never write to storage.
media.addEventListener("change", () => {
  if (storedChoice() === "system") reflect("system");
});
