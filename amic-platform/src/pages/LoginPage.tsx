/** 로그인 페이지 (AMIC x PETRA Platform 브랜딩 좌우 분할 레이아웃) */

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
      {/* Left Panel - AMIC x PETRA Platform Branding */}
      <div className="hidden lg:flex lg:w-1/2 bg-amic flex-col justify-center px-16">
        <div className="max-w-md">
          <h1 className="text-white font-heading font-bold text-3xl mb-2">
            AMIC x PETRA Platform
          </h1>
          <h2 className="text-white/80 font-heading text-xl mb-8">
            AMIC Law & PetraBridge Partners
          </h2>

          <div className="border-l-4 border-accent pl-4 mb-8">
            <p className="text-white/90 text-lg leading-relaxed">
              FDD · KIIS · IM<br />
              Unified Analysis Platform
            </p>
          </div>

          <p className="text-white/60 text-sm leading-relaxed">
            Auto FDD, KIIS, IM Generator를 하나로 통합한 플랫폼.
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
              AMIC x PETRA Platform
            </h1>
            <p className="text-text-secondary text-sm mt-1">
              AMIC Law & PetraBridge Partners
            </p>
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
            AMIC x PETRA Platform v1.0 | AMIC Law & PetraBridge Partners
          </p>
        </div>
      </div>
    </div>
  );
}
