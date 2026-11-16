// This project uses a subset of Leaflet's runtime API.
// Replace these compatibility types with @types/leaflet when available.
declare module "leaflet" {
  namespace L {
    type Map = any
    type LayerGroup = any
    type HeatLayer = any
    type TileLayer = any
  }
  const L: any
  export = L
}
