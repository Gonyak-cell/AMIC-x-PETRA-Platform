import kimUrl from "@/assets/images/members/김양태01-removebg.png";
import parkUrl from "@/assets/images/members/박병준02-removebg.png";
import seoUrl from "@/assets/images/members/서지원01-removebg.png";
import limUrl from "@/assets/images/members/임영훈01-removebg.png";
import joUrl from "@/assets/images/members/조우상01-removebg.png";

const memberPhotos: Record<string, string> = {
  서지원: seoUrl,
  김양태: kimUrl,
  박병준: parkUrl,
  임영훈: limUrl,
  조우상: joUrl,
};

export function getMemberPhoto(name: string): string | undefined {
  return memberPhotos[name];
}
