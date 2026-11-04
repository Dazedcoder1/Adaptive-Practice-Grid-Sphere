"use client";

import { useMutation, useQueryClient } from "@tanstack/react-query";
import { useRouter } from "next/navigation";
import { toast } from "sonner";
import { ApiError } from "@/services/api";
import { learning, type StartSession } from "./api";

/** Starts a practice session and opens the player. */
export function useStartSession() {
  const router = useRouter();
  const qc = useQueryClient();
  return useMutation({
    mutationFn: (body: StartSession) => learning.startSession(body),
    onSuccess: (s) => {
      void qc.invalidateQueries({ queryKey: ["sessions"] });
      router.push(`/practice/${s.id}`);
    },
    onError: (e) => toast.error(e instanceof ApiError ? e.message : "Couldn't start the session."),
  });
}
