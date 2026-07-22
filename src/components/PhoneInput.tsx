import * as React from "react";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { cn } from "@/lib/utils";

// Aplica máscara (99) 99999-9999
function maskPhone(value: string) {
  const digits = value.replace(/\D/g, "").slice(0, 11);
  const p1 = digits.slice(0, 2);
  const p2 = digits.slice(2, 7);
  const p3 = digits.slice(7, 11);
  if (digits.length <= 2) return p1 ? `(${p1}` : "";
  if (digits.length <= 7) return `(${p1}) ${p2}`;
  return `(${p1}) ${p2}-${p3}`;
}

export function isValidPhone(value: string) {
  return value.replace(/\D/g, "").length === 11;
}

interface Props extends Omit<React.InputHTMLAttributes<HTMLInputElement>, "onChange" | "value"> {
  label?: string;
  error?: string;
  value: string;
  onChange: (v: string) => void;
}

export function PhoneInput({ label, error, value, onChange, className, id, ...props }: Props) {
  const inputId = id ?? "phone-input";
  return (
    <div className="space-y-1.5">
      {label && (
        <Label htmlFor={inputId}>
          {label}
        </Label>
      )}
      <Input
        id={inputId}
        inputMode="tel"
        placeholder="(11) 99999-9999"
        value={value}
        onChange={(e) => onChange(maskPhone(e.target.value))}
        className={cn(error && "border-destructive focus-visible:ring-destructive", className)}
        aria-invalid={!!error}
        {...props}
      />
      {error && <p className="text-xs text-destructive">{error}</p>}
    </div>
  );
}
