import type { ReactNode } from "react";
import clsx from "clsx";

export function Panel({
  title,
  right,
  children,
  className,
  bodyClassName,
  id,
}: {
  title: string;
  right?: ReactNode;
  children: ReactNode;
  className?: string;
  bodyClassName?: string;
  id?: string;
}) {
  return (
    <section
      id={id}
      className={clsx(
        "flex flex-col rounded-sm border border-term-border bg-term-panel/60 overflow-hidden",
        className
      )}
    >
      <header className="flex items-center justify-between border-b border-term-border bg-term-panel-head px-3 py-1.5 shrink-0">
        <h2 className="label-xs text-[10px]">{title}</h2>
        {right}
      </header>
      <div className={clsx("flex-1 min-h-0", bodyClassName)}>{children}</div>
    </section>
  );
}
