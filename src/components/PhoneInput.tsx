import * as React from "react";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { cn } from "@/lib/utils";

// Aplica máscara (99) 99999-9999 (celular) ou (99) 9999-9999 (fixo).
// Celular sempre começa com 9 logo depois do DDD — é o único jeito de saber
// qual dos dois formatos usar enquanto a pessoa ainda está digitando.
function maskPhone(value: string) {
  const raw = value.replace(/\D/g, "");
  const ddd = raw.slice(0, 2);
  const isMobile = raw[2] === "9";
  const maxTotal = isMobile ? 11 : 10;
  const digits = raw.slice(0, maxTotal);
  const local = digits.slice(2);
  const splitAt = isMobile ? 5 : 4;

  if (digits.length <= 2) return ddd ? `(${ddd}` : "";
  if (local.length <= splitAt) return `(${ddd}) ${local}`;
  return `(${ddd}) ${local.slice(0, splitAt)}-${local.slice(splitAt)}`;
}

export function isValidPhone(value: string) {
  const digits = value.replace(/\D/g, "");
  return digits.length === 10 || digits.length === 11;
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
