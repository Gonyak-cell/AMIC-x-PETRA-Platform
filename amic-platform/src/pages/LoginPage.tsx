import { useEffect, useState, type FormEvent } from "react";
import { Navigate, useLocation, useNavigate } from "react-router-dom";
import { LogIn } from "lucide-react";

import brochureCover from "@/assets/images/brochure-cover.png";
import forestCover from "@/assets/images/forest-cover.jpg";
import amicPetraWhiteUrl from "@/assets/logos/AMIC_n_PETRA_Main_Simple_White.svg";
import { Button, Input } from "@/components/ui";
import { useAuth } from "@/hooks/useAuth";
import { APP_VERSION } from "@/lib/app-version";
import { DEFAULT_DEV_LOGIN } from "@/lib/devAuth";

const DEV_LOCAL_AUTH_ENABLED =
  (import.meta.env.VITE_DEV_LOCAL_AUTH ?? "").trim() === "true";
const POST_LOGIN_PATH = DEV_LOCAL_AUTH_ENABLED ? "/ma/transactions" : "/";
const DEV_AUTO_LOGIN_QUERY = "devLogin";

export default function LoginPage() {
  const { login, isAuthenticated } = useAuth();
  const location = useLocation();
  const navigate = useNavigate();

  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [error, setError] = useState("");
  const [loading, setLoading] = useState(false);

  useEffect(() => {
    if (!DEV_LOCAL_AUTH_ENABLED || isAuthenticated) return;

    const params = new URLSearchParams(location.search);
    if (params.get(DEV_AUTO_LOGIN_QUERY) !== "1") return;

    let cancelled = false;

    setError("");
    setLoading(true);

    void login(DEFAULT_DEV_LOGIN)
      .then(() => {
        if (cancelled) return;
        navigate(POST_LOGIN_PATH, { replace: true });
      })
      .catch(() => {
        if (cancelled) return;
        setError("Development auto-login failed.");
      })
      .finally(() => {
        if (cancelled) return;
        setLoading(false);
      });

    return () => {
      cancelled = true;
    };
  }, [isAuthenticated, location.search, login, navigate]);

  if (isAuthenticated) {
    return <Navigate to={POST_LOGIN_PATH} replace />;
  }

  async function handleSubmit(e: FormEvent) {
    e.preventDefault();
    setError("");
    setLoading(true);
    try {
      await login({ email, password });
      navigate(POST_LOGIN_PATH, { replace: true });
    } catch {
      setError("Invalid email or password.");
    } finally {
      setLoading(false);
    }
  }

  return (
    <div className="min-h-[100dvh] flex overflow-x-hidden">
      <div className="hidden lg:block lg:w-1/2 relative overflow-hidden">
        <img
          src={brochureCover}
          alt="AMIC & Petrabridge Partners"
          className="absolute inset-0 w-full h-full object-cover"
        />
      </div>

      <div className="flex-1 relative flex items-center justify-center px-6 lg:px-20 lg:bg-white">
        <div className="absolute inset-0 lg:hidden">
          <img
            src={forestCover}
            alt=""
            aria-hidden="true"
            className="absolute inset-0 w-full h-full object-cover object-top"
          />
          <div className="absolute inset-0 bg-gradient-to-b from-amic-900/60 via-amic-900/70 to-amic-900/90" />
        </div>

        <div className="relative z-10 w-full max-w-lg">
          <div className="lg:hidden mb-10 flex flex-col items-center">
            <img
              src={amicPetraWhiteUrl}
              alt="AMIC & PETRABRIDGE PARTNERS"
              className="h-9 w-auto"
            />
            <div className="mt-4 h-px w-20 bg-gradient-to-r from-transparent via-white/40 to-transparent" />
          </div>

          <div
            className="login-dark-theme lg:bg-transparent lg:border-0 lg:shadow-none lg:backdrop-blur-none
                        bg-white/[0.08] backdrop-blur-xl border border-white/[0.12]
                        rounded-dr-lg p-8 lg:p-0"
          >
            <div className="mb-8">
              <h2 className="text-2xl font-heading font-bold text-white lg:text-text-dark">
                Welcome
              </h2>
              <p className="text-white/65 lg:text-text-secondary mt-2">
                Sign in to continue
              </p>
              {DEV_LOCAL_AUTH_ENABLED && (
                <div
                  className="mt-4 rounded-corporate border border-white/15 bg-white/8 px-4 py-3 text-sm
                             text-white/80 lg:border-amic-100 lg:bg-amic-50 lg:text-text-dark"
                >
                  Development login: <code>ytkim@amic.kr</code> / <code>1111</code>
                </div>
              )}
            </div>

            <form onSubmit={handleSubmit} className="space-y-5">
              {error && (
                <div
                  className="text-sm text-red-300 lg:text-negative
                             bg-red-500/15 lg:bg-red-50
                             border border-red-400/20 lg:border-negative/20
                             rounded-corporate px-4 py-3"
                >
                  {error}
                </div>
              )}

              <Input
                label="Email"
                type="email"
                required
                value={email}
                onChange={(e) => setEmail(e.target.value)}
                placeholder="user@example.com"
              />

              <Input
                label="Password"
                type="password"
                required
                value={password}
                onChange={(e) => setPassword(e.target.value)}
                placeholder="Enter your password"
              />

              <Button
                type="submit"
                variant="primary"
                size="lg"
                className="w-full"
                loading={loading}
                icon={LogIn}
              >
                Sign In
              </Button>
            </form>

            <p className="mt-8 text-center text-footnote text-white/40 lg:text-text-muted">
              AMIC x PETRA Platform v{APP_VERSION}
            </p>
          </div>
        </div>
      </div>
    </div>
  );
}
