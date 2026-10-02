import "@testing-library/jest-dom";

// Mock HTMLCanvasElement.prototype.getContext for jsdom testing
if (typeof window !== "undefined") {
  HTMLCanvasElement.prototype.getContext = () => null;
}

