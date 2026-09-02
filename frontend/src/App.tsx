import { useEffect, useState } from "react";
import { Navigate, Route, Routes } from "react-router-dom";
import Layout from "./Layout";
import Dashboard from "./pages/Dashboard";
import Scan from "./pages/Scan";
import History from "./pages/History";
import Reports from "./pages/Reports";
import Rules from "./pages/Rules";
import Settings from "./pages/Settings";
import InspectionDetail from "./pages/InspectionDetail";
import { api } from "./api";

export default function App() {
  const [online, setOnline] = useState<boolean | null>(true);
  useEffect(() => {
    api("/api/health")
      .then(() => setOnline(true))
      .catch(() => setOnline(false));
  }, []);
  return (
    <Routes>
      <Route element={<Layout online={online} />}>
        <Route path="/" element={<Dashboard />} />
        <Route path="/scan" element={<Scan />} />
        <Route path="/history" element={<History />} />
        <Route path="/history/:id" element={<InspectionDetail />} />
        <Route path="/reports" element={<Reports />} />
        <Route path="/reports/:id" element={<InspectionDetail />} />
        <Route path="/rules" element={<Rules />} />
        <Route path="/settings" element={<Settings />} />
        <Route path="*" element={<Navigate to="/" replace />} />
      </Route>
    </Routes>
  );
}
