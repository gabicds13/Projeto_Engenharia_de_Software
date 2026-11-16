import { useEffect, useRef } from "react";

// Apenas endereços de interfaces de usuário divulgados ou documentados
// pelos respectivos grupos. Não incluir Swagger/APIs como se fossem portais.
const EXTERNAL_MODULES = [
  {
    number: 1,
    name: "Projetos e autenticação",
    url: "https://green-river-02e44e810.2.azurestaticapps.net/",
  },
  {
    number: 2,
    name: "Integração com GitHub",
    url: "https://ai-platform-github-service-eduardo-frapb8fbbcd0bfdm.brazilsouth-01.azurewebsites.net/",
  },
  {
    number: 5,
    name: "Curadoria tecnológica",
    url: "https://frontmodulo5-ecaqg8fghzhyeuh2.brazilsouth-01.azurewebsites.net/",
  },
  {
    number: 7,
    name: "MackAI",
    url: "https://mackai-conversas.calmfield-d7c6c49f.brazilsouth.azurecontainerapps.io/",
  },
] as const;

export function ExternalModulesMenu() {
  const detailsRef = useRef<HTMLDetailsElement>(null);

  useEffect(() => {
    const closeOnOutsideClick = (event: PointerEvent) => {
      if (
        detailsRef.current?.open &&
        event.target instanceof Node &&
        !detailsRef.current.contains(event.target)
      ) {
        detailsRef.current.open = false;
      }
    };

    const closeOnEscape = (event: KeyboardEvent) => {
      if (event.key === "Escape" && detailsRef.current?.open) {
        detailsRef.current.open = false;
        detailsRef.current.querySelector("summary")?.focus();
      }
    };

    document.addEventListener("pointerdown", closeOnOutsideClick);
    document.addEventListener("keydown", closeOnEscape);
    return () => {
      document.removeEventListener("pointerdown", closeOnOutsideClick);
      document.removeEventListener("keydown", closeOnEscape);
    };
  }, []);

  return (
    <details ref={detailsRef} className="group relative">
      <summary
        className="flex cursor-pointer list-none items-center gap-2 rounded-md border border-white/30 px-3 py-2 text-sm font-medium text-white hover:bg-primary-hover focus-visible:outline focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-white [&::-webkit-details-marker]:hidden"
      >
        Outros módulos
        <span aria-hidden="true" className="text-xs transition-transform group-open:rotate-180">▾</span>
      </summary>
      <div
        className="absolute right-0 top-full z-50 mt-2 w-72 max-w-[calc(100vw-2rem)] rounded-lg border border-border bg-surface p-2 text-text shadow-xl"
      >
        <p className="px-3 pb-2 pt-1 text-xs font-medium text-text-muted">
          Acessar outros módulos
        </p>
        <ul className="space-y-1">
          {EXTERNAL_MODULES.map((module) => (
            <li key={module.number}>
              <a
                href={module.url}
                target="_blank"
                rel="noopener noreferrer"
                onClick={() => {
                  if (detailsRef.current) detailsRef.current.open = false;
                }}
                className="block rounded-md px-3 py-2 hover:bg-bg focus-visible:outline focus-visible:outline-2 focus-visible:outline-primary"
              >
                <span className="block text-sm font-semibold text-text">
                  Módulo {module.number}
                  <span aria-hidden="true" className="ml-2 text-xs text-text-muted">↗</span>
                </span>
                <span className="block text-xs text-text-muted">{module.name}</span>
              </a>
            </li>
          ))}
        </ul>
        <p className="border-t border-border px-3 pt-2 text-xs text-text-muted">
          Abre em nova aba. Cada módulo pode exigir seu próprio login.
        </p>
      </div>
    </details>
  );
}
