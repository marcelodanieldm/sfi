"use client";

import { MapPin, Users, LayoutDashboard, Compass } from "lucide-react";
import type { AppMode } from "@/app/page";

interface SidebarProps {
  appMode: AppMode;
  setAppMode: (mode: AppMode) => void;
}

export function Sidebar({ appMode, setAppMode }: SidebarProps) {
  return (
    <aside className="fixed left-0 top-0 h-full w-64 bg-primary text-primary-foreground flex flex-col">
      <div className="p-6 border-b border-primary-foreground/20">
        <div className="flex items-center gap-3">
          <div className="w-10 h-10 rounded-lg bg-primary-foreground/20 flex items-center justify-center">
            <MapPin className="w-6 h-6" />
          </div>
          <div>
            <h1 className="font-bold text-lg">DestinoIA</h1>
            <p className="text-xs text-primary-foreground/70">Turismo Inteligente</p>
          </div>
        </div>
      </div>

      <nav className="flex-1 p-4">
        <p className="text-xs uppercase tracking-wider text-primary-foreground/50 mb-4 px-3">
          Interfaz
        </p>
        <ul className="space-y-2">
          <li>
            <button
              onClick={() => setAppMode("tourist")}
              className={`w-full flex items-center gap-3 px-3 py-3 rounded-lg transition-colors ${
                appMode === "tourist"
                  ? "bg-primary-foreground/20 text-primary-foreground"
                  : "text-primary-foreground/70 hover:bg-primary-foreground/10 hover:text-primary-foreground"
              }`}
            >
              <Compass className="w-5 h-5" />
              <div className="text-left">
                <span className="block font-medium">App Turista</span>
                <span className="text-xs text-primary-foreground/60">Experiencia B2C</span>
              </div>
            </button>
          </li>
          <li>
            <button
              onClick={() => setAppMode("merchant")}
              className={`w-full flex items-center gap-3 px-3 py-3 rounded-lg transition-colors ${
                appMode === "merchant"
                  ? "bg-primary-foreground/20 text-primary-foreground"
                  : "text-primary-foreground/70 hover:bg-primary-foreground/10 hover:text-primary-foreground"
              }`}
            >
              <LayoutDashboard className="w-5 h-5" />
              <div className="text-left">
                <span className="block font-medium">Panel Comerciante</span>
                <span className="text-xs text-primary-foreground/60">Dashboard B2B</span>
              </div>
            </button>
          </li>
        </ul>
      </nav>

      <div className="p-4 border-t border-primary-foreground/20">
        <div className="flex items-center gap-3 px-3 py-2">
          <div className="w-8 h-8 rounded-full bg-accent flex items-center justify-center">
            <Users className="w-4 h-4 text-accent-foreground" />
          </div>
          <div>
            <p className="text-sm font-medium">Municipio Demo</p>
            <p className="text-xs text-primary-foreground/60">Ecosistema Colaborativo</p>
          </div>
        </div>
      </div>
    </aside>
  );
}
