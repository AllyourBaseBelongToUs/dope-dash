import * as React from "react";
import { Check } from "lucide-react";

import { cn } from "@/lib/utils";

export interface CheckboxProps
  extends React.InputHTMLAttributes<HTMLInputElement> {}

const Checkbox = React.forwardRef<HTMLInputElement, CheckboxProps>(
  ({ className, ...props }, ref) => {
    return (
      <input
        type="checkbox"
        className={cn(
          "peer h-4 w-4 shrink-0 rounded-sm border border-primary ring-offset-background focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring focus-visible:ring-offset-2 disabled:cursor-not-allowed disabled:opacity-50 appearance-none cursor-pointer checked:bg-primary checked:border-primary transition-colors relative",
          className
        )}
        ref={ref}
        {...props}
        style={{
          ...props.style,
          backgroundImage: 'none',
        }}
      />
    );
  }
);
Checkbox.displayName = "Checkbox";

const CheckboxIndicator = ({ checked }: { checked: boolean }) => {
  return (
    <svg
      className={cn(
        "h-4 w-4 pointer-events-none absolute top-0 left-0 text-primary-foreground",
        !checked && "hidden"
      )}
      viewBox="0 0 24 24"
      fill="none"
      stroke="currentColor"
      strokeWidth="2"
      strokeLinecap="round"
      strokeLinejoin="round"
    >
      <polyline points="20 6 9 17 4 12" />
    </svg>
  );
};

export { Checkbox, CheckboxIndicator };
