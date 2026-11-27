export interface Module3Project {
  id?: string | number;
  project_id?: string | number;
  name?: string;
  title?: string;
}

export interface Module3Artifact {
  id?: string | number;
  artifact_id?: string | number;
  name?: string;
  filename?: string;
  title?: string;
  artifact_type?: string;
  created_at?: string;
  description?: string;
}

export interface Module3Version {
  id?: string | number;
  version_id?: string | number;
  version_number?: number;
  created_at?: string;
  analysis_id?: string | number;
  latest_analysis_id?: string | number;
  analysis?: { id?: string | number; status?: string } | string;
  analyses?: Array<{ id?: string | number; status?: string } | string>;
}

export interface Module3Analysis {
  id?: string | number;
  status?: string;
  classification?: string;
  classification_reason?: string;
  classification_evidence?: string | string[];
  confidence?: number;
  summary?: string;
  architecture?: string | Record<string, unknown>;
  extracted_metadata?: Record<string, unknown>;
  error_message?: string;
}

/** Aceita listas ou paginação comum sem criar dados fictícios. */
export function module3Items<T>(payload: unknown, ...keys: string[]): T[] {
  if (Array.isArray(payload)) return payload as T[];
  if (payload && typeof payload === "object") {
    const record = payload as Record<string, unknown>;
    for (const key of keys) {
      if (Array.isArray(record[key])) return record[key] as T[];
    }
  }
  throw new Error("O Módulo 3 retornou uma lista em formato inesperado.");
}

export function module3Id(record: { id?: string | number; project_id?: string | number; artifact_id?: string | number; version_id?: string | number }): string {
  return String(record.project_id ?? record.artifact_id ?? record.version_id ?? record.id ?? "");
}

export function module3AnalysisId(version: Module3Version): string {
  const direct = version.analysis_id ?? version.latest_analysis_id;
  if (direct != null) return String(direct);
  if (version.analysis && typeof version.analysis === "object" && version.analysis.id != null)
    return String(version.analysis.id);
  if (typeof version.analysis === "string") return version.analysis;
  const first = version.analyses?.find((item) => typeof item === "string" || (typeof item === "object" && item.id != null));
  return first ? typeof first === "string" ? first : String(first.id) : "";
}
