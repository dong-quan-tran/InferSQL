import type { PropsWithChildren, ReactNode } from "react";

type AppShellProps = PropsWithChildren<{
    sidebar?: ReactNode;
    header?: ReactNode;
}>;

export function AppShell({ sidebar, header, children }: AppShellProps) {
    return (
        <div className="min-h-screen bg-slate-950 text-slate-100">
            <div className="grid min-h-screen grid-cols-1 lg:grid-cols-[260px_minmax(0,1fr)]">
                <aside className="border-r border-slate-800 bg-slate-900/80">
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