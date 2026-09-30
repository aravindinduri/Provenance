import * as React from "react";
import { cva, type VariantProps } from "class-variance-authority";
import { cn } from "@/lib/utils";

const badgeVariants = cva(
  "inline-flex items-center gap-1.5 rounded-full border px-2.5 py-0.5 text-xs font-semibold transition-colors focus:outline-none focus:ring-2 focus:ring-ring focus:ring-offset-2",
  {
    variants: {
      variant: {
        default:
          "border-transparent bg-primary text-primary-foreground hover:bg-primary/80",
        secondary:
          "border-transparent bg-secondary text-secondary-foreground hover:bg-secondary/80",
        destructive:
          "border-transparent bg-destructive text-destructive-foreground hover:bg-destructive/80",
        outline: "text-foreground border-border/80",
        critical:
          "border-red-500/30 bg-red-500/10 text-red-500 dark:text-red-400 dark:border-red-500/30 dark:bg-red-500/15",
        high:
          "border-orange-500/30 bg-orange-500/10 text-orange-600 dark:text-orange-400 dark:border-orange-500/30 dark:bg-orange-500/15",
        medium:
          "border-amber-500/30 bg-amber-500/10 text-amber-600 dark:text-amber-400 dark:border-amber-500/30 dark:bg-amber-500/15",
        low:
          "border-blue-500/30 bg-blue-500/10 text-blue-600 dark:text-blue-400 dark:border-blue-500/30 dark:bg-blue-500/15",
        "needs-review":
          "border-purple-500/30 bg-purple-500/10 text-purple-600 dark:text-purple-400 dark:border-purple-500/30 dark:bg-purple-500/15",
        live:
          "border-emerald-500/30 bg-emerald-500/10 text-emerald-600 dark:text-emerald-400",
        cached:
          "border-slate-500/30 bg-slate-500/10 text-slate-600 dark:text-slate-400",
      },
    },
    defaultVariants: {
      variant: "default",
    },
  }
);

export interface BadgeProps
  extends React.HTMLAttributes<HTMLDivElement>,
    VariantProps<typeof badgeVariants> {}

function Badge({ className, variant, ...props }: BadgeProps) {
  return (
    <div className={cn(badgeVariants({ variant }), className)} {...props} />
  );
}

export { Badge, badgeVariants };
