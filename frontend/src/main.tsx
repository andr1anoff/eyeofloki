import { StrictMode } from "react";
import { createRoot } from "react-dom/client";
import { DashboardV2 } from "./dashboard-v2";
import "./app-v2.css";

createRoot(document.getElementById("root")!).render(
  <StrictMode>
    <DashboardV2 displayName="Ivan" />
  </StrictMode>,
);
