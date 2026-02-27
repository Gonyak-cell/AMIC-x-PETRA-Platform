import { useRef, useCallback } from "react";
import { gsap } from "@/lib/gsap";
import { getMemberPhoto } from "@/lib/member-photos";
import type { TeamMemberData } from "./TeamPage";

interface TeamMemberCardProps {
  member: TeamMemberData;
  onClick: () => void;
}

export function TeamMemberCard({ member, onClick }: TeamMemberCardProps) {
  const cardRef = useRef<HTMLDivElement>(null);
  const imgRef = useRef<HTMLImageElement>(null);
  const photoUrl = getMemberPhoto(member.name);

  const onMouseEnter = useCallback(() => {
    if (!cardRef.current) return;
    gsap.to(cardRef.current, {
      y: -4,
      scale: 1.03,
      boxShadow:
        "0 16px 48px -8px rgba(15,58,50,0.14), 0 8px 16px -4px rgba(15,58,50,0.08)",
      duration: 0.3,
      ease: "power2.out",
      overwrite: true,
    });
    if (imgRef.current) {
      gsap.to(imgRef.current, {
        scale: 1.05,
        duration: 0.4,
        ease: "power2.out",
        overwrite: true,
      });
    }
  }, []);

  const onMouseLeave = useCallback(() => {
    if (!cardRef.current) return;
    gsap.to(cardRef.current, {
      y: 0,
      scale: 1,
      boxShadow: "0 2px 8px -2px rgba(15,58,50,0.08)",
      duration: 0.5,
      ease: "elastic.out(1, 0.5)",
      overwrite: true,
    });
    if (imgRef.current) {
      gsap.to(imgRef.current, {
        scale: 1,
        duration: 0.4,
        ease: "power2.out",
        overwrite: true,
      });
    }
  }, []);

  const onKeyDown = useCallback(
    (e: React.KeyboardEvent) => {
      if (e.key === "Enter" || e.key === " ") {
        e.preventDefault();
        onClick();
      }
    },
    [onClick],
  );

  return (
    <div
      ref={cardRef}
      className="bg-white rounded-dr border border-gray-border overflow-hidden shadow-dr-sm cursor-pointer"
      role="button"
      tabIndex={0}
      onClick={onClick}
      onMouseEnter={onMouseEnter}
      onMouseLeave={onMouseLeave}
      onKeyDown={onKeyDown}
    >
      {/* Photo area */}
      <div className="aspect-[3/4] overflow-hidden bg-gradient-to-b from-gray-50 to-gray-100 relative">
        {photoUrl ? (
          <img
            ref={imgRef}
            src={photoUrl}
            alt={`${member.name} - ${member.title}`}
            className="w-full h-full object-cover object-top"
          />
        ) : (
          <div className="w-full h-full bg-gradient-to-br from-amic to-amic-700 flex items-center justify-center">
            <span className="text-white font-heading font-bold text-5xl">
              {member.name.charAt(0)}
            </span>
          </div>
        )}
      </div>

      {/* Text area */}
      <div className="p-4">
        <div className="text-lg font-heading font-semibold text-text-dark">
          {member.name}
        </div>
        <div className="text-sm text-text-secondary mt-0.5">{member.title}</div>
        <span className="inline-block mt-2 px-2 py-0.5 bg-amic-50 text-amic text-xs font-medium rounded-full">
          {member.org}
        </span>
      </div>
    </div>
  );
}
