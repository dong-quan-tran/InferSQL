type SqlEditorProps = {
    value: string;
    onChange: (value: string) => void;
    onValidate: () => void;
    onPlan: () => void;
    onExecute: () => void;
    isValidating: boolean;
    isPlanning: boolean;
    isExecuting: boolean;
};

function shortcutLabel(label: string) {
    return (
        <span className="rounded-md border border-slate-700 bg-slate-950 px-2 py-1 text-[11px] text-slate-400">
            {label}
        </span>
    );
}

export function SqlEditor({
    value,
    onChange,
    onValidate,
    onPlan,
    onExecute,
    isValidating,
    isPlanning,
    isExecuting,
}: SqlEditorProps) {
    function handleKeyDown(event: React.KeyboardEvent<HTMLTextAreaElement>) {
        if (event.key !== "Enter" || !(event.metaKey || event.ctrlKey)) {
            return;
        }

        event.preventDefault();

        if (event.shiftKey) {
            onPlan();
            return;
        }

        if (event.altKey) {
            onValidate();
            return;
        }

        onExecute();
    }

    return (
        <section className="rounded-xl border border-slate-800 bg-slate-900/60 p-4 sm:p-5">
            <div className="mb-4 flex flex-col gap-4 xl:flex-row xl:items-start xl:justify-between">
                <div className="min-w-0">
                    <h2 className="text-lg font-semibold text-white">SQL editor</h2>
                    <p className="mt-1 text-sm text-slate-400">
                        Write SQL, then run validate, plan, or execute without leaving the keyboard.
                    </p>
                </div>

                <div className="flex flex-wrap gap-2">
                    <button
                        onClick={onValidate}
                        disabled={isValidating || !value.trim()}
                        className="rounded-md border border-slate-700 bg-slate-950 px-3 py-2 text-sm text-slate-200 transition hover:border-cyan-500 hover:text-white disabled:cursor-not-allowed disabled:opacity-50"
                    >
                        {isValidating ? "Validating..." : "Validate"}
                    </button>

                    <button
                        onClick={onPlan}
                        disabled={isPlanning || !value.trim()}
                        className="rounded-md border border-slate-700 bg-slate-950 px-3 py-2 text-sm text-slate-200 transition hover:border-cyan-500 hover:text-white disabled:cursor-not-allowed disabled:opacity-50"
                    >
                        {isPlanning ? "Planning..." : "Plan"}
                    </button>

                    <button
                        onClick={onExecute}
                        disabled={isExecuting || !value.trim()}
                        className="rounded-md bg-cyan-500 px-3 py-2 text-sm font-medium text-slate-950 transition hover:bg-cyan-400 disabled:cursor-not-allowed disabled:opacity-50"
                    >
                        {isExecuting ? "Executing..." : "Execute"}
                    </button>
                </div>
            </div>

            <div className="mb-3 flex flex-wrap gap-2">
                {shortcutLabel("Ctrl/Cmd + Enter → Execute")}
                {shortcutLabel("Ctrl/Cmd + Shift + Enter → Plan")}
                {shortcutLabel("Ctrl/Cmd + Alt + Enter → Validate")}
            </div>

            <textarea
                value={value}
                onChange={(event) => onChange(event.target.value)}
                onKeyDown={handleKeyDown}
                spellCheck={false}
                placeholder="Write a query against a registered dataset..."
                className="min-h-[260px] w-full rounded-lg border border-slate-800 bg-slate-950 p-4 font-mono text-sm text-slate-100 outline-none transition focus:border-cyan-500 sm:min-h-[320px]"
            />
        </section>
    );
}