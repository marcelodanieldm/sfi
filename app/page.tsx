"use client";

import { useState } from "react";
import { Sidebar } from "@/components/sidebar";
import { TouristApp } from "@/components/tourist-app";
import { MerchantDashboard } from "@/components/merchant-dashboard";

export type WeatherMode = "sunny" | "rainy";
export type AppMode = "tourist" | "merchant";

export default function Home() {
  const [appMode, setAppMode] = useState<AppMode>("tourist");
  const [weather, setWeather] = useState<WeatherMode>("sunny");
  const [packagePublished, setPackagePublished] = useState(false);

  return (
    <div className="flex min-h-screen">
      <Sidebar appMode={appMode} setAppMode={setAppMode} />
      <main className="flex-1 ml-64">
        {appMode === "tourist" ? (
          <TouristApp 
            weather={weather} 
            setWeather={setWeather}
            packagePublished={packagePublished}
          />
        ) : (
          <MerchantDashboard
            weather={weather}
            packagePublished={packagePublished}
            setPackagePublished={setPackagePublished}
          />
        )}
      </main>
    </div>
  );
}
