/**
 * 로그인 페이지 — PEF/M&A 어드바이저리 스타일 Hero + 3단계 스태거 애니메이션
 *
 * 레이아웃: 풀스크린 숲 배경 + 어둠 오버레이, 좌측 타이틀 그룹 / 우측 글래스모피즘 로그인 폼
 * 애니메이션: GSAP timeline (1순위 타이틀 → 2순위 서브타이틀 → 3순위 로그인 폼)
 */

import { useState, useRef, type FormEvent } from "react";
import { useNavigate, Navigate } from "react-router-dom";
import { useAuth } from "@/hooks/useAuth";
import { Button, Input } from "@/components/ui";
import { LogIn } from "lucide-react";
import { gsap, useGSAP } from "@/lib/gsap";
import forestCover from "@/assets/images/forest-cover.jpg";

export default function LoginPage() {
  const { login, isAuthenticated } = useAuth();
  const navigate = useNavigate();

  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [error, setError] = useState("");
  const [loading, setLoading] = useState(false);

  // GSAP refs
  const containerRef = useRef<HTMLDivElement>(null);
  const titleGroupRef = useRef<HTMLDivElement>(null);
  const subtitleRef = useRef<HTMLParagraphElement>(null);
  const formRef = useRef<HTMLDivElement>(null);

  // 3-stage stagger animation
  useGSAP(
    () => {
      const tl = gsap.timeline({ defaults: { ease: "power3.out" } });

      if (titleGroupRef.current) {
        tl.fromTo(
          titleGroupRef.current,
          { y: 30, opacity: 0 },
          { y: 0, opacity: 1, duration: 0.7 },
        );
      }

      if (subtitleRef.current) {
        tl.fromTo(
          subtitleRef.current,
          { y: 20, opacity: 0 },
          { y: 0, opacity: 1, duration: 0.5 },
          0.6,
        );
      }

      if (formRef.current) {
        tl.fromTo(
          formRef.current,
          { y: 25, opacity: 0 },
          { y: 0, opacity: 1, duration: 0.6 },
          1.2,
        );
      }
    },
    { scope: containerRef },
  );

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
    <div
      ref={containerRef}
      className="min-h-[100dvh] relative flex overflow-hidden bg-amic-900"
    >
      {/* ── Background: forest image + dark overlay ── */}
      <img
        src={forestCover}
        alt=""
        aria-hidden="true"
        className="absolute inset-0 w-full h-full object-cover object-top"
      />
      <div className="absolute inset-0 bg-gradient-to-br from-black/65 via-black/55 to-black/70" />

      {/* ── Content: Left title + Right form ── */}
      <div className="relative z-10 flex flex-col lg:flex-row items-center justify-center lg:justify-between w-full max-w-6xl mx-auto px-6 sm:px-10 lg:px-16 py-12 lg:py-0 gap-12 lg:gap-20">
        {/* ── Left: Title Group ── */}
        <div className="flex-1 flex flex-col items-center lg:items-start text-center lg:text-left">
          {/* Stage 1: Title block */}
          <div ref={titleGroupRef} style={{ opacity: 0 }}>
            <div className="flex flex-col sm:flex-row items-center gap-3 sm:gap-6">
              {/* AMIC + 법무법인 아믹 */}
              <div className="flex flex-col items-center sm:items-start">
                <span className="font-heading text-4xl sm:text-5xl lg:text-6xl font-extrabold text-white tracking-tight leading-none">
                  AMIC
                </span>
                <span className="font-heading text-sm sm:text-base lg:text-lg text-white/70 mt-1">
                  법무법인 아믹
                </span>
              </div>

              {/* & */}
              <span className="font-heading text-2xl sm:text-3xl lg:text-4xl text-white/40 font-light sm:self-start sm:mt-2">
                &
              </span>

              {/* PETRABRIDGE + PARTNERS */}
              <div className="flex flex-col items-center sm:items-start">
                <span className="font-heading text-4xl sm:text-5xl lg:text-6xl font-extrabold text-white tracking-tight leading-none">
                  PETRABRIDGE
                </span>
                <span className="font-heading text-sm sm:text-base lg:text-lg text-white/70 mt-1">
                  PARTNERS
                </span>
              </div>
            </div>
          </div>

          {/* Stage 2: Subtitle */}
          <p
            ref={subtitleRef}
            style={{ opacity: 0 }}
            className="mt-6 lg:mt-8 font-body text-xs sm:text-sm lg:text-base text-white/60 tracking-[0.2em] uppercase"
          >
            M&A Joint Advisory Service Platform
          </p>
        </div>

        {/* ── Right: Glassmorphism Login Form ── */}
        <div
          ref={formRef}
          style={{ opacity: 0 }}
          className="login-hero w-full max-w-sm lg:max-w-md shrink-0"
        >
          <div className="backdrop-blur-lg bg-white/[0.07] border border-white/[0.10] rounded-dr-lg p-8 sm:p-10 shadow-dr-xl">
            {/* Header */}
            <div className="mb-8">
              <h2 className="font-heading text-2xl font-bold text-white">
                Welcome
              </h2>
              <p className="font-body text-white/60 mt-2 text-sm">
                Sign in to continue
              </p>
            </div>

            {/* Form */}
            <form onSubmit={handleSubmit} className="space-y-6">
              {error && (
                <div
                  role="alert"
                  className="text-sm text-red-300 bg-red-500/15 border border-red-400/20 rounded-corporate px-4 py-3"
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
                className="w-full mt-2 !bg-white/10 hover:!bg-white/20 !border-white/10 !text-white transition-all duration-300"
                loading={loading}
                icon={LogIn}
              >
                Sign In
              </Button>
            </form>

            {/* Footer */}
            <p className="mt-8 text-center text-xs text-white/30 tracking-wide">
              AMIC × PETRA Platform v1.0
            </p>
          </div>
        </div>
      </div>
    </div>
  );
}
