import { lazy, Suspense, type ReactNode } from "react";
import { Navigate, Route, Routes } from "react-router-dom";
import Layout from "./components/Layout";
import { PageLoader } from "./components/ui";
import { useAuth } from "./lib/auth";
import { isTelegram } from "./lib/telegram";
import Landing from "./pages/Landing";
import LessonPage from "./pages/LessonPage";
import Lessons from "./pages/Lessons";
import NeedRegistration from "./pages/NeedRegistration";
import Profile from "./pages/Profile";
import Progress from "./pages/Progress";
import Register from "./pages/Register";
import Today from "./pages/Today";
import Tutor from "./pages/Tutor";

// Admin panel alohida bo'lakda yuklanadi — oddiy foydalanuvchilar uchun ilova yengil bo'ladi
const AdminPage = lazy(() => import("./pages/admin/AdminPage"));

function RequireAdmin({ children }: { children: ReactNode }) {
  const { user } = useAuth();
  if (!user?.is_admin) return <Navigate to="/" replace />;
  return <Suspense fallback={<PageLoader />}>{children}</Suspense>;
}

function TelegramAuthFailed() {
  return (
    <div className="flex min-h-dvh flex-col items-center justify-center px-6 text-center">
      <p className="text-lg font-bold">Telegram orqali kirib bo'lmadi</p>
      <p className="mt-2 text-sm text-muted">Ilovani yopib, botdagi tugma orqali qayta oching.</p>
      <button className="btn-primary mt-5" onClick={() => window.location.reload()}>
        Qayta urinish
      </button>
    </div>
  );
}

export default function App() {
  const { user, loading } = useAuth();

  if (loading)
    return (
      <div className="flex min-h-dvh items-center justify-center">
        <PageLoader />
      </div>
    );

  return (
    <Routes>
      <Route path="/register" element={<Register />} />
      {!user ? (
        <Route path="*" element={isTelegram ? <TelegramAuthFailed /> : <Landing />} />
      ) : !user.registered ? (
        <Route path="*" element={<NeedRegistration />} />
      ) : (
        <Route element={<Layout />}>
          <Route index element={<Today />} />
          <Route path="lessons" element={<Lessons />} />
          <Route path="lessons/:slug" element={<LessonPage />} />
          <Route path="tutor" element={<Tutor />} />
          <Route path="progress" element={<Progress />} />
          <Route path="profile" element={<Profile />} />
          <Route
            path="admin"
            element={
              <RequireAdmin>
                <AdminPage />
              </RequireAdmin>
            }
          />
          <Route path="*" element={<Navigate to="/" replace />} />
        </Route>
      )}
    </Routes>
  );
}
