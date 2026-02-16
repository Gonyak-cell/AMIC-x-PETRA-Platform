/** 로그인 페이지 (AMIC 브랜딩 좌우 분할 레이아웃) */

import { useState, type FormEvent } from "react";
import { useNavigate, useLocation } from "react-router-dom";
import { useAuth } from "@/hooks/useAuth";
import { Button, Input } from "@/components/ui";
import { LogIn } from "lucide-react";

export default function LoginPage() {
  const { login, isAuthenticated } = useAuth();
  const navigate = useNavigate();
  const location = useLocation();
  const from = (location.state as { from?: { pathname: string } })?.from
    ?.pathname ?? "/deals";

  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [error, setError] = useState("");
  const [loading, setLoading] = useState(false);

  // Already authenticated — redirect
  if (isAuthenticated) {
    navigate(from, { replace: true });
    return null;
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
      {/* Left Panel - AMIC Branding */}
      <div className="hidden lg:flex lg:w-1/2 bg-amic flex-col justify-center px-16">
        <div className="max-w-md">
          <h1 className="text-white font-heading font-bold text-3xl mb-2">
            AMIC 법무법인 아믹
          </h1>
          <h2 className="text-white/80 font-heading text-xl mb-8">
            Auto FDD
          </h2>

          <div className="border-l-4 border-accent pl-4 mb-8">
            <p className="text-white/90 text-lg leading-relaxed">
              Financial Due Diligence<br />
              Automation Platform
            </p>
          </div>

          <p className="text-white/60 text-sm leading-relaxed">
            전문적이고 체계적인 FDD 분석을 위한 올인원 플랫폼.
            <br />
            QoE Bridge, Net Debt, Working Capital 분석을 자동화하여
            <br />
            딜 실행 속도를 높이고 분석 품질을 향상시킵니다.
          </p>
        </div>
      </div>

      {/* Right Panel - Login Form */}
      <div className="flex-1 flex items-center justify-center bg-white px-6 lg:px-16">
        <div className="w-full max-w-md">
          {/* Mobile Logo */}
          <div className="lg:hidden text-center mb-8">
            <h1 className="text-amic font-heading font-bold text-2xl">
              Auto FDD
            </h1>
            <p className="text-text-secondary text-sm mt-1">
              AMIC Law Financial Due Diligence
            </p>
          </div>

          <div className="mb-8">
            <h2 className="text-2xl font-heading font-bold text-text-dark">
              Welcome
            </h2>
            <p className="text-text-secondary mt-2">
              Sign in to Auto FDD to continue
            </p>
          </div>

          <form onSubmit={handleSubmit} className="space-y-5">
            {error && (
              <div className="text-sm text-negative bg-red-50 border border-negative/20 rounded-lg px-4 py-3">
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
              variant="accent"
              size="lg"
              className="w-full"
              loading={loading}
              icon={LogIn}
            >
              Sign In
            </Button>
          </form>

          <p className="mt-8 text-center text-footnote text-text-secondary">
            Auto FDD v1.0 | AMIC Law & PetraBridge Partners
          </p>
        </div>
      </div>
    </div>
  );
}
