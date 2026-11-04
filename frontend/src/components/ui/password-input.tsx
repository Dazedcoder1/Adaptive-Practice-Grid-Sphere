"use client";

import { Eye, EyeOff } from "lucide-react";
import * as React from "react";
import { Input } from "./input";

export function PasswordInput(props: React.ComponentProps<"input">) {
  const [show, setShow] = React.useState(false);
  return (
    <div className="relative">
      <Input type={show ? "text" : "password"} className="pr-10" {...props} />
      <button
        type="button"
        onClick={() => setShow((s) => !s)}
        className="text-muted-foreground hover:text-foreground absolute inset-y-0 right-0 flex w-10 items-center justify-center"
        aria-label={show ? "Hide password" : "Show password"}
      >
        {show ? <EyeOff className="size-4" /> : <Eye className="size-4" />}
      </button>
    </div>
  );
}
