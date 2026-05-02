import { useEffect, useState } from "react";
import { Server } from "lucide-react";
import { fetchMeta, fetchCacheStats, type ApiMeta, type CacheStats } from "../api";

export default function ServerStatus() {
  const [meta, setMeta] = useState<ApiMeta | null>(null);
  const [cache, setCache] = useState<CacheStats | null>(null);
  const [error, setError] = useState(false);

  useEffect(() => {
    Promise.all([fetchMeta(), fetchCacheStats()])
      .then(([m, c]) => {
        setMeta(m);
        setCache(c);
      })
      .catch(() => setError(true));
  }, []);

  if (error || !meta) return null;

  return (
    <div className="flex flex-wrap items-center gap-x-4 gap-y-1 text-[10px] text-muted-foreground mt-5 px-1">
      <span className="inline-flex items-center gap-1.5">
        <Server className="w-3 h-3" />
        <span className="font-mono">v{meta.version}</span>
        <span className="font-mono">py{meta.python}</span>
      </span>
      <span className="inline-flex items-center gap-1.5">
        <span
          className={`w-1.5 h-1.5 rounded-full ${
            cache && cache.hit_rate > 0
              ? "bg-emerald-400"
              : "bg-muted"
          }`}
        />
        cache <span className="font-mono">{cache ? `${cache.hits}h/${cache.misses}m` : "—"}</span>
        {cache && cache.hit_rate > 0 && (
          <span className="font-mono text-emerald-400">
            {(cache.hit_rate * 100).toFixed(1)}%
          </span>
        )}
      </span>
    </div>
  );
}