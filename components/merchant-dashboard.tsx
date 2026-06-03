"use client";

import { useState, useEffect } from "react";
import {
  Activity,
  TrendingUp,
  Users,
  CloudRain,
  Sun,
  Sparkles,
  CheckCircle2,
  Music,
  Heart,
  Utensils,
  Building2,
  ArrowRight,
} from "lucide-react";
import type { WeatherMode } from "@/app/page";

interface MerchantDashboardProps {
  weather: WeatherMode;
  packagePublished: boolean;
  setPackagePublished: (published: boolean) => void;
}

type HealthStatus = "green" | "yellow" | "red";

export function MerchantDashboard({
  weather,
  packagePublished,
  setPackagePublished,
}: MerchantDashboardProps) {
  const [showSuccess, setShowSuccess] = useState(false);
  const [healthStatus, setHealthStatus] = useState<HealthStatus>("yellow");
  const [occupancy, setOccupancy] = useState(65);

  // Simulate real-time data updates
  useEffect(() => {
    const interval = setInterval(() => {
      const newOccupancy = Math.floor(Math.random() * 30) + 50;
      setOccupancy(newOccupancy);
      if (newOccupancy > 80) setHealthStatus("red");
      else if (newOccupancy > 60) setHealthStatus("yellow");
      else setHealthStatus("green");
    }, 5000);
    return () => clearInterval(interval);
  }, []);

  const handlePublishPackage = () => {
    setShowSuccess(true);
    setPackagePublished(true);
    setTimeout(() => setShowSuccess(false), 3000);
  };

  const healthConfig = {
    green: {
      color: "bg-accent",
      textColor: "text-accent",
      bgLight: "bg-accent/10",
      borderColor: "border-accent/30",
      label: "Flujo Normal",
      description: "El destino tiene capacidad disponible",
    },
    yellow: {
      color: "bg-warning",
      textColor: "text-warning",
      bgLight: "bg-warning/10",
      borderColor: "border-warning/30",
      label: "Flujo Moderado",
      description: "Demanda creciente, considere ofertas valle",
    },
    red: {
      color: "bg-destructive",
      textColor: "text-destructive",
      bgLight: "bg-destructive/10",
      borderColor: "border-destructive/30",
      label: "Alta Ocupación",
      description: "Capacidad limitada, active precios dinámicos",
    },
  };

  const currentHealth = healthConfig[healthStatus];

  const stats = [
    {
      label: "Visitantes Hoy",
      value: "1,234",
      change: "+12%",
      icon: Users,
      color: "text-primary",
    },
    {
      label: "Reservas Activas",
      value: "89",
      change: "+8%",
      icon: Activity,
      color: "text-accent",
    },
    {
      label: "Paquetes Vendidos",
      value: "45",
      change: "+23%",
      icon: TrendingUp,
      color: "text-warning",
    },
  ];

  return (
    <div className="p-8 bg-background min-h-screen">
      {/* Success Toast */}
      {showSuccess && (
        <div className="fixed top-4 right-4 z-50 animate-in slide-in-from-top-2 fade-in duration-300">
          <div className="bg-accent text-accent-foreground px-6 py-4 rounded-xl shadow-lg flex items-center gap-3">
            <CheckCircle2 className="w-6 h-6" />
            <div>
              <p className="font-semibold">Paquete Publicado Exitosamente</p>
              <p className="text-sm text-accent-foreground/80">
                Ya está visible en la App Turista
              </p>
            </div>
          </div>
        </div>
      )}

      {/* Header */}
      <header className="mb-8">
        <h1 className="text-3xl font-bold text-foreground mb-2">
          Panel de Control Predictivo
        </h1>
        <p className="text-muted-foreground">
          Gestiona tu negocio con inteligencia artificial y datos en tiempo real
        </p>
      </header>

      {/* Stats Row */}
      <div className="grid grid-cols-1 md:grid-cols-3 gap-4 mb-8">
        {stats.map((stat) => {
          const Icon = stat.icon;
          return (
            <div
              key={stat.label}
              className="bg-card rounded-xl p-5 shadow-sm border"
            >
              <div className="flex items-center justify-between mb-3">
                <span className="text-sm text-muted-foreground">{stat.label}</span>
                <Icon className={`w-5 h-5 ${stat.color}`} />
              </div>
              <div className="flex items-baseline gap-2">
                <span className="text-3xl font-bold text-card-foreground">
                  {stat.value}
                </span>
                <span className="text-sm text-accent font-medium">{stat.change}</span>
              </div>
            </div>
          );
        })}
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-3 gap-8">
        <div className="lg:col-span-2 space-y-8">
          {/* AI Predictive Alert Box - STAR SECTION */}
          <section>
            <h2 className="text-xl font-semibold text-foreground mb-4 flex items-center gap-2">
              <Sparkles className="w-5 h-5 text-primary" />
              Alerta Predictiva IA
            </h2>
            <div className="bg-gradient-to-br from-primary/5 via-card to-accent/5 rounded-xl p-6 shadow-sm border-2 border-primary/20">
              <div className="flex items-start gap-4">
                <div className="w-14 h-14 rounded-xl bg-primary/10 flex items-center justify-center flex-shrink-0">
                  <Sparkles className="w-7 h-7 text-primary" />
                </div>
                <div className="flex-1">
                  <div className="flex items-center gap-2 mb-2">
                    <span className="text-xs bg-primary/10 text-primary px-2 py-1 rounded-full font-medium">
                      Predicción Activa
                    </span>
                    <span className="text-xs text-muted-foreground">
                      Actualizado hace 5 min
                    </span>
                  </div>
                  <h3 className="text-lg font-semibold text-card-foreground mb-3">
                    Insight de IA
                  </h3>
                  <div className="bg-card/80 rounded-lg p-4 border">
                    <p className="text-card-foreground leading-relaxed">
                      Se espera un <strong className="text-primary">aumento del 35% en parejas</strong> este viernes
                      debido al <span className="inline-flex items-center gap-1"><Music className="w-4 h-4 text-primary" /> concierto en vivo local</span>,
                      combinado con una <span className="inline-flex items-center gap-1">
                        {weather === "rainy" ? (
                          <CloudRain className="w-4 h-4 text-primary" />
                        ) : (
                          <Sun className="w-4 h-4 text-warning" />
                        )}
                        probabilidad del 70% de lluvia por la tarde
                      </span>.
                    </p>
                    <div className="mt-4 p-3 bg-accent/10 rounded-lg border border-accent/20">
                      <p className="text-sm font-medium text-accent flex items-center gap-2">
                        <Heart className="w-4 h-4" />
                        Sugerencia:
                      </p>
                      <p className="text-sm text-card-foreground mt-1">
                        Combine su horario de cena temprana con el tour del museo de al lado.
                        Paquete sugerido: <strong>Cena romántica + Visita guiada museo = $75</strong> (ahorro del 20%)
                      </p>
                    </div>
                  </div>

                  {/* Unified Action Button */}
                  <button
                    onClick={handlePublishPackage}
                    disabled={packagePublished}
                    className={`mt-6 w-full py-4 rounded-xl font-semibold text-lg transition-all flex items-center justify-center gap-3 ${
                      packagePublished
                        ? "bg-accent/20 text-accent cursor-not-allowed"
                        : "bg-primary text-primary-foreground hover:bg-primary/90 shadow-lg hover:shadow-xl"
                    }`}
                  >
                    {packagePublished ? (
                      <>
                        <CheckCircle2 className="w-5 h-5" />
                        Paquete Cooperativo Publicado
                      </>
                    ) : (
                      <>
                        Aceptar sugerencia de precio y publicar paquete cooperativo
                        <ArrowRight className="w-5 h-5" />
                      </>
                    )}
                  </button>
                </div>
              </div>
            </div>
          </section>

          {/* Cooperative Partners */}
          <section>
            <h2 className="text-xl font-semibold text-foreground mb-4">
              Socios del Paquete Sugerido
            </h2>
            <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
              <div className="bg-card rounded-xl p-5 shadow-sm border">
                <div className="flex items-center gap-3 mb-3">
                  <div className="w-10 h-10 rounded-lg bg-accent/10 flex items-center justify-center">
                    <Utensils className="w-5 h-5 text-accent" />
                  </div>
                  <div>
                    <h3 className="font-semibold text-card-foreground">Restaurante La Tradición</h3>
                    <p className="text-xs text-muted-foreground">Tu negocio</p>
                  </div>
                </div>
                <div className="space-y-2">
                  <div className="flex justify-between text-sm">
                    <span className="text-muted-foreground">Horario ofrecido</span>
                    <span className="text-card-foreground">18:00 - 20:00</span>
                  </div>
                  <div className="flex justify-between text-sm">
                    <span className="text-muted-foreground">Precio base</span>
                    <span className="text-card-foreground">$45/persona</span>
                  </div>
                  <div className="flex justify-between text-sm">
                    <span className="text-muted-foreground">Precio en paquete</span>
                    <span className="text-accent font-medium">$40/persona</span>
                  </div>
                </div>
              </div>

              <div className="bg-card rounded-xl p-5 shadow-sm border">
                <div className="flex items-center gap-3 mb-3">
                  <div className="w-10 h-10 rounded-lg bg-primary/10 flex items-center justify-center">
                    <Building2 className="w-5 h-5 text-primary" />
                  </div>
                  <div>
                    <h3 className="font-semibold text-card-foreground">Museo de Arte Regional</h3>
                    <p className="text-xs text-muted-foreground">Socio cooperativo</p>
                  </div>
                </div>
                <div className="space-y-2">
                  <div className="flex justify-between text-sm">
                    <span className="text-muted-foreground">Horario ofrecido</span>
                    <span className="text-card-foreground">16:00 - 18:00</span>
                  </div>
                  <div className="flex justify-between text-sm">
                    <span className="text-muted-foreground">Precio base</span>
                    <span className="text-card-foreground">$20/persona</span>
                  </div>
                  <div className="flex justify-between text-sm">
                    <span className="text-muted-foreground">Precio en paquete</span>
                    <span className="text-accent font-medium">$35/2 personas</span>
                  </div>
                </div>
              </div>
            </div>
          </section>
        </div>

        {/* Right Column - Health Indicator */}
        <div className="space-y-6">
          {/* Destination Health Indicator */}
          <div className="bg-card rounded-xl p-6 shadow-sm border">
            <h2 className="text-lg font-semibold text-card-foreground mb-4">
              Indicador de Salud del Destino
            </h2>
            <div className="flex flex-col items-center">
              {/* Traffic Light */}
              <div className="bg-secondary rounded-2xl p-4 mb-4">
                <div className="flex flex-col gap-3">
                  <div
                    className={`w-16 h-16 rounded-full transition-all duration-500 ${
                      healthStatus === "red"
                        ? "bg-destructive shadow-lg shadow-destructive/50"
                        : "bg-destructive/20"
                    }`}
                  />
                  <div
                    className={`w-16 h-16 rounded-full transition-all duration-500 ${
                      healthStatus === "yellow"
                        ? "bg-warning shadow-lg shadow-warning/50"
                        : "bg-warning/20"
                    }`}
                  />
                  <div
                    className={`w-16 h-16 rounded-full transition-all duration-500 ${
                      healthStatus === "green"
                        ? "bg-accent shadow-lg shadow-accent/50"
                        : "bg-accent/20"
                    }`}
                  />
                </div>
              </div>

              <div className={`text-center p-4 rounded-lg ${currentHealth.bgLight} border ${currentHealth.borderColor}`}>
                <p className={`font-semibold text-lg ${currentHealth.textColor}`}>
                  {currentHealth.label}
                </p>
                <p className="text-sm text-muted-foreground mt-1">
                  {currentHealth.description}
                </p>
              </div>

              <div className="w-full mt-6">
                <div className="flex justify-between text-sm mb-2">
                  <span className="text-muted-foreground">Ocupación actual</span>
                  <span className={`font-medium ${currentHealth.textColor}`}>{occupancy}%</span>
                </div>
                <div className="h-3 bg-secondary rounded-full overflow-hidden">
                  <div
                    className={`h-full ${currentHealth.color} transition-all duration-500`}
                    style={{ width: `${occupancy}%` }}
                  />
                </div>
              </div>
            </div>
          </div>

          {/* Weather Context */}
          <div className="bg-card rounded-xl p-6 shadow-sm border">
            <h2 className="text-lg font-semibold text-card-foreground mb-4">
              Contexto Climático
            </h2>
            <div className="flex items-center gap-4">
              <div
                className={`w-14 h-14 rounded-xl flex items-center justify-center ${
                  weather === "rainy" ? "bg-primary/10" : "bg-warning/10"
                }`}
              >
                {weather === "rainy" ? (
                  <CloudRain className="w-7 h-7 text-primary" />
                ) : (
                  <Sun className="w-7 h-7 text-warning" />
                )}
              </div>
              <div>
                <p className="font-semibold text-card-foreground">
                  {weather === "rainy" ? "Lluvia Prevista" : "Día Soleado"}
                </p>
                <p className="text-sm text-muted-foreground">
                  {weather === "rainy"
                    ? "Active ofertas bajo techo"
                    : "Promocione actividades al aire libre"}
                </p>
              </div>
            </div>
          </div>

          {/* Quick Actions */}
          <div className="bg-card rounded-xl p-6 shadow-sm border">
            <h2 className="text-lg font-semibold text-card-foreground mb-4">
              Acciones Rápidas
            </h2>
            <div className="space-y-3">
              <button className="w-full py-3 px-4 bg-secondary text-secondary-foreground rounded-lg text-sm font-medium hover:bg-secondary/80 transition-colors text-left">
                Ver historial de paquetes
              </button>
              <button className="w-full py-3 px-4 bg-secondary text-secondary-foreground rounded-lg text-sm font-medium hover:bg-secondary/80 transition-colors text-left">
                Configurar precios dinámicos
              </button>
              <button className="w-full py-3 px-4 bg-secondary text-secondary-foreground rounded-lg text-sm font-medium hover:bg-secondary/80 transition-colors text-left">
                Buscar nuevos socios
              </button>
            </div>
          </div>
        </div>
      </div>
    </div>
  );
}
