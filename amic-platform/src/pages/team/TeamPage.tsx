import { useRef } from "react";
import { Users } from "lucide-react";
import { Card, PageHero } from "@/components/ui";
import { useScrollReveal } from "@/hooks/useScrollReveal";
import { getMemberPhoto } from "@/lib/member-photos";
import heroImg from "@/assets/images/forest-bg.jpg";


const TEAM_MEMBERS = [
  { name: "김양태", title: "대표 / 회계사" },
  { name: "임영훈", title: "변호사" },
  { name: "박병준", title: "변호사" },
  { name: "조우상", title: "이사" },
  { name: "윤태리", title: "실장" },
  { name: "서지원", title: "변호사" },
];

export default function TeamPage() {
  const membersRef = useRef<HTMLDivElement>(null);
  useScrollReveal(membersRef, { stagger: 0.07 });

  return (
    <div className="space-y-6">
      <PageHero
        title="Our Team"
        subtitle="AMIC x PETRABRIDGE PARTNERS"
        backgroundImage={heroImg}
        backgroundOpacity={0.35}
        backgroundPosition="bottom"
        compact
      />

      <div>
        <h2 className="label-uppercase mb-3">Team Members</h2>
        <Card>
          <div className="flex items-center gap-2 mb-6">
            <Users className="h-4 w-4 text-text-secondary" />
            <span className="text-sm font-medium text-text-dark">
              AMIC x PETRABRIDGE PARTNERS
            </span>
          </div>
          <div
            ref={membersRef}
            className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-6"
          >
            {TEAM_MEMBERS.map((member) => {
              const photoUrl = getMemberPhoto(member.name);
              return (
                <div key={member.name} className="flex items-center gap-4 group">
                  {photoUrl ? (
                    <img
                      src={photoUrl}
                      alt={member.name}
                      className="w-14 h-14 rounded-full object-cover ring-2 ring-amic/10 group-hover:ring-accent/40 transition-all bg-amic-100"
                    />
                  ) : (
                    <div className="w-14 h-14 rounded-full bg-gradient-to-br from-amic to-amic-700 flex items-center justify-center ring-2 ring-amic/10">
                      <span className="text-white font-semibold text-base">
                        {member.name.charAt(0)}
                      </span>
                    </div>
                  )}
                  <div>
                    <div className="text-sm font-semibold text-text-dark">
                      {member.name}
                    </div>
                    <div className="text-xs text-text-secondary mt-0.5">
                      {member.title}
                    </div>
                  </div>
                </div>
              );
            })}
          </div>
        </Card>
      </div>
    </div>
  );
}
