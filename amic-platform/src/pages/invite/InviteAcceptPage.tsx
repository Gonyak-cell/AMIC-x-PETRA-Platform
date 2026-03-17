/** 초대 수락 페이지 — 신규 CLIENT가 비밀번호를 설정한다. */

import { useState, type FormEvent } from "react";
import { useSearchParams, useNavigate } from "react-router-dom";
import { useVerifyInvite, useAcceptInvite } from "@/hooks/useInvite";
import { Button, Input, Spinner } from "@/components/ui";
import { KeyRound } from "lucide-react";

export default function InviteAcceptPage() {
  const [searchParams] = useSearchParams();
  const navigate = useNavigate();
  const token = searchParams.get("token");

  const {
    data: tokenInfo,
    isLoading: isVerifying,
    isError: isVerifyError,
  } = useVerifyInvite(token);
  const acceptMutation = useAcceptInvite();

  const [password, setPassword] = useState("");
  const [confirmPassword, setConfirmPassword] = useState("");
  const [formError, setFormError] = useState("");
  const [success, setSuccess] = useState(false);

  async function handleSubmit(e: FormEvent) {
    e.preventDefault();
    setFormError("");

    if (password.length < 8) {
      setFormError("Password must be at least 8 characters.");
      return;
    }
    if (password !== confirmPassword) {
      setFormError("Passwords do not match.");
      return;
    }

    try {
      await acceptMutation.mutateAsync({ token: token!, password });
      setSuccess(true);
      setTimeout(() => navigate("/login", { replace: true }), 2000);
    } catch {
      setFormError("Failed to set password. The link may have expired.");
    }
  }

  // ── 레이아웃 래퍼 ──
  return (
    <div className="min-h-screen flex items-center justify-center bg-bg-base p-4">
      <div className="w-full max-w-md">
        {/* ── 토큰 없음 ── */}
        {!token && (
          <ErrorCard
            title="Invalid Link"
            message="No invitation token was provided. Please check your email and try again."
          />
        )}

        {/* ── 검증 중 ── */}
        {token && isVerifying && (
          <div className="flex flex-col items-center gap-3 text-text-secondary">
            <Spinner size="lg" />
            <p>Verifying your invitation…</p>
          </div>
        )}

        {/* ── 네트워크/서버 에러 ── */}
        {token && !isVerifying && isVerifyError && (
          <ErrorCard
            title="연결 오류"
            message="초대 링크를 확인할 수 없습니다. 네트워크 연결을 확인하고 다시 시도해 주세요."
          />
        )}

        {/* ── 토큰 에러 상태 ── */}
        {token &&
          !isVerifying &&
          !isVerifyError &&
          tokenInfo &&
          !tokenInfo.valid && (
            <ErrorCard
              title={
                tokenInfo.already_used
                  ? "Invitation Already Used"
                  : tokenInfo.expired
                    ? "Invitation Expired"
                    : "Invalid Invitation"
              }
              message={
                tokenInfo.already_used
                  ? "This invitation link has already been used. Please sign in or contact your administrator."
                  : tokenInfo.expired
                    ? "This invitation link has expired. Please contact your administrator for a new link."
                    : "This invitation link is invalid. Please contact your administrator."
              }
            />
          )}

        {/* ── 성공 ── */}
        {success && (
          <div className="rounded-lg border border-positive/30 bg-positive/10 px-6 py-8 text-center">
            <p className="text-lg font-semibold text-positive">
              Password set successfully!
            </p>
            <p className="mt-2 text-sm text-text-secondary">
              Redirecting you to the sign-in page…
            </p>
          </div>
        )}

        {/* ── 비밀번호 설정 폼 ── */}
        {token && !isVerifying && tokenInfo?.valid && !success && (
          <div className="rounded-lg border border-border-subtle bg-surface-card p-8 shadow-card">
            <div className="mb-6">
              <h1 className="text-xl font-heading font-bold text-text-dark">
                Set Your Password
              </h1>
              <p className="mt-1 text-sm text-text-secondary">
                Welcome,{" "}
                <span className="font-medium text-text-dark">
                  {tokenInfo.display_name ?? tokenInfo.email}
                </span>
                . Please create a password to activate your account.
              </p>
            </div>

            <form onSubmit={handleSubmit} className="space-y-4">
              {formError && (
                <div className="rounded-corporate border border-negative/20 bg-red-50 px-4 py-3 text-sm text-negative">
                  {formError}
                </div>
              )}

              <Input
                label="New Password"
                type="password"
                required
                value={password}
                onChange={(e) => setPassword(e.target.value)}
                placeholder="At least 8 characters"
              />

              <Input
                label="Confirm Password"
                type="password"
                required
                value={confirmPassword}
                onChange={(e) => setConfirmPassword(e.target.value)}
                placeholder="Re-enter your password"
              />

              <Button
                type="submit"
                variant="primary"
                size="lg"
                className="w-full"
                loading={acceptMutation.isPending}
                icon={KeyRound}
              >
                Activate Account
              </Button>
            </form>
          </div>
        )}
      </div>
    </div>
  );
}

// ── 에러 카드 서브 컴포넌트 ──
function ErrorCard({ title, message }: { title: string; message: string }) {
  return (
    <div className="rounded-lg border border-negative/30 bg-red-50 px-6 py-8 text-center">
      <p className="text-lg font-semibold text-negative">{title}</p>
      <p className="mt-2 text-sm text-text-secondary">{message}</p>
    </div>
  );
}
