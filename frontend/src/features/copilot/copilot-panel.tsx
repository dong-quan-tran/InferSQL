import { useState } from "react";
import { useMutation } from "@tanstack/react-query";
import { ApiError } from "../../lib/api/client";
import { runCopilotQuery } from "./api";
import type { CopilotQueryResponse } from "../../types/copilot";

type CopilotPanelProps = {
  onSendToEditor: (sql: string) => void;
};

function getErrorMessage(error: unknown): string {
  if (error instanceof ApiError) {
    const payload = error.payload as
      | { error?: { message?: string } }
      | undefined;

    return payload?.error?.message || error.message;
  }

  if (error instanceof Error) {
    return error.message;
  }

  return "Unknown error";
}

const STARTER_QUESTION =
  "Show me the symbols and closing prices above 100, highest first, limit 5.";

export function CopilotPanel({ onSendToEditor }: CopilotPanelProps) {
  const [question, setQuestion] = useState(STARTER_QUESTION);
  const [execute, setExecute] = useState(false);

  const mutation = useMutation<CopilotQueryResponse, Error>({
    mutationFn: () =>
      runCopilotQuery({
        question: question.trim(),
        execute,
      }),
  });

  const response = mutation.data;
  const candidate = response?.candidate;
  const validation = response?.validation;

  function handleSubmit(event: React.FormEvent<HTMLFormElement>) {
    event.preventDefault();
    mutation.mutate();
  }

  return (
    <div className="grid gap-6 p-6 xl:grid-cols-[minmax(0,1fr)_380px]">
      <div className="space-y-6">
        <section className="rounded-xl border border-slate-800 bg-slate-900/60 p-5">
          <div className="mb-4">
            <h2 className="text-lg font-semibold text-white">Copilot prompt</h2>
            <p className="mt-1 text-sm text-slate-400">
              Ask a natural-language question and generate SQL against the
              registered datasets.
            </p>
          </div>

          <form onSubmit={handleSubmit} className="space-y-4">
            <label className="block">
              <span className="mb-1 block text-sm text-slate-300">
                Question
              </span>
              <textarea
                value={question}
                onChange={(event) => setQuestion(event.target.value)}
                rows={4}
                placeholder="Ask a question about your registered datasets..."
                className="w-full rounded-lg border border-slate-800 bg-slate-950 px-3 py-2 text-sm text-white outline-none transition focus:border-cyan-500"
              />
            </label>

            <label className="flex items-center gap-3 text-sm text-slate-300">
              <input
                type="checkbox"
                checked={execute}
                onChange={(event) => setExecute(event.target.checked)}
                className="h-4 w-4 rounded border-slate-700 bg-slate-950 text-cyan-500"
              />
              Execute generated SQL after validation
            </label>

            <div className="flex flex-wrap gap-3">
              <button
                type="submit"
                disabled={mutation.isPending || !question.trim()}
                className="rounded-md bg-cyan-500 px-4 py-2 text-sm font-medium text-slate-950 transition hover:bg-cyan-400 disabled:cursor-not-allowed disabled:opacity-50"
              >
                {mutation.isPending ? "Generating..." : "Generate SQL"}
              </button>

              {candidate?.sql ? (
                <button
                  type="button"
                  onClick={() => onSendToEditor(candidate.sql)}
                  className="rounded-md border border-slate-700 bg-slate-950 px-4 py-2 text-sm text-slate-200 transition hover:border-cyan-500 hover:text-white"
                >
                  Send to editor
                </button>
              ) : null}
            </div>

            {mutation.isError ? (
              <div className="rounded-lg border border-rose-900 bg-rose-950/40 p-3 text-sm text-rose-200">
                {getErrorMessage(mutation.error)}
              </div>
            ) : null}
          </form>
        </section>

        <section className="rounded-xl border border-slate-800 bg-slate-900/60 p-5">
          <div className="mb-4 flex flex-wrap items-start justify-between gap-3">
            <div>
              <h2 className="text-lg font-semibold text-white">
                Generated SQL
              </h2>
              <p className="mt-1 text-sm text-slate-400">
                SQL candidate returned by the copilot backend.
              </p>
            </div>

            {response ? (
              <div className="flex flex-wrap gap-2 text-xs text-slate-400">
                <span className="rounded-md border border-slate-800 bg-slate-950 px-2 py-1">
                  Provider: {response.provider}
                </span>
                <span className="rounded-md border border-slate-800 bg-slate-950 px-2 py-1">
                  Model: {response.model}
                </span>
                <span className="rounded-md border border-slate-800 bg-slate-950 px-2 py-1">
                  Attempts: {response.attempts}
                </span>
                <span
                  className={`rounded-md border px-2 py-1 ${
                    response.repaired
                      ? "border-amber-800 bg-amber-950/40 text-amber-200"
                      : "border-slate-800 bg-slate-950 text-slate-400"
                  }`}
                >
                  {response.repaired ? "Repaired" : "No repair"}
                </span>
              </div>
            ) : null}
          </div>

          <pre className="max-h-[320px] overflow-auto rounded-lg border border-slate-800 bg-slate-950 p-4 text-xs text-slate-200">
            {candidate?.sql || "-- No SQL generated yet --"}
          </pre>
        </section>

        <section className="rounded-xl border border-slate-800 bg-slate-900/60 p-5">
          <div className="mb-4">
            <h2 className="text-lg font-semibold text-white">Execution</h2>
            <p className="mt-1 text-sm text-slate-400">
              Returned only when execute is enabled and execution succeeds.
            </p>
          </div>

          <pre className="max-h-[320px] overflow-auto rounded-lg border border-slate-800 bg-slate-950 p-4 text-xs text-slate-200">
            {JSON.stringify(response?.execution ?? { message: "No execution result." }, null, 2)}
          </pre>
        </section>
      </div>

      <div className="space-y-6">
        <section className="rounded-xl border border-slate-800 bg-slate-900/60 p-5">
          <div className="mb-4">
            <h2 className="text-lg font-semibold text-white">Assumptions</h2>
            <p className="mt-1 text-sm text-slate-400">
              Schema mappings and interpretation notes from the generated
              candidate.
            </p>
          </div>

          {candidate?.assumptions?.length ? (
            <ul className="space-y-2 text-sm text-slate-300">
              {candidate.assumptions.map((assumption, index) => (
                <li
                  key={`${assumption}-${index}`}
                  className="rounded-lg border border-slate-800 bg-slate-950 p-3"
                >
                  {assumption}
                </li>
              ))}
            </ul>
          ) : (
            <div className="rounded-lg border border-slate-800 bg-slate-950 p-4 text-sm text-slate-400">
              No assumptions returned.
            </div>
          )}
        </section>

        <section className="rounded-xl border border-slate-800 bg-slate-900/60 p-5">
          <div className="mb-4">
            <h2 className="text-lg font-semibold text-white">Validation</h2>
            <p className="mt-1 text-sm text-slate-400">
              Product-level validation result for the generated SQL.
            </p>
          </div>

          {validation ? (
            <div className="space-y-4">
              <div className="grid gap-3 md:grid-cols-2">
                <div className="rounded-lg border border-slate-800 bg-slate-950 p-3">
                  <p className="text-xs uppercase tracking-wide text-slate-500">
                    Valid
                  </p>
                  <p
                    className={`mt-2 text-sm font-medium ${
                      validation.is_valid ? "text-emerald-300" : "text-rose-300"
                    }`}
                  >
                    {validation.is_valid ? "Yes" : "No"}
                  </p>
                </div>

                <div className="rounded-lg border border-slate-800 bg-slate-950 p-3">
                  <p className="text-xs uppercase tracking-wide text-slate-500">
                    Query type
                  </p>
                  <p className="mt-2 text-sm text-slate-200">
                    {validation.query_type || "unknown"}
                  </p>
                </div>
              </div>

              <div className="rounded-lg border border-slate-800 bg-slate-950 p-3">
                <p className="mb-2 text-xs uppercase tracking-wide text-slate-500">
                  Normalized SQL
                </p>
                <pre className="overflow-auto text-xs text-slate-200">
                  {validation.normalized_sql}
                </pre>
              </div>

              <div className="grid gap-3 md:grid-cols-2">
                <div className="rounded-lg border border-slate-800 bg-slate-950 p-3">
                  <p className="mb-2 text-xs uppercase tracking-wide text-slate-500">
                    Tables
                  </p>
                  <div className="flex flex-wrap gap-2">
                    {validation.tables.length ? (
                      validation.tables.map((table) => (
                        <span
                          key={table}
                          className="rounded-md border border-slate-700 px-2 py-1 text-xs text-slate-300"
                        >
                          {table}
                        </span>
                      ))
                    ) : (
                      <span className="text-sm text-slate-500">None</span>
                    )}
                  </div>
                </div>

                <div className="rounded-lg border border-slate-800 bg-slate-950 p-3">
                  <p className="mb-2 text-xs uppercase tracking-wide text-slate-500">
                    Columns
                  </p>
                  <div className="flex flex-wrap gap-2">
                    {validation.columns.length ? (
                      validation.columns.map((column) => (
                        <span
                          key={column}
                          className="rounded-md border border-slate-700 px-2 py-1 text-xs text-slate-300"
                        >
                          {column}
                        </span>
                      ))
                    ) : (
                      <span className="text-sm text-slate-500">None</span>
                    )}
                  </div>
                </div>
              </div>

              <div className="rounded-lg border border-slate-800 bg-slate-950 p-3">
                <p className="mb-2 text-xs uppercase tracking-wide text-slate-500">
                  Shape flags
                </p>
                <div className="flex flex-wrap gap-2 text-xs">
                  <span className="rounded-md border border-slate-700 px-2 py-1 text-slate-300">
                    WHERE: {validation.has_where ? "yes" : "no"}
                  </span>
                  <span className="rounded-md border border-slate-700 px-2 py-1 text-slate-300">
                    GROUP BY: {validation.has_group_by ? "yes" : "no"}
                  </span>
                  <span className="rounded-md border border-slate-700 px-2 py-1 text-slate-300">
                    ORDER BY: {validation.has_order_by ? "yes" : "no"}
                  </span>
                  <span className="rounded-md border border-slate-700 px-2 py-1 text-slate-300">
                    LIMIT: {validation.has_limit ? "yes" : "no"}
                  </span>
                </div>
              </div>

              <div className="rounded-lg border border-slate-800 bg-slate-950 p-3">
                <p className="mb-2 text-xs uppercase tracking-wide text-slate-500">
                  Errors
                </p>
                {validation.errors.length ? (
                  <ul className="space-y-2 text-sm text-rose-300">
                    {validation.errors.map((error, index) => (
                      <li key={`${error}-${index}`}>{error}</li>
                    ))}
                  </ul>
                ) : (
                  <p className="text-sm text-slate-400">No validation errors.</p>
                )}
              </div>
            </div>
          ) : (
            <div className="rounded-lg border border-slate-800 bg-slate-950 p-4 text-sm text-slate-400">
              No validation result yet.
            </div>
          )}
        </section>

        <section className="rounded-xl border border-slate-800 bg-slate-900/60 p-5">
          <div className="mb-4">
            <h2 className="text-lg font-semibold text-white">Repair history</h2>
            <p className="mt-1 text-sm text-slate-400">
              Retry steps recorded when the copilot repairs an invalid
              candidate.
            </p>
          </div>

          {response?.retry_history?.length ? (
            <div className="space-y-4">
              {response.retry_history.map((step) => (
                <div
                  key={step.attempt}
                  className="rounded-lg border border-slate-800 bg-slate-950 p-4"
                >
                  <p className="mb-2 text-sm font-medium text-white">
                    Attempt {step.attempt}
                  </p>

                  <pre className="max-h-[160px] overflow-auto rounded-md border border-slate-800 bg-slate-900 p-3 text-xs text-slate-200">
                    {step.candidate.sql}
                  </pre>

                  <div className="mt-3">
                    <p className="mb-1 text-xs uppercase tracking-wide text-slate-500">
                      Validation
                    </p>
                    <p
                      className={`text-sm ${
                        step.validation.is_valid
                          ? "text-emerald-300"
                          : "text-rose-300"
                      }`}
                    >
                      {step.validation.is_valid ? "Valid" : "Invalid"}
                    </p>

                    {step.validation.errors.length ? (
                      <ul className="mt-2 space-y-1 text-sm text-rose-300">
                        {step.validation.errors.map((error, index) => (
                          <li key={`${error}-${index}`}>{error}</li>
                        ))}
                      </ul>
                    ) : null}
                  </div>
                </div>
              ))}
            </div>
          ) : (
            <div className="rounded-lg border border-slate-800 bg-slate-950 p-4 text-sm text-slate-400">
              No repair history yet.
            </div>
          )}
        </section>
      </div>
    </div>
  );
}