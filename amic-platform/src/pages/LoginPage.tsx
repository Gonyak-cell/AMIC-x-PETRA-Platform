/** 로그인 페이지 (TM CI 기반 리디자인 — 숲 배경 + 세리프/산세리프 브랜딩) */

import { useState, type FormEvent } from "react";
import { useNavigate, useLocation, Navigate } from "react-router-dom";
import { useAuth } from "@/hooks/useAuth";
import { Button, Input } from "@/components/ui";
import { LogIn } from "lucide-react";
import brochureCover from "@/assets/images/brochure-cover.png";

export default function LoginPage() {
  const { login, isAuthenticated } = useAuth();
  const navigate = useNavigate();
  const location = useLocation();
  const from = (location.state as { from?: { pathname: string } })?.from
    ?.pathname ?? "/";

  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [error, setError] = useState("");
  const [loading, setLoading] = useState(false);

  // Already authenticated — redirect
  if (isAuthenticated) {
    return <Navigate to={from} replace />;
  }

  async function handleSubmit(e: FormEvent) {
    e.preventDefault();
    setError("");
    setLoading(true);
    try {
      await login({ email, password });
      navigate(from, { replace: true });
    } catch {
      setError("Invalid email or password.");
    } finally {
      setLoading(false);
    }
  }

  return (
    <div className="min-h-screen flex">
      {/* Left Panel — Brochure Cover */}
      <div className="hidden lg:block lg:w-1/2 relative overflow-hidden">
        <img
          src={brochureCover}
          alt="AMIC & Petrabridge Partners"
          className="absolute inset-0 w-full h-full object-cover"
        />
      </div>

      {/* Right Panel — Login Form */}
      <div className="flex-1 flex items-center justify-center bg-white px-6 lg:px-20">
        <div className="w-full max-w-lg">
          {/* Mobile Logo */}
          <div className="lg:hidden mb-10">
            <div className="flex items-start justify-center gap-3">
              <span className="text-amic font-serif font-bold text-[26px] tracking-[0.2em] leading-none mt-0.5">
                AMIC
              </span>
              <span className="text-amic/25 text-2xl font-extralight leading-none">&amp;</span>
              <div className="text-accent font-heading font-bold leading-[1.15]">
                <div className="text-lg tracking-[0.1em]">PETRABRIDGE</div>
                <div className="text-lg tracking-[0.1em]">PARTNERS</div>
              </div>
            </div>
            <div className="mt-4 mx-auto h-px w-20 bg-gradient-to-r from-transparent via-accent/40 to-transparent" />
          </div>

          <div className="mb-8">
            <h2 className="text-2xl font-heading font-bold text-text-dark">
              Welcome
            </h2>
            <p className="text-text-secondary mt-2">
              Sign in to continue
            </p>
          </div>

          <form onSubmit={handleSubmit} className="space-y-5">
            {error && (
              <div className="text-sm text-negative bg-red-50 border border-negative/20 rounded-corporate px-4 py-3">
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

          <p className="mt-8 text-center text-footnote text-text-muted">
            AMIC x PETRA Platform v1.0
          </p>
        </div>
      </div>
    </div>
  );
}
