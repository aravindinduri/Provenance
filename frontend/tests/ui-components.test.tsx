import { describe, it, expect, vi } from "vitest";
import React from "react";
import { render, screen, fireEvent } from "@testing-library/react";
import { Button } from "@/components/ui/button";
import { Badge } from "@/components/ui/badge";
import { Card, CardHeader, CardTitle, CardContent } from "@/components/ui/card";
import { MetricCard } from "@/components/ui/metric-card";
import { ErrorBoundary } from "@/components/error-boundary";

describe("UI Components", () => {
  describe("Button", () => {
    it("renders with default styles and triggers click", () => {
      const handleClick = vi.fn();
      render(<Button onClick={handleClick}>Click Me</Button>);
      const btn = screen.getByRole("button", { name: /click me/i });
      expect(btn).toBeInTheDocument();
      fireEvent.click(btn);
      expect(handleClick).toHaveBeenCalledTimes(1);
    });

    it("renders disabled state and ignores click", () => {
      const handleClick = vi.fn();
      render(<Button disabled onClick={handleClick}>Disabled</Button>);
      const btn = screen.getByRole("button", { name: /disabled/i });
      expect(btn).toBeDisabled();
      fireEvent.click(btn);
      expect(handleClick).not.toHaveBeenCalled();
    });

    it("supports glow and outline variants", () => {
      const { rerender } = render(<Button variant="glow">Glow Button</Button>);
      expect(screen.getByRole("button")).toHaveClass("shadow-glow-primary");

      rerender(<Button variant="outline">Outline</Button>);
      expect(screen.getByRole("button")).toHaveClass("border-input");
    });
  });

  describe("Badge", () => {
    it("renders critical severity variant", () => {
      render(<Badge variant="critical">CRITICAL</Badge>);
      const badge = screen.getByText("CRITICAL");
      expect(badge).toBeInTheDocument();
      expect(badge).toHaveClass("text-red-500");
    });

    it("renders needs-review variant for low-confidence findings", () => {
      render(<Badge variant="needs-review">Needs Human Judgment</Badge>);
      const badge = screen.getByText("Needs Human Judgment");
      expect(badge).toBeInTheDocument();
      expect(badge).toHaveClass("text-purple-600");
    });

    it("renders live and cached source badges", () => {
      const { rerender } = render(<Badge variant="live">LIVE</Badge>);
      expect(screen.getByText("LIVE")).toHaveClass("text-emerald-600");

      rerender(<Badge variant="cached">CACHED</Badge>);
      expect(screen.getByText("CACHED")).toHaveClass("text-slate-600");
    });
  });

  describe("Card", () => {
    it("renders card title and content", () => {
      render(
        <Card>
          <CardHeader>
            <CardTitle>Sanctions Advisory</CardTitle>
          </CardHeader>
          <CardContent>Advisory details here</CardContent>
        </Card>
      );
      expect(screen.getByText("Sanctions Advisory")).toBeInTheDocument();
      expect(screen.getByText("Advisory details here")).toBeInTheDocument();
    });
  });

  describe("MetricCard", () => {
    it("renders metric value and change indicator", () => {
      render(
        <MetricCard
          title="Spend Exposed"
          value="$14.2M"
          subtitle="3 high risk nodes"
          change={{ value: "+$2M", isPositive: false }}
          accent="critical"
        />
      );
      expect(screen.getByText("Spend Exposed")).toBeInTheDocument();
      expect(screen.getByText("$14.2M")).toBeInTheDocument();
      expect(screen.getByText("3 high risk nodes")).toBeInTheDocument();
      expect(screen.getByText("+$2M")).toBeInTheDocument();
    });
  });

  describe("ErrorBoundary", () => {
    it("renders children when no error occurs", () => {
      render(
        <ErrorBoundary>
          <div>Safe Component</div>
        </ErrorBoundary>
      );
      expect(screen.getByText("Safe Component")).toBeInTheDocument();
    });

    it("catches error and displays fallback UI", () => {
      const ThrowingComponent = () => {
        throw new Error("Simulated failure in test");
      };

      // Suppress console.error in test output for intentional throw
      const originalConsoleError = console.error;
      console.error = vi.fn();

      render(
        <ErrorBoundary>
          <ThrowingComponent />
        </ErrorBoundary>
      );

      expect(screen.getByText("Something went wrong")).toBeInTheDocument();
      expect(screen.getByText(/Simulated failure in test/i)).toBeInTheDocument();
      expect(screen.getByRole("button", { name: /try again/i })).toBeInTheDocument();

      console.error = originalConsoleError;
    });
  });
});
