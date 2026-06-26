import { useState } from "react";
import type { PropsWithChildren, ReactNode } from "react";

type AppShellProps = PropsWithChildren<{
    sidebar?: ReactNode;
    header?: ReactNode;
}>;

export function AppShell({ sidebar, header, children }: AppShellProps) {
    const [sidebarOpen, setSidebarOpen] = useState(false);

    return (
        <div className="min-h-screen bg-slate-950 text-slate-100">
            <div className="lg:hidden">
                <div className="flex items-center justify-between border-b border-slate-800 bg-slate-900/90 px-4 py-3">
                    <div>
                        <p className="text-xs font-semibold uppercase tracking-[0.2em] text-cyan-400">
                            InferSQL
                        </p>
                        <p className="text-sm text-slate-300">Frontend demo</p>
                    </div>

                    <button
                        type="button"
                        onClick={() => setSidebarOpen((open) => !open)}
                        className="rounded-md border border-slate-700 bg-slate-950 px-3 py-2 text-sm text-slate-200 transition hover:border-cyan-500 hover:text-white"
                        aria-expanded={sidebarOpen}
                        aria-controls="mobile-sidebar"
                    >
                        {sidebarOpen ? "Close" : "Menu"}
                    </button>
                </div>

                {sidebarOpen ? (
                    <aside
                        id="mobile-sidebar"
                        className="border-b border-slate-800 bg-slate-900/95"
                    >
                        <div className="flex flex-col">
                            <div onClick={() => setSidebarOpen(false)}>{sidebar}</div>
                        </div>
                    </aside>
                ) : null}
            </div>

            <div className="grid min-h-screen grid-cols-1 lg:grid-cols-[260px_minmax(0,1fr)]">
                <aside className="hidden border-r border-slate-800 bg-slate-900/80 lg:block">
                    <div className="flex h-full flex-col">{sidebar}</div>
                </aside>

                <div className="flex min-w-0 flex-col">
                    <header className="border-b border-slate-800 bg-slate-900/60">
                        {header}
                    </header>

                    <main className="min-h-0 flex-1">{children}</main>
                </div>
            </div>
        </div>
    );
}