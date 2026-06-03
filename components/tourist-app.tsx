"use client";

import { useState } from "react";
import {
  Sun,
  CloudRain,
  Clock,
  Utensils,
  Mountain,
  Ticket,
  ShoppingCart,
  Sparkles,
  Building2,
  Palette,
  Wine,
  Timer,
} from "lucide-react";
import type { WeatherMode } from "@/app/page";

interface TouristAppProps {
  weather: WeatherMode;
  setWeather: (weather: WeatherMode) => void;
  packagePublished: boolean;
}

interface CartItem {
  id: string;
  name: string;
  price: number;
  type: "activity" | "restaurant" | "excursion";
}

export function TouristApp({ weather, setWeather, packagePublished }: TouristAppProps) {
  const [selectedTimeSlot, setSelectedTimeSlot] = useState<string | null>(null);
  const [cart, setCart] = useState<CartItem[]>([]);

  const timeSlots = [
    { time: "09:00", price: 15, isPeak: false },
    { time: "10:00", price: 18, isPeak: false },
    { time: "11:00", price: 25, isPeak: true },
    { time: "12:00", price: 28, isPeak: true },
    { time: "13:00", price: 28, isPeak: true },
    { time: "14:00", price: 25, isPeak: true },
    { time: "15:00", price: 18, isPeak: false },
    { time: "16:00", price: 15, isPeak: false },
    { time: "17:00", price: 12, isPeak: false },
  ];

  const sunnyActivities = [
    { id: "beach", name: "Tour Playa Dorada", price: 45, icon: Sun, discount: 0 },
    { id: "hiking", name: "Senderismo Montaña", price: 35, icon: Mountain, discount: 10 },
    { id: "winery", name: "Visita Bodega Local", price: 40, icon: Wine, discount: 0 },
  ];

  const rainyActivities = [
    { id: "museum", name: "Museo de Arte Regional", price: 20, icon: Building2, discount: 40 },
    { id: "gallery", name: "Galería de Artesanías", price: 15, icon: Palette, discount: 35 },
    { id: "winery", name: "Cata de Vinos Premium", price: 55, icon: Wine, discount: 25 },
  ];

  const activities = weather === "sunny" ? sunnyActivities : rainyActivities;

  const flashDeals = [
    { id: "kayak", name: "Kayak en Río Cristal", originalPrice: 80, price: 45, spotsLeft: 3, hoursLeft: 12 },
    { id: "paragliding", name: "Parapente al Atardecer", originalPrice: 120, price: 75, spotsLeft: 2, hoursLeft: 24 },
    { id: "cave", name: "Exploración Cuevas", originalPrice: 50, price: 30, spotsLeft: 5, hoursLeft: 36 },
  ];

  const addToCart = (item: CartItem) => {
    if (!cart.find((c) => c.id === item.id)) {
      setCart([...cart, item]);
    }
  };

  const removeFromCart = (id: string) => {
    setCart(cart.filter((c) => c.id !== id));
  };

  const hasActivityAndRestaurant =
    cart.some((c) => c.type === "activity" || c.type === "excursion") &&
    cart.some((c) => c.type === "restaurant");

  const subtotal = cart.reduce((sum, item) => sum + item.price, 0);
  const packageDiscount = hasActivityAndRestaurant ? Math.round(subtotal * 0.15) : 0;
  const total = subtotal - packageDiscount;

  return (
    <div className="p-8 bg-background min-h-screen">
      {/* Header */}
      <header className="mb-8">
        <h1 className="text-3xl font-bold text-foreground mb-2">
          Descubre tu Destino Perfecto
        </h1>
        <p className="text-muted-foreground">
          Experiencias personalizadas con precios dinámicos en tiempo real
        </p>
      </header>

      {/* Weather Toggle - Contextual Hero Section */}
      <section className="mb-8">
        <div className="bg-card rounded-xl p-6 shadow-sm border">
          <div className="flex items-center justify-between mb-4">
            <div>
              <h2 className="text-lg font-semibold text-card-foreground">Simulador de Clima</h2>
              <p className="text-sm text-muted-foreground">
                Cambia el clima para ver ofertas contextuales
              </p>
            </div>
            <div className="flex items-center gap-2 bg-secondary rounded-full p-1">
              <button
                onClick={() => setWeather("sunny")}
                className={`flex items-center gap-2 px-4 py-2 rounded-full transition-all ${
                  weather === "sunny"
                    ? "bg-warning text-warning-foreground shadow-sm"
                    : "text-muted-foreground hover:text-foreground"
                }`}
              >
                <Sun className="w-4 h-4" />
                <span className="text-sm font-medium">Soleado</span>
              </button>
              <button
                onClick={() => setWeather("rainy")}
                className={`flex items-center gap-2 px-4 py-2 rounded-full transition-all ${
                  weather === "rainy"
                    ? "bg-primary text-primary-foreground shadow-sm"
                    : "text-muted-foreground hover:text-foreground"
                }`}
              >
                <CloudRain className="w-4 h-4" />
                <span className="text-sm font-medium">Lluvioso</span>
              </button>
            </div>
          </div>

          {weather === "rainy" && (
            <div className="bg-primary/10 border border-primary/20 rounded-lg p-4 mt-4">
              <div className="flex items-start gap-3">
                <Sparkles className="w-5 h-5 text-primary mt-0.5" />
                <div>
                  <p className="font-medium text-primary">
                    Combo Día Lluvioso Activado
                  </p>
                  <p className="text-sm text-muted-foreground mt-1">
                    Descuentos especiales en actividades bajo techo: museos, galerías y catas de vino
                  </p>
                </div>
              </div>
            </div>
          )}

          {packagePublished && (
            <div className="bg-accent/10 border border-accent/20 rounded-lg p-4 mt-4">
              <div className="flex items-start gap-3">
                <Sparkles className="w-5 h-5 text-accent mt-0.5" />
                <div>
                  <p className="font-medium text-accent">
                    Nuevo Paquete Cooperativo Disponible
                  </p>
                  <p className="text-sm text-muted-foreground mt-1">
                    Los comerciantes locales han creado un paquete especial para este viernes con descuentos exclusivos
                  </p>
                </div>
              </div>
            </div>
          )}
        </div>
      </section>

      <div className="grid grid-cols-1 lg:grid-cols-3 gap-8">
        <div className="lg:col-span-2 space-y-8">
          {/* Activities based on weather */}
          <section>
            <h2 className="text-xl font-semibold text-foreground mb-4 flex items-center gap-2">
              {weather === "sunny" ? (
                <>
                  <Sun className="w-5 h-5 text-warning" />
                  Actividades para Día Soleado
                </>
              ) : (
                <>
                  <Building2 className="w-5 h-5 text-primary" />
                  Actividades Bajo Techo
                </>
              )}
            </h2>
            <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
              {activities.map((activity) => {
                const Icon = activity.icon;
                const finalPrice = activity.discount
                  ? Math.round(activity.price * (1 - activity.discount / 100))
                  : activity.price;
                return (
                  <div
                    key={activity.id}
                    className="bg-card rounded-xl p-5 shadow-sm border hover:shadow-md transition-shadow"
                  >
                    <div className="w-12 h-12 rounded-lg bg-primary/10 flex items-center justify-center mb-4">
                      <Icon className="w-6 h-6 text-primary" />
                    </div>
                    <h3 className="font-semibold text-card-foreground mb-2">{activity.name}</h3>
                    <div className="flex items-baseline gap-2 mb-4">
                      {activity.discount > 0 && (
                        <span className="text-sm text-muted-foreground line-through">
                          ${activity.price}
                        </span>
                      )}
                      <span className="text-2xl font-bold text-primary">${finalPrice}</span>
                      {activity.discount > 0 && (
                        <span className="text-xs bg-accent text-accent-foreground px-2 py-0.5 rounded-full">
                          -{activity.discount}%
                        </span>
                      )}
                    </div>
                    <button
                      onClick={() =>
                        addToCart({
                          id: activity.id,
                          name: activity.name,
                          price: finalPrice,
                          type: "activity",
                        })
                      }
                      className="w-full py-2 bg-primary text-primary-foreground rounded-lg font-medium hover:bg-primary/90 transition-colors"
                    >
                      Agregar
                    </button>
                  </div>
                );
              })}
            </div>
          </section>

          {/* Dynamic Ticketing Module */}
          <section>
            <h2 className="text-xl font-semibold text-foreground mb-4 flex items-center gap-2">
              <Ticket className="w-5 h-5 text-primary" />
              Catedral Histórica - Horarios y Precios Dinámicos
            </h2>
            <div className="bg-card rounded-xl p-6 shadow-sm border">
              <p className="text-sm text-muted-foreground mb-4">
                Los precios varían según la demanda. Horarios valle tienen descuentos automáticos.
              </p>
              <div className="grid grid-cols-3 md:grid-cols-9 gap-2">
                {timeSlots.map((slot) => (
                  <button
                    key={slot.time}
                    onClick={() => setSelectedTimeSlot(slot.time)}
                    className={`p-3 rounded-lg border text-center transition-all ${
                      selectedTimeSlot === slot.time
                        ? "border-primary bg-primary/10 ring-2 ring-primary"
                        : slot.isPeak
                        ? "border-warning/50 bg-warning/5 hover:border-warning"
                        : "border-accent/50 bg-accent/5 hover:border-accent"
                    }`}
                  >
                    <span className="block text-sm font-medium text-card-foreground">
                      {slot.time}
                    </span>
                    <span
                      className={`block text-lg font-bold ${
                        slot.isPeak ? "text-warning" : "text-accent"
                      }`}
                    >
                      ${slot.price}
                    </span>
                    {!slot.isPeak && (
                      <span className="text-xs text-accent">Valle</span>
                    )}
                  </button>
                ))}
              </div>
              {selectedTimeSlot && (
                <button
                  onClick={() => {
                    const slot = timeSlots.find((s) => s.time === selectedTimeSlot);
                    if (slot) {
                      addToCart({
                        id: `cathedral-${slot.time}`,
                        name: `Catedral ${slot.time}`,
                        price: slot.price,
                        type: "activity",
                      });
                    }
                  }}
                  className="mt-4 w-full py-3 bg-primary text-primary-foreground rounded-lg font-medium hover:bg-primary/90 transition-colors"
                >
                  Reservar {selectedTimeSlot} hs
                </button>
              )}
            </div>
          </section>

          {/* Gastronomy Valley Hour */}
          <section>
            <h2 className="text-xl font-semibold text-foreground mb-4 flex items-center gap-2">
              <Utensils className="w-5 h-5 text-accent" />
              Gastronomía - Hora Valle
            </h2>
            <div className="bg-card rounded-xl p-6 shadow-sm border">
              <div className="flex items-start gap-4">
                <div className="w-16 h-16 rounded-xl bg-accent/10 flex items-center justify-center flex-shrink-0">
                  <Clock className="w-8 h-8 text-accent" />
                </div>
                <div className="flex-1">
                  <h3 className="font-semibold text-lg text-card-foreground">
                    Restaurante La Tradición
                  </h3>
                  <p className="text-muted-foreground text-sm mt-1">
                    Cocina regional con ingredientes locales de temporada
                  </p>
                  <div className="mt-3 p-3 bg-accent/10 rounded-lg border border-accent/20">
                    <p className="text-sm font-medium text-accent">
                      Reserva antes de las 20:00 hs y obtén:
                    </p>
                    <ul className="mt-2 space-y-1">
                      <li className="text-sm text-card-foreground flex items-center gap-2">
                        <span className="w-1.5 h-1.5 rounded-full bg-accent" />
                        20% de descuento en tu cena
                      </li>
                      <li className="text-sm text-card-foreground flex items-center gap-2">
                        <span className="w-1.5 h-1.5 rounded-full bg-accent" />
                        Copa de vino local de cortesía
                      </li>
                    </ul>
                  </div>
                  <div className="mt-4 flex items-center gap-4">
                    <div>
                      <span className="text-sm text-muted-foreground line-through">$45</span>
                      <span className="text-2xl font-bold text-accent ml-2">$36</span>
                      <span className="text-sm text-muted-foreground">/persona</span>
                    </div>
                    <button
                      onClick={() =>
                        addToCart({
                          id: "restaurant-tradicion",
                          name: "Cena La Tradición (Valle)",
                          price: 36,
                          type: "restaurant",
                        })
                      }
                      className="px-6 py-2 bg-accent text-accent-foreground rounded-lg font-medium hover:bg-accent/90 transition-colors"
                    >
                      Reservar Mesa
                    </button>
                  </div>
                </div>
              </div>
            </div>
          </section>

          {/* Last-Minute Excursions */}
          <section>
            <h2 className="text-xl font-semibold text-foreground mb-4 flex items-center gap-2">
              <Timer className="w-5 h-5 text-destructive" />
              Excursiones de Última Hora
            </h2>
            <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
              {flashDeals.map((deal) => (
                <div
                  key={deal.id}
                  className="bg-card rounded-xl p-5 shadow-sm border border-destructive/20 relative overflow-hidden"
                >
                  <div className="absolute top-0 right-0 bg-destructive text-destructive-foreground text-xs px-3 py-1 rounded-bl-lg font-medium">
                    {deal.spotsLeft} lugares
                  </div>
                  <h3 className="font-semibold text-card-foreground mb-2 pr-16">{deal.name}</h3>
                  <div className="flex items-center gap-2 text-sm text-muted-foreground mb-3">
                    <Timer className="w-4 h-4" />
                    <span>Quedan {deal.hoursLeft} horas</span>
                  </div>
                  <div className="flex items-baseline gap-2 mb-4">
                    <span className="text-sm text-muted-foreground line-through">
                      ${deal.originalPrice}
                    </span>
                    <span className="text-2xl font-bold text-destructive">${deal.price}</span>
                    <span className="text-xs bg-destructive/10 text-destructive px-2 py-0.5 rounded-full">
                      -{Math.round((1 - deal.price / deal.originalPrice) * 100)}%
                    </span>
                  </div>
                  <button
                    onClick={() =>
                      addToCart({
                        id: deal.id,
                        name: deal.name,
                        price: deal.price,
                        type: "excursion",
                      })
                    }
                    className="w-full py-2 bg-destructive text-destructive-foreground rounded-lg font-medium hover:bg-destructive/90 transition-colors"
                  >
                    Reservar Ahora
                  </button>
                </div>
              ))}
            </div>
          </section>
        </div>

        {/* Cart / Collaborative Checkout */}
        <div className="lg:col-span-1">
          <div className="bg-card rounded-xl p-6 shadow-sm border sticky top-8">
            <div className="flex items-center gap-2 mb-4">
              <ShoppingCart className="w-5 h-5 text-primary" />
              <h2 className="text-lg font-semibold text-card-foreground">Tu Reserva</h2>
            </div>

            {cart.length === 0 ? (
              <p className="text-muted-foreground text-sm py-8 text-center">
                Agrega actividades y restaurantes para crear tu paquete personalizado
              </p>
            ) : (
              <>
                <div className="space-y-3 mb-4">
                  {cart.map((item) => (
                    <div
                      key={item.id}
                      className="flex items-center justify-between py-2 border-b"
                    >
                      <div>
                        <p className="text-sm font-medium text-card-foreground">{item.name}</p>
                        <p className="text-xs text-muted-foreground capitalize">{item.type}</p>
                      </div>
                      <div className="flex items-center gap-3">
                        <span className="font-medium text-card-foreground">${item.price}</span>
                        <button
                          onClick={() => removeFromCart(item.id)}
                          className="text-destructive text-xs hover:underline"
                        >
                          Quitar
                        </button>
                      </div>
                    </div>
                  ))}
                </div>

                <div className="space-y-2 pt-4 border-t">
                  <div className="flex justify-between text-sm">
                    <span className="text-muted-foreground">Subtotal</span>
                    <span className="text-card-foreground">${subtotal}</span>
                  </div>
                  {hasActivityAndRestaurant && (
                    <div className="flex justify-between text-sm">
                      <span className="text-accent font-medium">Descuento Paquete (-15%)</span>
                      <span className="text-accent font-medium">-${packageDiscount}</span>
                    </div>
                  )}
                  <div className="flex justify-between text-lg font-bold pt-2">
                    <span className="text-card-foreground">Total</span>
                    <span className="text-primary">${total}</span>
                  </div>
                </div>

                {hasActivityAndRestaurant && (
                  <div className="mt-4 p-3 bg-accent/10 rounded-lg border border-accent/20">
                    <p className="text-xs text-accent font-medium">
                      Precio de Paquete Colaborativo
                    </p>
                    <p className="text-xs text-muted-foreground mt-1">
                      Al combinar actividad + restaurante, obtienes un precio especial unificado
                    </p>
                  </div>
                )}

                <button className="w-full mt-4 py-3 bg-primary text-primary-foreground rounded-lg font-medium hover:bg-primary/90 transition-colors">
                  Confirmar Reserva
                </button>
              </>
            )}
          </div>
        </div>
      </div>
    </div>
  );
}
