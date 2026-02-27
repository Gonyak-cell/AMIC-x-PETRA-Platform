import { useEffect, useRef, useCallback, useId } from "react";
import { X } from "lucide-react";
import { gsap } from "@/lib/gsap";
import { getMemberPhoto } from "@/lib/member-photos";
import type { TeamMemberData } from "./TeamPage";

interface MemberDetailModalProps {
  member: TeamMemberData;
  onClose: () => void;
}

const FOCUSABLE_SELECTOR =
  'button, [href], input, select, textarea, [tabindex]:not([tabindex="-1"])';

export function MemberDetailModal({ member, onClose }: MemberDetailModalProps) {
  const titleId = useId();
  const dialogRef = useRef<HTMLDialogElement>(null);
  const previousFocusRef = useRef<HTMLElement | null>(null);
  const backdropRef = useRef<HTMLDivElement>(null);
  const contentRef = useRef<HTMLDivElement>(null);
  const sectionsRef = useRef<HTMLDivElement>(null);
  const isClosingRef = useRef(false);
  const photoUrl = getMemberPhoto(member.name);

  // Open dialog + enter animation
  useEffect(() => {
    const dialog = dialogRef.current;
    if (!dialog) return;

    isClosingRef.current = false;
    previousFocusRef.current = document.activeElement as HTMLElement;
    dialog.showModal();

    const tl = gsap.timeline({ defaults: { ease: "power3.out" } });

    tl.fromTo(
      backdropRef.current,
      { opacity: 0 },
      { opacity: 1, duration: 0.2 },
    );

    tl.fromTo(
      contentRef.current,
      { scale: 0.95, y: 20, opacity: 0 },
      { scale: 1, y: 0, opacity: 1, duration: 0.4 },
      "-=0.1",
    );

    if (sectionsRef.current?.children.length) {
      tl.fromTo(
        Array.from(sectionsRef.current.children),
        { y: 15, opacity: 0 },
        { y: 0, opacity: 1, stagger: 0.08, duration: 0.4 },
        "-=0.2",
      );
    }

    requestAnimationFrame(() => {
      const firstFocusable =
        contentRef.current?.querySelector<HTMLElement>(FOCUSABLE_SELECTOR);
      if (firstFocusable) firstFocusable.focus();
    });
  }, []);

  // Close with exit animation
  const handleClose = useCallback(() => {
    if (isClosingRef.current) return;
    isClosingRef.current = true;

    const tl = gsap.timeline({
      defaults: { ease: "power2.in" },
      onComplete: () => {
        dialogRef.current?.close();
        onClose();
        requestAnimationFrame(() => {
          previousFocusRef.current?.focus();
        });
      },
    });

    tl.to(contentRef.current, {
      scale: 0.95,
      y: 20,
      opacity: 0,
      duration: 0.25,
    });
    tl.to(backdropRef.current, { opacity: 0, duration: 0.15 }, "-=0.1");
  }, [onClose]);

  const hasCareer = member.career.length > 0;
  const hasEducation = member.education.length > 0;
  const hasQualifications =
    member.qualifications && member.qualifications.length > 0;
  const hasContent = hasCareer || hasEducation || hasQualifications;

  return (
    <dialog
      ref={dialogRef}
      className="fixed inset-0 z-50 bg-transparent p-0 m-0 max-w-none max-h-none w-full h-full backdrop:bg-transparent"
      onCancel={(e) => {
        e.preventDefault();
        handleClose();
      }}
      onClick={(e) => {
        if (e.target === dialogRef.current) handleClose();
      }}
      aria-labelledby={titleId}
    >
      {/* Animated backdrop */}
      <div
        ref={backdropRef}
        className="fixed inset-0 bg-amic-900/70 backdrop-blur-sm"
        style={{ opacity: 0 }}
      />

      <div className="relative flex items-center justify-center min-h-screen p-4">
        <div
          ref={contentRef}
          className="relative bg-white rounded-2xl shadow-dr-xl w-full max-w-2xl max-h-[85vh] overflow-y-auto"
          style={{ opacity: 0 }}
          onClick={(e) => e.stopPropagation()}
        >
          {/* Close button */}
          <button
            onClick={handleClose}
            className="absolute top-4 right-4 z-10 p-2 rounded-full hover:bg-gray-100 transition-colors text-text-secondary hover:text-text-dark"
            aria-label="닫기"
          >
            <X className="h-5 w-5" />
          </button>

          <div ref={sectionsRef} className="p-6 md:p-8">
            {/* Header: Photo + Name */}
            <div className="flex flex-col sm:flex-row gap-6 items-start">
              {photoUrl ? (
                <img
                  src={photoUrl}
                  alt={`${member.name} - ${member.title}`}
                  className="w-36 h-auto rounded-xl object-cover object-top bg-gradient-to-b from-gray-50 to-gray-100 shrink-0"
                />
              ) : (
                <div className="w-36 h-48 rounded-xl bg-gradient-to-br from-amic to-amic-700 flex items-center justify-center shrink-0">
                  <span className="text-white font-heading font-bold text-4xl">
                    {member.name.charAt(0)}
                  </span>
                </div>
              )}
              <div className="pt-1">
                <h2
                  id={titleId}
                  className="text-2xl font-heading font-bold text-text-dark tracking-tight"
                >
                  {member.name}
                </h2>
                <p className="text-amic font-semibold mt-1">{member.org}</p>
                <p className="text-sm text-text-secondary mt-0.5">
                  {member.title}
                </p>
              </div>
            </div>

            {/* Empty profile message */}
            {!hasContent && (
              <div className="mt-8 text-center py-6 text-text-secondary text-sm">
                프로필 준비 중입니다.
              </div>
            )}

            {/* Career */}
            {hasCareer && (
              <div className="mt-6">
                <h3 className="text-sm font-semibold text-amic uppercase tracking-wider mb-3">
                  경력
                </h3>
                <div className="border-t border-gray-border" />
                <ul className="mt-3 space-y-2">
                  {member.career.map((item, i) => (
                    <li key={i} className="flex gap-4 text-sm">
                      <span className="text-text-secondary whitespace-nowrap w-28 shrink-0">
                        {item.period}
                      </span>
                      <span className="text-text-dark">{item.desc}</span>
                    </li>
                  ))}
                </ul>
              </div>
            )}

            {/* Education */}
            {hasEducation && (
              <div className="mt-6">
                <h3 className="text-sm font-semibold text-amic uppercase tracking-wider mb-3">
                  학력
                </h3>
                <div className="border-t border-gray-border" />
                <ul className="mt-3 space-y-2">
                  {member.education.map((item, i) => (
                    <li key={i} className="flex gap-4 text-sm">
                      <span className="text-text-secondary whitespace-nowrap w-28 shrink-0">
                        {item.year}
                      </span>
                      <span className="text-text-dark">{item.desc}</span>
                    </li>
                  ))}
                </ul>
              </div>
            )}

            {/* Qualifications */}
            {hasQualifications && (
              <div className="mt-6">
                <h3 className="text-sm font-semibold text-amic uppercase tracking-wider mb-3">
                  자격
                </h3>
                <div className="border-t border-gray-border" />
                <ul className="mt-3 space-y-2">
                  {member.qualifications!.map((item, i) => (
                    <li
                      key={i}
                      className="flex items-center gap-2 text-sm text-text-dark"
                    >
                      <span className="w-1.5 h-1.5 rounded-full bg-amic shrink-0" />
                      {item}
                    </li>
                  ))}
                </ul>
              </div>
            )}
          </div>
        </div>
      </div>
    </dialog>
  );
}
