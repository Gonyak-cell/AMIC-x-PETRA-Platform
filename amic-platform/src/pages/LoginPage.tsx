/** 로그인 페이지 (포레스트 배경 + 글래스 카드 + 공식 SVG 로고) */

import { useState, type FormEvent } from "react";
import { useNavigate, Navigate } from "react-router-dom";
import { useAuth } from "@/hooks/useAuth";
import { Button, Input } from "@/components/ui";
import { LogIn } from "lucide-react";
import { APP_VERSION } from "@/lib/app-version";
import brochureCover from "@/assets/images/brochure-cover.png";
import forestCover from "@/assets/images/forest-cover.jpg";
import amicPetraWhiteUrl from "@/assets/logos/AMIC_n_PETRA_Main_Simple_White.svg";

export default function LoginPage() {
  const { login, isAuthenticated } = useAuth();
  const navigate = useNavigate();

  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [error, setError] = useState("");
  const [loading, setLoading] = useState(false);

  // Already authenticated — redirect to dashboard
  if (isAuthenticated) {
    return <Navigate to="/" replace />;
  }

  async function handleSubmit(e: FormEvent) {
    e.preventDefault();
    setError("");
    setLoading(true);
    try {
      await login({ email, password });
      navigate("/", { replace: true });
    } catch {
      setError("Invalid email or password.");
    } finally {
      setLoading(false);
    }
  }

  return (
    <div className="min-h-[100dvh] flex overflow-x-hidden">
      {/* Left Panel — Brochure Cover (Desktop only) */}
      <div className="hidden lg:block lg:w-1/2 relative overflow-hidden">
        <img
          src={brochureCover}
          alt="AMIC & Petrabridge Partners"
          className="absolute inset-0 w-full h-full object-cover"
        />
      </div>

      {/* Right Panel — Login Form */}
      <div className="flex-1 relative flex items-center justify-center px-6 lg:px-20 lg:bg-white">
        {/* Mobile Forest Background */}
        <div className="absolute inset-0 lg:hidden">
          <img
            src={forestCover}
            alt=""
            aria-hidden="true"
            className="absolute inset-0 w-full h-full object-cover object-top"
          />
          <div className="absolute inset-0 bg-gradient-to-b from-amic-900/60 via-amic-900/70 to-amic-900/90" />
        </div>

        {/* Form Container */}
        <div className="relative z-10 w-full max-w-lg">
          {/* Mobile Logo — SVG (white, on forest background) */}
          <div className="lg:hidden mb-10 flex flex-col items-center">
            <img
              src={amicPetraWhiteUrl}
              alt="AMIC & PETRABRIDGE PARTNERS"
              className="h-9 w-auto"
            />
            <div className="mt-4 h-px w-20 bg-gradient-to-r from-transparent via-white/40 to-transparent" />
          </div>

          {/* Glass Card on mobile, plain on desktop */}
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
