"use client";
import { useClusterWebSocket } from "@/hooks/useWebSocket";
import { Activity, Wifi, WifiOff } from "lucide-react";

interface NavbarProps {
  title: string;
  subtitle?: string;
}

export default function Navbar({ title, subtitle }: NavbarProps) {
  const { connected, topology } = useClusterWebSocket();

  return (
    <header className="h-14 flex items-center justify-between px-6 border-b border-gray-800 bg-gray-900/60 backdrop-blur shrink-0">
      <div>
        <h1 className="text-base font-semibold text-white">{title}</h1>
        {subtitle && <p className="text-xs text-gray-500">{subtitle}</p>}
      </div>

      <div className="flex items-center gap-4">
        {/* Cluster health pill */}
        {topology && (
          <div className="flex items-center gap-1.5 text-xs text-gray-400">
            <Activity size={13} className="text-green-400" />
            <span>
              <span className="text-green-400 font-semibold">{topology.healthy_nodes}</span>
              /{topology.total_nodes} nodes
            </span>
            {topology.failed_nodes > 0 && (
              <span className="ml-1 px-1.5 py-0.5 bg-red-500/20 text-red-400 rounded text-[10px] font-semibold">
                {topology.failed_nodes} FAILED
              </span>
            )}
          </div>
        )}

        {/* WebSocket status */}
        <div className={`flex items-center gap-1.5 text-xs ${connected ? "text-green-400" : "text-red-400"}`}>
          {connected ? <Wifi size={13} /> : <WifiOff size={13} />}
          <span>{connected ? "Live" : "Reconnecting…"}</span>
          {connected && (
            <span className="w-1.5 h-1.5 rounded-full bg-green-400 animate-ping-slow" />
          )}
        </div>
      </div>
    </header>
  );
}
