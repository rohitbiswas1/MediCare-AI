"use client";
import { useState } from "react";
import { APIProvider, Map, Marker } from "@vis.gl/react-google-maps";
import {
  Search,
  LocateFixed,
  MapPin,
  Navigation,
  Phone,
  Info,
} from "lucide-react";
import { api, type Pharmacy } from "@/lib/api";
import { useLocale } from "@/lib/i18n";
import { PageTitle, ErrorNotice, Loading } from "@/components/common";
import { Card } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
export default function Page() {
  const { t } = useLocale();
  const [q, setQ] = useState("");
  const [rows, setRows] = useState<Pharmacy[]>([]);
  const [error, setError] = useState("");
  const [busy, setBusy] = useState(false);
  const [searched, setSearched] = useState(false);
  const [selected, setSelected] = useState("");
  const [inventory, setInventory] = useState<
    Record<
      string,
      { status: string; medicine_id: string; verified_at: string }[]
    >
  >({});
  const mapKey = process.env.NEXT_PUBLIC_GOOGLE_MAPS_API_KEY;
  async function search(params: string) {
    setBusy(true);
    setError("");
    try {
      setRows(await api<Pharmacy[]>("/pharmacies/nearby?" + params));
      setSearched(true);
    } catch (e) {
      setError((e as Error).message);
    } finally {
      setBusy(false);
    }
  }
  function locate() {
    if (!navigator.geolocation) {
      setError("Location is unavailable. Enter your city instead.");
      return;
    }
    navigator.geolocation.getCurrentPosition(
      (p) => void search(`lat=${p.coords.latitude}&lng=${p.coords.longitude}`),
      () =>
        setError(
          "Location permission was not granted. Enter your city or PIN code instead.",
        ),
      { timeout: 10000, maximumAge: 0 },
    );
  }
  async function stock(id: string) {
    try {
      const result = await api<{
        items: { status: string; medicine_id: string; verified_at: string }[];
      }>(`/pharmacies/${id}/inventory`);
      setInventory((prev) => ({ ...prev, [id]: result.items }));
    } catch (e) {
      setError((e as Error).message);
    }
  }
  const center = rows.find((r) => r.latitude !== null && r.longitude !== null);
  return (
    <>
      <PageTitle title={t("pharmacies")} subtitle={t("locationNotice")} />
      <div className="stack">
        <Card>
          <form
            className="searchbar"
            onSubmit={(e) => {
              e.preventDefault();
              void search("q=" + encodeURIComponent(q));
            }}
          >
            <Input
              aria-label={t("location")}
              placeholder={t("location")}
              value={q}
              onChange={(e) => setQ(e.target.value)}
              required
            />
            <Button disabled={busy}>
              <Search />
              {t("search")}
            </Button>
            <Button type="button" variant="outline" onClick={locate}>
              <LocateFixed />
              {t("useLocation")}
            </Button>
          </form>
        </Card>
        <ErrorNotice message={error} />
        <div className="two-grid">
          <div className="map-container">
            {mapKey && center ? (
              <APIProvider apiKey={mapKey}>
                <Map
                  key={center.id}
                  defaultCenter={{
                    lat: center.latitude!,
                    lng: center.longitude!,
                  }}
                  defaultZoom={13}
                  gestureHandling="cooperative"
                  disableDefaultUI
                >
                  {rows
                    .filter((r) => r.latitude !== null && r.longitude !== null)
                    .map((r) => (
                      <Marker
                        key={r.id}
                        position={{ lat: r.latitude!, lng: r.longitude! }}
                        title={r.name}
                        onClick={() => setSelected(r.id)}
                      />
                    ))}
                </Map>
              </APIProvider>
            ) : (
              <div className="map-placeholder">
                <div className="icon-box teal">
                  <MapPin />
                </div>
                <p>
                  {mapKey
                    ? "Search to explore nearby pharmacies."
                    : "The interactive map appears when Google Maps is connected."}
                </p>
              </div>
            )}
          </div>
          <div className="stack">
            {busy ? (
              <Loading />
            ) : rows.length ? (
              rows.map((r) => (
                <Card
                  className="pharmacy-card"
                  key={r.id}
                  style={
                    selected === r.id ? { borderColor: "var(--blue)" } : {}
                  }
                >
                  <div className="between">
                    <h3>{r.name}</h3>
                    <MapPin size={17} color="#0d9488" />
                  </div>
                  <p>{r.address}</p>
                  <span className="badge amber" style={{ margin: "12px 0" }}>
                    {t("unconfirmed")}
                  </span>
                  {r.hours.length > 0 && (
                    <details>
                      <summary className="muted" style={{ fontSize: 11 }}>
                        Opening hours
                      </summary>
                      {r.hours.map((h) => (
                        <p key={h}>{h}</p>
                      ))}
                    </details>
                  )}
                  <div className="row wrap" style={{ marginTop: 15 }}>
                    <Button asChild variant="outline" size="sm">
                      <a
                        href={r.directions_url}
                        target="_blank"
                        rel="noreferrer"
                      >
                        <Navigation />
                        {t("directions")}
                      </a>
                    </Button>
                    {r.phone && (
                      <Button asChild variant="outline" size="sm">
                        <a href={"tel:" + r.phone.replace(/[^\d+]/g, "")}>
                          <Phone />
                          {t("call")}
                        </a>
                      </Button>
                    )}
                    <Button
                      variant="ghost"
                      size="sm"
                      onClick={() => stock(r.id)}
                    >
                      Check partner stock
                    </Button>
                  </div>
                  {inventory[r.id] && (
                    <p style={{ marginTop: 12 }}>
                      {inventory[r.id].length
                        ? inventory[r.id]
                            .map(
                              (i) =>
                                `${i.medicine_id}: ${i.status.replaceAll("_", " ")}`,
                            )
                            .join("; ")
                        : t("unconfirmed")}
                    </p>
                  )}
                  <small className="muted">Google Maps</small>
                </Card>
              ))
            ) : (
              <Card>
                <div className="empty">
                  <MapPin size={30} color="#0d9488" />
                  <h3>
                    {searched
                      ? "No matching pharmacies returned"
                      : t("pharmacyTool")}
                  </h3>
                  <p>{t("locationNotice")}</p>
                </div>
              </Card>
            )}
          </div>
        </div>
        <div className="notice">
          <Info />
          <span>
            Verified stock requires a current pharmacy-partner inventory record.
            Contact the pharmacy before travelling. No substitutions or
            prescription authorizations are provided.
          </span>
        </div>
      </div>
    </>
  );
}
