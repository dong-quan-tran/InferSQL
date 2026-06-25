type ResponsePanelProps = {
    title: string;
    subtitle?: string;
    data: unknown;
};

export function ResponsePanel({ title, subtitle, data }: ResponsePanelProps) {
    return (
        <section className="rounded-xl border border-slate-800 bg-slate-900/60 p-5">
            <div className="mb-4">
                <h2 className="text-lg font-semibold text-white">{title}</h2>
                {subtitle ? (
                    <p className="mt-1 text-sm text-slate-400">{subtitle}</p>
                ) : null}
            </div>

            <pre className="max-h-[520px] overflow-auto rounded-lg border border-slate-800 bg-slate-950 p-4 text-xs text-slate-200">
                {JSON.stringify(data, null, 2)}
            </pre>
        </section>
    );
}