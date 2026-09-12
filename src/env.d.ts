type ThemeChoice = "light" | "dark" | "system";

interface Window {
  theme?: {
    /** What the reader picked. "system" means they have not picked. */
    readonly choice: ThemeChoice;
    /** What that resolves to right now. */
    resolved: () => "light" | "dark";
    choose: (choice: ThemeChoice) => void;
    reflect: (choice?: ThemeChoice) => void;
  };
}
